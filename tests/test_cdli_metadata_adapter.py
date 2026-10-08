import unittest

from research.ancient_scripts.adapters.cdli_metadata import normalize_cdli_artifact


class CdliMetadataAdapterTests(unittest.TestCase):
    def test_normalizes_documented_cdli_fields(self):
        record = normalize_cdli_artifact(
            {
                "artifact_id": "008001",
                "designation": "MDP 06, 201",
                "museum_no": "Sb 15075",
                "collections": "Louvre Museum, Paris, France",
                "provenience": "Susa (mod. Shush)",
                "period": "Proto-Elamite (ca. 3100-2900 BC)",
                "artifact_type": "tablet or envelope > tablet",
                "materials": "clay",
            },
            retrieved_on="2026-10-08",
        )
        self.assertEqual(record["artifact"]["artifact_id"], "CDLI:P008001")
        self.assertEqual(record["artifact"]["museum_number"], "Sb 15075")
        self.assertEqual(record["artifact"]["source_url"], "https://cdli.earth/search?id=P008001&layout=compact")
        self.assertEqual(record["observations"], [])
        self.assertEqual(record["claims"], [])

    def test_requires_period_and_collection(self):
        with self.assertRaisesRegex(ValueError, "period and collections"):
            normalize_cdli_artifact({"artifact_id": "008001", "period": "Proto-Elamite"}, retrieved_on="2026-10-08")

    def test_does_not_create_image_assets(self):
        record = normalize_cdli_artifact(
            {"artifact_id": "008001", "period": "Proto-Elamite", "collections": "Louvre"},
            retrieved_on="2026-10-08",
        )
        self.assertEqual(record["provenance"]["image_rights_status"], "not_included")
        self.assertEqual(record["observations"], [])
        self.assertEqual(record["claims"], [])

    def test_unrecognized_interpretive_fields_do_not_become_claims(self):
        raw = {"artifact_id": "008001", "period": "Proto-Elamite", "collections": "Louvre", "reading": "invented"}
        record = normalize_cdli_artifact(raw, retrieved_on="2026-10-08")
        self.assertEqual(record["claims"], [])
        self.assertNotIn("reading", record["artifact"])


if __name__ == "__main__":
    unittest.main()
