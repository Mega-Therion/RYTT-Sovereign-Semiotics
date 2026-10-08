import copy
import json
import unittest

from research.ancient_scripts.evaluation.generate_holdout_split import assign, build_manifest, canonical_snapshot_hash


def record(aid):
    return {
        "schema_version": "0.1.0",
        "record_status": "catalog_metadata_only",
        "artifact": {
            "artifact_id": aid,
            "collection": None,
            "designation": None,
            "museum_number": None,
            "provenience": None,
            "period": "Proto-Elamite (ca. 3100-2900 BC)",
            "script": "Proto-Elamite",
            "language": None,
            "language_status": "undetermined",
            "object_type": None,
            "material": None,
            "source_url": f"https://cdli.earth/search?id={aid.split(':')[1]}&layout=compact"
        },
        "observations": [],
        "claims": [],
        "provenance": {
            "catalog_source": "Cuneiform Digital Library Initiative (CDLI)",
            "retrieved_on": "2026-10-08",
            "metadata_rights_status": "review_required",
            "image_rights_status": "not_included",
            "notes": "metadata only"
        }
    }


class HoldoutSplitTests(unittest.TestCase):
    def test_assignment_is_deterministic(self):
        self.assertEqual(assign("a" * 64, "CDLI:P008001"), assign("a" * 64, "CDLI:P008001"))

    def test_manifest_counts_and_no_overlap(self):
        records = [record(f"CDLI:P{i:06d}") for i in range(8001, 8051)]
        snapshot = {
            "dataset_status": "frozen_metadata_snapshot",
            "snapshot_sha256": canonical_snapshot_hash(records),
            "records": records
        }
        manifest, assignments = build_manifest(snapshot)
        all_ids = sum(assignments.values(), [])
        self.assertEqual(manifest["corpus"]["artifact_count"], 50)
        self.assertEqual(len(all_ids), 50)
        self.assertEqual(len(set(all_ids)), 50)
        self.assertEqual(set(assignments["train"]).isdisjoint(assignments["validation"]), True)
        self.assertEqual(set(assignments["train"]).isdisjoint(assignments["test"]), True)
        self.assertEqual(set(assignments["validation"]).isdisjoint(assignments["test"]), True)

    def test_tampered_snapshot_hash_is_rejected(self):
        records = [record("CDLI:P008001")]
        snapshot = {"dataset_status": "frozen_metadata_snapshot", "snapshot_sha256": "0" * 64, "records": copy.deepcopy(records)}
        with self.assertRaisesRegex(ValueError, "snapshot_sha256"):
            build_manifest(snapshot)

    def test_noncanonical_artifact_id_is_rejected(self):
        records = [record("CDLI:P8001")]
        snapshot = {
            "dataset_status": "frozen_metadata_snapshot",
            "snapshot_sha256": canonical_snapshot_hash(records),
            "records": records
        }
        with self.assertRaisesRegex(ValueError, "canonical CDLI"):
            build_manifest(snapshot)


if __name__ == "__main__":
    unittest.main()
