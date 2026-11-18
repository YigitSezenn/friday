import json
import os
import tempfile
import unittest
from unittest import mock

from tools.actions import confirm


class ConfirmGateTest(unittest.TestCase):
    def setUp(self):
        confirm._pending.clear()

    def test_requires_prior_ask_and_wait(self):
        parts = ("a@b.co", "s", "b")
        self.assertIn("ONAY", confirm.check("mail", parts))
        confirm.ask("mail", parts, "x")
        self.assertIn("ONAY", confirm.check("mail", parts))  # çok erken
        with mock.patch.object(confirm, "MIN_WAIT", 0):
            self.assertEqual(confirm.check("mail", parts), "")
            self.assertIn("ONAY", confirm.check("mail", parts))  # tek kullanımlık

    def test_changed_content_not_confirmed(self):
        confirm.ask("mail", ("a@b.co", "s", "b"), "x")
        with mock.patch.object(confirm, "MIN_WAIT", 0):
            self.assertIn("ONAY", confirm.check("mail", ("a@b.co", "s", "baska")))


class MailTest(unittest.TestCase):
    def setUp(self):
        confirm._pending.clear()
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.dict(os.environ, {"JARVIS_DATA_DIR": self.tmp.name})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def _connect(self):
        from tools.actions import mail

        mail._token_file().write_text(json.dumps({"refresh_token": "r"}), encoding="utf-8")
        mail._client_file().write_text(json.dumps({"installed": {"client_id": "c", "client_secret": "s"}}), encoding="utf-8")

    def test_validation(self):
        from tools.actions.mail import send_email

        self.assertIn("Gecersiz", send_email("yanlis", "s", "b"))
        self.assertIn("Gecersiz", send_email("a@b.co", "s\nBcc: x@y.z", "b"))
        with mock.patch("webbrowser.open"):
            self.assertIn("tarayicida", send_email("a@b.co", "s", "b", provider="gmail"))

    def test_draft_then_confirm_sends_once(self):
        from tools.actions import mail

        self._connect()
        first = mail.send_email("a@b.co", "Konu", "Merhaba")
        self.assertIn("ONAY GEREKLI", first)
        sent = []

        class Resp:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return b"{}"

        def fake_urlopen(req, timeout=0):
            sent.append(req.full_url)
            return Resp()

        with mock.patch.object(confirm, "MIN_WAIT", 0), mock.patch.object(mail, "_access_token", return_value="t"), mock.patch.object(mail.urllib.request, "urlopen", fake_urlopen):
            self.assertIn("gonderildi", mail.send_email("a@b.co", "Konu", "Merhaba", confirm_send=True))
            self.assertEqual(len(sent), 1)
            self.assertIn("ONAY", mail.send_email("a@b.co", "Konu", "Merhaba", confirm_send=True))
            self.assertEqual(len(sent), 1)

    def test_confirm_without_ask_is_refused(self):
        from tools.actions import mail

        self._connect()
        self.assertIn("ONAY", mail.send_email("a@b.co", "K", "B", confirm_send=True))

    def test_whatsapp_send_now_needs_confirm(self):
        from tools.actions import whatsapp

        with mock.patch("webbrowser.open") as opened:
            out = whatsapp.send_whatsapp_message("selam", "05551112233", send_now=True)
        self.assertIn("ONAY GEREKLI", out)
        opened.assert_not_called()

    def test_client_file_name_variants(self):
        from tools.actions import mail

        (mail.data_path("gmail_client_secret.json.json")).write_text("{}", encoding="utf-8")
        self.assertTrue(str(mail._client_file()).endswith("gmail_client_secret.json.json"))

    def test_auto_import_from_downloads(self):
        import pathlib

        from tools.actions import mail

        downloads = pathlib.Path(self.tmp.name) / "Downloads"
        downloads.mkdir()
        (downloads / "client_secret_123.json").write_text(json.dumps({"installed": {"client_id": "c", "client_secret": "s"}}), encoding="utf-8")
        (downloads / "client_secret_bozuk.json").write_text("{}", encoding="utf-8")
        with mock.patch.object(mail, "_search_dirs", return_value=[downloads]):
            self.assertTrue(mail.import_client_file())
        self.assertEqual(mail._client().get("client_id"), "c")
        with mock.patch.object(mail, "_search_dirs", return_value=[]):
            self.assertTrue(mail.import_client_file())

    def test_no_client_found(self):
        from tools.actions import mail

        with mock.patch.object(mail, "_search_dirs", return_value=[]):
            self.assertFalse(mail.import_client_file())

    def test_auto_route_opens_gmail_web_compose(self):
        from tools.actions import mail

        with mock.patch.object(mail, "outlook_available", return_value=False), mock.patch.object(mail.webbrowser, "open") as opened:
            out = mail.send_email("a@b.co", "Konu ş", "Merhaba dünya")
        self.assertIn("Gonder", out)
        url = opened.call_args[0][0]
        self.assertTrue(url.startswith("https://mail.google.com/mail/?view=cm&fs=1&to=a%40b.co"))
        self.assertIn("su=Konu%20%C5%9F", url)
        self.assertIn("body=Merhaba%20d%C3%BCnya", url)

    def test_explicit_mailto_draft(self):
        from tools.actions import mail

        with mock.patch.object(mail.webbrowser, "open") as opened:
            self.assertIn("taslagi", mail.send_email("a@b.co", "K", "B", provider="taslak"))
        self.assertTrue(opened.call_args[0][0].startswith("mailto:a@b.co?"))

    def test_outlook_route_needs_confirm_then_sends(self):
        from tools.actions import mail

        sent = []
        with mock.patch.object(mail, "outlook_available", return_value=True), mock.patch.object(mail, "_send_outlook", lambda *a: sent.append(a)):
            self.assertIn("Outlook", mail.send_email("a@b.co", "K", "B"))
            self.assertEqual(sent, [])
            with mock.patch.object(confirm, "MIN_WAIT", 0):
                self.assertIn("Outlook ile", mail.send_email("a@b.co", "K", "B", confirm_send=True))
        self.assertEqual(sent, [("a@b.co", "K", "B")])

    def test_explicit_outlook_missing(self):
        from tools.actions import mail

        with mock.patch.object(mail, "outlook_available", return_value=False):
            self.assertIn("Klasik Outlook kullanilmiyor", mail.send_email("a@b.co", "K", "B", provider="outlook"))

    def test_mime_utf8(self):
        from tools.actions.mail import build_message

        msg = build_message("a@b.co", "Şu Çalışma", "Günaydın")
        self.assertIn("Günaydın", msg.get_content())


if __name__ == "__main__":
    unittest.main()
