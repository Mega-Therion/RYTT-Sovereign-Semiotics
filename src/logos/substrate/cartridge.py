"""S — Portable Verifiable `.logos` Session Cartridge Export / Verify / Load."""
from __future__ import annotations

import hashlib
import io
import json
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from ..layers.bloom_mmu import BLOOM_BYTES

CARTRIDGE_FORMAT = "logos-cartridge"
CARTRIDGE_VERSION = "0.1.0"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def export_cartridge(orchestrator: Any, output_path: str | Path) -> Path:
    """
    Export a complete portable `.logos` session cartridge (ZIP + per-file SHA-256 manifest):
      - manifest.json
      - glyph_tree.json
      - bitemporal_ledger.json
      - raw_blocks.jsonl
      - vectors.npz
      - bloom_filters.bin
      - checksums.json
    """
    out = Path(output_path)
    if out.suffix != ".logos":
        out = out.with_suffix(".logos")
    out.parent.mkdir(parents=True, exist_ok=True)

    tree_dict = orchestrator.tree.to_dict()
    raw_blocks = orchestrator.substrate.list_raw_blocks()

    # Build vector archive + concatenated 1280-byte bloom slices
    node_ids = sorted(orchestrator.tree.nodes.keys())
    if node_ids:
        sem_mat = np.stack(
            [orchestrator.tree.nodes[gid].semantic.vector for gid in node_ids], axis=0
        ).astype(np.float32)
        bloom_blob = b"".join(
            orchestrator.tree.nodes[gid].provenance.bloom_bytes for gid in node_ids
        )
    else:
        sem_mat = np.zeros((0, orchestrator.compiler.dim), dtype=np.float32)
        bloom_blob = b""

    vec_buf = io.BytesIO()
    np.savez_compressed(vec_buf, node_ids=np.array(node_ids), semantic_vectors=sem_mat)
    vec_bytes = vec_buf.getvalue()

    manifest = {
        "format": CARTRIDGE_FORMAT,
        "version": CARTRIDGE_VERSION,
        "created_at": time.time(),
        "frontier_notation": orchestrator.tree.frontier_notation(),
        "fanout": orchestrator.tree.fanout,
        "context_budget_tokens": orchestrator.context_budget_tokens,
        "total_ingested_tokens": orchestrator.total_ingested_tokens,
        "node_count": len(orchestrator.tree.nodes),
        "anti_glyph_count": len(orchestrator.tree.anti_glyphs),
        "raw_block_count": len(raw_blocks),
        "embedder_backend": orchestrator.compiler.embedder.backend_name,
        "active_turns": [t.to_dict() for t in orchestrator.active_turns],
    }

    members: Dict[str, bytes] = {
        "manifest.json": (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8"),
        "glyph_tree.json": (json.dumps(tree_dict, sort_keys=True, indent=2) + "\n").encode("utf-8"),
        "bitemporal_ledger.json": (
            json.dumps(orchestrator.tree.bitemporal_ledger, sort_keys=True, indent=2) + "\n"
        ).encode("utf-8"),
        "raw_blocks.jsonl": (
            "\n".join(json.dumps(blk, sort_keys=True) for blk in raw_blocks)
            + ("\n" if raw_blocks else "")
        ).encode("utf-8"),
        "vectors.npz": vec_bytes,
        "bloom_filters.bin": bloom_blob,
    }
    checksums = {name: _sha256_bytes(blob) for name, blob in members.items()}
    members["checksums.json"] = (json.dumps(checksums, sort_keys=True, indent=2) + "\n").encode("utf-8")

    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, blob in members.items():
            zf.writestr(name, blob)
    return out


def verify_cartridge(path: str | Path) -> Dict[str, Any]:
    """Fail-closed verification of a `.logos` cartridge archive (checksums + raw + Merkle)."""
    p = Path(path)
    errors: List[str] = []
    required = {
        "manifest.json",
        "glyph_tree.json",
        "bitemporal_ledger.json",
        "raw_blocks.jsonl",
        "vectors.npz",
        "bloom_filters.bin",
        "checksums.json",
    }

    if not p.exists():
        return {"valid": False, "errors": [f"Cartridge not found: {p}"]}

    with zipfile.ZipFile(p, "r") as zf:
        names = set(zf.namelist())
        missing = sorted(required - names)
        if missing:
            return {"valid": False, "errors": [f"Missing cartridge members: {missing}"]}

        checksums = json.loads(zf.read("checksums.json").decode("utf-8"))
        for member in sorted(required - {"checksums.json"}):
            data = zf.read(member)
            expected = checksums.get(member)
            actual = _sha256_bytes(data)
            if expected != actual:
                errors.append(f"Checksum mismatch for {member}: expected {expected}, got {actual}")

        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        if manifest.get("format") != CARTRIDGE_FORMAT:
            errors.append(f"Unexpected format: {manifest.get('format')!r}")

        tree_data = json.loads(zf.read("glyph_tree.json").decode("utf-8"))
        raw_lines = [ln for ln in zf.read("raw_blocks.jsonl").decode("utf-8").splitlines() if ln.strip()]
        raw_hashes: set[str] = set()
        for ln in raw_lines:
            blk = json.loads(ln)
            computed = _sha256_bytes(blk["content"].encode("utf-8"))
            if computed != blk["raw_sha256"]:
                errors.append(f"Raw block SHA-256 mismatch: {blk['raw_sha256']}")
            raw_hashes.add(blk["raw_sha256"])

        from ..glyphs.tree import DualPlaneGlyphTree  # local import

        tree = DualPlaneGlyphTree.from_dict(tree_data)
        tree_report = tree.verify_integrity()
        if not tree_report["valid"]:
            errors.extend(tree_report["errors"])

        # Verify every Level-1 leaf raw hash is backed by raw_blocks.jsonl
        for node in tree.nodes.values():
            if node.level == 1 and node.provenance.raw_sha256 not in raw_hashes:
                errors.append(f"Leaf {node.glyph_id} raw block missing from raw_blocks.jsonl")

        bloom_blob = zf.read("bloom_filters.bin")
        expected_bloom_len = len(tree.nodes) * BLOOM_BYTES
        if len(bloom_blob) != expected_bloom_len:
            errors.append(
                f"bloom_filters.bin length {len(bloom_blob)} != expected {expected_bloom_len}"
            )

    return {
        "valid": not errors,
        "errors": errors,
        "manifest": manifest,
        "tree_integrity": tree_report,
    }


def load_cartridge(path: str | Path) -> Dict[str, Any]:
    """Verify (fail-closed) and unpack a `.logos` cartridge payload."""
    report = verify_cartridge(path)
    if not report["valid"]:
        raise ValueError(f"Invalid .logos cartridge: {report['errors']}")

    with zipfile.ZipFile(path, "r") as zf:
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        tree_dict = json.loads(zf.read("glyph_tree.json").decode("utf-8"))
        raw_lines = [ln for ln in zf.read("raw_blocks.jsonl").decode("utf-8").splitlines() if ln.strip()]
        raw_blocks = [json.loads(ln) for ln in raw_lines]

    return {
        "manifest": manifest,
        "tree_dict": tree_dict,
        "raw_blocks": raw_blocks,
        "verification": report,
    }
