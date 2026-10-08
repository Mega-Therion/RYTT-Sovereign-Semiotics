#!/usr/bin/env python3
"""Validate the metadata-only ancient-script sample with Python's standard library."""
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "research/ancient_scripts/samples/cdli-proto-elamite-sample.json"
STATUSES = {"catalog_metadata_only", "observations_added", "hypotheses_added", "reviewed"}
RIGHTS = {"review_required", "permission_verified", "license_verified", "public_domain_verified"}


def validate_document(document):
    if not isinstance(document, dict) or document.get("dataset_version") != "0.1.0":
        raise ValueError("dataset_version must be 0.1.0")
    records = document.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty array")
    ids = set()
    for i, record in enumerate(records):
        p = f"records[{i}]"
        if record.get("schema_version") != "0.1.0":
            raise ValueError(f"{p}: unsupported schema_version")
        if record.get("record_status") not in STATUSES:
            raise ValueError(f"{p}: invalid record_status")
        artifact = record.get("artifact")
        if not isinstance(artifact, dict):
            raise ValueError(f"{p}: artifact must be an object")
        for key in ("artifact_id", "collection", "period", "source_url"):
            if not isinstance(artifact.get(key), str) or not artifact[key].strip():
                raise ValueError(f"{p}: artifact.{key} is required")
        aid = artifact["artifact_id"]
        if aid in ids:
            raise ValueError(f"duplicate artifact_id: {aid}")
        ids.add(aid)
        url = urlparse(artifact["source_url"])
        if url.scheme != "https" or url.netloc != "cdli.earth":
            raise ValueError(f"{p}: source_url must be an HTTPS CDLI URL")
        observations, claims = record.get("observations"), record.get("claims")
        if not isinstance(observations, list) or not isinstance(claims, list):
            raise ValueError(f"{p}: observations and claims must be arrays")
        prov = record.get("provenance")
        if not isinstance(prov, dict) or prov.get("metadata_rights_status") not in RIGHTS:
            raise ValueError(f"{p}: invalid provenance or metadata rights status")
        if prov.get("image_rights_status") not in {"not_included", "review_required", "explicitly_permitted", "public_domain_verified", "not_reusable"}:
            raise ValueError(f"{p}: invalid image rights status")
        if record["record_status"] == "catalog_metadata_only":
            if observations or claims or prov["image_rights_status"] != "not_included":
                raise ValueError(f"{p}: metadata-only record must have no observations, claims, or image assets")
        obs_ids = {o.get("observation_id") for o in observations if isinstance(o, dict)}
        if len(obs_ids) != len(observations) or None in obs_ids:
            raise ValueError(f"{p}: every observation needs a unique observation_id")
        claim_ids = [c.get("claim_id") for c in claims if isinstance(c, dict)]
        if len(claim_ids) != len(claims) or None in claim_ids or len(set(claim_ids)) != len(claim_ids):
            raise ValueError(f"{p}: every claim needs a unique claim_id")
        for claim in claims:
            refs = claim.get("evidence_refs")
            if not isinstance(refs, list) or len(refs) != len(set(refs)) or not set(refs) <= obs_ids:
                raise ValueError(f"{p}: claim evidence_refs must refer to known observations")
            confidence = claim.get("confidence")
            if confidence is not None and (isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1):
                raise ValueError(f"{p}: confidence must be null or between 0 and 1")
    return sorted(ids)


def main():
    try:
        ids = validate_document(json.loads(SAMPLE.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: validated {len(ids)} catalog metadata records: {', '.join(ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
