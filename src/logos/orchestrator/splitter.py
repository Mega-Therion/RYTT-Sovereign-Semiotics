"""Semantic-Closure Episode Splitter (prevents mid-topic chronological tearing)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from ..layers.compiler import estimate_tokens
from ..layers.embedder import DeterministicSpectralEmbedder, Embedder
from ..layers.schema import EpistemicTier, _l2_normalize


@dataclass
class TurnRecord:
    """Single verbatim conversational / tool turn inside active raw viewport."""

    turn_id: int
    role: str
    content: str
    token_count: int
    epistemic_tier: EpistemicTier = EpistemicTier.P
    timestamp: float = field(default_factory=time.time)
    explicit_slots: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def render(self) -> str:
        return f"[{self.role}#t{self.turn_id}]: {self.content}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turn_id": int(self.turn_id),
            "role": self.role,
            "content": self.content,
            "token_count": int(self.token_count),
            "epistemic_tier": self.epistemic_tier.value,
            "timestamp": float(self.timestamp),
            "explicit_slots": dict(self.explicit_slots),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TurnRecord":
        return cls(
            turn_id=int(data["turn_id"]),
            role=str(data["role"]),
            content=str(data["content"]),
            token_count=int(data["token_count"]),
            epistemic_tier=EpistemicTier(str(data.get("epistemic_tier", "P"))),
            timestamp=float(data.get("timestamp", 0.0)),
            explicit_slots=dict(data.get("explicit_slots", {})),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class EpisodeBatch:
    """Coherent sequence of turns sealed into one TensorGlyph."""

    turns: List[TurnRecord]
    combined_text: str
    token_count: int
    epistemic_tier: EpistemicTier
    explicit_slots: Dict[str, str]


class SemanticEpisodeSplitter:
    """
    Splits eligible overflow turns along topic/cosine transitions and explicit
    boundary hints rather than cutting mid-proof on a rigid chronological modulo.
    """

    def __init__(
        self,
        embedder: Optional[Embedder] = None,
        similarity_drop_threshold: float = 0.25,
        min_episode_tokens: int = 80,
        max_episode_tokens: int = 1200,
    ) -> None:
        self.embedder: Embedder = embedder or DeterministicSpectralEmbedder(dim=768)
        self.similarity_drop_threshold = float(similarity_drop_threshold)
        self.min_episode_tokens = max(1, int(min_episode_tokens))
        self.max_episode_tokens = max(self.min_episode_tokens, int(max_episode_tokens))

    def _finalize_batch(self, group: List[TurnRecord]) -> EpisodeBatch:
        combined = "\n".join(t.render() for t in group)
        merged_slots: Dict[str, str] = {}
        tiers = [t.epistemic_tier for t in group]
        for t in group:
            merged_slots.update(t.explicit_slots)
        tier_rank = {EpistemicTier.O: 0, EpistemicTier.P: 1, EpistemicTier.D: 2, EpistemicTier.F: -1}
        chosen_tier = min(tiers, key=lambda x: tier_rank.get(x, 1))
        return EpisodeBatch(
            turns=list(group),
            combined_text=combined,
            token_count=sum(t.token_count for t in group) or estimate_tokens(combined),
            epistemic_tier=chosen_tier,
            explicit_slots=merged_slots,
        )

    def split(self, turns: Sequence[TurnRecord]) -> List[EpisodeBatch]:
        if not turns:
            return []

        batches: List[EpisodeBatch] = []
        cur_group: List[TurnRecord] = []
        cur_tokens = 0
        centroid: Optional[np.ndarray] = None

        for turn in turns:
            turn_vec, _ = self.embedder.embed(turn.content)
            should_cut = False

            if cur_group:
                if cur_tokens + turn.token_count > self.max_episode_tokens:
                    should_cut = True
                elif cur_tokens >= self.min_episode_tokens:
                    if turn.metadata.get("topic_break"):
                        should_cut = True
                    elif centroid is not None:
                        cos_sim = float(np.dot(centroid, turn_vec))
                        if cos_sim < (1.0 - self.similarity_drop_threshold):
                            should_cut = True

            if should_cut:
                batches.append(self._finalize_batch(cur_group))
                cur_group = [turn]
                cur_tokens = turn.token_count
                centroid = turn_vec.copy()
            else:
                cur_group.append(turn)
                cur_tokens += turn.token_count
                if centroid is None:
                    centroid = turn_vec.copy()
                else:
                    centroid = _l2_normalize((centroid * (len(cur_group) - 1)) + turn_vec)

        if cur_group:
            batches.append(self._finalize_batch(cur_group))

        return batches
