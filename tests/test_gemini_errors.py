import os
import tempfile
import unittest


class GeminiErrorTests(unittest.TestCase):
    def test_clean_api_key_drops_whitespace_and_quotes(self):
        from jarvis.gemini_errors import clean_api_key

        self.assertEqual(clean_api_key('  "AIza ab\r\ncd"\n'), "AIzaabcd")
        self.assertEqual(clean_api_key(None), "")

    def test_denied_access_is_closed_and_not_retried(self):
        from jarvis.gemini_errors import classify

        issue = classify(Exception("1008 (policy violation): Your project has been denied access."))
        self.assertEqual(issue.code, "ERİŞİM KAPALI")
        self.assertFalse(issue.retry)
        self.assertTrue(issue.rejection)

    def test_free_tier_and_credits_have_their_own_labels(self):
        from jarvis.gemini_errors import classify

        free = classify(Exception("1008: The Gemini API free tier is not available for this project"))
        self.assertEqual(free.code, "ERİŞİM KAPALI")
        credits = classify(Exception("1011: Your prepayment credits are depleted"))
        self.assertEqual(credits.code, "KREDİ BİTTİ")
        self.assertFalse(credits.retry)

    def test_network_causes_are_named(self):
        from jarvis.gemini_errors import classify

        self.assertEqual(classify(Exception("SSL: CERTIFICATE_VERIFY_FAILED")).code, "SSL SORUNU")
        self.assertEqual(classify(Exception("Invalid port: 'x'")).code, "PROXY SORUNU")
        self.assertEqual(classify(Exception("getaddrinfo failed")).code, "GOOGLE'A ULAŞILAMIYOR")

    def test_key_is_never_echoed(self):
        from jarvis.gemini_errors import classify

        issue = classify(Exception("boom AIzaSECRET failed"), "AIzaSECRET")
        self.assertNotIn("AIzaSECRET", issue.message)

    def test_nested_exception_group_is_read(self):
        from jarvis.gemini_errors import classify

        inner = Exception("prepayment credits are depleted")
        group = ExceptionGroup("tg", [inner])
        self.assertEqual(classify(group).code, "KREDİ BİTTİ")

    def test_budget_stops_after_twenty_rejections_until_key_changes(self):
        from jarvis.gemini_errors import ConnectIssue, RejectionBudget

        budget = RejectionBudget(limit=20)
        issue = ConnectIssue("X", "x", retry=True, rejection=True)
        for _ in range(19):
            budget.note(issue, "k1")
        self.assertFalse(budget.should_wait("k1"))
        budget.note(issue, "k1")
        self.assertTrue(budget.should_wait("k1"))
        self.assertFalse(budget.should_wait("k2"))
        self.assertFalse(budget.should_wait("k1"))

    def test_budget_reset_by_user_action_and_plain_errors_clear_count(self):
        from jarvis.gemini_errors import ConnectIssue, RejectionBudget

        budget = RejectionBudget(limit=2)
        reject = ConnectIssue("X", "x", rejection=True)
        budget.note(reject, "k")
        budget.note(reject, "k")
        self.assertTrue(budget.should_wait("k"))
        budget.reset()
        self.assertFalse(budget.should_wait("k"))
        budget.note(reject, "k")
        budget.note(ConnectIssue("Y", "y"), "k")
        self.assertEqual(budget.count, 0)

    def test_google_hosts_bypass_proxy(self):
        from jarvis.gemini_errors import without_proxy_for_google

        saved = {k: os.environ.pop(k, None) for k in ("NO_PROXY", "no_proxy")}
        try:
            without_proxy_for_google()
            self.assertIn("googleapis.com", os.environ["NO_PROXY"])
            without_proxy_for_google()
            self.assertEqual(os.environ["NO_PROXY"].count("generativelanguage"), 1)
        finally:
            for k in ("NO_PROXY", "no_proxy"):
                os.environ.pop(k, None)
                if saved[k] is not None:
                    os.environ[k] = saved[k]


class LocationToolTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["JARVIS_DATA_DIR"] = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def test_location_is_saved_and_can_go_back_to_auto(self):
        from jarvis.config import get_app_config_value
        from tools.dispatch import execute_tool

        self.assertIn("Izmir", execute_tool("set_location", {"location": "Izmir"}))
        self.assertEqual(get_app_config_value("weather_location"), "Izmir")
        self.assertIn("otomatik", execute_tool("set_location", {"auto": True}))
        self.assertEqual(get_app_config_value("weather_location"), "")

    def test_empty_or_huge_location_is_rejected(self):
        from tools.dispatch import execute_tool

        self.assertIn("geçersiz", execute_tool("set_location", {"location": "  "}))
        self.assertIn("geçersiz", execute_tool("set_location", {"location": "x" * 200}))

    def test_saved_key_is_cleaned(self):
        from jarvis.config import get_app_config_value, save_app_config

        save_app_config({"gemini_api_key": " AIza\nabc "})
        self.assertEqual(get_app_config_value("gemini_api_key"), "AIzaabc")


if __name__ == "__main__":
    unittest.main()


class IdleTimeoutTests(unittest.TestCase):
    def test_client_inactivity_is_quiet_reconnect(self):
        from jarvis.gemini_errors import RejectionBudget, classify

        text = "(unhandled errors in a TaskGroup (1 sub-exception)) 1008 None. Session closed due to client inactivity. received 1008 (policy violation) Session closed due to client inactivity."
        issue = classify(Exception(text), "anahtar")
        self.assertTrue(issue.quiet)
        self.assertFalse(issue.rejection)
        budget = RejectionBudget()
        budget.note(issue, "anahtar")
        self.assertFalse(budget.should_wait("anahtar"))

    def test_real_denied_access_still_blocks(self):
        from jarvis.gemini_errors import classify

        issue = classify(Exception("1008 (policy violation): Your project has been denied access."))
        self.assertFalse(issue.quiet)
        self.assertTrue(issue.rejection)


class SleepGuardTests(unittest.TestCase):
    def test_model_cannot_sleep_on_its_own(self):
        from tools import handlers
        from tools.actions import confirm

        class Ctx:
            class ui:
                calls = []
                @staticmethod
                def _js(s): Ctx.ui.calls.append(s)
        confirm._said.clear()
        out = handlers.sleep_mode({"asleep": True}, Ctx)
        self.assertIn("yalnızca kullanıcı", out)
        self.assertEqual(Ctx.ui.calls, [])
        confirm.note_user_said("friday uyu")
        handlers.sleep_mode({"asleep": True}, Ctx)
        self.assertTrue(Ctx.ui.calls)


class AbnormalClosureTests(unittest.TestCase):
    def test_1006_is_quiet_reconnect(self):
        from jarvis.gemini_errors import classify

        issue = classify(Exception("(unhandled errors in a TaskGroup (1 sub-exception)) 1006 None. abnormal closure [internal] no close frame received or sent"), "k")
        self.assertTrue(issue.quiet)
        self.assertFalse(issue.rejection)
        self.assertTrue(issue.retry)

    def test_other_errors_stay_loud(self):
        from jarvis.gemini_errors import classify

        self.assertFalse(classify(Exception("getaddrinfo failed"), "k").quiet)
        self.assertFalse(classify(Exception("1008 denied access"), "k").quiet)
        self.assertFalse(classify(Exception("durum 11006 tutarı"), "k").quiet)
