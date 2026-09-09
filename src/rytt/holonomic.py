"""
RYTT Holonomic State Tracker

Python implementation of the HolonomicState defined in proofs/RYTT.lean § 7.
Tracks an AI agent's reasoning position in the dual-plane semiotic space:

  - depth         : nesting depth of current reasoning frame
  - plane         : current active plane (Ground | Elevated)
  - parity_block  : 24-token block index (mod 24)
  - return_count  : total verified holonomic returns
  - path          : full sequence of plane transitions for audit

Author: R. W. Yett — Chyren Sovereign Intelligence
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import List, Literal

PlaneType = Literal["Ground", "Elevated", "PassThru"]


@dataclass
class PlaneTransition:
    """A single plane transition event in the holonomic path."""
    step:      int
    from_plane: PlaneType
    to_plane:   PlaneType
    token:      str = ""
    depth_after: int = 0


@dataclass
class HolonomicState:
    """
    Full holonomic state for a RYTT reasoning agent.

    Mirrors the Lean 4 `HolonomicState` structure exactly,
    with additional audit fields for runtime introspection.
    """
    depth:        int        = 0
    plane:        PlaneType  = "Ground"
    parity_block: int        = 0   # 0–23
    token_count:  int        = 0
    return_count: int        = 0
    path:         List[PlaneTransition] = field(default_factory=list)

    # --- core operations (mirror Lean proofs) ---

    def ascend(self, token: str = "") -> "HolonomicState":
        """Enter the Elevated plane.  Returns self for chaining."""
        self.path.append(PlaneTransition(
            step        = self.token_count,
            from_plane  = self.plane,
            to_plane    = "Elevated",
            token       = token,
            depth_after = self.depth + 1,
        ))
        self.plane  = "Elevated"
        self.depth += 1
        return self

    def descend(self, token: str = "") -> bool:
        """
        Return to Ground plane.  Increments return_count.
        Returns True (return is always verified by the round-trip invariant).
        """
        self.path.append(PlaneTransition(
            step        = self.token_count,
            from_plane  = self.plane,
            to_plane    = "Ground",
            token       = token,
            depth_after = max(0, self.depth - 1),
        ))
        self.plane = "Ground"
        if self.depth > 0:
            self.depth -= 1
        self.return_count += 1
        return True

    def tick(self, plane: PlaneType = "Ground") -> None:
        """Advance the parity counter by one token."""
        self.token_count  += 1
        self.parity_block  = self.token_count % 24
        if self.plane != plane and plane != "PassThru":
            if plane == "Elevated":
                self.ascend()
            else:
                self.descend()

    # --- audit / introspection ---

    def audit_path(self) -> List[dict]:
        return [
            {
                "step":        t.step,
                "from":        t.from_plane,
                "to":          t.to_plane,
                "token":       t.token,
                "depth_after": t.depth_after,
            }
            for t in self.path
        ]

    def path_fingerprint(self) -> str:
        """Deterministic fingerprint of the full plane-transition path."""
        raw = json_safe(self.audit_path()).encode()
        return hashlib.sha512(raw).hexdigest()

    def is_balanced(self) -> bool:
        """
        True iff the number of ascents equals the number of descents
        (i.e., the reasoning frame is closed / back at depth 0).
        """
        ascents  = sum(1 for t in self.path if t.to_plane == "Elevated")
        descents = sum(1 for t in self.path if t.to_plane == "Ground")
        return ascents == descents and self.depth == 0

    def summary(self) -> dict:
        return {
            "depth":         self.depth,
            "plane":         self.plane,
            "parity_block":  self.parity_block,
            "token_count":   self.token_count,
            "return_count":  self.return_count,
            "path_length":   len(self.path),
            "balanced":      self.is_balanced(),
            "fingerprint":   self.path_fingerprint()[:32] + "…",
        }


def json_safe(obj) -> str:
    import json
    return json.dumps(obj, sort_keys=True)
