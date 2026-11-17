import unittest


class TranscriptTests(unittest.TestCase):
    def test_turkish_text_is_untouched(self):
        from jarvis.heard import usable_transcript

        self.assertEqual(usable_transcript("Merhaba, saat kaç şimdi?"), ("Merhaba, saat kaç şimdi?", False))

    def test_chinese_only_text_is_rejected(self):
        from jarvis.heard import usable_transcript

        self.assertEqual(usable_transcript("你好，今天天气怎么样"), ("", True))
        self.assertEqual(usable_transcript("こんにちは"), ("", True))
        self.assertEqual(usable_transcript("안녕하세요"), ("", True))
        self.assertEqual(usable_transcript("Привет как дела"), ("", True))

    def test_a_stray_foreign_character_is_only_dropped(self):
        from jarvis.heard import usable_transcript

        text, rejected = usable_transcript("müziği aç 你 lütfen şimdi hemen")
        self.assertFalse(rejected)
        self.assertNotIn("你", text)
        self.assertIn("müziği aç", text)

    def test_control_tokens_and_replacement_chars_are_removed(self):
        from jarvis.heard import usable_transcript

        self.assertEqual(usable_transcript("aç<ctrl46> beni\ufffd")[0], "aç beni")
        self.assertEqual(usable_transcript("\ufffd\x00<ctrl12>"), ("", True))

    def test_arabic_is_only_allowed_for_arabic_setting(self):
        from jarvis.heard import usable_transcript

        self.assertEqual(usable_transcript("مرحبا كيف حالك", "ar"), ("مرحبا كيف حالك", False))
        self.assertEqual(usable_transcript("مرحبا كيف حالك", "tr"), ("", True))

    def test_empty_and_whitespace(self):
        from jarvis.heard import usable_transcript

        self.assertEqual(usable_transcript(""), ("", False))
        self.assertEqual(usable_transcript("   \n "), ("", False))


class RepeatPolicyTests(unittest.TestCase):
    def test_cooldown_and_streak_limit(self):
        from jarvis.heard import RepeatPolicy

        policy = RepeatPolicy(cooldown=10, max_streak=2)
        self.assertTrue(policy.should_ask(100))
        self.assertFalse(policy.should_ask(105))
        self.assertTrue(policy.should_ask(111))
        self.assertFalse(policy.should_ask(200))  # ust uste iki kez sordu, vazgec
        policy.understood()
        self.assertTrue(policy.should_ask(300))


class StallWatchTests(unittest.TestCase):
    def talk(self, watch, start, frames=10, level=0.2):
        for i in range(frames):
            watch.voice(start + i * 0.064, level)

    def test_real_speech_without_any_reply_is_a_stall(self):
        from jarvis.heard import StallWatch

        watch = StallWatch(limit=15)
        self.talk(watch, 0)
        self.assertFalse(watch.stalled(5))
        self.assertTrue(watch.stalled(16))

    def test_a_server_reply_clears_it(self):
        from jarvis.heard import StallWatch

        watch = StallWatch(limit=15)
        self.talk(watch, 0)
        watch.server_event()
        self.assertFalse(watch.stalled(60))

    def test_short_noise_is_not_speech(self):
        from jarvis.heard import StallWatch

        watch = StallWatch(limit=15)
        self.talk(watch, 0, frames=3)  # tiktik
        self.assertFalse(watch.stalled(60))
        self.talk(watch, 100, frames=20, level=0.01)  # sessiz gurultu
        self.assertFalse(watch.stalled(200))

    def test_interrupted_run_restarts_the_count(self):
        from jarvis.heard import StallWatch

        watch = StallWatch(limit=15, min_frames=8)
        self.talk(watch, 0, frames=5)
        watch.voice(1, 0.0)
        self.talk(watch, 2, frames=5)
        self.assertFalse(watch.stalled(100))

    def test_idle_states_never_count(self):
        from jarvis.heard import StallWatch

        watch = StallWatch(limit=15)
        self.talk(watch, 0)
        self.assertFalse(watch.stalled(100, idle=True))

    def test_gives_up_after_three_unanswered_resets(self):
        from jarvis.heard import StallWatch

        watch = StallWatch(limit=15, max_trips=3)
        for round_ in range(3):
            self.talk(watch, round_ * 100)
            self.assertTrue(watch.stalled(round_ * 100 + 20))
            watch.reset()
        self.talk(watch, 400)
        self.assertFalse(watch.stalled(500))
        watch.server_event()
        self.talk(watch, 600)
        self.assertTrue(watch.stalled(620))

    def test_take_voice_reads_once(self):
        from jarvis.heard import StallWatch

        watch = StallWatch()
        self.talk(watch, 0)
        self.assertTrue(watch.take_voice())
        self.assertFalse(watch.take_voice())


class PromptRuleTests(unittest.TestCase):
    def test_every_language_mode_tells_the_model_not_to_guess(self):
        from jarvis.language import LANGUAGES, instruction

        for key in LANGUAGES:
            text = instruction({"language": key})
            self.assertIn("ANLAŞILMAYAN SES", text, key)
            self.assertIn("Çince", text, key)
        self.assertIn("Türkçe", instruction({"language": "auto"}))


class _Stop(Exception):
    pass


def _response(heard=None, spoken=None, done=False, data=None):
    from types import SimpleNamespace as NS

    content = NS(
        input_transcription=NS(text=heard) if heard is not None else None,
        output_transcription=NS(text=spoken) if spoken is not None else None,
        turn_complete=done,
    )
    return NS(data=data, server_content=content, tool_call=None)


class LiveTurnTests(unittest.TestCase):
    def run_turns(self, turns, *, voiced=True, muted=False):
        import asyncio

        from jarvis.live import JarvisLive

        logs, nudges = [], []

        class UI:
            def __init__(self):
                self.muted = muted
                self.last_heard = 0

            def write_log(self, text):
                logs.append(text)

            def set_state(self, state):
                pass

        class Session:
            def __init__(self):
                self.calls = 0

            async def receive(self):
                self.calls += 1
                if self.calls > len(turns):
                    raise _Stop()
                for item in turns[self.calls - 1]:
                    yield item

        async def nudge(text):
            nudges.append(text)

        live = JarvisLive.__new__(JarvisLive)
        live.ui, live.session = UI(), Session()
        live._paused, live._said_result, live._is_speaking = False, False, False
        live._speaking_lock = __import__("threading").Lock()
        live._nudge = nudge
        live.audio_in_queue = asyncio.Queue()
        if voiced:
            for i in range(10):
                live.stall.voice(float(i), 0.3)
        try:
            asyncio.run(live._receive_audio())
        except _Stop:
            pass
        return logs, nudges

    def test_chinese_transcript_is_hidden_and_user_is_asked_to_repeat(self):
        logs, nudges = self.run_turns([[_response(heard="你好今天天气"), _response(done=True)]])
        self.assertFalse(any("你" in line for line in logs))
        self.assertFalse(any(line.startswith("Siz:") for line in logs))
        self.assertEqual(len(nudges), 1)

    def test_normal_turn_logs_and_does_not_nudge(self):
        logs, nudges = self.run_turns([[_response(heard="saat kaç"), _response(spoken="Saat on iki."), _response(done=True)]])
        self.assertIn("Siz: saat kaç", logs)
        self.assertIn("JARVIS: Saat on iki.", logs)
        self.assertEqual(nudges, [])

    def test_voice_with_no_transcript_and_no_answer_asks_again(self):
        _, nudges = self.run_turns([[_response(done=True)]])
        self.assertEqual(len(nudges), 1)

    def test_silence_does_not_nudge(self):
        _, nudges = self.run_turns([[_response(done=True)]], voiced=False)
        self.assertEqual(nudges, [])

    def test_muted_never_nudges(self):
        _, nudges = self.run_turns([[_response(heard="你好今天天气"), _response(done=True)]], muted=True)
        self.assertEqual(nudges, [])

    def test_chinese_model_output_is_not_shown(self):
        logs, _ = self.run_turns([[_response(heard="merhaba"), _response(spoken="你好我是助手"), _response(done=True)]])
        self.assertFalse(any("你" in line for line in logs))

    def test_repeat_requests_are_rate_limited(self):
        _, nudges = self.run_turns([
            [_response(heard="你好今天天气"), _response(done=True)],
            [_response(heard="你好今天天气"), _response(done=True)],
        ])
        self.assertEqual(len(nudges), 1)


if __name__ == "__main__":
    unittest.main()
