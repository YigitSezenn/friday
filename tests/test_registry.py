import unittest


class ToolRegistryTests(unittest.TestCase):
    def test_every_declaration_has_a_handler_and_back(self):
        from tools.dispatch import TOOL_DECLARATIONS
        from tools.handlers import HANDLERS

        declared = {item["name"] for item in TOOL_DECLARATIONS}
        self.assertEqual(declared, set(HANDLERS))

    def test_declaration_names_are_unique(self):
        from tools.dispatch import TOOL_DECLARATIONS

        names = [item["name"] for item in TOOL_DECLARATIONS]
        self.assertEqual(len(names), len(set(names)))

    def test_unknown_tool_and_missing_webcam(self):
        from tools.dispatch import execute_tool

        self.assertIn("Bilinmeyen", execute_tool("yok", {}))
        self.assertIn("kullanilamiyor", execute_tool("toggle_webcam", {"action": "start"}))

    def test_int_helper_falls_back(self):
        from tools.handlers import as_int

        self.assertEqual(as_int("7", 1), 7)
        self.assertEqual(as_int("x", 3), 3)
        self.assertEqual(as_int(None, 5), 5)


if __name__ == "__main__":
    unittest.main()
