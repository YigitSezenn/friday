import unittest

from tools.vercel_temizle import select_deletable


class SelectDeletableTests(unittest.TestCase):
    def test_keeps_newest_ready_and_drops_failed_and_old(self):
        items = [{"id": str(i), "created": i, "state": "READY" if i % 2 else "ERROR"} for i in range(1, 21)]
        doomed = {item["id"] for item in select_deletable(items, 3)}
        self.assertTrue({"19", "17", "15"}.isdisjoint(doomed))
        self.assertTrue({str(i) for i in range(2, 21, 2)} <= doomed)
        self.assertTrue({"1", "3", "13"} <= doomed)

    def test_never_deletes_in_flight_deployments(self):
        items = [{"id": "a", "created": 1, "state": "BUILDING"}, {"id": "b", "created": 2, "state": "QUEUED"}]
        self.assertEqual(select_deletable(items, 0), [])


if __name__ == "__main__":
    unittest.main()
