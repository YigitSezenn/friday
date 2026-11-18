import unittest

from tools.actions.volume import normalize_target, resolve_level, set_volume


class Vol:
    def __init__(self, v):
        self.v, self.muted = v, 0

    def GetMasterVolume(self): return self.v
    def SetMasterVolume(self, v, _ctx): self.v = v
    def GetMasterVolumeLevelScalar(self): return self.v
    def SetMasterVolumeLevelScalar(self, v, _ctx): self.v = v
    def SetMute(self, m, _ctx): self.muted = m


class FakeBackend:
    def __init__(self, sessions):
        self.by_exe = sessions
        self.speakers = Vol(0.5)

    def sessions(self, exes):
        return [vol for exe, vol in self.by_exe if exe in exes]

    def master(self):
        return self.speakers


class VolumeTest(unittest.TestCase):
    def test_targets(self):
        self.assertEqual(normalize_target("Spotify'ın"), "spotify")
        self.assertEqual(normalize_target("YouTube"), "youtube")
        self.assertEqual(normalize_target("bilgisayar"), "system")
        self.assertEqual(normalize_target(""), "system")

    def test_levels(self):
        self.assertEqual(resolve_level(50, level=30), 30)
        self.assertEqual(resolve_level(50, change=+15), 65)
        self.assertEqual(resolve_level(95, change=20), 100)
        self.assertEqual(resolve_level(5, change="-20"), 0)
        self.assertEqual(resolve_level(40, level="%70"), 70)

    def test_spotify_up(self):
        vol = Vol(0.4)
        out = set_volume("spotify", change=20, backend=FakeBackend([("spotify.exe", vol)]))
        self.assertAlmostEqual(vol.v, 0.6)
        self.assertIn("%60", out)

    def test_browser_all_sessions(self):
        a, b = Vol(0.8), Vol(0.8)
        set_volume("youtube", level=30, backend=FakeBackend([("chrome.exe", a), ("msedge.exe", b), ("spotify.exe", Vol(1))]))
        self.assertAlmostEqual(a.v, 0.3)
        self.assertAlmostEqual(b.v, 0.3)

    def test_not_playing_falls_back_to_system(self):
        backend = FakeBackend([])
        out = set_volume("spotify", change=10, backend=backend)
        self.assertIn("genel sesini %60", out)
        self.assertAlmostEqual(backend.speakers.v, 0.6)

    def test_app_at_max_raises_system(self):
        backend = FakeBackend([("spotify.exe", Vol(1.0))])
        out = set_volume("spotify", change=15, backend=backend)
        self.assertIn("en yüksekteydi", out)
        self.assertAlmostEqual(backend.speakers.v, 0.65)

    def test_fraction_levels(self):
        self.assertEqual(resolve_level(50, level=0.4), 40)
        self.assertEqual(resolve_level(50, change=-0.15), 35)

    def test_raise_unmutes(self):
        vol = Vol(0.3)
        vol.muted = 1
        set_volume("spotify", change=10, backend=FakeBackend([("spotify.exe", vol)]))
        self.assertEqual(vol.muted, 0)

    def test_system_and_mute(self):
        backend = FakeBackend([])
        set_volume("sistem", level=20, backend=backend)
        self.assertAlmostEqual(backend.speakers.v, 0.2)
        vol = Vol(0.5)
        self.assertIn("sessize", set_volume("spotify", mute=True, backend=FakeBackend([("spotify.exe", vol)])))
        self.assertEqual(vol.muted, 1)

    def test_no_backend_is_graceful(self):
        # pycaw kurulu Windows'ta gerçek sese dokunmasın: arka uç kurulamıyormuş gibi yap.
        from unittest import mock

        from tools.actions import volume

        with mock.patch.object(volume, "_Backend", side_effect=ImportError("pycaw yok")):
            self.assertIn("kullanılamıyor", set_volume("spotify", change=10))


if __name__ == "__main__":
    unittest.main()
