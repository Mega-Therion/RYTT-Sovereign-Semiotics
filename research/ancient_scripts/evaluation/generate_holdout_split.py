#!/usr/bin/env python3
"""Generate a deterministic artifact-level holdout split from a frozen snapshot."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def canonical_snapshot_hash(records: list[dict]) -> str:
    canonical = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def assignment_sha256(ids: list[str]) -> str:
    return hashlib.sha256(("\n".join(sorted(ids))).encode("utf-8")).hexdigest()


def assign(snapshot_sha256: str, artifact_id: str) -> str:
    bucket = int(hashlib.sha256(f"{snapshot_sha256}\n{artifact_id}".encode("utf-8")).hexdigest()[:16], 16) % 1000
    if bucket < 800:
        return "train"
    if bucket < 900:
        return "validation"
    return "test"


def build_manifest(corpus: dict, *, snapshot_artifact_run_id: int, snapshot_artifact_id: int) -> tuple[dict, dict[str, list[str]]]:
    records = corpus.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("snapshot records must be a non-empty array")
    if corpus.get("dataset_status") != "frozen_metadata_snapshot":
        raise ValueError("input must be a frozen metadata snapshot")

    computed = canonical_snapshot_hash(records)
    declared = corpus.get("snapshot_sha256")
    if computed != declared:
        raise ValueError("snapshot_sha256 does not match the snapshot records")

    ids = []
    for index, record in enumerate(records):
        artifact = record.get("artifact", {})
        artifact_id = artifact.get("artifact_id")
        if not isinstance(artifact_id, str) or not artifact_id:
            raise ValueError(f"record {index}: artifact_id is required")
        if not __import__("re").fullmatch(r"CDLI:P\d{6}", artifact_id):
            raise ValueError(f"record {index}: artifact_id is not canonical CDLI:P######")
        if record.get("record_status") != "catalog_metadata_only":
            raise ValueError(f"record {index}: snapshot must be metadata-only")
        ids.append(artifact_id)

    if len(ids) != len(set(ids)):
        raise ValueError("snapshot contains duplicate artifact IDs")

    assignments = {"train": [], "validation": [], "test": []}
    for artifact_id in sorted(ids):
        assignments[assign(declared, artifact_id)].append(artifact_id)

    if sum(map(len, assignments.values())) != len(ids):
        raise ValueError("split counts do not sum to corpus size")

    manifest = {
        "manifest_version": "0.1.0",
        "status": "frozen_unlabeled_holdout",
        "corpus": {
            "name": "CDLI Proto-Elamite",
            "script": "Proto-Elamite",
            "artifact_count": len(ids)
        },
        "snapshot_sha256": declared,
        "snapshot_artifact": {
            "workflow_run_id": snapshot_artifact_run_id,
            "artifact_name": "proto-elamite-metadata-snapshot-v0.2.0",
            "artifact_id": snapshot_artifact_id
        },
        "split_method": {
            "name": "snapshot-bound-sha256-bucket",
            "hash": "sha256",
            "input": "snapshot_sha256 + newline + canonical_artifact_id",
            "modulus": 1000,
            "train_cutoff": 800,
            "validation_cutoff": 900
        },
        "splits": {
            split: {
                "count": len(split_ids),
                "assignment_sha256": assignment_sha256(split_ids)
            }
            for split, split_ids in assignments.items()
        },
        "assignment_policy": {
            "artifact_unit": "artifact_id",
            "duplicates_allowed": False,
            "cross_split_overlap_allowed": False
        },
        "evaluation": {
            "task_status": "not_ready",
            "labels_status": "not_frozen",
            "preprocessing_status": "not_frozen"
        }
    }
    return manifest, assignments


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--assignments", type=Path)
    parser.add_argument("--snapshot-artifact-run-id", type=int, required=True)
    parser.add_argument("--snapshot-artifact-id", type=int, required=True)
    args = parser.parse_args()
    try:
        corpus = json.loads(args.snapshot.read_text(encoding="utf-8"))
        manifest, assignments = build_manifest(corpus, snapshot_artifact_run_id=args.snapshot_artifact_run_id, snapshot_artifact_id=args.snapshot_artifact_id)
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        if args.assignments:
            args.assignments.parent.mkdir(parents=True, exist_ok=True)
            args.assignments.write_text(json.dumps(assignments, indent=2) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("PASS: generated frozen artifact-level holdout split")
    for split, data in manifest["splits"].items():
        print(f"{split}: {data['count']} artifacts; assignment_sha256={data['assignment_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
