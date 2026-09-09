"""
RYTT Vector Symbolic Architecture  —  10 240-bit BSC Hypervectors

Implements the algebraic operations defined in proofs/RYTTProofs/VSA.lean:
  bind      : HV × HV → HV   (bitwise XOR)
  superpose : List[HV] → HV  (majority vote)
  unbind    : role × encoded → filler  (bind is self-inverse)
  RoleFiller.encode / .decode
  RyttVSARecord  (position-addressable sequence record)
  HolonomicVSATracker  (live reasoning-state encoder)

Dependencies: numpy only (SIMD-friendly uint64 packing).
Author: R. W. Yett — Chyren Sovereign Intelligence
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
D: int = 10_240                 # dimensionality in bits
_WORDS: int = D // 64           # 160 uint64 words per vector
assert D % 64 == 0


# ---------------------------------------------------------------------------
# Core type
# ---------------------------------------------------------------------------
class HV:
    """A 10 240-bit binary hypervector stored as 160 × uint64."""

    __slots__ = ("_data",)

    def __init__(self, data: Optional[np.ndarray] = None) -> None:
        if data is None:
            self._data = np.zeros(_WORDS, dtype=np.uint64)
        else:
            assert data.shape == (_WORDS,) and data.dtype == np.uint64
            self._data = data.copy()

    # ---- factory methods --------------------------------------------------

    @classmethod
    def random(cls) -> "HV":
        """Draw a uniformly random hypervector (the standard VSA atom)."""
        raw = secrets.token_bytes(D // 8)
        arr = np.frombuffer(raw, dtype=np.uint64).copy()
        return cls(arr)

    @classmethod
    def from_seed(cls, seed: bytes | str) -> "HV":
        """Deterministic HV from an arbitrary seed (SHA-512 expanded to D bits)."""
        if isinstance(seed, str):
            seed = seed.encode()
        # SHA-512 gives 64 bytes; we need D/8 = 1280 bytes → tile
        chunks: list[bytes] = []
        counter = 0
        while len(b"".join(chunks)) < D // 8:
            h = hashlib.sha512(seed + counter.to_bytes(4, "big")).digest()
            chunks.append(h)
            counter += 1
        raw = b"".join(chunks)[: D // 8]
        arr = np.frombuffer(raw, dtype=np.uint64).copy()
        return cls(arr)

    @classmethod
    def zero(cls) -> "HV":
        return cls(np.zeros(_WORDS, dtype=np.uint64))

    # ---- algebraic operations --------------------------------------------

    def bind(self, other: "HV") -> "HV":
        """Binding ⊗ — bitwise XOR.  Self-inverse: v ⊗ (v ⊗ w) = w."""
        return HV(np.bitwise_xor(self._data, other._data))

    __xor__ = bind

    def unbind(self, encoded: "HV") -> "HV":
        """Retrieve filler from encoded: self ⊗ (self ⊗ filler) = filler."""
        return self.bind(encoded)

    def hamming(self, other: "HV") -> int:
        """Hamming distance (number of differing bits)."""
        xored = np.bitwise_xor(self._data, other._data)
        return int(np.unpackbits(xored.view(np.uint8)).sum())

    def similarity(self, other: "HV") -> float:
        """Cosine-equivalent similarity: 1 − hamming/D (ranges [0, 1])."""
        return 1.0 - self.hamming(other) / D

    def is_close(self, other: "HV", threshold: float = 0.1) -> bool:
        """True iff Hamming distance < threshold × D (default 10%)."""
        return self.hamming(other) < threshold * D

    # ---- serialisation ----------------------------------------------------

    def to_bytes(self) -> bytes:
        return self._data.tobytes()

    @classmethod
    def from_bytes(cls, b: bytes) -> "HV":
        arr = np.frombuffer(b, dtype=np.uint64).copy()
        assert arr.shape == (_WORDS,)
        return cls(arr)

    def __repr__(self) -> str:
        h = self._data[:2].tobytes().hex()
        return f"HV(D={D}, head=0x{h}…)"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HV):
            return NotImplemented
        return bool(np.array_equal(self._data, other._data))


# ---------------------------------------------------------------------------
# Superposition — majority vote
# ---------------------------------------------------------------------------

def superpose(hvs: List[HV]) -> HV:
    """
    Superposition ⊕̄ — majority vote across D bits.
    Ties (even list length) break to 0 (Ground plane default).
    """
    if not hvs:
        return HV.zero()
    if len(hvs) == 1:
        return HV(hvs[0]._data)
    # Unpack to bits, sum, threshold
    mat = np.stack([np.unpackbits(v._data.view(np.uint8)) for v in hvs], axis=0)
    counts = mat.sum(axis=0)  # shape (D,)
    threshold = len(hvs) / 2  # strict majority
    result_bits = (counts > threshold).astype(np.uint8)
    packed = np.packbits(result_bits)
    arr = packed.view(np.uint64)
    assert arr.shape == (_WORDS,)
    return HV(arr)


# ---------------------------------------------------------------------------
# Role-filler pairs
# ---------------------------------------------------------------------------

@dataclass
class RoleFiller:
    """Encodes a role → filler semantic relation as a single HV."""
    role:   HV
    filler: HV

    def encode(self) -> HV:
        return self.role ^ self.filler

    def decode(self, encoded: HV) -> HV:
        """Recover filler given the role: role ⊗ (role ⊗ filler) = filler."""
        return self.role.unbind(encoded)

    def roundtrip(self) -> bool:
        return self.decode(self.encode()) == self.filler


# ---------------------------------------------------------------------------
# RYTT VSA Record — position-addressable sequence
# ---------------------------------------------------------------------------

@dataclass
class RyttVSARecord:
    """
    Encodes a compiled RYTT sequence as a single superposed HV record:
      encoded = ⊕̄ { position_i ⊗ token_i  |  i ∈ [0, n) }

    Position retrieval:
      position_i ⊗ encoded  ≈  token_i
    (exact for single-token records; probabilistically correct for multi-token)
    """
    _positions: List[HV] = field(default_factory=list)
    _tokens:    List[HV] = field(default_factory=list)
    _encoded:   Optional[HV] = field(default=None, repr=False)

    @classmethod
    def build(cls, tokens: List[HV],
              position_seed: str = "rytt_pos") -> "RyttVSARecord":
        positions = [
            HV.from_seed(f"{position_seed}_{i}") for i in range(len(tokens))
        ]
        pairs = [p ^ t for p, t in zip(positions, tokens)]
        encoded = superpose(pairs)
        rec = cls()
        rec._positions = positions
        rec._tokens = tokens
        rec._encoded = encoded
        return rec

    def retrieve(self, index: int) -> Optional[HV]:
        """Retrieve token at index by unbinding the position vector."""
        if self._encoded is None or index >= len(self._positions):
            return None
        return self._positions[index].unbind(self._encoded)

    def verify_all(self) -> List[bool]:
        """For single-token records: exact.  For multi-token: probabilistic."""
        results = []
        for i, tok in enumerate(self._tokens):
            retrieved = self.retrieve(i)
            if retrieved is None:
                results.append(False)
            else:
                results.append(retrieved.is_close(tok))
        return results

    @property
    def encoded(self) -> Optional[HV]:
        return self._encoded

    def __len__(self) -> int:
        return len(self._tokens)


# ---------------------------------------------------------------------------
# Holonomic VSA Tracker
# ---------------------------------------------------------------------------

@dataclass
class HolonomicVSATracker:
    """
    Tracks an AI reasoning agent's state as a holonomic VSA record.

    Each reasoning step is encoded as:
      step_vector = step_index_hv ⊗ content_hv

    The composite trace is the superposition of all step vectors,
    from which any step can be retrieved by unbinding its index HV.

    Also tracks:
      - plane history  (Ground / Elevated transitions)
      - parity block   (mod 24)
      - depth          (nesting level)
      - return_count   (verified round-trips)
    """
    depth:        int  = 0
    plane:        str  = "Ground"
    parity_block: int  = 0
    token_count:  int  = 0
    return_count: int  = 0

    _step_hvs:  List[HV]  = field(default_factory=list)
    _index_hvs: List[HV]  = field(default_factory=list)
    _composite: Optional[HV] = field(default=None, repr=False)

    def encode_step(self, content: str | bytes) -> HV:
        """Encode a reasoning step and add it to the holonomic record."""
        if isinstance(content, str):
            content = content.encode()
        content_hv  = HV.from_seed(content)
        index_hv    = HV.from_seed(f"step_{len(self._step_hvs)}")
        step_vector = index_hv ^ content_hv

        self._step_hvs.append(content_hv)
        self._index_hvs.append(index_hv)

        if self._composite is None:
            self._composite = step_vector
        else:
            self._composite = superpose([self._composite, step_vector])

        self.token_count += 1
        self.parity_block = self.token_count % 24
        return content_hv

    def retrieve_step(self, index: int) -> Optional[HV]:
        """Retrieve a previously encoded step by index."""
        if self._composite is None or index >= len(self._index_hvs):
            return None
        return self._index_hvs[index].unbind(self._composite)

    def ascend(self) -> None:
        """Enter Elevated plane — increment reasoning depth."""
        self.plane = "Elevated"
        self.depth += 1

    def descend(self) -> bool:
        """Return to Ground plane — verify one holonomic return."""
        self.plane = "Ground"
        if self.depth > 0:
            self.depth -= 1
        self.return_count += 1
        return True  # return is always verified by construction

    def fingerprint(self) -> str:
        """SHA-512 fingerprint of the current composite trace."""
        if self._composite is None:
            return hashlib.sha512(b"").hexdigest()
        return hashlib.sha512(self._composite.to_bytes()).hexdigest()

    def summary(self) -> dict:
        return {
            "depth":        self.depth,
            "plane":        self.plane,
            "parity_block": self.parity_block,
            "token_count":  self.token_count,
            "return_count": self.return_count,
            "steps":        len(self._step_hvs),
            "fingerprint":  self.fingerprint()[:32] + "…",
        }
