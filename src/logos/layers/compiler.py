"""Layer Compiler: compiles raw episodes into 3-layer TensorGlyph packets."""
from __future__ import annotations

import hashlib
import math
import re
import time
from collections import Counter
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from rytt.compiler import RYTT_GENOME, RyttCompiler
from rytt.embedding_init import _get_raw_glyph_features

from .bloom_mmu import BloomFilter10240, extract_entities
from .delta_extractor import (
    DeltaExtractionResult,
    NaturalLanguageDeltaExtractor,
    OllamaStateDeltaExtractor,
)
from .embedder import DeterministicSpectralEmbedder, Embedder
from .schema import (
    EpistemicTier,
    ProvenanceLayer,
    RelationalLayer,
    RelationEdge,
    RelationType,
    SemanticLayer,
    TensorGlyph,
    _l2_normalize,
)

_GROUND_CYCLE: Tuple[str, ...] = (
    "r", "y", "t", "t",
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l",
    "m", "n", "o", "p", "q", "s", "u", "v", "w", "x", "z",
)
_ELEVATED_CYCLE: Tuple[str, ...] = tuple(ch.upper() for ch in _GROUND_CYCLE)

_SLOT_KV_RE = re.compile(
    r"(?:^|[\s;])([A-Za-z][A-Za-z0-9_.-]{1,36})\s*(?:=|:=|->)\s*([^\s;,#]{1,64})"
)
_DECISION_RE = re.compile(
    r"(?im)^\s*(?:decision|canonical|endpoint|active_[a-z0-9_]+|port|model|policy|path|version)\s*[:=]\s*([^\n]+)$"
)
_KEYWORD_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_-]{3,28}\b")

_STOPWORDS = frozenset({
    "this", "that", "with", "from", "into", "when", "where", "which", "have",
    "has", "had", "were", "will", "would", "could", "should", "about", "after",
    "before", "then", "than", "also", "more", "most", "some", "such", "only",
    "they", "them", "their", "there", "here", "what", "your", "been", "being",
})


def estimate_tokens(text: str) -> int:
    """Fast deterministic token estimator (~4 chars per token, min 1 for non-empty)."""
    stripped = text.strip()
    if not stripped:
        return 0
    return max(1, math.ceil(len(stripped) / 4))


def cycle_symbol_for(slot_index: int, plane: str, cycle_len: int = 4) -> str:
    """Return canonical RYTT cycle glyph symbol (`r, y, t, t` -> `R, Y, T, T`)."""
    table = _GROUND_CYCLE if plane == "Ground" else _ELEVATED_CYCLE
    effective_len = max(2, min(int(cycle_len), len(table)))
    return table[slot_index % effective_len]


def _extract_state_deltas(text: str) -> Dict[str, str]:
    deltas: Dict[str, str] = {}
    for key, val in _SLOT_KV_RE.findall(text):
        k_clean = key.strip()
        v_clean = val.strip().rstrip(".")
        if k_clean.lower() in {"http", "https", "sha256"}:
            continue
        if v_clean:
            deltas[k_clean] = v_clean

    for match in _DECISION_RE.finditer(text):
        full = match.group(0)
        sep = ":" if ":" in full else "="
        raw_k, raw_v = full.split(sep, 1)
        k_clean = raw_k.strip()
        v_clean = raw_v.strip().rstrip(".")
        if k_clean and v_clean:
            deltas.setdefault(k_clean, v_clean)
    return deltas


def _extract_keywords(text: str, limit: int = 8) -> Tuple[str, ...]:
    words = [w for w in _KEYWORD_RE.findall(text) if w.lower() not in _STOPWORDS]
    freq = Counter(words)
    return tuple(word for word, _ in freq.most_common(limit))


def _summarize_episode(text: str, max_chars: int = 240) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return "(empty episode)"
    joined = " | ".join(lines[:3])
    if len(joined) <= max_chars:
        return joined
    return joined[: max_chars - 3].rstrip() + "..."


class LogosLayerCompiler:
    """Compiles raw episodes into 3-layer RYTT-grounded TensorGlyphs."""

    def __init__(
        self,
        embedder: Optional[Embedder] = None,
        rytt_compiler: Optional[RyttCompiler] = None,
        rank: int = 4,
        use_nl_extractor: bool = True,
        use_ollama_extractor: bool = False,
        ollama_model: str = "qwen2.5:1.5b",
        ollama_url: str = "http://127.0.0.1:11434",
    ) -> None:
        self.embedder: Embedder = embedder or DeterministicSpectralEmbedder(dim=768)
        self.rytt = rytt_compiler or RyttCompiler()
        self.rank = max(1, int(rank))
        self.use_nl_extractor = bool(use_nl_extractor)
        self.use_ollama_extractor = bool(use_ollama_extractor)
        if self.use_ollama_extractor:
            self.delta_extractor: NaturalLanguageDeltaExtractor | OllamaStateDeltaExtractor = (
                OllamaStateDeltaExtractor(model=ollama_model, base_url=ollama_url)
            )
        else:
            self.delta_extractor = NaturalLanguageDeltaExtractor()
        self.last_extraction: Optional[DeltaExtractionResult] = None

    @property
    def dim(self) -> int:
        return self.embedder.dim

    def rytt_metadata_for(self, symbol: str) -> Tuple[str, np.ndarray]:
        """Resolve RYTT PUA codepoint and exact 22-D geometric feature vector."""
        if symbol not in RYTT_GENOME:
            raise KeyError(f"Symbol {symbol!r} not in RYTT_GENOME")
        pua = RYTT_GENOME[symbol]["pua"]
        geom = np.asarray(_get_raw_glyph_features(symbol), dtype=np.float32)
        return pua, geom

    def build_rank_r_operator(
        self,
        sem_vec: np.ndarray,
        state_deltas: Dict[str, str],
        keywords: Sequence[str],
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Construct rank-r relational operator factors (U, V) encoding key->val flows."""
        d = self.dim
        r = self.rank
        u_mat = np.zeros((d, r), dtype=np.float32)
        v_mat = np.zeros((d, r), dtype=np.float32)

        base = _l2_normalize(sem_vec)
        u_mat[:, 0] = 0.15 * base
        v_mat[:, 0] = 0.15 * base

        col = 1
        for k, val in list(state_deltas.items())[: max(0, r - 1)]:
            val_vec, _ = self.embedder.embed(f"{k} {val}")
            key_vec, _ = self.embedder.embed(k)
            u_mat[:, col] = 0.12 * val_vec
            v_mat[:, col] = 0.12 * key_vec
            col += 1

        if col < r and keywords:
            for kw in keywords:
                if col >= r:
                    break
                kw_vec, _ = self.embedder.embed(kw)
                u_mat[:, col] = 0.08 * base
                v_mat[:, col] = 0.08 * kw_vec
                col += 1

        return u_mat, v_mat

    def compile_episode(
        self,
        episode_text: str,
        glyph_id: str,
        slot_index: int = 0,
        plane: str = "Ground",
        level: int = 1,
        epistemic_tier: EpistemicTier = EpistemicTier.P,
        storage_uri: Optional[str] = None,
        explicit_slots: Optional[Dict[str, str]] = None,
        edges: Optional[List[RelationEdge]] = None,
        summary: Optional[str] = None,
        anti_reason: str = "",
    ) -> TensorGlyph:
        """Compile raw episode prose/logs into a verified 3-layer TensorGlyph."""
        if not isinstance(epistemic_tier, EpistemicTier):
            epistemic_tier = EpistemicTier(str(epistemic_tier))

        symbol = cycle_symbol_for(slot_index, plane)
        pua, geom_vec = self.rytt_metadata_for(symbol)

        sem_vec, backend = self.embedder.embed(episode_text)
        keywords = _extract_keywords(episode_text)
        final_summary = summary or _summarize_episode(episode_text)
        semantic = SemanticLayer(
            vector=sem_vec,
            summary=final_summary,
            keywords=keywords,
            backend=backend,
        )

        # Extract deltas; enforce epistemic quarantine on Tier F (disproven claims)
        deltas = _extract_state_deltas(episode_text)
        merged_edges: List[RelationEdge] = list(edges or [])
        extracted_anti_claims: List[Dict[str, str]] = []
        if self.use_nl_extractor or self.use_ollama_extractor:
            ext = self.delta_extractor.extract(episode_text, glyph_id=glyph_id)
            self.last_extraction = ext
            deltas.update(ext.slots)
            merged_edges.extend(ext.relations)
            extracted_anti_claims = list(ext.anti_claims)
        if explicit_slots:
            deltas.update(explicit_slots)

        is_anti = epistemic_tier == EpistemicTier.F or bool(anti_reason)
        if is_anti:
            active_slots: Dict[str, str] = {}
            quarantine_note = anti_reason or "Quarantined EpistemicTier.F claim"
        else:
            active_slots = dict(deltas)
            quarantine_note = ""

        op_u, op_v = self.build_rank_r_operator(sem_vec, deltas, keywords)
        relational = RelationalLayer(
            edges=merged_edges,
            state_deltas=deltas,
            active_slots=active_slots,
            superseded_slots={},
            operator_u=op_u,
            operator_v=op_v,
        )

        # Layer 3: SHA-256 raw anchor + 10,240-bit entity Bloom filter
        raw_bytes = episode_text.encode("utf-8")
        raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        entities = extract_entities(episode_text)
        for token in re.findall(r"[A-Za-z0-9_./:-]{6,}", episode_text):
            low = token.lower()
            if low not in _STOPWORDS:
                if token not in entities:
                    entities.append(token)
                if low not in entities:
                    entities.append(low)
        for k, v in deltas.items():
            for item in (k, v):
                if item and item not in entities:
                    entities.append(item)
        for ac in extracted_anti_claims:
            cl = ac.get("claim", "")
            if cl and cl not in entities:
                entities.append(cl)
        bloom = BloomFilter10240()
        entity_count = bloom.add_many(entities)

        provenance = ProvenanceLayer(
            raw_sha256=raw_sha256,
            raw_token_count=estimate_tokens(episode_text),
            raw_char_count=len(episode_text),
            storage_uri=storage_uri or f"logos://raw/{raw_sha256}",
            bloom_bytes=bloom.to_bytes(),
            entity_count=entity_count,
            epistemic_tier=epistemic_tier,
        )

        return TensorGlyph(
            glyph_id=glyph_id,
            symbol=symbol,
            plane=plane,
            level=level,
            rytt_pua=pua,
            geometric_vec=geom_vec,
            semantic=semantic,
            relational=relational,
            provenance=provenance,
            created_at=time.time(),
            is_anti_glyph=is_anti,
            anti_reason=quarantine_note,
            tombstoned=is_anti,
        )
