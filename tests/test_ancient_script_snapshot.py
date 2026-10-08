import copy
import json
import tempfile
import unittest
from pathlib import Path

from research.ancient_scripts.scripts.ingest_proto_elamite import artifact_ids_hash, canonical_records_hash
from scripts.validate_ancient_script_snapshot import validate_snapshot


def record(aid):
    return {
        "schema_version": "0.1.0",
        "record_status": "catalog_metadata_only",
        "artifact": {
            "artifact_id": aid,
            "collection": None,
            "provenience": None,
            "period": "Proto-Elamite (ca. 3100-2900 BC)",
            "script": "Proto-Elamite",
            "language": None,
            "language_status": "undetermined",
            "designation": None,
            "museum_number": None,
            "object_type": None,
            "material": None,
            "source_url": "https://cdli.earth/search?id=" + aid.split(":")[1] + "&layout=compact",
        },
        "observations": [],
        "claims": [],
        "provenance": {
            "catalog_source": "Cuneiform Digital Library Initiative (CDLI)",
            "retrieved_on": "2026-10-08",
            "metadata_rights_status": "review_required",
            "image_rights_status": "not_included",
            "notes": "metadata only",
        },
    }


class AncientScriptSnapshotTests(unittest.TestCase):
    def test_valid_snapshot_is_accepted(self):
        records = [record("CDLI:P008001"), record("CDLI:P008002")]
        digest = canonical_records_hash(records)
        manifest = {
            "manifest_version": "0.2.0",
            "status": "frozen_metadata_snapshot",
            "corpus": {
                "name": "CDLI Proto-Elamite",
                "script": "Proto-Elamite",
                "period_filter": "Proto-Elamite",
                "artifact_count": 2,
                "source": "https://cdli.earth/search",
                "source_query": "limit=1000&f%5Bperiod%5D%5B%5D=Proto-Elamite",
                "retrieved_on_utc": "2026-10-08T16:00:00+00:00",
                "canonicalization": "JSON UTF-8 sort_keys=true separators=(',', ':') over sorted records",
            },
            "snapshot_sha256": digest,
            "artifact_ids_sha256": artifact_ids_hash(records),
            "rights": {
                "metadata_rights_status": "review_required",
                "images_included": False,
                "image_rights_status": "not_included",
            },
            "evaluation": {"status": "not_ready", "reason": "labels not frozen"},
            "source_policy": {
                "api_documented": True,
                "image_assets_included": False,
                "metadata_license_status": "review_required",
            },
        }
        corpus = {
            "dataset_version": "0.2.0",
            "dataset_status": "frozen_metadata_snapshot",
            "corpus": manifest["corpus"],
            "rights": manifest["rights"],
            "snapshot_sha256": digest,
            "records": records,
        }
        with tempfile.TemporaryDirectory() as tmp:
            cp = Path(tmp) / "corpus.json"
            mp = Path(tmp) / "manifest.json"
            cp.write_text(json.dumps(corpus), encoding="utf-8")
            mp.write_text(json.dumps(manifest), encoding="utf-8")
            validate_snapshot(cp, mp)

    def test_tampered_record_hash_is_rejected(self):
        records = [record("CDLI:P008001"), record("CDLI:P008002")]
        digest = canonical_records_hash(records)
        manifest = {
            "manifest_version": "0.2.0",
            "status": "frozen_metadata_snapshot",
        }
        corpus = {
            "dataset_version": "0.2.0",
            "dataset_status": "frozen_metadata_snapshot",
            "corpus": {"artifact_count": 2},
            "snapshot_sha256": digest,
            "records": copy.deepcopy(records),
        }
        corpus["records"][1]["artifact"]["material"] = "tampered"
        corpus["snapshot_sha256"] = digest
        with tempfile.TemporaryDirectory() as tmp:
            cp = Path(tmp) / "corpus.json"
            mp = Path(tmp) / "manifest.json"
            cp.write_text(json.dumps(corpus), encoding="utf-8")
            mp.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_snapshot(cp, mp)


if __name__ == "__main__":
    unittest.main()
