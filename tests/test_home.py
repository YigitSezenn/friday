import base64
import os
import tempfile
import unittest


class FakeBridge:
    sent = []
    packet = b"\x26\x00abc"

    def send_data(self, data):
        FakeBridge.sent.append(data)

    def enter_learning(self):
        pass

    def check_data(self):
        return FakeBridge.packet


class HomeControlTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["JARVIS_DATA_DIR"] = self.tmp.name
        from tools.actions import home

        self.home = home
        home._bridge = lambda host: FakeBridge()
        home.time.sleep = lambda s: None
        FakeBridge.sent.clear()

    def tearDown(self):
        os.environ.pop("JARVIS_DATA_DIR", None)
        self.tmp.cleanup()

    def test_add_learn_send(self):
        run = self.home.run
        self.assertIn("eklendi", run("add", "Salon Klima", host="192.168.1.20"))
        self.assertIn("öğrenildi", run("learn", "salon klima", "aç"))
        self.assertIn("gönderildi", run("send", "SALON  klima", "Aç"))
        self.assertEqual(FakeBridge.sent, [FakeBridge.packet])
        self.assertIn("aç", run("list"))

    def test_unknown_device_and_command(self):
        run = self.home.run
        self.assertIn("kayıtlı değil", run("send", "garaj", "aç"))
        run("add", "salon klima", host="1.2.3.4")
        self.assertIn("öğrenilmemiş", run("send", "salon klima", "kapat"))
        self.assertEqual(FakeBridge.sent, [])

    def test_bridge_error_is_reported(self):
        def boom(host):
            raise OSError("zaman aşımı")

        self.home._bridge = boom
        self.home.run("add", "x", host="1.1.1.1")
        self.assertIn("ulaşılamadı", self.home.run("send", "x", "aç"))


if __name__ == "__main__":
    unittest.main()


class SnapshotTests(unittest.TestCase):
    def test_snapshot_hides_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["JARVIS_DATA_DIR"] = tmp
            try:
                from tools.actions import home

                home._bridge = lambda host: FakeBridge()
                home.time.sleep = lambda s: None
                home.run("add", "masa led", host="10.0.0.5")
                home.run("learn", "masa led", "aç")
                snap = home.snapshot()
                self.assertEqual(snap, {"masa led": {"host": "10.0.0.5", "codes": ["aç"]}})
            finally:
                os.environ.pop("JARVIS_DATA_DIR", None)


class DiscoverTests(unittest.TestCase):
    def _run(self, found):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["JARVIS_DATA_DIR"] = tmp
            try:
                from tools.actions import home

                home._discover = lambda: found
                return home.run("add", "salon klima")
            finally:
                os.environ.pop("JARVIS_DATA_DIR", None)

    def test_single_bridge_is_used(self):
        self.assertIn("10.0.0.7", self._run(["10.0.0.7"]))

    def test_none_found(self):
        self.assertIn("bulunamadı", self._run([]))

    def test_several_found_asks_user(self):
        out = self._run(["10.0.0.7", "10.0.0.8"])
        self.assertIn("Birden fazla", out)
        self.assertIn("10.0.0.8", out)


class RemoveTests(unittest.TestCase):
    def test_remove_code_and_device(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["JARVIS_DATA_DIR"] = tmp
            try:
                from tools.actions import home

                home._bridge = lambda host: FakeBridge()
                home.time.sleep = lambda s: None
                home.run("add", "x", host="1.1.1.1")
                home.run("learn", "x", "aç")
                self.assertIn("silindi", home.run("remove", "x", "aç"))
                self.assertEqual(home.snapshot()["x"]["codes"], [])
                self.assertIn("yok", home.run("remove", "x", "aç"))
                self.assertIn("silindi", home.run("remove", "x"))
                self.assertEqual(home.snapshot(), {})
                self.assertIn("kayıtlı değil", home.run("remove", "x"))
            finally:
                os.environ.pop("JARVIS_DATA_DIR", None)
