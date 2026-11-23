"""Layer 3 Hardware-Speed 10,240-bit Bloom Filter & Exact-Entity MMU."""
from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

import numpy as np

from rytt.vsa import D as VSA_BITS
from rytt.vsa import HV

BLOOM_BITS: int = VSA_BITS  # 10,240 bits = 160 x uint64
BLOOM_BYTES: int = BLOOM_BITS // 8  # 1,280 bytes
BLOOM_HASHES: int = 7

_STOPWORDS = frozenset({
    "the", "and", "for", "with", "that", "this", "from", "into", "when", "where",
    "what", "which", "will", "would", "could", "should", "have", "has", "had",
    "are", "was", "were", "been", "being", "not", "but", "all", "any", "can",
    "use", "using", "used", "only", "also", "then", "than", "about", "after",
    "before", "between", "under", "over", "each", "more", "most", "some", "such",
})

_URL_RE = re.compile(r"https?://[^\s\)\]>\"']+")
_PATH_RE = re.compile(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+")
_COLON_TOKEN_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]{1,20}:[A-Za-z0-9_./-]{2,64}\b")
_HEX_RE = re.compile(r"\b0x[0-9a-fA-F]{4,64}\b|\b[0-9a-fA-F]{10,64}\b")
_PUA_CODE_RE = re.compile(r"\bU\+[0-9A-Fa-f]{4,6}\b")
_BACKTICK_RE = re.compile(r"`([^`\n]{2,80})`")
_SNAKE_OR_CODE_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*_[A-Za-z0-9_]+\b")
_CAMEL_RE = re.compile(r"\b[A-Z][a-z0-9]+(?:[A-Z][a-zA-Z0-9]*)+\b")
_UPPER_TOKEN_RE = re.compile(r"\b[A-Z][A-Z0-9-]{2,24}\b")


def extract_entities(text: str) -> List[str]:
    """Deterministically extract exact high-leverage technical entities from text."""
    seen: set[str] = set()
    ordered: List[str] = []

    def _add(tok: str) -> None:
        cleaned = tok.strip(".,;:!?\"'()[]{}<>")
        if len(cleaned) < 3:
            return
        if cleaned.lower() in _STOPWORDS:
            return
        if cleaned not in seen:
            seen.add(cleaned)
            ordered.append(cleaned)
        lowered = cleaned.lower()
        if len(lowered) >= 5 and lowered != cleaned and lowered not in seen:
            seen.add(lowered)
            ordered.append(lowered)

    for pattern in (
        _URL_RE,
        _COLON_TOKEN_RE,
        _HEX_RE,
        _PUA_CODE_RE,
        _PATH_RE,
        _SNAKE_OR_CODE_RE,
        _CAMEL_RE,
        _UPPER_TOKEN_RE,
    ):
        for match in pattern.findall(text):
            _add(match)

    for inner in _BACKTICK_RE.findall(text):
        for part in re.split(r"[\s,;]+", inner.strip()):
            if part:
                _add(part)

    return ordered


class BloomFilter10240:
    """10,240-bit deterministic Bloom filter stored inside a RYTT 160xuint64 HV."""

    __slots__ = ("_hv",)

    def __init__(self, hv: HV | None = None) -> None:
        self._hv: HV = HV(hv._data) if hv is not None else HV.zero()

    @staticmethod
    def _bit_indices(item: str) -> List[int]:
        encoded = item.encode("utf-8")
        digest = hashlib.sha256(encoded).digest() + hashlib.sha512(b"logos_bloom:" + encoded).digest()
        indices: List[int] = []
        for k in range(BLOOM_HASHES):
            offset = (k * 4) % (len(digest) - 4)
            val = int.from_bytes(digest[offset : offset + 4], "big")
            indices.append(val % BLOOM_BITS)
        return indices

    @property
    def hv(self) -> HV:
        return self._hv

    def add(self, item: str) -> None:
        data = self._hv._data
        for bit_idx in self._bit_indices(item):
            word = bit_idx >> 6
            bit = bit_idx & 63
            data[word] |= np.uint64(1) << np.uint64(bit)

    def add_many(self, items: Iterable[str]) -> int:
        count = 0
        for item in items:
            self.add(item)
            count += 1
        return count

    def might_contain(self, item: str) -> bool:
        data = self._hv._data
        for bit_idx in self._bit_indices(item):
            word = bit_idx >> 6
            bit = bit_idx & 63
            if (int(data[word]) & (1 << bit)) == 0:
                return False
        return True

    def is_superset_of(self, child: "BloomFilter10240") -> bool:
        """Exact bitwise invariant check: (child & parent) == child."""
        return bool(np.array_equal(np.bitwise_and(child._hv._data, self._hv._data), child._hv._data))

    def bit_count(self) -> int:
        return int(np.unpackbits(self._hv._data.view(np.uint8)).sum())

    def to_bytes(self) -> bytes:
        return self._hv._data.astype("<u8", copy=False).tobytes()

    @classmethod
    def from_bytes(cls, raw: bytes) -> "BloomFilter10240":
        if len(raw) != BLOOM_BYTES:
            raise ValueError(f"Expected {BLOOM_BYTES} bytes, got {len(raw)}")
        arr = np.frombuffer(raw, dtype="<u8").astype(np.uint64, copy=True)
        return cls(HV(arr))

    @classmethod
    def union(cls, filters: Iterable["BloomFilter10240"]) -> "BloomFilter10240":
        acc = np.zeros(160, dtype=np.uint64)
        for flt in filters:
            np.bitwise_or(acc, flt._hv._data, out=acc)
        return cls(HV(acc))


@dataclass(frozen=True)
class BloomHit:
    """Exact-entity hit recorded by the Bloom MMU."""

    glyph_id: str
    matched_entities: Tuple[str, ...]
    hit_count: int
    latency_us: float


class BloomMMU:
    """Microsecond CPU auto-prefetcher over TensorGlyph Layer-3 Bloom masks."""

    def match_query(
        self,
        query: str,
        glyphs: Sequence["TensorGlyph"],
    ) -> Tuple[List[BloomHit], float]:
        from .schema import TensorGlyph  # local import avoids circular type references

        t0 = time.perf_counter_ns()
        entities = extract_entities(query)
        # Also include long distinctive plain words (>= 6 chars) from query for fallback exact probes
        for token in re.findall(r"[A-Za-z0-9_./:-]{6,}", query):
            low = token.lower()
            if low not in _STOPWORDS and token not in entities:
                entities.append(token)
                if low not in entities:
                    entities.append(low)

        hits: List[BloomHit] = []
        if not entities:
            elapsed_us = (time.perf_counter_ns() - t0) / 1000.0
            return hits, elapsed_us

        for glyph in glyphs:
            if not isinstance(glyph, TensorGlyph):
                continue
            g0 = time.perf_counter_ns()
            flt = BloomFilter10240.from_bytes(glyph.provenance.bloom_bytes)
            matched = tuple(ent for ent in entities if flt.might_contain(ent))
            if matched:
                hits.append(
                    BloomHit(
                        glyph_id=glyph.glyph_id,
                        matched_entities=matched,
                        hit_count=len(matched),
                        latency_us=(time.perf_counter_ns() - g0) / 1000.0,
                    )
                )

        hits.sort(key=lambda h: (-h.hit_count, h.glyph_id))
        total_us = (time.perf_counter_ns() - t0) / 1000.0
        return hits, total_us
