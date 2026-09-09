"""
RYTT AI Integration Layer

Provides three concrete integration modes for deploying RYTT in AI pipelines:

  1. MemoryEncoder  — encodes episodic memory items as RYTT+VSA records
                      for compact, addressable, diffable storage

  2. ChainOfThought  — wraps an AI reasoning chain, encoding each step
                       holonomically and verifying round-trip at every step

  3. SemanticAnnotator — dual-channel annotation using Ground/Elevated plane
                          to carry two semantic layers simultaneously

Author: R. W. Yett — Chyren Sovereign Intelligence
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .compiler import RyttCompiler
from .vsa import HV, HolonomicVSATracker, RyttVSARecord, superpose

_compiler = RyttCompiler()


# ---------------------------------------------------------------------------
# 1. Memory Encoder
# ---------------------------------------------------------------------------

@dataclass
class MemoryItem:
    """A single episodic memory item with RYTT + VSA encoding."""
    id:           str
    content:      str
    encoded_pua:  str
    hv:           Optional[HV]     = field(default=None, repr=False)
    timestamp:    float            = field(default_factory=time.time)
    round_trip:   bool             = False
    token_count:  int              = 0
    compression:  float            = 1.0
    metadata:     Dict[str, Any]   = field(default_factory=dict)


class MemoryEncoder:
    """
    Encodes episodic memory items into RYTT PUA + VSA hypervectors.

    Each item is stored as:
      - A RYTT-encoded PUA string (geometric re-representation)
      - A deterministic HV derived from the encoded string
      - A VSA record enabling position-addressable retrieval

    Retrieval:
      - Exact: by item ID
      - Approximate: by HV similarity search (nearest-neighbour)
    """

    def __init__(self) -> None:
        self._store: Dict[str, MemoryItem] = {}
        self._hvs:   List[HV] = []
        self._ids:   List[str] = []

    def encode(self, item_id: str, content: str,
               metadata: Optional[Dict[str, Any]] = None) -> MemoryItem:
        result       = _compiler.compile(content)
        recovered    = _compiler.decompile(result.encoded_pua)
        hv           = HV.from_seed(result.encoded_pua)
        item = MemoryItem(
            id           = item_id,
            content      = content,
            encoded_pua  = result.encoded_pua,
            hv           = hv,
            round_trip   = (recovered == content),
            token_count  = len(result.tokens),
            compression  = result.compression_ratio,
            metadata     = metadata or {},
        )
        self._store[item_id] = item
        self._hvs.append(hv)
        self._ids.append(item_id)
        return item

    def retrieve(self, item_id: str) -> Optional[MemoryItem]:
        return self._store.get(item_id)

    def search(self, query: str, top_k: int = 5) -> List[MemoryItem]:
        """Nearest-neighbour search by HV similarity."""
        if not self._hvs:
            return []
        q_result = _compiler.compile(query)
        q_hv     = HV.from_seed(q_result.encoded_pua)
        scored   = [
            (self._ids[i], q_hv.similarity(hv))
            for i, hv in enumerate(self._hvs)
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [
            self._store[id_] for id_, _ in scored[:top_k]
            if id_ in self._store
        ]

    def build_vsa_record(self) -> Optional[RyttVSARecord]:
        """Build a single VSA record for all stored items."""
        if not self._hvs:
            return None
        return RyttVSARecord.build(self._hvs)

    def export_json(self) -> str:
        """Export store metadata (without HVs) as JSON."""
        items = [
            {
                "id":          item.id,
                "content":     item.content,
                "round_trip":  item.round_trip,
                "token_count": item.token_count,
                "compression": item.compression,
                "timestamp":   item.timestamp,
                "metadata":    item.metadata,
            }
            for item in self._store.values()
        ]
        return json.dumps({"version": "0.2.0", "items": items}, indent=2)


# ---------------------------------------------------------------------------
# 2. Chain-of-Thought Encoder
# ---------------------------------------------------------------------------

@dataclass
class ReasoningStep:
    index:         int
    content:       str
    encoded_pua:   str
    round_trip:    bool
    token_count:   int
    compression:   float
    plane:         str
    depth:         int
    parity_block:  int
    hv_fingerprint: str


class ChainOfThoughtEncoder:
    """
    Wraps an AI reasoning chain and encodes each step holonomically.

    Usage:
        cot = ChainOfThoughtEncoder()
        cot.step("First, consider the dual-plane structure of the problem.")
        cot.step("ASCENDING: abstract analysis", ascend=True)
        cot.step("Conclusion: lossless by construction.", descend=True)
        report = cot.report()

    Guarantees:
      - Every step is round-trip verified.
      - The holonomic trace is position-addressable via VSA unbinding.
      - A SHA-512 fingerprint of the full trace is available at any point.
    """

    def __init__(self) -> None:
        self._tracker = HolonomicVSATracker()
        self._steps:  List[ReasoningStep] = []

    def step(self, content: str,
             ascend: bool = False,
             descend: bool = False) -> ReasoningStep:
        if ascend:
            self._tracker.ascend()
        result    = _compiler.compile(content)
        recovered = _compiler.decompile(result.encoded_pua)
        self._tracker.encode_step(result.encoded_pua)
        if descend:
            self._tracker.descend()
        s = ReasoningStep(
            index          = len(self._steps),
            content        = content,
            encoded_pua    = result.encoded_pua,
            round_trip     = (recovered == content),
            token_count    = len(result.tokens),
            compression    = result.compression_ratio,
            plane          = self._tracker.plane,
            depth          = self._tracker.depth,
            parity_block   = self._tracker.parity_block,
            hv_fingerprint = self._tracker.fingerprint()[:32],
        )
        self._steps.append(s)
        return s

    def report(self) -> dict:
        return {
            "version":      "0.2.0",
            "step_count":   len(self._steps),
            "tracker":      self._tracker.summary(),
            "steps":        [
                {
                    "index":          s.index,
                    "round_trip":     s.round_trip,
                    "token_count":    s.token_count,
                    "compression":    s.compression,
                    "plane":          s.plane,
                    "depth":          s.depth,
                    "parity_block":   s.parity_block,
                    "hv_fingerprint": s.hv_fingerprint,
                }
                for s in self._steps
            ],
        }

    def all_round_trips_exact(self) -> bool:
        return all(s.round_trip for s in self._steps)

    def fingerprint(self) -> str:
        return self._tracker.fingerprint()


# ---------------------------------------------------------------------------
# 3. Semantic Annotator
# ---------------------------------------------------------------------------

@dataclass
class AnnotatedToken:
    source:  str
    pua:     str
    plane:   str          # "Ground" | "Elevated" | "PassThru"
    ground_role:   str    # semantic role assigned via Ground plane
    elevated_role: str    # semantic role assigned via Elevated plane


class SemanticAnnotator:
    """
    Dual-channel semantic annotation using RYTT's two planes.

    Ground Plane  → carries one semantic layer (e.g., syntactic role)
    Elevated Plane → carries a second semantic layer (e.g., salience / abstraction)

    No extra tokens are consumed: the annotation is embedded in the
    plane geometry itself.
    """

    def __init__(
        self,
        ground_classifier:   Optional[Callable[[str], str]] = None,
        elevated_classifier: Optional[Callable[[str], str]] = None,
    ) -> None:
        self._gc = ground_classifier   or (lambda s: "surface")
        self._ec = elevated_classifier or (lambda s: "abstract")

    def annotate(self, text: str) -> List[AnnotatedToken]:
        result = _compiler.compile(text)
        annotated = []
        for tok in result.tokens:
            plane = "PassThru"
            if tok.plane == "Ground":
                plane = "Ground"
            elif tok.plane == "Elevated":
                plane = "Elevated"
            annotated.append(AnnotatedToken(
                source        = tok.source_char,
                pua           = tok.pua_char,
                plane         = plane,
                ground_role   = self._gc(tok.source_char) if plane == "Ground" else "",
                elevated_role = self._ec(tok.source_char) if plane == "Elevated" else "",
            ))
        return annotated

    def dual_channel_summary(self, text: str) -> dict:
        tokens     = self.annotate(text)
        ground     = [t for t in tokens if t.plane == "Ground"]
        elevated   = [t for t in tokens if t.plane == "Elevated"]
        passthru   = [t for t in tokens if t.plane == "PassThru"]
        return {
            "total_tokens":    len(tokens),
            "ground_count":    len(ground),
            "elevated_count":  len(elevated),
            "passthru_count":  len(passthru),
            "ground_roles":    list({t.ground_role for t in ground if t.ground_role}),
            "elevated_roles":  list({t.elevated_role for t in elevated if t.elevated_role}),
        }
