from __future__ import annotations

import asyncio
import datetime
import re
import threading
import traceback

from tools.actions.webcam import WebcamStreamer
from jarvis.config import get_app_config_value
from jarvis.language import live_speech_code, speech_codes
from jarvis.memory_store import format_memory_for_prompt, load_memory
from jarvis.prompt import load_system_prompt
from jarvis.textfix import repair_text
from tools.dispatch import TOOL_DECLARATIONS, execute_tool, looks_like_error

def current_live_model() -> str:
    from jarvis.config import LIVE_MODELS

    chosen = str(get_app_config_value("live_model", LIVE_MODELS[0]) or LIVE_MODELS[0]).strip()
    return chosen if chosen in LIVE_MODELS else LIVE_MODELS[0]


class Reconnect(Exception):
    """Ses veya uyku değişince aynı modele yeniden bağlan."""
SEND_RATE = 16000
RECV_RATE = 24000
CHUNK = 1024
CONTROL_TOKEN_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)


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
        ui.on_webcam_toggle = self._on_webcam_toggle
        ui.on_settings_saved = self.request_reconnect

    def request_reconnect(self) -> None:
        loop = self._loop
        event = self._reconnect
        if loop and event and loop.is_running():
            loop.call_soon_threadsafe(event.set)

    def _on_pause_toggle(self, paused: bool) -> None:
        self._paused = paused
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
        asyncio.run_coroutine_threadsafe(self._send_text(text), self._loop)

    async def _send_text(self, text: str) -> None:
        await self.session.send_client_content(turns={"parts": [{"text": text}]}, turn_complete=True)

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
        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription=spoken,
            input_audio_transcription=heard,
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
            speech_config=speech,
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
            self.ui.write_log(f"ERR: {name} — {exc}")
            traceback.print_exc()
        if looks_like_error(result):
            self.ui.set_state("ERROR")
            text = repair_text(str(result))
            shown = text if len(text) <= 240 else text[:70] + " … " + text[-140:]
            self.ui.write_log(f"ERR: {name} — {shown}")
        else:
            shown = repair_text(str(result or "")).strip()
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
            await self._send_media(message["data"], message["mime_type"])

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
        from jarvis.audio.capture import CaptureFilter, aec_wanted, chunks_for_model

        self._capture = CaptureFilter()
        echo = False
        stream = None
        audio = None
        if aec_wanted():
            from jarvis.audio.win_aec import open_dsp_mic

            stream = await asyncio.to_thread(open_dsp_mic)
            echo = stream is not None
            if stream is None:
                self.ui.write_log("Yankı engelleme açılamadı, düz mikrofon kullanılıyor.")
        if stream is None:
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

                    phone_pcm = take_phone_audio()
                    if not phone_pcm or self.ui.muted or self._paused:
                        continue
                    for part in chunks_for_model(phone_pcm, speaking=False, echo_cancelled=False, filt=self._capture):
                        await self.out_queue.put({"data": part, "mime_type": f"audio/pcm;rate={SEND_RATE}"})
        elif echo:
            self.ui.write_log("Yankı engelleme açık.")
        try:
            while True:
                data = await asyncio.to_thread(stream.read, CHUNK, exception_on_overflow=False)
                with self._speaking_lock:
                    speaking = self._is_speaking
                if self.ui.muted or self._paused:
                    continue
                from jarvis.phone_server import take_phone_audio

                phone_pcm = take_phone_audio()
                frames = [(data, speaking, echo)]
                if phone_pcm:
                    frames.append((phone_pcm, False, False))
                for frame, frame_speaking, frame_echo in frames:
                    for part in chunks_for_model(frame, speaking=frame_speaking, echo_cancelled=frame_echo, filt=self._capture):
                        if self.out_queue.full():
                            try:
                                self.out_queue.get_nowait()
                            except asyncio.QueueEmpty:
                                pass
                        await self.out_queue.put({"data": part, "mime_type": f"audio/pcm;rate={SEND_RATE}"})
        finally:
            close = getattr(stream, "close", None)
            if close:
                close()
            if audio is not None:
                audio.terminate()

    async def _receive_audio(self) -> None:
        out_buf, in_buf = [], []
        output_noise = False
        while True:
            async for response in self.session.receive():
                if response.data:
                    self.audio_in_queue.put_nowait(response.data)
                content = response.server_content
                if content:
                    if content.output_transcription and content.output_transcription.text:
                        self.set_speaking(True)
                        text, noisy = clean_transcript(content.output_transcription.text)
                        output_noise = output_noise or noisy
                        if text:
                            out_buf.append(text)
                    if content.input_transcription and content.input_transcription.text:
                        heard = content.input_transcription.text.strip()
                        if heard:
                            in_buf.append(heard)
                            self.ui.last_heard = __import__("time").time()
                    if content.turn_complete:
                        self.set_speaking(False)
                        heard = repair_text(" ".join(in_buf).strip())
                        if heard and not repeated_typed_line(getattr(self, "_typed", None), heard):
                            self.ui.write_log(f"Siz: {heard}")
                        if repeated_typed_line(getattr(self, "_typed", None), heard):
                            self._typed = None
                        spoken = repair_text(" ".join(out_buf).strip())
                        if spoken and not self._said_result:
                            self.ui.write_log(f"JARVIS: {spoken}")
                        elif output_noise and not self._said_result:
                            self.ui.write_log("ERR: JARVIS sesli yanitini cozumlerken bir hata olustu.")
                            self.ui.set_state("ERROR")
                        in_buf, out_buf, output_noise = [], [], False
                        self._said_result = False
                if response.tool_call:
                    responses = []
                    for function_call in response.tool_call.function_calls:
                        responses.append(await self._execute(function_call))
                    await self.session.send_tool_response(function_responses=responses)

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
        try:
            while True:
                chunk = await self.audio_in_queue.get()
                self.set_speaking(True)
                heard = self._scale_output(chunk)
                capture = getattr(self, "_capture", None)
                if capture is not None:
                    capture.note_playback(heard)
                from jarvis.phone_server import publish_speaker

                publish_speaker(heard)
                await asyncio.to_thread(stream.write, heard)
                if self.audio_in_queue.empty():
                    self.set_speaking(False)
        finally:
            self.set_speaking(False)
            stream.close()
            audio.terminate()

    def _scale_output(self, chunk: bytes) -> bytes:
        level = int(get_app_config_value("voice_volume", 100) or 100)
        level = max(0, min(150, level))
        factor = level / 100
        capture = getattr(self, "_capture", None)
        if capture is not None and capture.ducked:
            factor *= 0.35
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
                self.ui.write_log(f"ERR: Kamera karesi gonderilemedi. ({exc})")
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
        while True:
            if self._paused:
                await asyncio.sleep(0.4)
                continue
            key = str(get_app_config_value("gemini_api_key", "") or "").strip()
            if not key:
                self.ui.set_state("ERROR")
                if not getattr(self, "_missing_key_logged", False):
                    self.ui.write_log("ERR: Gemini API anahtarı yok. Ayarlardan kaydet.")
                    self._missing_key_logged = True
                await asyncio.sleep(2)
                continue
            self._missing_key_logged = False
            if self._reconnect is None:
                self._reconnect = asyncio.Event()
            try:
                client = genai.Client(api_key=key, http_options={"api_version": "v1alpha"})
                self.ui.set_state("THINKING")
                config = self._build_config()
                self._reconnect.clear()
                async with client.aio.live.connect(model=current_live_model(), config=config) as session, asyncio.TaskGroup() as group:
                    self.session = session
                    self._loop = asyncio.get_running_loop()
                    self.audio_in_queue = asyncio.Queue()
                    self.out_queue = asyncio.Queue(maxsize=8)
                    attempts = 0
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
            except Reconnect:
                self.set_speaking(False)
                if not self._paused:
                    self.ui.write_log("SYS: Ses ayari uygulandi, yeniden baglaniyor.")
                continue
            except Exception as exc:
                if _reconnect_error(exc):
                    self.set_speaking(False)
                    if not self._paused:
                        self.ui.write_log("SYS: Ses ayari uygulandi, yeniden baglaniyor.")
                    continue
                traceback.print_exc()
                self.set_speaking(False)
                if self.webcam.is_active:
                    self.webcam.stop()
                    self.ui.set_webcam_active(False)
                attempts += 1
                self.ui.set_state("ERROR")
                message = _public_connect_error(exc, key)
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
        from google.genai import types

        await self.session.send_client_content(
            turns=types.Content(role="user", parts=[types.Part(text=f"[Sistem notu, sesli ve kisa soyle] {text}")]),
            turn_complete=True,
        )

    async def _watch_reconnect(self) -> None:
        await self._reconnect.wait()
        raise Reconnect()


def _public_connect_error(exc: BaseException, key: str) -> str:
    detail = str(exc)
    secret = str(key or "").strip()
    if secret:
        detail = detail.replace(secret, "")
    detail = " ".join(detail.split())
    if len(detail) > 160:
        detail = detail[:160] + "…"
    return f"ERR: Bağlantı koptu. API anahtarını ve interneti kontrol et. ({detail})"


def _reconnect_error(exc: BaseException) -> bool:
    if isinstance(exc, Reconnect):
        return True
    nested = getattr(exc, "exceptions", None)
    return bool(nested) and any(_reconnect_error(item) for item in nested)
