import unittest

from research.ancient_scripts.adapters.cdli_metadata import normalize_cdli_artifact


class CdliMetadataAdapterTests(unittest.TestCase):
    def test_normalizes_documented_fields_and_explicit_script(self):
        record = normalize_cdli_artifact(
            {
                "id_text": "P008001",
                "museum_no": "Sb 15075",
                "collections": [{"collection": {"collection": "Louvre Museum, Paris, France"}}],
                "provenience": {"provenience": "Susa (mod. Shush)", "id": 12},
                "period": {"period": "Proto-Elamite (ca. 3100-2900 BC)"},
                "artifact_type": {"artifact_type": "tablet"},
                "materials": [{"material": {"material": "clay"}}],
            },
            script_name="Proto-Elamite",
            retrieved_on="2026-10-08",
        )
        artifact = record["artifact"]
        self.assertEqual(artifact["artifact_id"], "CDLI:P008001")
        self.assertEqual(artifact["museum_number"], "Sb 15075")
        self.assertEqual(artifact["collection"], "Louvre Museum, Paris, France")
        self.assertEqual(artifact["provenience"], "Susa (mod. Shush)")
        self.assertEqual(artifact["period"], "Proto-Elamite (ca. 3100-2900 BC)")
        self.assertEqual(artifact["script"], "Proto-Elamite")
        self.assertEqual(artifact["language_status"], "undetermined")
        self.assertEqual(artifact["object_type"], "tablet")
        self.assertEqual(artifact["material"], "clay")

    def test_missing_collection_stays_null(self):
        record = normalize_cdli_artifact(
            {"id_text": "P008001", "period": "Proto-Elamite"},
            script_name="Proto-Elamite",
            retrieved_on="2026-10-08",
        )
        self.assertIsNone(record["artifact"]["collection"])

    def test_missing_metadata_is_never_filled_with_fallbacks(self):
        record = normalize_cdli_artifact(
            {"id_text": "P008001", "period": "Proto-Elamite"},
            script_name="Proto-Elamite",
            retrieved_on="2026-10-08",
        )
        artifact = record["artifact"]
        self.assertIsNone(artifact["designation"])
        self.assertIsNone(artifact["museum_number"])
        self.assertIsNone(artifact["provenience"])
        self.assertIsNone(artifact["object_type"])
        self.assertIsNone(artifact["material"])
        self.assertEqual(record["claims"], [])

    def test_interpretive_input_cannot_become_a_claim(self):
        raw = {
            "id_text": "P008001",
            "period": "Proto-Elamite",
            "reading": "invented",
            "collections": [{"collection": {"collection": "Louvre"}}],
        }
        record = normalize_cdli_artifact(raw, script_name="Proto-Elamite", retrieved_on="2026-10-08")
        self.assertEqual(record["claims"], [])
        self.assertNotIn("reading", record["artifact"])

    def test_script_name_is_required(self):
        with self.assertRaisesRegex(ValueError, "script_name is required"):
            normalize_cdli_artifact(
                {"id_text": "P008001", "period": "Proto-Elamite"},
                script_name="",
                retrieved_on="2026-10-08",
            )


if __name__ == "__main__":
    unittest.main()


    def test_zero_pads_short_cdli_p_numbers(self):
        record = normalize_cdli_artifact(
            {"id_text": "P8001", "period": "Proto-Elamite", "collections": "Louvre"},
            script_name="Proto-Elamite",
            retrieved_on="2026-10-08",
        )
        self.assertEqual(record["artifact"]["artifact_id"], "CDLI:P008001")
        self.assertEqual(record["artifact"]["source_url"], "https://cdli.earth/search?id=P008001&layout=compact")
