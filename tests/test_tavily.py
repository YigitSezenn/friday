import io
import json
import unittest
from unittest import mock

from tools.actions import search


class TavilyTests(unittest.TestCase):
    def test_default_backend_exists_and_parses_answer(self):
        body = json.dumps({"answer": "Cevap", "results": [{"title": "Kaynak"}]}).encode()
        with mock.patch("urllib.request.urlopen", return_value=io.BytesIO(body)):
            self.assertEqual(search._tavily("k", "soru"), "Cevap Kaynaklar: Kaynak.")


if __name__ == "__main__":
    unittest.main()
