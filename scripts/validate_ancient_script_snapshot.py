#!/usr/bin/env python3
"""Verify a frozen ancient-script corpus against its schemas, manifest, and hashes."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jsonschema import Draft202012Validator

from research.ancient_scripts.scripts.ingest_proto_elamite import artifact_ids_hash, canonical_records_hash

ROOT = Path(__file__).resolve().parents[1]
RECORD_SCHEMA = ROOT / "research/ancient_scripts/schema/claim-record-v0.1.0.schema.json"
MANIFEST_SCHEMA = ROOT / "research/ancient_scripts/schema/snapshot-manifest-v0.2.0.schema.json"


def _validate_schema(document: dict, schema_path: Path, label: str) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    errors = sorted(Draft202012Validator(schema).iter_errors(document), key=lambda error: list(error.path))
    if errors:
        messages = "; ".join("/".join(str(part) for part in error.path) + ": " + error.message for error in errors)
        raise ValueError(f"{label} schema validation failed: {messages}")


def validate_snapshot(corpus_path: Path, manifest_path: Path) -> None:
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if corpus.get("dataset_version") != "0.2.0":
        raise ValueError("corpus dataset_version must be 0.2.0")
    if corpus.get("dataset_status") != "frozen_metadata_snapshot":
        raise ValueError("corpus is not marked frozen_metadata_snapshot")
    if manifest.get("manifest_version") != "0.2.0":
        raise ValueError("manifest_version must be 0.2.0")
    if manifest.get("status") != "frozen_metadata_snapshot":
        raise ValueError("manifest is not marked frozen_metadata_snapshot")

    records = corpus.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("frozen corpus records must be a non-empty array")

    for index, record in enumerate(records):
        _validate_schema(record, RECORD_SCHEMA, f"record[{index}]")

    _validate_schema(manifest, MANIFEST_SCHEMA, "manifest")

    ids = [record["artifact"]["artifact_id"] for record in records]
    if ids != sorted(ids):
        raise ValueError("artifact records are not sorted by artifact_id")
    if len(ids) != len(set(ids)):
        raise ValueError("frozen corpus contains duplicate artifact IDs")

    digest = canonical_records_hash(records)
    ids_digest = artifact_ids_hash(records)

    if corpus.get("snapshot_sha256") != digest:
        raise ValueError("corpus snapshot_sha256 does not match records")
    if manifest.get("snapshot_sha256") != digest:
        raise ValueError("manifest snapshot_sha256 does not match corpus")
    if manifest.get("artifact_ids_sha256") != ids_digest:
        raise ValueError("manifest artifact_ids_sha256 does not match corpus")

    count = len(records)
    if corpus.get("corpus", {}).get("artifact_count") != count:
        raise ValueError("corpus artifact_count does not match record count")
    if manifest.get("corpus", {}).get("artifact_count") != count:
        raise ValueError("manifest artifact_count does not match record count")

    if any(
        record["observations"]
        or record["claims"]
        or record["record_status"] != "catalog_metadata_only"
        or record["provenance"]["image_rights_status"] != "not_included"
        for record in records
    ):
        raise ValueError("frozen snapshot contains non-metadata-only or image-bearing records")

    print(f"PASS: verified frozen snapshot with {count} records; sha256={digest}")


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: validate_ancient_script_snapshot.py CORPUS.json MANIFEST.json", file=sys.stderr)
        return 2
    try:
        validate_snapshot(Path(sys.argv[1]), Path(sys.argv[2]))
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
