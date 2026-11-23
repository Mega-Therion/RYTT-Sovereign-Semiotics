"""O — Dynamic LOD Viewport Camera, Bloom MMU Auto-Prefetcher & Lossless Hydration."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from ..glyphs.tree import DualPlaneGlyphTree
from ..layers.bloom_mmu import BloomFilter10240, BloomHit, BloomMMU, extract_entities
from ..layers.compiler import LogosLayerCompiler, estimate_tokens
from ..layers.embedder import DeterministicSpectralEmbedder, Embedder
from ..layers.schema import EpistemicTier, TensorGlyph
from ..operators.horizon1_text import Horizon1TextOperator
from ..operators.horizon2_tensor import Horizon2MatrixProjector, KVGlyphBank
from ..substrate.store import LogosSubstrate
from .splitter import SemanticEpisodeSplitter, TurnRecord


@dataclass
class HydratedSlice:
    """Losslessly recovered verbatim block extracted from Substrate via Layer 3 SHA-256."""

    glyph_id: str
    raw_sha256: str
    verified_sha256: bool
    content: str
    token_count: int
    trigger: str


@dataclass
class ViewportFrame:
    """Rendered context window snapshot produced by LogosOrchestrator."""

    query: str
    frontier_notation: str
    rendered_text: str
    total_tokens: int
    budget_tokens: int
    virtual_tokens_covered: int
    compression_ratio: float
    lod0_hydrated: List[HydratedSlice] = field(default_factory=list)
    lod1_glyphs: List[str] = field(default_factory=list)
    lod2_glyphs: List[str] = field(default_factory=list)
    hot_tail_turn_ids: List[int] = field(default_factory=list)
    bloom_hits: List[BloomHit] = field(default_factory=list)
    bloom_latency_us: float = 0.0
    active_truth_table: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class LogosOrchestrator:
    """
    Coordinates Rolling RYTT Context Crystallization, Dynamic LOD Viewport rendering,
    Hierarchical Layer-3 Bloom MMU auto-prefetching, and Fail-Closed Hydration.
    """

    def __init__(
        self,
        substrate: Optional[LogosSubstrate] = None,
        embedder: Optional[Embedder] = None,
        fanout: int = 4,
        context_budget_tokens: int = 250_000,
        watermark_ratio: float = 0.85,
        hot_tail_ratio: float = 0.20,
        prefetch_budget_ratio: float = 0.25,
        min_episode_tokens: int = 80,
        max_episode_tokens: int = 1200,
        kv_max_slots: int = 64,
    ) -> None:
        if not (0.2 <= watermark_ratio <= 0.98):
            raise ValueError(f"watermark_ratio must be in [0.2, 0.98], got {watermark_ratio}")
        if not (0.05 <= hot_tail_ratio < watermark_ratio):
            raise ValueError(
                f"hot_tail_ratio ({hot_tail_ratio}) must be >= 0.05 and < watermark_ratio ({watermark_ratio})"
            )

        self.substrate = substrate or LogosSubstrate(":memory:")
        self.embedder: Embedder = embedder or DeterministicSpectralEmbedder(dim=768)
        self.compiler = LogosLayerCompiler(embedder=self.embedder)
        self.tree = DualPlaneGlyphTree(compiler=self.compiler, fanout=fanout)
        self.splitter = SemanticEpisodeSplitter(
            embedder=self.embedder,
            min_episode_tokens=min_episode_tokens,
            max_episode_tokens=max_episode_tokens,
        )
        self.bloom_mmu = BloomMMU()
        self.h1_op = Horizon1TextOperator()
        self.h2_projector = Horizon2MatrixProjector(semantic_dim=self.embedder.dim, model_dim=self.embedder.dim)
        self.kv_bank = KVGlyphBank(num_layers=self.h2_projector.num_layers, max_slots=kv_max_slots)

        self.context_budget_tokens = max(64, int(context_budget_tokens))
        self.watermark_ratio = float(watermark_ratio)
        self.hot_tail_ratio = float(hot_tail_ratio)
        self.prefetch_budget_ratio = float(prefetch_budget_ratio)

        self.active_turns: List[TurnRecord] = []
        self._turn_counter: int = 0
        self.total_ingested_tokens: int = 0
        self.flush_count: int = 0

    def active_raw_tokens(self) -> int:
        return sum(t.token_count for t in self.active_turns)

    def live_truth_table(self) -> Dict[str, Dict[str, Any]]:
        """Truth table combining crystallized bitemporal slots + newer hot-tail slots."""
        table = self.tree.active_truth_table()
        for rec in self.active_turns:
            if rec.epistemic_tier == EpistemicTier.F:
                continue
            for key, val in rec.explicit_slots.items():
                prev_revs = table.get(key, {}).get("revisions", 0)
                table[key] = {
                    "value": val,
                    "glyph_id": f"hot_tail#t{rec.turn_id}",
                    "epistemic_tier": rec.epistemic_tier.value,
                    "revisions": prev_revs + 1,
                }
        return table

    def _persist_tree_nodes(self) -> None:
        for node in self.tree.nodes.values():
            self.substrate.put_glyph(node)
        for ag in self.tree.anti_glyphs.values():
            self.substrate.put_glyph(ag)

    def _crystallize_oldest(self, force: bool = False) -> int:
        """Freeze oldest turns above the hot tail into Ground glyphs (+ rollup)."""
        if not self.active_turns:
            return 0

        tail_cap = int(self.context_budget_tokens * self.hot_tail_ratio)
        # Walk backwards from newest to protect hot tail verbatim
        tail_tokens = 0
        split_idx = len(self.active_turns)
        for idx in range(len(self.active_turns) - 1, -1, -1):
            t_tok = self.active_turns[idx].token_count
            if tail_tokens + t_tok <= tail_cap or idx == len(self.active_turns) - 1:
                tail_tokens += t_tok
                split_idx = idx
            else:
                break

        eligible = self.active_turns[:split_idx]
        watermark = int(self.context_budget_tokens * self.watermark_ratio)
        if not eligible:
            if self.active_raw_tokens() > watermark and len(self.active_turns) > 1:
                split_idx = 1
                eligible = self.active_turns[:split_idx]
            else:
                return 0

        batches = self.splitter.split(eligible)
        if not batches:
            return 0

        # Consume at least the first batch (or all eligible if flushing down past watermark)
        watermark = int(self.context_budget_tokens * self.watermark_ratio)
        remaining_after_first = sum(t.token_count for t in self.active_turns[len(batches[0].turns) :])
        to_consume = batches if (force or remaining_after_first > watermark) else [batches[0]]

        consumed_turns = 0
        new_glyphs = 0
        for batch in to_consume:
            raw_sha = self.substrate.put_raw_block(
                content=batch.combined_text,
                token_count=batch.token_count,
                epistemic_tier=batch.epistemic_tier.value,
            )
            storage_uri = f"logos://raw/{raw_sha}"
            before_frontier = set(self.tree.active_frontier)
            glyph = self.tree.append_episode(
                episode_text=batch.combined_text,
                epistemic_tier=batch.epistemic_tier,
                storage_uri=storage_uri,
                explicit_slots=batch.explicit_slots,
            )
            after_frontier = set(self.tree.active_frontier)
            for gid in sorted(after_frontier - before_frontier):
                node = self.tree.nodes[gid]
                self.kv_bank.allocate_slot(node, self.h2_projector.compile_kv_glyph(node))
            for retired in sorted(before_frontier - after_frontier):
                self.kv_bank.retire_slot(retired)
            consumed_turns += len(batch.turns)
            new_glyphs += 1

        self.active_turns = self.active_turns[consumed_turns:]
        self.flush_count += new_glyphs
        self._persist_tree_nodes()
        return new_glyphs

    def ingest_turn(
        self,
        role: str,
        content: str,
        epistemic_tier: EpistemicTier = EpistemicTier.P,
        explicit_slots: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        anti_reason: str = "",
    ) -> Dict[str, Any]:
        if not isinstance(epistemic_tier, EpistemicTier):
            epistemic_tier = EpistemicTier(str(epistemic_tier))

        tok_count = max(1, estimate_tokens(content))
        raw_sha = self.substrate.put_raw_block(
            content=content,
            token_count=tok_count,
            epistemic_tier=epistemic_tier.value,
        )
        self.total_ingested_tokens += tok_count

        if epistemic_tier == EpistemicTier.F or anti_reason:
            ag = self.tree.register_anti_glyph(
                episode_text=content,
                reason=anti_reason or "EpistemicTier.F quarantined input",
                storage_uri=f"logos://raw/{raw_sha}",
            )
            self.substrate.put_glyph(ag)
            return {
                "status": "quarantined_anti_glyph",
                "glyph_id": ag.glyph_id,
                "raw_sha256": raw_sha,
                "frontier": self.tree.frontier_notation(),
                "flushes_triggered": 0,
            }

        self._turn_counter += 1
        rec = TurnRecord(
            turn_id=self._turn_counter,
            role=role,
            content=content,
            token_count=tok_count,
            epistemic_tier=epistemic_tier,
            explicit_slots=dict(explicit_slots or {}),
            metadata=dict(metadata or {}),
        )
        self.active_turns.append(rec)

        watermark = int(self.context_budget_tokens * self.watermark_ratio)
        flushes = 0
        while self.active_raw_tokens() > watermark:
            did = self._crystallize_oldest(force=False)
            if did == 0:
                break
            flushes += did

        return {
            "status": "ingested",
            "turn_id": rec.turn_id,
            "raw_sha256": raw_sha,
            "active_raw_tokens": self.active_raw_tokens(),
            "frontier": self.tree.frontier_notation(),
            "flushes_triggered": flushes,
        }

    def force_flush(self) -> int:
        """Manually crystallize oldest turns above the hot tail (keeps hot tail verbatim)."""
        return self._crystallize_oldest(force=True)

    def _drill_matching_leaves(
        self,
        glyph: TensorGlyph,
        query: str,
        entities: Sequence[str],
    ) -> List[TensorGlyph]:
        """Recursively traverse Elevated -> Ground leaves guided strictly by Layer-3 Bloom hits."""
        if glyph.level == 1 or not glyph.provenance.child_ids:
            return [glyph]

        matched_children: List[TensorGlyph] = []
        for cid in glyph.provenance.child_ids:
            child = self.tree.nodes.get(cid)
            if child is None:
                continue
            flt = BloomFilter10240.from_bytes(child.provenance.bloom_bytes)
            if any(flt.might_contain(ent) for ent in entities):
                matched_children.extend(self._drill_matching_leaves(child, query, entities))

        if matched_children:
            return matched_children
        # Semantic tie-breaker fallback inside matched subtree
        q_vec, _ = self.embedder.embed(query)
        leaves = self.tree.get_leaves(glyph.glyph_id)
        if not leaves:
            return []
        best = max(leaves, key=lambda lf: lf.semantic.similarity(q_vec))
        return [best]

    def _extract_relevant_excerpt(self, raw_text: str, query: str, max_chars: int) -> str:
        if len(raw_text) <= max_chars or not query.strip():
            return raw_text[:max_chars]

        q_entities = extract_entities(query)
        q_words = [w.lower() for w in re.findall(r"[A-Za-z0-9_./:-]{3,}", query)]
        lines = raw_text.splitlines()
        scored_lines: List[Tuple[int, int, str]] = []
        for idx, line in enumerate(lines):
            low = line.lower()
            ent_hits = sum(3 for e in q_entities if e.lower() in low)
            word_hits = sum(1 for w in q_words if w in low)
            scored_lines.append((ent_hits + word_hits, idx, line))

        best_score, best_idx, _ = max(scored_lines, key=lambda x: (x[0], -x[1]))
        if best_score == 0:
            return raw_text[:max_chars]

        # Expand symmetrically around best matching line
        selected: List[str] = [lines[best_idx]]
        total_len = len(lines[best_idx])
        offset = 1
        while total_len < max_chars and (best_idx - offset >= 0 or best_idx + offset < len(lines)):
            if best_idx - offset >= 0:
                cand = lines[best_idx - offset]
                if total_len + len(cand) + 1 <= max_chars:
                    selected.insert(0, cand)
                    total_len += len(cand) + 1
            if best_idx + offset < len(lines):
                cand = lines[best_idx + offset]
                if total_len + len(cand) + 1 <= max_chars:
                    selected.append(cand)
                    total_len += len(cand) + 1
            offset += 1
        return "\n".join(selected)

    def hydrate(
        self,
        glyph_id: str,
        query: str = "",
        max_chars: int = 2000,
        trigger: str = "explicit",
    ) -> HydratedSlice:
        """Fail-closed Layer-3 SHA-256 dereference returning verified raw text."""
        glyph = self.tree.nodes.get(glyph_id) or self.tree.anti_glyphs.get(glyph_id)
        if glyph is None:
            raise KeyError(f"Unknown glyph_id {glyph_id!r}")

        target = glyph
        if glyph.provenance.child_ids:
            entities = extract_entities(query) if query else []
            leaves = self._drill_matching_leaves(glyph, query, entities) if query else self.tree.get_leaves(glyph.glyph_id)
            if not leaves:
                raise ValueError(f"Parent glyph {glyph_id} has no resolvable leaf blocks")
            target = leaves[0]

        raw_text = self.substrate.get_raw_block(target.provenance.raw_sha256, verify_sha=True)
        if raw_text is None:
            raise KeyError(
                f"Raw block missing for glyph {target.glyph_id} (sha={target.provenance.raw_sha256})"
            )
        actual_sha = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        verified = actual_sha == target.provenance.raw_sha256
        if not verified:
            raise ValueError(
                f"Fail-closed SHA-256 mismatch hydrating {target.glyph_id}"
            )

        excerpt = self._extract_relevant_excerpt(raw_text, query, max_chars=max_chars)
        return HydratedSlice(
            glyph_id=target.glyph_id,
            raw_sha256=actual_sha,
            verified_sha256=verified,
            content=excerpt,
            token_count=estimate_tokens(excerpt),
            trigger=trigger,
        )

    def compose_viewport(
        self,
        query: str,
        max_tokens: Optional[int] = None,
        auto_prefetch: bool = True,
        zoom_glyph_ids: Sequence[str] = (),
    ) -> ViewportFrame:
        """
        Render the Dynamic LOD Viewport combining:
          - LOD-1 / LOD-2 pinned frontier glyphs + active truth mask + Anti-Glyphs
          - LOD-0 auto-prefetched slices from hierarchical Bloom MMU & zoomed glyphs
          - LOD-0 verbatim Hot Tail
        Strictly respects max_tokens / context_budget_tokens.
        """
        budget = max(64, int(max_tokens if max_tokens is not None else self.context_budget_tokens))
        frontier = self.tree.frontier_glyphs()
        truth_table = self.live_truth_table()
        anti_list = list(self.tree.anti_glyphs.values())

        # 1. Layer-3 Bloom MMU check on frontier + hierarchical leaf drill-down
        bloom_hits, bloom_us = (
            self.bloom_mmu.match_query(query, frontier)
            if (auto_prefetch and query and frontier)
            else ([], 0.0)
        )
        hit_ids = {h.glyph_id for h in bloom_hits}
        q_entities = extract_entities(query)
        for token in re.findall(r"[A-Za-z0-9_./:-]{6,}", query):
            if token not in q_entities:
                q_entities.append(token)

        prefetch_targets: Dict[str, str] = {}
        for gid in zoom_glyph_ids:
            prefetch_targets[gid] = "explicit_zoom"
        for hit in bloom_hits:
            f_node = self.tree.nodes.get(hit.glyph_id)
            if f_node is None:
                continue
            leaves = self._drill_matching_leaves(f_node, query, q_entities)
            for lf in leaves[:2]:
                prefetch_targets.setdefault(
                    lf.glyph_id, f"bloom_mmu({','.join(hit.matched_entities[:3])})"
                )

        # 2. Score frontier glyphs using Layer 1 + Layer 2 operator steering + Layer 3 Bloom hits
        q_vec, _ = self.embedder.embed(query) if query.strip() else (np.zeros(self.embedder.dim, dtype=np.float32), "none")
        scored_frontier: List[Tuple[float, TensorGlyph]] = []
        for g in frontier:
            if query.strip():
                steered_q = g.relational.apply(q_vec)
                sem_sim = max(g.semantic.similarity(q_vec), g.semantic.similarity(steered_q))
            else:
                sem_sim = 0.0
            b_score = 1.0 if g.glyph_id in hit_ids else 0.0
            c_score = min(1.0, len(g.relational.edges) / 5.0)
            s_score = 1.0 if g.relational.live_slots() else 0.0
            lod_score = 0.45 * max(0.0, sem_sim) + 0.30 * b_score + 0.15 * c_score + 0.10 * s_score
            scored_frontier.append((lod_score, g))
        scored_frontier.sort(key=lambda item: (-item[0], item[1].glyph_id))

        # 3. Render sections within strict token budget
        pinned_text = self.h1_op.render_frontier(
            [g for _, g in scored_frontier],
            truth_table=truth_table,
            anti_glyphs=anti_list,
            notation=self.tree.frontier_notation(),
        )
        pinned_tokens = estimate_tokens(pinned_text)
        # If pinned alone exceeds budget on tiny windows, compact summaries
        if pinned_tokens > int(budget * 0.55) and frontier:
            compact_lines = [f"=== L.O.G.O.S. PINNED GLYPHS [{self.tree.frontier_notation()}] ==="]
            for _, g in scored_frontier[:6]:
                stale_for_g = {
                    k: str(truth_table[k]["glyph_id"])
                    for k, v in g.relational.active_slots.items()
                    if k in truth_table and truth_table[k]["value"] != v
                }
                compact_lines.append(
                    self.h1_op.render_glyph(
                        g,
                        include_slots=True,
                        include_summary=False,
                        superseded_keys=stale_for_g,
                    )
                )
            if truth_table:
                compact_lines.append(
                    "ACTIVE_TRUTH_MASK: "
                    + "; ".join(f"{k}={v['value']}" for k, v in sorted(truth_table.items()))
                )
            for ag in anti_list[:4]:
                compact_lines.append(self.h1_op.render_anti_glyph(ag))
            pinned_text = "\n".join(compact_lines)
            pinned_tokens = estimate_tokens(pinned_text)

        remaining_tokens = max(0, budget - pinned_tokens)
        prefetch_cap = min(remaining_tokens, max(64, int(budget * self.prefetch_budget_ratio)))

        lod0_slices: List[HydratedSlice] = []
        prefetch_blocks: List[str] = []
        used_prefetch = 0
        for target_gid, trigger in prefetch_targets.items():
            avail = prefetch_cap - used_prefetch
            if avail <= 12:
                break
            max_slice_chars = max(80, min(1400, avail * 3))
            try:
                sl = self.hydrate(target_gid, query=query, max_chars=max_slice_chars, trigger=trigger)
            except (KeyError, ValueError):
                continue
            limit = remaining_tokens if used_prefetch == 0 else prefetch_cap
            if used_prefetch + sl.token_count <= limit:
                lod0_slices.append(sl)
                prefetch_blocks.append(
                    f"[HYDRATED {sl.glyph_id} via {sl.trigger} sha={sl.raw_sha256[:8]}]\n{sl.content}"
                )
                used_prefetch += sl.token_count

        tail_cap = max(0, remaining_tokens - used_prefetch)
        chosen_tail: List[TurnRecord] = []
        used_tail = 0
        for rec in reversed(self.active_turns):
            rendered_turn = rec.render()
            t_est = estimate_tokens(rendered_turn)
            if used_tail + t_est <= tail_cap:
                chosen_tail.insert(0, rec)
                used_tail += t_est
            else:
                break

        sections: List[str] = [pinned_text]
        if prefetch_blocks:
            sections.append("=== LOD-0 AUTO-PREFETCHED SLICES ===\n" + "\n---\n".join(prefetch_blocks))
        if chosen_tail:
            sections.append("=== LOD-0 VERBATIM HOT TAIL ===\n" + "\n".join(t.render() for t in chosen_tail))

        rendered_text = "\n\n".join(s for s in sections if s.strip())
        total_toks = estimate_tokens(rendered_text)
        # Hard guard: ensure total_tokens <= budget even for tiny toy budgets
        if total_toks > budget:
            char_cap = budget * 4
            rendered_text = rendered_text[:char_cap]
            total_toks = estimate_tokens(rendered_text)

        virtual_covered = self.total_ingested_tokens
        comp_ratio = virtual_covered / float(max(1, total_toks))

        return ViewportFrame(
            query=query,
            frontier_notation=self.tree.frontier_notation(),
            rendered_text=rendered_text,
            total_tokens=total_toks,
            budget_tokens=budget,
            virtual_tokens_covered=virtual_covered,
            compression_ratio=comp_ratio,
            lod0_hydrated=lod0_slices,
            lod1_glyphs=[g.glyph_id for _, g in scored_frontier if g.level == 1],
            lod2_glyphs=[g.glyph_id for _, g in scored_frontier if g.level >= 2],
            hot_tail_turn_ids=[t.turn_id for t in chosen_tail],
            bloom_hits=bloom_hits,
            bloom_latency_us=bloom_us,
            active_truth_table=truth_table,
        )
