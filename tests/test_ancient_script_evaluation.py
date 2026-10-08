import copy
import json
import unittest
from pathlib import Path

from research.ancient_scripts.evaluation.check_split import validate_split_manifest


class AncientScriptEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = Path("research/ancient_scripts/evaluation/splits/pilot-split-v0.1.0.json")
        cls.document = json.loads(cls.path.read_text(encoding="utf-8"))

    def test_pilot_split_is_valid(self):
        validate_split_manifest(self.document)

    def test_duplicate_artifact_is_rejected(self):
        doc = copy.deepcopy(self.document)
        doc["assignments"].append({"artifact_id": "CDLI:P008001", "split": "test"})
        with self.assertRaisesRegex(ValueError, "appears more than once"):
            validate_split_manifest(doc)

    def test_invalid_split_is_rejected(self):
        doc = copy.deepcopy(self.document)
        doc["assignments"][0]["split"] = "dev"
        with self.assertRaisesRegex(ValueError, "split is invalid"):
            validate_split_manifest(doc)


if __name__ == "__main__":
    unittest.main()
