import unittest

from scripts.validate_ancient_script_schema import main


class AncientScriptSchemaTests(unittest.TestCase):
    def test_schema_validation_command_passes(self):
        self.assertEqual(main(), 0)


if __name__ == "__main__":
    unittest.main()
