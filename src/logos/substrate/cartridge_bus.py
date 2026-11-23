"""Horizon 3 Completion: Sovereign Multi-Agent Bitemporal `.logos` Cartridge Merge Bus."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..glyphs.tree import DualPlaneGlyphTree, _TIER_ORDER
from ..layers.embedder import build_embedder
from ..layers.schema import EpistemicTier, RelationEdge, RelationType, TensorGlyph
from ..orchestrator.splitter import TurnRecord
from .cartridge import export_cartridge, load_cartridge, verify_cartridge
from .store import LogosSubstrate


def _tier_rank(tier_val: str | EpistemicTier) -> int:
    try:
        t = tier_val if isinstance(tier_val, EpistemicTier) else EpistemicTier(str(tier_val))
    except ValueError:
        t = EpistemicTier.O
    return _TIER_ORDER.get(t, 0)


def merge_cartridges(
    path_a: str | Path,
    path_b: str | Path,
    output_path: str | Path,
    fanout: Optional[int] = None,
    consolidate: bool = False,
) -> Dict[str, Any]:
    """
    Deterministic CRDT / Bitemporal merge of two `.logos` cartridges authored independently:
      1. Fail-closed verification of both input cartridges (`verify_cartridge`).
      2. Content-addressed deduplication of identical raw blocks by `raw_sha256`.
      3. Ground leaf union (`level == 1`) with deterministic ordering by `(created_at, raw_sha256, glyph_id)`
         plus merged Anti-Glyph quarantines (`EpistemicTier.F`).
      4. Deterministic slot conflict resolution by `(epistemic_tier_rank, timestamp, glyph_id)`
         while preserving complete historical revision chains in `bitemporal_ledger`.
      5. Clean Dual-Plane rollup tree reconstruction (+ optional `sleep_consolidate()`) and
         fail-closed verification of the resulting merged `.logos` cartridge.
    """
    from ..orchestrator.viewport import LogosOrchestrator

    cart_a = load_cartridge(path_a)
    cart_b = load_cartridge(path_b)

    manifest_a = cart_a["manifest"]
    manifest_b = cart_b["manifest"]
    chosen_fanout = int(fanout or manifest_a.get("fanout", manifest_b.get("fanout", 4)))
    chosen_budget = max(
        int(manifest_a.get("context_budget_tokens", 250_000)),
        int(manifest_b.get("context_budget_tokens", 250_000)),
    )

    # 1. Deduplicate raw blocks by SHA-256 (keep earliest timestamp and highest epistemic tier)
    raw_by_sha: Dict[str, Dict[str, Any]] = {}
    for blk in cart_a["raw_blocks"] + cart_b["raw_blocks"]:
        sha = str(blk["raw_sha256"])
        if sha not in raw_by_sha:
            raw_by_sha[sha] = dict(blk)
        else:
            existing = raw_by_sha[sha]
            if float(blk.get("created_at", 0.0)) < float(existing.get("created_at", 0.0)):
                existing["created_at"] = blk["created_at"]
            if _tier_rank(str(blk.get("epistemic_tier", "P"))) > _tier_rank(str(existing.get("epistemic_tier", "P"))):
                existing["epistemic_tier"] = blk["epistemic_tier"]

    substrate = LogosSubstrate(":memory:")
    for sha in sorted(raw_by_sha.keys()):
        blk = raw_by_sha[sha]
        substrate.put_raw_block(
            content=str(blk["content"]),
            token_count=int(blk["token_count"]),
            epistemic_tier=str(blk.get("epistemic_tier", "P")),
            storage_uri=str(blk.get("storage_uri", f"logos://raw/{sha}")),
        )

    embedder = build_embedder(use_ollama=False)
    orch = LogosOrchestrator(
        substrate=substrate,
        embedder=embedder,
        fanout=chosen_fanout,
        context_budget_tokens=chosen_budget,
    )

    tree_a = DualPlaneGlyphTree.from_dict(cart_a["tree_dict"], compiler=orch.compiler)
    tree_b = DualPlaneGlyphTree.from_dict(cart_b["tree_dict"], compiler=orch.compiler)

    # 2. Collect Ground leaves from both trees, deduplicating identical leaf content digests
    leaves_a = [n for n in tree_a.nodes.values() if n.level == 1]
    leaves_b = [n for n in tree_b.nodes.values() if n.level == 1]

    seen_leaf_keys: set[Tuple[str, Tuple[Tuple[str, str], ...]]] = set()
    merged_leaves: List[TensorGlyph] = []
    for lf in sorted(leaves_a + leaves_b, key=lambda g: (float(g.created_at), g.provenance.raw_sha256, g.glyph_id)):
        dedup_key = (lf.provenance.raw_sha256, tuple(sorted(lf.relational.state_deltas.items())))
        if dedup_key in seen_leaf_keys:
            continue
        seen_leaf_keys.add(dedup_key)
        merged_leaves.append(lf)

    # 3. Re-index and append Ground leaves into clean DualPlaneGlyphTree
    old_to_new_id: Dict[str, str] = {}
    for idx, lf in enumerate(merged_leaves):
        plane, sym, new_gid = orch.tree._next_symbol_and_id(level=1)
        pua, geom_vec = orch.compiler.rytt_metadata_for(sym)
        old_to_new_id[lf.glyph_id] = new_gid

        # Clone leaf with fresh canonical ID and cleared parent_ids / superseded_slots
        clean_edges = [
            e for e in lf.relational.edges if e.relation != RelationType.SUPERSEDES
        ]
        cloned_leaf = TensorGlyph(
            glyph_id=new_gid,
            symbol=sym,
            plane=plane,
            level=1,
            rytt_pua=pua,
            geometric_vec=geom_vec,
            semantic=lf.semantic,
            relational=type(lf.relational)(
                edges=clean_edges,
                state_deltas=dict(lf.relational.state_deltas),
                active_slots=dict(lf.relational.state_deltas) if not lf.is_anti_glyph else {},
                superseded_slots={},
                operator_u=lf.relational.operator_u.copy(),
                operator_v=lf.relational.operator_v.copy(),
            ),
            provenance=type(lf.provenance)(
                raw_sha256=lf.provenance.raw_sha256,
                raw_token_count=lf.provenance.raw_token_count,
                raw_char_count=lf.provenance.raw_char_count,
                storage_uri=lf.provenance.storage_uri,
                bloom_bytes=lf.provenance.bloom_bytes,
                entity_count=lf.provenance.entity_count,
                epistemic_tier=lf.provenance.epistemic_tier,
                parent_ids=(),
                child_ids=(),
            ),
            created_at=float(lf.created_at),
            is_anti_glyph=False,
            anti_reason="",
            tombstoned=False,
        )
        orch.tree.nodes[new_gid] = cloned_leaf

    # 4. Merge and resolve bitemporal slot history deterministically by (epistemic_tier_rank, timestamp, glyph_id)
    raw_histories: Dict[str, List[Dict[str, Any]]] = {}
    for src_tree in (tree_a, tree_b):
        for slot_key, entries in src_tree.bitemporal_ledger.items():
            for entry in entries:
                mapped_gid = old_to_new_id.get(str(entry["glyph_id"]), str(entry["glyph_id"]))
                raw_histories.setdefault(slot_key, []).append(
                    {
                        "glyph_id": mapped_gid,
                        "value": str(entry["value"]),
                        "epistemic_tier": str(entry.get("epistemic_tier", "P")),
                        "valid_from": float(entry.get("valid_from", 0.0)),
                    }
                )
    # Also ensure every Ground leaf's state_deltas are represented in raw_histories
    for gid, lf in orch.tree.nodes.items():
        for slot_key, val in lf.relational.state_deltas.items():
            raw_histories.setdefault(slot_key, []).append(
                {
                    "glyph_id": gid,
                    "value": str(val),
                    "epistemic_tier": lf.provenance.epistemic_tier.value,
                    "valid_from": float(lf.created_at),
                }
            )
    # Also include active hot-tail turn slots from both cartridges in bitemporal conflict resolution
    for agent_tag, m_dict in (("agentA", manifest_a), ("agentB", manifest_b)):
        for t_dict in m_dict.get("active_turns", []):
            rec = TurnRecord.from_dict(t_dict)
            if rec.epistemic_tier == EpistemicTier.F:
                continue
            for slot_key, val in rec.explicit_slots.items():
                raw_histories.setdefault(slot_key, []).append(
                    {
                        "glyph_id": f"{agent_tag}_hot_tail#t{rec.turn_id}",
                        "value": str(val),
                        "epistemic_tier": rec.epistemic_tier.value,
                        "valid_from": float(rec.timestamp),
                    }
                )

    conflicts_resolved = 0
    merged_ledger: Dict[str, List[Dict[str, Any]]] = {}
    for slot_key, candidates in sorted(raw_histories.items()):
        # Deduplicate identical (glyph_id, value) revision entries
        dedup_cands: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for c in candidates:
            ck = (c["glyph_id"], c["value"])
            if ck not in dedup_cands:
                dedup_cands[ck] = c
            else:
                if _tier_rank(c["epistemic_tier"]) > _tier_rank(dedup_cands[ck]["epistemic_tier"]):
                    dedup_cands[ck]["epistemic_tier"] = c["epistemic_tier"]

        # Deterministic ordering: (epistemic_tier_rank, valid_from, glyph_id)
        # Highest rank & timestamp is placed last as the winning live truth; earlier/lower-tier entries precede it
        ordered = sorted(
            dedup_cands.values(),
            key=lambda item: (
                _tier_rank(item["epistemic_tier"]),
                float(item["valid_from"]),
                str(item["glyph_id"]),
            ),
        )
        if len({c["value"] for c in ordered}) > 1:
            conflicts_resolved += 1

        chain: List[Dict[str, Any]] = []
        for idx, item in enumerate(ordered):
            is_last = idx == len(ordered) - 1
            next_item = ordered[idx + 1] if not is_last else None
            chain.append(
                {
                    "glyph_id": item["glyph_id"],
                    "value": item["value"],
                    "epistemic_tier": item["epistemic_tier"],
                    "valid_from": float(item["valid_from"]),
                    "valid_to": float(next_item["valid_from"]) if next_item is not None else None,
                    "superseded_by": str(next_item["glyph_id"]) if next_item is not None else None,
                }
            )
            if not is_last:
                holder = orch.tree.nodes.get(item["glyph_id"])
                if holder is not None and next_item is not None:
                    holder.relational.superseded_slots[slot_key] = str(next_item["glyph_id"])
                    winner = orch.tree.nodes.get(str(next_item["glyph_id"]))
                    if winner is not None:
                        winner.relational.edges.append(
                            RelationEdge(
                                source_id=winner.glyph_id,
                                target_id=holder.glyph_id,
                                relation=RelationType.SUPERSEDES,
                                key=slot_key,
                                note=f"{slot_key}: '{item['value']}' -> '{next_item['value']}'",
                                timestamp=float(next_item["valid_from"]),
                            )
                        )
        merged_ledger[slot_key] = chain

    orch.tree.bitemporal_ledger = merged_ledger

    # 5. Cascade Dual-Plane rollups over merged Ground leaves (or run sleep_consolidate)
    from rytt.vsa import HV, VSAAccumulator

    for gid in sorted(orch.tree.nodes.keys()):
        node = orch.tree.nodes[gid]
        acc = VSAAccumulator()
        acc.add(HV.from_seed(node.content_digest()))
        orch.tree.vsa_accumulators[gid] = acc
        orch.tree.active_frontier.append(gid)
        orch.tree._cascade_rollup()

    if consolidate:
        orch.tree.sleep_consolidate()

    # 6. Merge Anti-Glyph quarantines deduplicated by raw_sha256
    seen_anti_sha: set[str] = set()
    for ag in list(tree_a.anti_glyphs.values()) + list(tree_b.anti_glyphs.values()):
        if ag.provenance.raw_sha256 in seen_anti_sha:
            continue
        seen_anti_sha.add(ag.provenance.raw_sha256)
        idx = orch.tree._anti_counter
        orch.tree._anti_counter += 1
        ag_id = f"anti_{idx:04d}"
        cloned_ag = TensorGlyph(
            glyph_id=ag_id,
            symbol=ag.symbol,
            plane="Ground",
            level=1,
            rytt_pua=ag.rytt_pua,
            geometric_vec=ag.geometric_vec.copy(),
            semantic=ag.semantic,
            relational=ag.relational,
            provenance=ag.provenance,
            created_at=float(ag.created_at),
            is_anti_glyph=True,
            anti_reason=ag.anti_reason,
            tombstoned=True,
        )
        orch.tree.anti_glyphs[ag_id] = cloned_ag

    # 7. Merge active hot-tail turns (deduplicating identical role + content and pruning slots resolved by higher tier)
    winning_values = {k: v["value"] for k, v in orch.tree.active_truth_table().items()}
    turns_a = [TurnRecord.from_dict(t) for t in manifest_a.get("active_turns", [])]
    turns_b = [TurnRecord.from_dict(t) for t in manifest_b.get("active_turns", [])]
    seen_turns: set[Tuple[str, str]] = set()
    merged_turns: List[TurnRecord] = []
    for t in sorted(turns_a + turns_b, key=lambda rec: (float(rec.timestamp), int(rec.turn_id))):
        tk = (t.role, t.content)
        if tk in seen_turns:
            continue
        seen_turns.add(tk)
        t.turn_id = len(merged_turns) + 1
        t.explicit_slots = {
            k: v for k, v in t.explicit_slots.items() if winning_values.get(k, v) == v
        }
        merged_turns.append(t)

    orch.active_turns = merged_turns
    orch._turn_counter = len(merged_turns)
    orch.total_ingested_tokens = sum(int(b["token_count"]) for b in raw_by_sha.values())
    orch._persist_tree_nodes()

    out_file = export_cartridge(orch, output_path)
    verification = verify_cartridge(out_file)
    if not verification["valid"]:
        raise ValueError(f"Merged cartridge failed verification: {verification['errors']}")

    return {
        "valid": True,
        "output_path": str(out_file),
        "raw_blocks_a": len(cart_a["raw_blocks"]),
        "raw_blocks_b": len(cart_b["raw_blocks"]),
        "raw_blocks_merged": len(raw_by_sha),
        "raw_blocks_deduplicated": (len(cart_a["raw_blocks"]) + len(cart_b["raw_blocks"])) - len(raw_by_sha),
        "ground_leaves_merged": len(merged_leaves),
        "total_nodes_merged": len(orch.tree.nodes),
        "anti_glyphs_merged": len(orch.tree.anti_glyphs),
        "frontier_notation": orch.tree.frontier_notation(),
        "conflicts_resolved": conflicts_resolved,
        "active_truth_table": orch.tree.active_truth_table(),
        "verification": verification,
    }
