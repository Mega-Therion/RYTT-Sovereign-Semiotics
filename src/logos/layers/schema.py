"""Canonical data structures for L.O.G.O.S. Layer 1/2/3 Tensor-Glyphs."""
from __future__ import annotations

import base64
import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


def _l2_normalize(vec: np.ndarray) -> np.ndarray:
    arr = np.asarray(vec, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(arr))
    if norm > 1e-12:
        return (arr / norm).astype(np.float32, copy=False)
    return arr.astype(np.float32, copy=True)


def _encode_array_b64(arr: np.ndarray) -> str:
    arr32 = np.asarray(arr, dtype="<f4")
    return base64.b64encode(arr32.tobytes()).decode("ascii")


def _decode_array_b64(payload: str, shape: Tuple[int, ...]) -> np.ndarray:
    raw = base64.b64decode(payload.encode("ascii"))
    return np.frombuffer(raw, dtype="<f4").astype(np.float32, copy=True).reshape(shape)


class EpistemicTier(str, Enum):
    """Epistemic qualification tiers aligned with Chyren fail-closed governance."""

    D = "D"  # Verified / tested / observed fact
    P = "P"  # Robust theory / working invariant / engineered pattern
    O = "O"  # Open speculation / unverified hypothesis
    F = "F"  # Quarantined / falsified / rejected claim


class RelationType(str, Enum):
    """Typed relational edges stored inside Layer 2."""

    SUPERSEDES = "supersedes"
    REFUTES = "refutes"
    VERIFIES = "verifies"
    DEPENDS_ON = "depends_on"
    DERIVED_FROM = "derived_from"
    CONTRADICTS = "contradicts"
    EXTENDS = "extends"


@dataclass(frozen=True)
class RelationEdge:
    """Directed typed edge between two glyphs or state slots."""

    source_id: str
    target_id: str
    relation: RelationType
    weight: float = 1.0
    key: str = ""
    note: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation": self.relation.value,
            "weight": float(self.weight),
            "key": self.key,
            "note": self.note,
            "timestamp": float(self.timestamp),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RelationEdge":
        return cls(
            source_id=str(data["source_id"]),
            target_id=str(data["target_id"]),
            relation=RelationType(str(data["relation"])),
            weight=float(data.get("weight", 1.0)),
            key=str(data.get("key", "")),
            note=str(data.get("note", "")),
            timestamp=float(data.get("timestamp", 0.0)),
        )


@dataclass
class SemanticLayer:
    """Layer 1: Dense normalized semantic vector, dense summary, and top keywords."""

    vector: np.ndarray
    summary: str
    keywords: Tuple[str, ...] = ()
    backend: str = "deterministic-spectral"

    def __post_init__(self) -> None:
        self.vector = _l2_normalize(self.vector)

    def similarity(self, query_vec: np.ndarray) -> float:
        q = _l2_normalize(query_vec)
        if q.shape != self.vector.shape:
            raise ValueError(
                f"Dimension mismatch: glyph vector {self.vector.shape} vs query {q.shape}"
            )
        return float(np.dot(self.vector, q))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dim": int(self.vector.shape[0]),
            "vector_b64": _encode_array_b64(self.vector),
            "summary": self.summary,
            "keywords": list(self.keywords),
            "backend": self.backend,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SemanticLayer":
        if "vector_b64" in data:
            vec = _decode_array_b64(data["vector_b64"], (int(data["dim"]),))
        else:
            vec = np.asarray(data["vector"], dtype=np.float32)
        return cls(
            vector=vec,
            summary=str(data["summary"]),
            keywords=tuple(data.get("keywords", ())),
            backend=str(data.get("backend", "deterministic-spectral")),
        )


@dataclass
class RelationalLayer:
    """Layer 2: Bitemporal state deltas, active/superseded truth slots, and rank-r operator."""

    edges: List[RelationEdge] = field(default_factory=list)
    state_deltas: Dict[str, str] = field(default_factory=dict)
    active_slots: Dict[str, str] = field(default_factory=dict)
    superseded_slots: Dict[str, str] = field(default_factory=dict)
    operator_u: np.ndarray = field(default_factory=lambda: np.zeros((768, 4), dtype=np.float32))
    operator_v: np.ndarray = field(default_factory=lambda: np.zeros((768, 4), dtype=np.float32))

    def __post_init__(self) -> None:
        self.operator_u = np.asarray(self.operator_u, dtype=np.float32)
        self.operator_v = np.asarray(self.operator_v, dtype=np.float32)
        if self.operator_u.ndim != 2 or self.operator_v.ndim != 2:
            raise ValueError("Relational operator factors must be 2D matrices")
        if self.operator_u.shape != self.operator_v.shape:
            raise ValueError(
                f"Operator factor shape mismatch: {self.operator_u.shape} vs {self.operator_v.shape}"
            )

    @property
    def dim(self) -> int:
        return int(self.operator_u.shape[0])

    @property
    def rank(self) -> int:
        return int(self.operator_u.shape[1])

    def apply(self, query_vec: np.ndarray) -> np.ndarray:
        """Apply M(q) = normalize(q + U @ (V^T @ q)) without materializing d x d."""
        q = _l2_normalize(query_vec)
        if q.shape != (self.dim,):
            raise ValueError(f"Expected query shape ({self.dim},), got {q.shape}")
        if self.rank == 0:
            return q
        proj = self.operator_v.T @ q
        steered = q + (self.operator_u @ proj)
        return _l2_normalize(steered)

    def live_slots(self) -> Dict[str, str]:
        """Return only non-superseded slots."""
        return {
            k: v for k, v in self.active_slots.items() if k not in self.superseded_slots
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dim": self.dim,
            "rank": self.rank,
            "edges": [edge.to_dict() for edge in self.edges],
            "state_deltas": dict(self.state_deltas),
            "active_slots": dict(self.active_slots),
            "superseded_slots": dict(self.superseded_slots),
            "operator_u_b64": _encode_array_b64(self.operator_u),
            "operator_v_b64": _encode_array_b64(self.operator_v),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RelationalLayer":
        dim = int(data["dim"])
        rank = int(data["rank"])
        return cls(
            edges=[RelationEdge.from_dict(e) for e in data.get("edges", [])],
            state_deltas=dict(data.get("state_deltas", {})),
            active_slots=dict(data.get("active_slots", {})),
            superseded_slots=dict(data.get("superseded_slots", {})),
            operator_u=_decode_array_b64(data["operator_u_b64"], (dim, rank)),
            operator_v=_decode_array_b64(data["operator_v_b64"], (dim, rank)),
        )


@dataclass
class ProvenanceLayer:
    """Layer 3: Lossless raw hash pointer, 10,240-bit entity Bloom mask, and Merkle linkage."""

    raw_sha256: str
    raw_token_count: int
    raw_char_count: int
    storage_uri: str
    bloom_bytes: bytes
    entity_count: int = 0
    epistemic_tier: EpistemicTier = EpistemicTier.P
    parent_ids: Tuple[str, ...] = ()
    child_ids: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if len(self.bloom_bytes) != 1280:
            raise ValueError(
                f"Expected 1280 bytes (10,240 bits) for bloom_bytes, got {len(self.bloom_bytes)}"
            )
        if not isinstance(self.epistemic_tier, EpistemicTier):
            self.epistemic_tier = EpistemicTier(str(self.epistemic_tier))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_sha256": self.raw_sha256,
            "raw_token_count": int(self.raw_token_count),
            "raw_char_count": int(self.raw_char_count),
            "storage_uri": self.storage_uri,
            "bloom_b64": base64.b64encode(self.bloom_bytes).decode("ascii"),
            "entity_count": int(self.entity_count),
            "epistemic_tier": self.epistemic_tier.value,
            "parent_ids": list(self.parent_ids),
            "child_ids": list(self.child_ids),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProvenanceLayer":
        return cls(
            raw_sha256=str(data["raw_sha256"]),
            raw_token_count=int(data["raw_token_count"]),
            raw_char_count=int(data["raw_char_count"]),
            storage_uri=str(data["storage_uri"]),
            bloom_bytes=base64.b64decode(data["bloom_b64"].encode("ascii")),
            entity_count=int(data.get("entity_count", 0)),
            epistemic_tier=EpistemicTier(str(data.get("epistemic_tier", "P"))),
            parent_ids=tuple(data.get("parent_ids", ())),
            child_ids=tuple(data.get("child_ids", ())),
        )


@dataclass
class TensorGlyph:
    """Unified 3-layer Tensor-Glyph bound to RYTT Dual-Plane geometry."""

    glyph_id: str
    symbol: str
    plane: str
    level: int
    rytt_pua: str
    geometric_vec: np.ndarray
    semantic: SemanticLayer
    relational: RelationalLayer
    provenance: ProvenanceLayer
    created_at: float = field(default_factory=time.time)
    is_anti_glyph: bool = False
    anti_reason: str = ""
    tombstoned: bool = False

    def __post_init__(self) -> None:
        self.geometric_vec = np.asarray(self.geometric_vec, dtype=np.float32).reshape(-1)
        if self.level < 1:
            raise ValueError(f"TensorGlyph level must be >= 1, got {self.level}")
        if self.plane not in ("Ground", "Elevated", "Super"):
            raise ValueError(f"Unsupported glyph plane: {self.plane!r}")

    def content_digest(self) -> str:
        """Canonical cryptographic digest covering structural, semantic, and provenance identity."""
        payload = {
            "glyph_id": self.glyph_id,
            "symbol": self.symbol,
            "plane": self.plane,
            "level": int(self.level),
            "rytt_pua": self.rytt_pua,
            "raw_sha256": self.provenance.raw_sha256,
            "bloom_sha256": hashlib.sha256(self.provenance.bloom_bytes).hexdigest(),
            "epistemic_tier": self.provenance.epistemic_tier.value,
            "child_ids": list(self.provenance.child_ids),
            "summary": self.semantic.summary,
            "keywords": list(self.semantic.keywords),
            "state_deltas": sorted(self.relational.state_deltas.items()),
            "is_anti_glyph": bool(self.is_anti_glyph),
            "anti_reason": self.anti_reason,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "glyph_id": self.glyph_id,
            "symbol": self.symbol,
            "plane": self.plane,
            "level": int(self.level),
            "rytt_pua": self.rytt_pua,
            "geometric_dim": int(self.geometric_vec.shape[0]),
            "geometric_b64": _encode_array_b64(self.geometric_vec),
            "semantic": self.semantic.to_dict(),
            "relational": self.relational.to_dict(),
            "provenance": self.provenance.to_dict(),
            "created_at": float(self.created_at),
            "is_anti_glyph": bool(self.is_anti_glyph),
            "anti_reason": self.anti_reason,
            "tombstoned": bool(self.tombstoned),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TensorGlyph":
        geom_dim = int(data["geometric_dim"])
        return cls(
            glyph_id=str(data["glyph_id"]),
            symbol=str(data["symbol"]),
            plane=str(data["plane"]),
            level=int(data["level"]),
            rytt_pua=str(data["rytt_pua"]),
            geometric_vec=_decode_array_b64(data["geometric_b64"], (geom_dim,)),
            semantic=SemanticLayer.from_dict(data["semantic"]),
            relational=RelationalLayer.from_dict(data["relational"]),
            provenance=ProvenanceLayer.from_dict(data["provenance"]),
            created_at=float(data.get("created_at", 0.0)),
            is_anti_glyph=bool(data.get("is_anti_glyph", False)),
            anti_reason=str(data.get("anti_reason", "")),
            tombstoned=bool(data.get("tombstoned", False)),
        )
