import unittest

from tools.actions.confirm import ask, friendly


class FriendlyConfirmTests(unittest.TestCase):
    def test_whatsapp_prompt_is_readable(self):
        raw = ask("whatsapp", ("Yiğit", "Teşekkürler"), "WhatsApp taslağı — Kime: Yiğit, Mesaj: Teşekkürler.")
        text = friendly(raw)
        self.assertNotIn("confirm=true", text)
        self.assertNotIn("ONAY GEREKLİ", text)
        self.assertIn("Yiğit", text)
        self.assertIn("“Teşekkürler”", text)
        self.assertIn("Göndereyim mi?", text)

    def test_mail_and_shell_and_plain(self):
        mail = friendly("ONAY GEREKLİ: E-posta taslağı (smtp) — Kime: Ali <a@b.com>, Konu: Merhaba, Metin: Selam. Göndermeden önce kullanıcıya sesli sor: 'Göndereyim mi?' Evet derse aynı bilgilerle confirm=true ile tekrar çağır.")
        self.assertIn("Konu: Merhaba", mail)
        self.assertNotIn("confirm", mail)
        shell = friendly("ONAY GEREKLİ: Bu komut bilgisayarda değişiklik yapabilir: `Remove-Item x`. Göndermeden önce")
        self.assertIn("Remove-Item x", shell)
        self.assertEqual(friendly("Mesaj iletildi."), "Mesaj iletildi.")
        self.assertIn("bekliyorum", friendly("ONAY GEREKLİ: kullanıcının cevabini bekle; onayi kendin varsayma."))


if __name__ == "__main__":
    unittest.main()
