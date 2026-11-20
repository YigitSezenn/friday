import base64
import io
import unittest

from tests._env import decode_qr, needs_module


class SiteQrTest(unittest.TestCase):
    def test_url_points_to_download_section(self):
        from jarvis.gate_client import SITE, site_download_url

        url = site_download_url()
        self.assertTrue(url.startswith(SITE + "/"))
        self.assertTrue(url.endswith("#indir"))
        self.assertNotIn("#k=", url)  # kapı anahtarı ASLA bu QR'a girmez

    @needs_module("qrcode", "cv2", "numpy", "PIL")
    def test_qr_decodes_to_site(self):
        from PIL import Image

        from jarvis.gate_client import site_download_url
        from jarvis.phone_server import phone_qr_data_url

        encoded = phone_qr_data_url(site_download_url()).split(",", 1)[1]
        image = Image.open(io.BytesIO(base64.b64decode(encoded))).convert("RGB")
        value = decode_qr(image)
        self.assertEqual(value, site_download_url())


if __name__ == "__main__":
    unittest.main()
