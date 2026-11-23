"""G — Dual-Plane RYTT Geometry & Logarithmic Rollup Merkle-VSA Tree."""
from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from rytt.vsa import HV, VSAAccumulator

from ..layers.bloom_mmu import BloomFilter10240
from ..layers.compiler import LogosLayerCompiler, cycle_symbol_for
from ..layers.schema import (
    EpistemicTier,
    ProvenanceLayer,
    RelationalLayer,
    RelationEdge,
    RelationType,
    SemanticLayer,
    TensorGlyph,
    _l2_normalize,
)

_TIER_ORDER = {
    EpistemicTier.D: 3,
    EpistemicTier.P: 2,
    EpistemicTier.O: 1,
    EpistemicTier.F: 0,
}


def _svd_compress_operators(
    u_list: Sequence[np.ndarray],
    v_list: Sequence[np.ndarray],
    target_rank: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Fast QR+SVD rank-r approximation of (1/b) * sum_i U_i V_i^T in O(d * (b*r)^2).
    """
    d = u_list[0].shape[0]
    if target_rank <= 0 or not u_list:
        return np.zeros((d, target_rank), dtype=np.float32), np.zeros((d, target_rank), dtype=np.float32)

    scale = 1.0 / float(len(u_list))
    u_cat = np.concatenate(u_list, axis=1).astype(np.float64, copy=False)
    v_cat = np.concatenate(v_list, axis=1).astype(np.float64, copy=False)

    if np.allclose(u_cat, 0.0) or np.allclose(v_cat, 0.0):
        return np.zeros((d, target_rank), dtype=np.float32), np.zeros((d, target_rank), dtype=np.float32)

    q_u, r_u = np.linalg.qr(u_cat, mode="reduced")
    q_v, r_v = np.linalg.qr(v_cat, mode="reduced")
    core = scale * (r_u @ r_v.T)
    u_c, s_vals, vt_c = np.linalg.svd(core, full_matrices=False)

    k = min(target_rank, len(s_vals))
    sqrt_s = np.sqrt(np.maximum(s_vals[:k], 0.0))
    out_u = np.zeros((d, target_rank), dtype=np.float32)
    out_v = np.zeros((d, target_rank), dtype=np.float32)
    out_u[:, :k] = (q_u @ (u_c[:, :k] * sqrt_s[None, :])).astype(np.float32)
    out_v[:, :k] = (q_v @ (vt_c[:k, :].T * sqrt_s[None, :])).astype(np.float32)
    return out_u, out_v


class DualPlaneGlyphTree:
    """
    Append-only Dual-Plane RYTT Merkle-VSA Tree implementing 1r -> 2ry -> 3ryt -> 4rytt -> R.

    Ground-plane glyphs (level=1, lowercase `r,y,t,t,...`) roll up recursively into
    Elevated-plane meta-glyphs (level=2, uppercase `R,Y,T,T,...`) and Super-plane chords
    (level>=3) with fixed bounded fanout (2 <= fanout <= 8) to stay safely above VSA SNR limits.
    """

    def __init__(self, compiler: Optional[LogosLayerCompiler] = None, fanout: int = 4) -> None:
        if not (2 <= fanout <= 8):
            raise ValueError(
                f"fanout must be in [2, 8] to respect the VSA SNR capacity wall; got {fanout}"
            )
        self.compiler: LogosLayerCompiler = compiler or LogosLayerCompiler()
        self.fanout: int = int(fanout)
        self.nodes: Dict[str, TensorGlyph] = {}
        self.active_frontier: List[str] = []
        self.anti_glyphs: Dict[str, TensorGlyph] = {}
        self.bitemporal_ledger: Dict[str, List[Dict[str, Any]]] = {}
        self.vsa_accumulators: Dict[str, VSAAccumulator] = {}
        self._level_counters: Dict[int, int] = {}
        self._anti_counter: int = 0

    def _next_symbol_and_id(self, level: int) -> Tuple[str, str, str]:
        idx = self._level_counters.get(level, 0)
        self._level_counters[level] = idx + 1
        plane = "Ground" if level == 1 else ("Elevated" if level == 2 else "Super")
        lookup_plane = "Ground" if level == 1 else "Elevated"
        sym = cycle_symbol_for(idx, lookup_plane, cycle_len=self.fanout)
        prefix = "g" if level == 1 else ("E" if level == 2 else f"S{level}")
        return plane, sym, f"{prefix}{level}_{sym}_{idx:04d}"

    def _record_slots_bitemporal(self, glyph: TensorGlyph) -> None:
        """Register glyph slots and supersede any prior conflicting slot holders."""
        if glyph.is_anti_glyph or glyph.provenance.epistemic_tier == EpistemicTier.F:
            return

        now = float(glyph.created_at)
        # Check for inline natural-language supersession edges ("switched KEY from OLD to NEW")
        inline_prior: Dict[str, str] = {}
        for edge in glyph.relational.edges:
            if edge.relation == RelationType.SUPERSEDES and edge.key and edge.target_id.startswith("slot:"):
                parts = edge.target_id.split(":", 2)
                if len(parts) == 3 and parts[2]:
                    inline_prior[edge.key] = parts[2]

        for key, value in list(glyph.relational.active_slots.items()):
            history = self.bitemporal_ledger.setdefault(key, [])
            if not history and key in inline_prior and inline_prior[key] != value:
                history.append(
                    {
                        "glyph_id": f"{glyph.glyph_id}#prior",
                        "value": inline_prior[key],
                        "epistemic_tier": glyph.provenance.epistemic_tier.value,
                        "valid_from": max(0.0, now - 1e-3),
                        "valid_to": now,
                        "superseded_by": glyph.glyph_id,
                    }
                )
            for prev_entry in history:
                if prev_entry["superseded_by"] is None:
                    prev_id = prev_entry["glyph_id"]
                    prev_entry["superseded_by"] = glyph.glyph_id
                    prev_entry["valid_to"] = now
                    prev_node = self.nodes.get(prev_id)
                    if prev_node is not None:
                        prev_node.relational.superseded_slots[key] = glyph.glyph_id
                    glyph.relational.edges.append(
                        RelationEdge(
                            source_id=glyph.glyph_id,
                            target_id=prev_id,
                            relation=RelationType.SUPERSEDES,
                            key=key,
                            note=f"{key}: '{prev_entry['value']}' -> '{value}'",
                            timestamp=now,
                        )
                    )
            history.append(
                {
                    "glyph_id": glyph.glyph_id,
                    "value": value,
                    "epistemic_tier": glyph.provenance.epistemic_tier.value,
                    "valid_from": now,
                    "valid_to": None,
                    "superseded_by": None,
                }
            )

    def append_episode(
        self,
        episode_text: str,
        epistemic_tier: EpistemicTier = EpistemicTier.P,
        storage_uri: Optional[str] = None,
        explicit_slots: Optional[Dict[str, str]] = None,
        edges: Optional[List[RelationEdge]] = None,
        summary: Optional[str] = None,
        anti_reason: str = "",
    ) -> TensorGlyph:
        """Compile a raw episode into a Ground glyph (or Anti-Glyph) and update frontier."""
        if epistemic_tier == EpistemicTier.F or anti_reason:
            return self.register_anti_glyph(
                episode_text=episode_text,
                reason=anti_reason or "EpistemicTier.F quarantine",
                storage_uri=storage_uri,
            )

        idx = self._level_counters.get(1, 0)
        plane, _sym, glyph_id = self._next_symbol_and_id(level=1)
        glyph = self.compiler.compile_episode(
            episode_text=episode_text,
            glyph_id=glyph_id,
            slot_index=idx,
            plane=plane,
            level=1,
            epistemic_tier=epistemic_tier,
            storage_uri=storage_uri,
            explicit_slots=explicit_slots,
            edges=edges,
            summary=summary,
        )
        ext = getattr(self.compiler, "last_extraction", None)
        if ext is not None and ext.anti_claims:
            existing_claims = {ag.semantic.summary for ag in self.anti_glyphs.values()}
            for ac in ext.anti_claims:
                claim_tok = ac.get("claim", "")
                reason_txt = ac.get("reason", "Disproved in natural-language turn")
                summary_line = f"{claim_tok} rejected: {reason_txt}"
                if claim_tok and summary_line not in existing_claims:
                    self.register_anti_glyph(
                        episode_text=summary_line,
                        reason=reason_txt,
                        storage_uri=storage_uri,
                    )
                    existing_claims.add(summary_line)
        return self.append_ground_glyph(glyph)

    def append_ground_glyph(self, glyph: TensorGlyph) -> TensorGlyph:
        """Attach a pre-compiled Ground TensorGlyph and cascade fanout rollups."""
        if glyph.is_anti_glyph or glyph.provenance.epistemic_tier == EpistemicTier.F:
            self.anti_glyphs[glyph.glyph_id] = glyph
            return glyph

        if glyph.glyph_id in self.nodes:
            raise ValueError(f"Duplicate glyph_id {glyph.glyph_id!r}")

        self.nodes[glyph.glyph_id] = glyph
        acc = VSAAccumulator()
        acc.add(HV.from_seed(glyph.content_digest()))
        self.vsa_accumulators[glyph.glyph_id] = acc

        self._record_slots_bitemporal(glyph)
        self.active_frontier.append(glyph.glyph_id)
        self._cascade_rollup()
        return glyph

    def register_anti_glyph(
        self,
        episode_text: str,
        reason: str,
        storage_uri: Optional[str] = None,
    ) -> TensorGlyph:
        """Record an explicit dead-end / failure mask without polluting active slots."""
        idx = self._anti_counter
        self._anti_counter += 1
        glyph_id = f"anti_{idx:04d}"
        glyph = self.compiler.compile_episode(
            episode_text=episode_text,
            glyph_id=glyph_id,
            slot_index=idx,
            plane="Ground",
            level=1,
            epistemic_tier=EpistemicTier.F,
            storage_uri=storage_uri,
            anti_reason=reason,
        )
        self.anti_glyphs[glyph_id] = glyph
        return glyph

    def _build_parent_glyph(self, children: Sequence[TensorGlyph], target_level: int) -> TensorGlyph:
        slot_idx = self._level_counters.get(target_level, 0)
        plane, sym, parent_id = self._next_symbol_and_id(target_level)
        lookup_sym = sym if target_level == 2 else sym.upper()
        pua, geom_vec = self.compiler.rytt_metadata_for(lookup_sym)

        # Layer 1: centroid semantic vector + merged summary & keywords
        sem_vecs = np.stack([c.semantic.vector for c in children], axis=0)
        mean_vec = _l2_normalize(sem_vecs.mean(axis=0))
        summary = " | ".join(f"[{c.symbol}:{c.glyph_id}] {c.semantic.summary}" for c in children)
        if len(summary) > 480:
            summary = summary[:477].rstrip() + "..."
        kw_counts: Dict[str, int] = {}
        for c in children:
            for kw in c.semantic.keywords:
                kw_counts[kw] = kw_counts.get(kw, 0) + 1
        top_kw = tuple(k for k, _ in sorted(kw_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:8])
        semantic = SemanticLayer(
            vector=mean_vec,
            summary=summary,
            keywords=top_kw,
            backend=children[0].semantic.backend,
        )

        # Layer 2: live slots (excluding superseded keys), child edges, and compressed rank-r operator
        live_slots: Dict[str, str] = {}
        superseded: Dict[str, str] = {}
        edges: List[RelationEdge] = []
        now = time.time()
        for c in children:
            for k, v in c.relational.active_slots.items():
                if self._is_key_superseded_after(k, c.glyph_id):
                    superseded[k] = self.bitemporal_ledger[k][-1]["glyph_id"]
                else:
                    live_slots[k] = v
            edges.append(
                RelationEdge(
                    source_id=parent_id,
                    target_id=c.glyph_id,
                    relation=RelationType.DERIVED_FROM,
                    weight=1.0,
                    note=f"rollup L{c.level}->{target_level}",
                    timestamp=now,
                )
            )
            edges.extend(c.relational.edges[:4])

        # Filter out slots that are currently held by a newer node globally
        active_truth = {k: v["glyph_id"] for k, v in self.active_truth_table().items()}
        merged_active = {
            k: v for k, v in live_slots.items() if active_truth.get(k) in {c.glyph_id for c in children} or k not in active_truth
        }
        op_u, op_v = _svd_compress_operators(
            [c.relational.operator_u for c in children],
            [c.relational.operator_v for c in children],
            target_rank=self.compiler.rank,
        )
        relational = RelationalLayer(
            edges=edges,
            state_deltas=dict(merged_active),
            active_slots=merged_active,
            superseded_slots=superseded,
            operator_u=op_u,
            operator_v=op_v,
        )

        # Layer 3: Merkle digest + exact bitwise OR union of child Bloom filters + int32 VSA merge
        merkle_material = ":".join(c.content_digest() for c in children).encode("utf-8")
        merkle_sha = hashlib.sha256(merkle_material).hexdigest()
        union_bloom = BloomFilter10240.union(
            BloomFilter10240.from_bytes(c.provenance.bloom_bytes) for c in children
        )
        min_tier = min(
            (c.provenance.epistemic_tier for c in children),
            key=lambda t: _TIER_ORDER.get(t, 0),
        )
        provenance = ProvenanceLayer(
            raw_sha256=merkle_sha,
            raw_token_count=sum(c.provenance.raw_token_count for c in children),
            raw_char_count=sum(c.provenance.raw_char_count for c in children),
            storage_uri=f"logos://merkle/{merkle_sha}",
            bloom_bytes=union_bloom.to_bytes(),
            entity_count=sum(c.provenance.entity_count for c in children),
            epistemic_tier=min_tier,
            parent_ids=(),
            child_ids=tuple(c.glyph_id for c in children),
        )

        parent = TensorGlyph(
            glyph_id=parent_id,
            symbol=lookup_sym,
            plane=plane,
            level=target_level,
            rytt_pua=pua,
            geometric_vec=geom_vec,
            semantic=semantic,
            relational=relational,
            provenance=provenance,
            created_at=now,
        )
        self.nodes[parent_id] = parent

        parent_acc = VSAAccumulator()
        for child_idx, child in enumerate(children):
            child.provenance.parent_ids = child.provenance.parent_ids + (parent_id,)
            pos_hv = HV.from_seed(f"child_{child_idx}")
            child_hv = HV.from_seed(child.content_digest())
            parent_acc.add(pos_hv ^ child_hv)
        self.vsa_accumulators[parent_id] = parent_acc
        return parent

    def _is_key_superseded_after(self, key: str, glyph_id: str) -> bool:
        for entry in self.bitemporal_ledger.get(key, []):
            if entry["glyph_id"] == glyph_id:
                return entry["superseded_by"] is not None
        return False

    def _cascade_rollup(self) -> None:
        while True:
            rolled = False
            levels = sorted({self.nodes[gid].level for gid in self.active_frontier})
            for lvl in levels:
                run_indices: List[int] = []
                for idx, gid in enumerate(self.active_frontier):
                    if self.nodes[gid].level == lvl:
                        run_indices.append(idx)
                        if len(run_indices) == self.fanout:
                            child_ids = [self.active_frontier[i] for i in run_indices]
                            children = [self.nodes[cid] for cid in child_ids]
                            parent = self._build_parent_glyph(children, target_level=lvl + 1)
                            first, last = run_indices[0], run_indices[-1]
                            self.active_frontier = (
                                self.active_frontier[:first]
                                + [parent.glyph_id]
                                + self.active_frontier[last + 1 :]
                            )
                            rolled = True
                            break
                    else:
                        run_indices = []
                if rolled:
                    break
            if not rolled:
                break

    def frontier_glyphs(self) -> List[TensorGlyph]:
        return [self.nodes[gid] for gid in self.active_frontier]

    def frontier_notation(self, use_pua: bool = False) -> str:
        """Compact shorthand mirror of 1r -> 2ry -> 3ryt -> 1R -> 1R+2ry (or actual PUA glyphs when use_pua=True)."""
        if not self.active_frontier:
            return "0"
        by_level: Dict[int, List[str]] = {}
        for gid in self.active_frontier:
            node = self.nodes[gid]
            char = node.rytt_pua if use_pua else node.symbol
            by_level.setdefault(node.level, []).append(char)
        parts: List[str] = []
        for lvl in sorted(by_level.keys(), reverse=True):
            syms = "".join(by_level[lvl])
            if lvl <= 2:
                parts.append(f"{len(syms)}{syms}")
            else:
                parts.append(f"{len(syms)}{syms}^L{lvl}")
        return "+".join(parts)

    def pua_frontier_notation(self) -> str:
        """Frontier notation rendered in genuine Unicode PUA glyphs (U+E000..U+E019 / U+E800..U+E819 / chords)."""
        return self.frontier_notation(use_pua=True)

    def pua_frontier_hex(self) -> str:
        """Frontier rendered as hex codepoints (e.g. '[U+E011, U+E018]')."""
        if not self.active_frontier:
            return "[]"
        codepoints = [
            f"U+{ord(self.nodes[gid].rytt_pua):04X}"
            for gid in self.active_frontier
            if gid in self.nodes and self.nodes[gid].rytt_pua
        ]
        return f"[{', '.join(codepoints)}]"

    def drill_down(self, glyph_id: str) -> List[TensorGlyph]:
        node = self.nodes.get(glyph_id)
        if node is None:
            return []
        if not node.provenance.child_ids:
            return [node]
        return [self.nodes[cid] for cid in node.provenance.child_ids if cid in self.nodes]

    def get_leaves(self, glyph_id: Optional[str] = None) -> List[TensorGlyph]:
        if glyph_id is None:
            return [n for n in self.nodes.values() if n.level == 1]
        out: List[TensorGlyph] = []
        stack = [glyph_id]
        visited: set[str] = set()
        while stack:
            cur = stack.pop(0)
            if cur in visited or cur not in self.nodes:
                continue
            visited.add(cur)
            node = self.nodes[cur]
            if not node.provenance.child_ids:
                out.append(node)
            else:
                stack = list(node.provenance.child_ids) + stack
        return out

    def active_truth_table(self) -> Dict[str, Dict[str, Any]]:
        """Current latest non-superseded value for every tracked state slot."""
        table: Dict[str, Dict[str, Any]] = {}
        for key, history in self.bitemporal_ledger.items():
            live = [entry for entry in history if entry["superseded_by"] is None]
            if live:
                latest = live[-1]
                table[key] = {
                    "value": latest["value"],
                    "glyph_id": latest["glyph_id"],
                    "epistemic_tier": latest["epistemic_tier"],
                    "revisions": len(history),
                }
        return table

    def _mean_elevated_intra_cosine(self) -> float:
        """Compute mean pairwise cosine similarity among children of Level-2 Elevated nodes."""
        l2_nodes = [n for n in self.nodes.values() if n.level == 2 and len(n.provenance.child_ids) >= 2]
        if not l2_nodes:
            return 0.0
        scores: List[float] = []
        for parent in l2_nodes:
            children = [self.nodes[cid] for cid in parent.provenance.child_ids if cid in self.nodes]
            if len(children) < 2:
                continue
            for i in range(len(children)):
                for j in range(i + 1, len(children)):
                    sim = float(np.dot(children[i].semantic.vector, children[j].semantic.vector))
                    scores.append(sim)
        return float(sum(scores) / len(scores)) if scores else 0.0

    def sleep_consolidate(self) -> Dict[str, Any]:
        """
        Offline Sleep / Idle Consolidation:
        Re-clusters Ground leaves (`level == 1`) into semantically tighter Elevated chords
        via greedy cosine similarity clustering with bounded fanout `2 <= b <= self.fanout`,
        while keeping every Layer-3 raw SHA-256 block immutable, preserving bitemporal truth
        slots, and satisfying 100% Merkle + Bloom superset invariants.
        """
        leaves = sorted(
            [n for n in self.nodes.values() if n.level == 1],
            key=lambda g: (float(g.created_at), g.glyph_id),
        )
        frontier_before = self.frontier_notation()
        coherence_before = self._mean_elevated_intra_cosine()

        if len(leaves) < 2:
            integrity = self.verify_integrity()
            return {
                "consolidated": False,
                "leaf_count": len(leaves),
                "clusters_formed": 0,
                "frontier_before": frontier_before,
                "frontier_after": frontier_before,
                "mean_intra_cluster_cosine_before": round(coherence_before, 4),
                "mean_intra_cluster_cosine_after": round(coherence_before, 4),
                "coherence_gain": 0.0,
                "raw_sha256_preserved": True,
                "truth_slots_preserved": True,
                "integrity": integrity,
            }

        orig_leaf_shas = {lf.glyph_id: lf.provenance.raw_sha256 for lf in leaves}
        truth_before = self.active_truth_table()

        # Reset non-leaf rollup nodes and rebuild from immutable Ground leaves
        self.nodes = {}
        self.vsa_accumulators = {}
        self.active_frontier = []
        for lvl in list(self._level_counters.keys()):
            if lvl >= 2:
                self._level_counters[lvl] = 0

        for lf in leaves:
            lf.provenance.parent_ids = ()
            self.nodes[lf.glyph_id] = lf
            acc = VSAAccumulator()
            acc.add(HV.from_seed(lf.content_digest()))
            self.vsa_accumulators[lf.glyph_id] = acc

        # Greedy semantic cosine clustering with bounded fanout 2 <= b <= self.fanout
        pool = list(leaves)
        clusters: List[List[TensorGlyph]] = []
        while len(pool) >= 2:
            rem = len(pool)
            if rem >= self.fanout:
                # Avoid leaving a single orphan leaf if rem == self.fanout + 1 and fanout >= 3
                if rem == self.fanout + 1 and self.fanout >= 3:
                    b = self.fanout - 1
                else:
                    b = self.fanout
            else:
                b = rem

            anchor = pool.pop(0)
            ranked = sorted(
                pool,
                key=lambda cand: (-float(np.dot(anchor.semantic.vector, cand.semantic.vector)), cand.glyph_id),
            )
            chosen = ranked[: b - 1]
            chosen_ids = {c.glyph_id for c in chosen}
            pool = [c for c in pool if c.glyph_id not in chosen_ids]
            clusters.append([anchor] + chosen)

        l2_parents: List[TensorGlyph] = []
        for cluster in clusters:
            parent = self._build_parent_glyph(cluster, target_level=2)
            l2_parents.append(parent)

        self.active_frontier = [p.glyph_id for p in l2_parents] + [r.glyph_id for r in pool]
        self._cascade_rollup()

        coherence_after = self._mean_elevated_intra_cosine()
        shas_ok = all(self.nodes[gid].provenance.raw_sha256 == sha for gid, sha in orig_leaf_shas.items())
        truth_ok = self.active_truth_table() == truth_before
        integrity = self.verify_integrity()

        return {
            "consolidated": True,
            "leaf_count": len(leaves),
            "clusters_formed": len(clusters),
            "frontier_before": frontier_before,
            "frontier_after": self.frontier_notation(),
            "mean_intra_cluster_cosine_before": round(coherence_before, 4),
            "mean_intra_cluster_cosine_after": round(coherence_after, 4),
            "coherence_gain": round(coherence_after - coherence_before, 4),
            "raw_sha256_preserved": shas_ok,
            "truth_slots_preserved": truth_ok,
            "integrity": integrity,
        }

    def verify_integrity(self) -> Dict[str, Any]:
        """Verify Merkle child hashes, Bloom superset containment, and DAG acyclicity."""
        errors: List[str] = []
        merkle_checked = 0
        bloom_checked = 0

        for gid, node in self.nodes.items():
            if not node.provenance.child_ids:
                continue
            children = [self.nodes[cid] for cid in node.provenance.child_ids if cid in self.nodes]
            if len(children) != len(node.provenance.child_ids):
                errors.append(f"Missing child reference under {gid}")
                continue

            expected_sha = hashlib.sha256(
                ":".join(c.content_digest() for c in children).encode("utf-8")
            ).hexdigest()
            merkle_checked += 1
            if expected_sha != node.provenance.raw_sha256:
                errors.append(f"Merkle mismatch at {gid}")

            parent_bloom = BloomFilter10240.from_bytes(node.provenance.bloom_bytes)
            for child in children:
                child_bloom = BloomFilter10240.from_bytes(child.provenance.bloom_bytes)
                bloom_checked += 1
                if not parent_bloom.is_superset_of(child_bloom):
                    errors.append(f"Bloom superset violation: {child.glyph_id} -> {gid}")

        # Cycle check
        visiting: set[str] = set()
        visited: set[str] = set()

        def _dfs(cur: str) -> bool:
            if cur in visiting:
                return False
            if cur in visited or cur not in self.nodes:
                return True
            visiting.add(cur)
            for cid in self.nodes[cur].provenance.child_ids:
                if not _dfs(cid):
                    return False
            visiting.remove(cur)
            visited.add(cur)
            return True

        acyclic = all(_dfs(gid) for gid in self.nodes)
        if not acyclic:
            errors.append("Cycle detected in DualPlaneGlyphTree")

        return {
            "valid": not errors,
            "errors": errors,
            "total_nodes": len(self.nodes),
            "frontier_count": len(self.active_frontier),
            "anti_glyph_count": len(self.anti_glyphs),
            "merkle_checked": merkle_checked,
            "bloom_checked": bloom_checked,
            "acyclic": acyclic,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fanout": self.fanout,
            "active_frontier": list(self.active_frontier),
            "level_counters": {str(k): int(v) for k, v in self._level_counters.items()},
            "anti_counter": int(self._anti_counter),
            "nodes": {gid: node.to_dict() for gid, node in self.nodes.items()},
            "anti_glyphs": {gid: node.to_dict() for gid, node in self.anti_glyphs.items()},
            "bitemporal_ledger": self.bitemporal_ledger,
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        compiler: Optional[LogosLayerCompiler] = None,
    ) -> "DualPlaneGlyphTree":
        tree = cls(compiler=compiler, fanout=int(data["fanout"]))
        tree.active_frontier = list(data.get("active_frontier", []))
        tree._level_counters = {int(k): int(v) for k, v in data.get("level_counters", {}).items()}
        tree._anti_counter = int(data.get("anti_counter", 0))
        tree.nodes = {gid: TensorGlyph.from_dict(nd) for gid, nd in data.get("nodes", {}).items()}
        tree.anti_glyphs = {
            gid: TensorGlyph.from_dict(nd) for gid, nd in data.get("anti_glyphs", {}).items()
        }
        tree.bitemporal_ledger = dict(data.get("bitemporal_ledger", {}))
        return tree
