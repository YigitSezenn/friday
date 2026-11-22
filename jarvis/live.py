from __future__ import annotations

import asyncio
import datetime
import re
import threading
import time
import traceback

from tools.actions.webcam import WebcamStreamer
from jarvis.audio.barge import peak
from jarvis.config import get_app_config_value
from jarvis.gemini_errors import RejectionBudget, classify, clean_api_key, without_proxy_for_google
from jarvis.heard import REPEAT_NOTE, MicGate, RepeatPolicy, StallWatch, usable_transcript
from jarvis.intents import is_close, is_minimize, is_sleep
from jarvis.language import current as current_language, live_speech_code, speech_codes
from jarvis.memory_store import format_memory_for_prompt, load_memory
from jarvis.prompt import load_system_prompt
from jarvis.textfix import repair_text
from tools.dispatch import TOOL_DECLARATIONS, execute_tool, looks_like_error

def current_live_model() -> str:
    from jarvis.config import LIVE_MODELS

    from jarvis.config import RETIRED_LIVE_MODELS

    chosen = str(get_app_config_value("live_model", LIVE_MODELS[0]) or LIVE_MODELS[0]).strip()
    chosen = RETIRED_LIVE_MODELS.get(chosen, chosen)
    return chosen if chosen in LIVE_MODELS else LIVE_MODELS[0]


class Reconnect(Exception):
    """Ses veya uyku değişince aynı modele yeniden bağlan."""
SEND_RATE = 16000
RECV_RATE = 24000
CHUNK = 1024
CONTROL_TOKEN_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)


class SafeStream:
    """PyAudio akışını iş parçacığı güvenli sarar.

    Yeniden bağlanmada (uyku, ayar kaydı) görevler iptal edilir ama `asyncio.to_thread` ile
    başlamış read/write iş parçacığı sürer. Akış o sırada kapatılırsa PortAudio yerel kodda
    çöker ve uygulama kapanır. Kilit: close() süren okuma/yazmanın bitmesini bekler,
    kapandıktan sonra gelen okuma/yazma sessizce atlanır.
    """

    def __init__(self, audio, stream) -> None:
        self._audio = audio
        self._stream = stream
        self._lock = threading.Lock()
        self.closed = False

    def write(self, data: bytes) -> None:
        with self._lock:
            if not self.closed:
                self._stream.write(data)

    def read(self, frames: int) -> bytes:
        with self._lock:
            if self.closed:
                return b""
            return self._stream.read(frames, exception_on_overflow=False)

    def close(self) -> None:
        with self._lock:
            if self.closed:
                return
            self.closed = True
            for step in (getattr(self._stream, "stop_stream", None), getattr(self._stream, "close", None), getattr(self._audio, "terminate", None)):
                if step is None:
                    continue
                try:
                    step()
                except Exception:
                    pass


def listening_config(patient: bool) -> dict | None:
    """Sunucu ses algılama ayarı. Gemini Live varsayılanı konuşmayı erken bitmiş sayar
    (END_SENSITIVITY_HIGH); hızlı ya da duraksayarak konuşanın cümlesi yarıda kesilir.
    Sabırlı modda konuşma başı kaçırılmaz, bitiş için kısa bir sessizlik beklenir."""
    if not patient:
        return None
    return {
        "start_of_speech_sensitivity": "START_SENSITIVITY_HIGH",
        "end_of_speech_sensitivity": "END_SENSITIVITY_LOW",
        "prefix_padding_ms": 200,
        "silence_duration_ms": 700,
    }


def queue_mic_frame(pcm: bytes, *, speaking: bool, muted: bool, paused: bool) -> dict | None:
    """V3 ile aynı: asistan konuşurken, sessizde ve durakta mikrofon modele gitmez."""
    if speaking or muted or paused or not pcm:
        return None
    return {"data": pcm, "mime_type": "audio/pcm"}


def repeated_typed_line(typed: str | None, heard: str) -> bool:
    """Yazılan satır sayfada zaten duruyor. Aynı metin mikrofon dökümünden gelirse ikinci kez yazılmaz."""
    left = str(typed or "").strip()
    right = str(heard or "").strip()
    return bool(left) and left == right


def clean_transcript(text: str) -> tuple[str, bool]:
    raw = str(text or "")
    had_noise = bool(CONTROL_TOKEN_RE.search(raw))
    raw = CONTROL_TOKEN_RE.sub(" ", raw)
    cleaned = []
    for char in raw:
        if char in "\n\r\t" or ord(char) >= 32:
            cleaned.append(char)
        else:
            had_noise = True
    return " ".join("".join(cleaned).split()).strip(), had_noise


class JarvisLive:
    def __init__(self, ui):
        self.ui = ui
        self.session = None
        self.audio_in_queue = None
        self.out_queue = None
        self._loop = None
        self._is_speaking = False
        self._speaking_lock = threading.Lock()
        self._paused = False
        self._typed = None
        self._said_result = False
        self._text_only = False
        self._reconnect = None
        self.webcam = WebcamStreamer()
        ui.on_text_command = self._on_text_command
        ui.on_pause_toggle = self._on_pause_toggle
        ui.speak_note = self.nudge
        ui.on_webcam_toggle = self._on_webcam_toggle
        ui.on_settings_saved = self.request_reconnect

    @property
    def rejections(self) -> RejectionBudget:
        budget = self.__dict__.get("_rejections")
        if budget is None:
            budget = self.__dict__["_rejections"] = RejectionBudget()
        return budget

    @property
    def stall(self) -> StallWatch:
        return self.__dict__.setdefault("_stall", StallWatch())

    @property
    def repeat(self) -> RepeatPolicy:
        return self.__dict__.setdefault("_repeat", RepeatPolicy())

    def request_reconnect(self) -> None:
        loop = self._loop
        event = self._reconnect
        if loop and event and loop.is_running():
            loop.call_soon_threadsafe(event.set)

    def _on_pause_toggle(self, paused: bool) -> None:
        self._paused = paused
        self.rejections.reset()
        self.request_reconnect()

    def _on_webcam_toggle(self, activate: bool) -> None:
        if activate:
            status = self.webcam.start()
            self.ui.set_webcam_active(status in {"ok", "already_active"})
            if status == "missing":
                self.ui.write_log("ERR: Kamera açılamadı.")
        else:
            self.webcam.stop()
            self.ui.set_webcam_active(False)

    def _on_text_command(self, text: str) -> None:
        self.rejections.reset()
        if self._paused:
            return
        text = repair_text(str(text or "")).strip()
        if not text:
            return
        # Sayfa bu satırı kendisi çizer. Buradan tekrar "Siz:" basmak hem
        # dökümü ikiye çıkarır hem de API geri çağrısının içinde evaluate_js
        # çalıştırır; numara gibi bir metin o scripti düşürüp süreci çökertiyordu.
        self._typed = text
        if not self._loop or not self.session:
            self.ui.write_log("ERR: JARVIS bağlantısı henüz hazır değil.")
            return
        from tools.actions import confirm as _confirm
        _confirm.note_user_said(text)
        asyncio.run_coroutine_threadsafe(self._send_text(text), self._loop)

    async def _send_text(self, text: str) -> None:
        await self._send_user_text(text)

    async def _send_user_text(self, text: str) -> None:
        """3.x canlı modeller oturum ortasında send_client_content'i 1007 ile kapatır
        (S-022'de yeniden üretildi). Metin yalnızca send_realtime_input(text=) ile gider;
        eski yola düşmek oturumu kopardığı için geri dönüş yok."""
        try:
            await self.session.send_realtime_input(text=text)
        except TypeError:
            self.ui.write_log("ERR: Yazılı mesaj gönderilemedi: Gemini kütüphanesi eski. FRIDAY'i güncelle.")

    def set_speaking(self, value: bool) -> None:
        with self._speaking_lock:
            self._is_speaking = value
        self.ui.set_state("SPEAKING" if value else "LISTENING")

    def _build_config(self):
        from google.genai import types

        memory = format_memory_for_prompt(load_memory())
        now = datetime.datetime.now().strftime("%A, %d %B %Y — %H:%M")
        parts = [f"[ŞU ANKİ ZAMAN]\n{now}\n\n"]
        if memory:
            parts.append(memory + "\n\n")
        parts.append(load_system_prompt())
        voice = str(get_app_config_value("voice", "Charon") or "Charon")
        model = current_live_model()
        code = live_speech_code(model)
        if code is None:
            heard = types.AudioTranscriptionConfig()
            spoken = types.AudioTranscriptionConfig()
        else:
            heard = types.AudioTranscriptionConfig(language_codes=speech_codes())
            spoken = types.AudioTranscriptionConfig(language_codes=speech_codes())
        speech = types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
            )
        )
        if code:
            speech.language_code = code
        extra = {}
        listening = listening_config(bool(get_app_config_value("patient_listening", True)))
        if listening:
            extra["realtime_input_config"] = types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(**listening)
            )
        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription=spoken,
            input_audio_transcription=heard,
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
            speech_config=speech,
            **extra,
        )

    async def _execute(self, function_call):
        from google.genai import types

        name = function_call.name
        args = dict(function_call.args or {})
        self.ui.set_state("THINKING")
        try:
            result = await asyncio.to_thread(execute_tool, name, args, self.webcam, self.ui)
        except Exception as exc:
            result = f"Hata: {exc}"
            from jarvis.shown import tool_label

            self.ui.write_log(f"ERR: {tool_label(name)} tamamlanamadı. ({exc})")
            traceback.print_exc()
        if looks_like_error(result):
            self.ui.set_state("ERROR")
            from jarvis.shown import for_screen

            text = for_screen(result)
            shown = text if len(text) <= 240 else text[:70] + " … " + text[-140:]
            from jarvis.shown import tool_label

            self.ui.write_log(f"ERR: {tool_label(name)}: {shown}")
        else:
            from jarvis.shown import for_screen

            shown = for_screen(result)
            # Sesli yanıt zaten söylüyor; basit eylemlerin "açıldı" satırı ikinci kez yazılmaz.
            if name in {"open_app", "browser_control", "play_media", "control_media", "set_volume", "desktop_action", "app_window"}:
                shown = ""
            if shown:
                self.ui.write_log(f"JARVIS: {shown}")
                self._said_result = True
            if name in {"open_app", "add_calendar_event", "add_reminder", "delete_calendar_event"}:
                self.ui.play_success_sfx()
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
        return types.FunctionResponse(id=function_call.id, name=name, response={"result": result})

    async def _send_realtime(self) -> None:
        while True:
            message = await self.out_queue.get()
            mime = str(message.get("mime_type") or "")
            if mime.startswith("image/"):
                await self._send_media(message["data"], mime)
                continue
            await self._send_audio(message["data"])

    async def _send_audio(self, data: bytes) -> None:
        """`media=` kullanımdan kalktı ve 3.x canlı modellerde bağlantıyı 1007 ile düşürür;
        mikrofon sesi `audio=` Blob'u ve açık örnekleme hızıyla gider."""
        from google.genai import types

        try:
            await self.session.send_realtime_input(audio=types.Blob(data=data, mime_type=f"audio/pcm;rate={SEND_RATE}"))
        except TypeError:
            await self.session.send_realtime_input(media={"data": data, "mime_type": "audio/pcm"})

    async def _send_media(self, data: bytes, mime: str) -> None:
        from google.genai import types

        blob = types.Blob(data=data, mime_type=mime)
        try:
            if mime.startswith("image/"):
                await self.session.send_realtime_input(video=blob)
            else:
                await self.session.send_realtime_input(audio=blob)
        except TypeError:
            await self.session.send_realtime_input(media={"data": data, "mime_type": mime})

    async def _listen_audio(self) -> None:
        import pyaudio

        audio = pyaudio.PyAudio()
        try:
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=SEND_RATE,
                input=True,
                frames_per_buffer=CHUNK,
            )
        except Exception as exc:
            self._text_only = True
            self.ui.write_log(f"ERR: Mikrofon açılamadı, yazı ile devam edebilirsin. ({exc})")
            audio.terminate()
            while True:
                await asyncio.sleep(0.2)
                from jarvis.phone_server import take_phone_audio

                frame = queue_mic_frame(
                    take_phone_audio() or b"",
                    speaking=self._is_speaking,
                    muted=bool(self.ui.muted),
                    paused=bool(self._paused),
                )
                if frame:
                    await self.out_queue.put(frame)
        mic = SafeStream(audio, stream)
        gate = MicGate()
        try:
            while True:
                data = await asyncio.to_thread(mic.read, CHUNK)
                if mic.closed:
                    break
                with self._speaking_lock:
                    speaking = self._is_speaking
                from jarvis.phone_server import take_phone_audio

                if bool(get_app_config_value("mic_gate", True)) and not gate.passes(peak(data)):
                    data = bytes(len(data))  # sessizlik: sunucu cümlenin bittiğini görsün
                for pcm in (data, take_phone_audio() or b""):
                    frame = queue_mic_frame(
                        pcm,
                        speaking=speaking,
                        muted=bool(self.ui.muted),
                        paused=bool(self._paused),
                    )
                    if frame:
                        self.stall.voice(time.monotonic(), peak(pcm))
                        await self.out_queue.put(frame)
        finally:
            mic.close()

    async def _wait_for_clap(self) -> None:
        """Uykudayken (kullanıcı izin verdiyse) yalnızca ses seviyesine bakar; çift alkışta uyandırır."""
        import pyaudio
        from jarvis.audio.clap import ClapDetector

        audio = pyaudio.PyAudio()
        try:
            stream = audio.open(format=pyaudio.paInt16, channels=1, rate=SEND_RATE, input=True, frames_per_buffer=CHUNK)
        except Exception:
            audio.terminate()
            await asyncio.sleep(2)
            return
        mic = SafeStream(audio, stream)
        detector = ClapDetector()
        try:
            while self._paused and bool(get_app_config_value("clap_wake", False)):
                data = await asyncio.to_thread(mic.read, CHUNK)
                if mic.closed:
                    break
                if detector.feed(peak(data), time.monotonic()) and hasattr(self.ui, "_js"):
                    self.ui._js("window.hud && window.hud.sleep(false, 0)")
                    await asyncio.sleep(0.5)
        finally:
            mic.close()

    async def _receive_audio(self) -> None:
        out_buf, in_buf = [], []
        output_noise = False
        misheard = False
        got_audio = False
        idle_rounds = 0
        while True:
            produced = False
            async for response in self.session.receive():
                produced = True
                self.stall.server_event()
                if response.data:
                    got_audio = True
                    self.audio_in_queue.put_nowait(response.data)
                content = response.server_content
                if content:
                    if content.output_transcription and content.output_transcription.text:
                        self.set_speaking(True)
                        text, noisy = clean_transcript(content.output_transcription.text)
                        text, rejected = usable_transcript(text, current_language())
                        output_noise = output_noise or noisy or rejected
                        if text:
                            out_buf.append(text)
                    if content.input_transcription and content.input_transcription.text:
                        heard, rejected = usable_transcript(content.input_transcription.text, current_language())
                        misheard = misheard or rejected
                        if heard:
                            in_buf.append(heard)
                            from tools.actions import confirm as _confirm
                            _confirm.note_user_said(heard)
                            self.ui.last_heard = time.time()
                    if content.turn_complete:
                        self.set_speaking(False)
                        heard = repair_text(" ".join(in_buf).strip())
                        if heard and not repeated_typed_line(getattr(self, "_typed", None), heard):
                            self.ui.write_log(f"Siz: {heard}")
                        if heard and is_sleep(heard) and hasattr(self.ui, "_js"):
                            self.ui._js("window.hud && window.hud.sleep(true, 2500)")
                        if heard and is_minimize(heard) and hasattr(self.ui, "minimize_to_taskbar"):
                            threading.Timer(1.5, self.ui.minimize_to_taskbar).start()
                        elif heard and is_close(heard) and hasattr(self.ui, "quit_app"):
                            threading.Timer(3.5, self.ui.quit_app).start()  # önce vedalaşma cümlesi söylensin
                        if repeated_typed_line(getattr(self, "_typed", None), heard):
                            self._typed = None
                        spoken = repair_text(" ".join(out_buf).strip())
                        if spoken and not self._said_result:
                            self.ui.write_log(f"JARVIS: {spoken}")
                        elif output_noise and not self._said_result:
                            self.ui.write_log("ERR: JARVIS sesli yanıtını çözümlerken bir hata oluştu.")
                            self.ui.set_state("ERROR")
                        await self._after_turn(bool(heard), bool(spoken) or got_audio, misheard)
                        in_buf, out_buf, output_noise = [], [], False
                        misheard = got_audio = False
                        self._said_result = False
                if response.tool_call:
                    responses = []
                    for function_call in response.tool_call.function_calls:
                        responses.append(await self._execute(function_call))
                    await self.session.send_tool_response(function_responses=responses)
            # receive() hiç yanıt vermeden bittiyse oturum kopmuştur. Boşa dönüp olay döngüsünü kilitlemek yerine yeniden bağlan.
            if produced:
                idle_rounds = 0
                continue
            idle_rounds += 1
            if idle_rounds >= 3:
                raise Reconnect()
            await asyncio.sleep(0.2)

    async def _after_turn(self, heard: bool, answered: bool, misheard: bool) -> None:
        """Konuştun ama model yanıt vermediyse ya da döküm bozuksa, tahmin ettirmeden tekrar iste."""
        voiced = self.stall.take_voice()
        if answered or self._said_result:
            self.repeat.understood()
            return
        if not (misheard or (voiced and not heard)):
            return
        if self.ui.muted or self._paused or not self.repeat.should_ask(time.monotonic()):
            return
        await self._nudge(REPEAT_NOTE)

    async def _watch_stall(self) -> None:
        """Konuşuldu ama yanıt hiç gelmediyse bağlantıyı yenile; yoksa uygulama sonsuza dek dinliyor görünür."""
        while True:
            await asyncio.sleep(1)
            idle = bool(self._is_speaking or self.ui.muted or self._paused)
            if self.stall.stalled(time.monotonic(), idle=idle):
                self.stall.reset()
                self.ui.write_log("SYS: Yanıt gelmedi, bağlantı yenileniyor.")
                if self._reconnect is not None:
                    self._reconnect.set()

    async def _play_audio(self) -> None:
        import pyaudio

        audio = pyaudio.PyAudio()
        try:
            stream = audio.open(format=pyaudio.paInt16, channels=1, rate=RECV_RATE, output=True)
        except Exception as exc:
            self.ui.write_log(f"ERR: Hoparlör açılamadı. ({exc})")
            audio.terminate()
            while True:
                await self.audio_in_queue.get()
        speaker = SafeStream(audio, stream)
        try:
            while True:
                chunk = await self.audio_in_queue.get()
                self.set_speaking(True)
                heard = self._scale_output(chunk)
                from jarvis.phone_server import publish_speaker

                publish_speaker(heard)
                await asyncio.to_thread(speaker.write, heard)
                if self.audio_in_queue.empty():
                    self.set_speaking(False)
        finally:
            self.set_speaking(False)
            speaker.close()

    def _scale_output(self, chunk: bytes) -> bytes:
        level = int(get_app_config_value("voice_volume", 100) or 100)
        level = max(0, min(150, level))
        factor = level / 100
        if factor == 1 or not chunk:
            return chunk
        import array

        samples = array.array("h")
        usable = chunk[: len(chunk) // 2 * 2]
        samples.frombytes(usable)
        for index, sample in enumerate(samples):
            samples[index] = max(-32768, min(32767, int(sample * factor)))
        return samples.tobytes()

    async def _stream_webcam(self) -> None:
        last = None
        while True:
            if not self.webcam.is_active:
                await asyncio.sleep(0.2)
                continue
            frame = self.webcam.get_latest_frame()
            if not frame or frame is last:
                await asyncio.sleep(0.2)
                continue
            last = frame
            try:
                await self._send_media(frame, "image/jpeg")
            except Exception as exc:
                self.ui.write_log(f"ERR: Kamera karesi gönderilemedi. ({exc})")
            await asyncio.sleep(0.5)

    async def _preview_webcam(self) -> None:
        while True:
            if self.webcam.is_active:
                frame = self.webcam.get_latest_frame()
                if frame:
                    self.ui.update_webcam_preview(frame)
            await asyncio.sleep(1 / 12)

    async def run(self) -> None:
        from google import genai

        attempts = 0
        quiet_streak = 0
        without_proxy_for_google()
        while True:
            if self._paused:
                if bool(get_app_config_value("clap_wake", False)):
                    await self._wait_for_clap()
                else:
                    await asyncio.sleep(0.4)
                continue
            key = clean_api_key(get_app_config_value("gemini_api_key", ""))
            if not key:
                self.ui.set_state("ERROR")
                if not getattr(self, "_missing_key_logged", False):
                    self.ui.write_log("ERR: Gemini API anahtarı yok. Ayarlardan kaydet.")
                    self._missing_key_logged = True
                await asyncio.sleep(2)
                continue
            self._missing_key_logged = False
            if self.rejections.should_wait(key):
                self.ui.set_state("ERROR")
                await asyncio.sleep(1)
                continue
            if self._reconnect is None:
                self._reconnect = asyncio.Event()
            try:
                client = genai.Client(api_key=key, http_options={"api_version": "v1alpha"})
                self.ui.set_state("THINKING")
                config = self._build_config()
                self._reconnect.clear()
                async with client.aio.live.connect(model=current_live_model(), config=config) as session, asyncio.TaskGroup() as group:
                    self.session = session
                    from tools.actions import confirm as _confirm
                    _confirm.require_user_yes = True
                    self._loop = asyncio.get_running_loop()
                    self.audio_in_queue = asyncio.Queue()
                    self.out_queue = asyncio.Queue(maxsize=8)
                    attempts = 0
                    quiet_streak = 0
                    self.rejections.success()
                    self.ui.set_state("LISTENING")
                    if not getattr(self, "_ready_announced", False):
                        self._ready_announced = True
                        self.ui.write_log("SYS: Her şey çalıştı. FRIDAY ayakta.")
                    group.create_task(self._send_realtime())
                    group.create_task(self._listen_audio())
                    group.create_task(self._receive_audio())
                    group.create_task(self._play_audio())
                    group.create_task(self._stream_webcam())
                    group.create_task(self._preview_webcam())
                    group.create_task(self._watch_reconnect())
                    group.create_task(self._watch_stall())
                self.session = None
            except Reconnect:
                self.session = None
                self.set_speaking(False)
                if not self._paused:
                    self.ui.write_log("SYS: Ses ayarı uygulandı, yeniden bağlanıyor.")
                continue
            except Exception as exc:
                self.session = None
                if _reconnect_error(exc):
                    self.set_speaking(False)
                    if not self._paused:
                        self.ui.write_log("SYS: Ses ayarı uygulandı, yeniden bağlanıyor.")
                    continue
                from jarvis.gemini_errors import classify as _classify

                if _classify(exc, key).quiet:
                    # Boşta kalma: hata değil. Ekrana kırmızı yazı çıkarmadan yeniden bağlan.
                    self.set_speaking(False)
                    self.ui.set_state("THINKING")
                    quiet_streak += 1
                    if quiet_streak == 4:
                        # Üst üste kopuyorsa kullanıcı bilsin: tek seferlik, kırmızı olmayan bilgi.
                        self.ui.write_log("SYS: Bağlantı kararsız görünüyor; internetini kontrol et, yeniden denemeye devam ediyorum.")
                    await asyncio.sleep(min(0.5 * quiet_streak, 5))
                    continue
                traceback.print_exc()
                _log_error(exc, key)
                self.set_speaking(False)
                if self.webcam.is_active:
                    self.webcam.stop()
                    self.ui.set_webcam_active(False)
                attempts += 1
                self.ui.set_state("ERROR")
                issue = classify(exc, key)
                self.rejections.note(issue, key)
                message = issue.message
                if self.rejections.should_wait(key) and issue.rejection:
                    message += " Yeniden denemek için bir şey yaz, mikrofona bas ya da anahtarı değiştir."
                if message != getattr(self, "_last_connect_error", ""):
                    self._last_connect_error = message
                    self.ui.write_log(message)
                await asyncio.sleep(2 if attempts <= 3 else 5)

    def nudge(self, text: str) -> None:
        loop = getattr(self, "_loop", None)
        if loop is None or self.session is None or self._paused:
            return
        asyncio.run_coroutine_threadsafe(self._nudge(text), loop)

    async def _nudge(self, text: str) -> None:
        if self.session is None:
            return
        try:
            await self._send_user_text(f"[Sistem notu, sesli ve kısa söyle] {text}")
        except Exception:
            pass  # oturum o anda kapanıyorsa sessizce vazgeç

    async def _watch_reconnect(self) -> None:
        await self._reconnect.wait()
        raise Reconnect()


def _log_error(exc: BaseException, key: str) -> None:
    """Bağlantı hatalarını data/logs/live-errors.log'a yazar (anahtar silinir, 256 KB'de döner)."""
    try:
        from jarvis.paths import data_path

        path = data_path("logs", "live-errors.log")
        if path.exists() and path.stat().st_size > 256 * 1024:
            path.replace(path.with_suffix(".log.1"))
        text = "".join(traceback.format_exception(exc))
        secret = str(key or "").strip()
        if secret:
            text = text.replace(secret, "***")
        stamp = datetime.datetime.now().isoformat(timespec="seconds")
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"--- {stamp} model={current_live_model()}\n{text}\n")
    except Exception:
        pass


def _reconnect_error(exc: BaseException) -> bool:
    if isinstance(exc, Reconnect):
        return True
    nested = getattr(exc, "exceptions", None)
    return bool(nested) and any(_reconnect_error(item) for item in nested)
