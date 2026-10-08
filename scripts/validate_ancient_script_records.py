#!/usr/bin/env python3
"""Validate RYTT ancient-script research records and catalog snapshots."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE = ROOT / "research/ancient_scripts/samples/cdli-proto-elamite-sample.json"
STATUSES = {"catalog_metadata_only", "observations_added", "hypotheses_added", "reviewed"}
RIGHTS = {"review_required", "permission_verified", "license_verified", "public_domain_verified"}
IMAGE_RIGHTS = {"not_included", "review_required", "explicitly_permitted", "public_domain_verified", "not_reusable"}
LANGUAGE_STATUS = {"known", "undetermined", "disputed"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_document(document: dict) -> list[str]:
    _require(isinstance(document, dict), "document must be an object")
    _require(document.get("dataset_version") in {"0.1.0", "0.2.0"}, "unsupported dataset_version")
    records = document.get("records")
    _require(isinstance(records, list) and records, "records must be a non-empty array")

    ids: set[str] = set()
    for index, record in enumerate(records):
        prefix = f"records[{index}]"
        _require(isinstance(record, dict), f"{prefix} must be an object")
        _require(record.get("schema_version") == "0.1.0", f"{prefix}.schema_version must be 0.1.0")
        _require(record.get("record_status") in STATUSES, f"{prefix}.record_status is invalid")

        artifact = record.get("artifact")
        _require(isinstance(artifact, dict), f"{prefix}.artifact must be an object")
        for key in ("artifact_id", "collection", "period", "script", "language_status", "source_url"):
            _require(key in artifact, f"{prefix}.artifact.{key} is required")
        for key in ("artifact_id", "period", "script"):
            _require(isinstance(artifact[key], str) and artifact[key].strip(), f"{prefix}.artifact.{key} is required")
        _require(artifact["language_status"] in LANGUAGE_STATUS, f"{prefix}.artifact.language_status is invalid")
        _require(artifact["collection"] is None or isinstance(artifact["collection"], str), f"{prefix}.artifact.collection must be string or null")

        aid = artifact["artifact_id"]
        _require(aid not in ids, f"duplicate artifact_id: {aid}")
        ids.add(aid)

        parsed = urlparse(artifact["source_url"])
        _require(parsed.scheme == "https" and parsed.netloc == "cdli.earth", f"{prefix}.artifact.source_url must be an HTTPS CDLI URL")

        observations = record.get("observations")
        claims = record.get("claims")
        _require(isinstance(observations, list), f"{prefix}.observations must be an array")
        _require(isinstance(claims, list), f"{prefix}.claims must be an array")

        provenance = record.get("provenance")
        _require(isinstance(provenance, dict), f"{prefix}.provenance must be an object")
        _require(provenance.get("metadata_rights_status") in RIGHTS, f"{prefix}.provenance.metadata_rights_status is invalid")
        _require(provenance.get("image_rights_status") in IMAGE_RIGHTS, f"{prefix}.provenance.image_rights_status is invalid")

        if record["record_status"] == "catalog_metadata_only":
            _require(not observations and not claims, f"{prefix}: metadata-only record cannot contain observations or claims")
            _require(provenance["image_rights_status"] == "not_included", f"{prefix}: metadata-only record cannot include image assets")

        observation_ids: set[str] = set()
        for obs_index, observation in enumerate(observations):
            _require(isinstance(observation, dict), f"{prefix}.observations[{obs_index}] must be an object")
            obs_id = observation.get("observation_id")
            _require(isinstance(obs_id, str) and obs_id.strip(), f"{prefix}.observations[{obs_index}].observation_id is required")
            _require(obs_id not in observation_ids, f"{prefix}: duplicate observation_id {obs_id}")
            observation_ids.add(obs_id)

        claim_ids: set[str] = set()
        for claim_index, claim in enumerate(claims):
            _require(isinstance(claim, dict), f"{prefix}.claims[{claim_index}] must be an object")
            claim_id = claim.get("claim_id")
            _require(isinstance(claim_id, str) and claim_id.strip(), f"{prefix}.claims[{claim_index}].claim_id is required")
            _require(claim_id not in claim_ids, f"{prefix}: duplicate claim_id {claim_id}")
            claim_ids.add(claim_id)
            refs = claim.get("evidence_refs")
            _require(isinstance(refs, list) and len(refs) == len(set(refs)), f"{prefix}.claims[{claim_index}].evidence_refs must be a unique array")
            _require(set(refs) <= observation_ids, f"{prefix}.claims[{claim_index}] references an unknown observation")
            confidence = claim.get("confidence")
            _require(confidence is None or (isinstance(confidence, (int, float)) and not isinstance(confidence, bool) and 0 <= confidence <= 1), f"{prefix}.claims[{claim_index}].confidence must be null or between 0 and 1")
    return sorted(ids)


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SAMPLE
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        ids = validate_document(document)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: validated {len(ids)} catalog metadata records: {', '.join(ids[:10])}" + (" ..." if len(ids) > 10 else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
