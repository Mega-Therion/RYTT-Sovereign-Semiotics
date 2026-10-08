import copy
import json
import unittest

from scripts.validate_ancient_script_records import SAMPLE, validate_document


class AncientScriptRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads(SAMPLE.read_text(encoding="utf-8"))

    def test_real_catalog_sample_is_metadata_only(self):
        self.assertEqual(validate_document(self.document), ["CDLI:P008001", "CDLI:P008002"])
        for record in self.document["records"]:
            self.assertEqual(record["record_status"], "catalog_metadata_only")
            self.assertEqual(record["observations"], [])
            self.assertEqual(record["claims"], [])

    def test_duplicate_artifact_id_is_rejected(self):
        doc = copy.deepcopy(self.document)
        doc["records"][1]["artifact"]["artifact_id"] = doc["records"][0]["artifact"]["artifact_id"]
        with self.assertRaisesRegex(ValueError, "duplicate artifact_id"):
            validate_document(doc)

    def test_non_cdli_source_is_rejected(self):
        doc = copy.deepcopy(self.document)
        doc["records"][0]["artifact"]["source_url"] = "https://example.com/P008001"
        with self.assertRaisesRegex(ValueError, "HTTPS CDLI URL"):
            validate_document(doc)

    def test_metadata_only_record_cannot_contain_claims(self):
        doc = copy.deepcopy(self.document)
        doc["records"][0]["claims"] = [{"claim_id": "claim-1", "evidence_refs": [], "confidence": None}]
        with self.assertRaisesRegex(ValueError, "metadata-only record"):
            validate_document(doc)

    def test_claim_confidence_is_bounded(self):
        doc = copy.deepcopy(self.document)
        record = doc["records"][0]
        record["record_status"] = "hypotheses_added"
        record["observations"] = [{"observation_id": "obs-1"}]
        record["claims"] = [{"claim_id": "claim-1", "evidence_refs": ["obs-1"], "confidence": 1.1}]
        with self.assertRaisesRegex(ValueError, "confidence must be null or between 0 and 1"):
            validate_document(doc)


if __name__ == "__main__":
    unittest.main()
