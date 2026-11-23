"""Unified High-Level LogosSession Facade with SQLite Persistence & Cartridge Recovery."""
from __future__ import annotations

from pathlib import Path
import json
from typing import Any, Dict, List, Optional, Sequence

from .glyphs.tree import DualPlaneGlyphTree
from .layers.bloom_mmu import BLOOM_BITS, BloomFilter10240
from .layers.embedder import build_embedder
from .layers.schema import EpistemicTier
from .orchestrator.splitter import TurnRecord
from .orchestrator.viewport import HydratedSlice, LogosOrchestrator, ViewportFrame
from .substrate.cartridge import export_cartridge, load_cartridge, verify_cartridge
from .substrate.cartridge_bus import merge_cartridges
from .substrate.store import LogosSubstrate


class LogosSession:
    """High-level persistent session API wrapping the 5-part L.O.G.O.S. stack."""

    def __init__(
        self,
        orchestrator: Optional[LogosOrchestrator] = None,
        db_path: str | Path = ":memory:",
        use_ollama: bool = False,
        fanout: int = 4,
        context_budget_tokens: int = 250_000,
    ) -> None:
        if orchestrator is not None:
            self.orchestrator = orchestrator
        else:
            substrate = LogosSubstrate(db_path)
            embedder = build_embedder(use_ollama=use_ollama)
            self.orchestrator = LogosOrchestrator(
                substrate=substrate,
                embedder=embedder,
                fanout=fanout,
                context_budget_tokens=context_budget_tokens,
            )

    @classmethod
    def from_db(
        cls,
        db_path: str | Path,
        use_ollama: bool = False,
        fanout: int = 4,
        context_budget_tokens: int = 250_000,
    ) -> "LogosSession":
        substrate = LogosSubstrate(db_path)
        embedder = build_embedder(use_ollama=use_ollama)
        saved = substrate.get_meta("logos_session_state")
        if saved is not None:
            budget = int(saved.get("context_budget_tokens", context_budget_tokens))
            saved_fanout = int(saved.get("tree", {}).get("fanout", fanout))
            orch = LogosOrchestrator(
                substrate=substrate,
                embedder=embedder,
                fanout=saved_fanout,
                context_budget_tokens=budget,
            )
            orch.tree = DualPlaneGlyphTree.from_dict(saved["tree"], compiler=orch.compiler)
            orch.active_turns = [TurnRecord.from_dict(t) for t in saved.get("active_turns", [])]
            orch._turn_counter = int(saved.get("turn_counter", len(orch.active_turns)))
            orch.total_ingested_tokens = int(saved.get("total_ingested_tokens", 0))
            orch.flush_count = int(saved.get("flush_count", 0))
            for g in orch.tree.frontier_glyphs():
                orch.kv_bank.allocate_slot(g, orch.h2_projector.compile_kv_glyph(g))
            return cls(orchestrator=orch)

        return cls(
            db_path=db_path,
            use_ollama=use_ollama,
            fanout=fanout,
            context_budget_tokens=context_budget_tokens,
        )

    def save(self) -> None:
        orch = self.orchestrator
        state = {
            "context_budget_tokens": orch.context_budget_tokens,
            "turn_counter": orch._turn_counter,
            "total_ingested_tokens": orch.total_ingested_tokens,
            "flush_count": orch.flush_count,
            "active_turns": [t.to_dict() for t in orch.active_turns],
            "tree": orch.tree.to_dict(),
        }
        orch.substrate.set_meta("logos_session_state", state)

    def ingest(
        self,
        role: str,
        content: str,
        epistemic_tier: str | EpistemicTier = EpistemicTier.P,
        explicit_slots: Optional[Dict[str, str]] = None,
        anti_reason: str = "",
        autosave: bool = True,
    ) -> Dict[str, Any]:
        tier = epistemic_tier if isinstance(epistemic_tier, EpistemicTier) else EpistemicTier(epistemic_tier)
        res = self.orchestrator.ingest_turn(
            role=role,
            content=content,
            epistemic_tier=tier,
            explicit_slots=explicit_slots,
            anti_reason=anti_reason,
        )
        if autosave and self.orchestrator.substrate.db_path != ":memory:":
            self.save()
        return res

    def force_flush(self, autosave: bool = True) -> int:
        count = self.orchestrator.force_flush()
        if autosave and self.orchestrator.substrate.db_path != ":memory:":
            self.save()
        return count

    def register_anti_glyph(
        self,
        content: str,
        reason: str,
        autosave: bool = True,
    ) -> Dict[str, Any]:
        return self.ingest(
            role="system",
            content=content,
            epistemic_tier=EpistemicTier.F,
            anti_reason=reason,
            autosave=autosave,
        )

    def compose(
        self,
        query: str,
        max_tokens: Optional[int] = None,
        auto_prefetch: bool = True,
        zoom_glyph_ids: Sequence[str] = (),
    ) -> ViewportFrame:
        return self.orchestrator.compose_viewport(
            query=query,
            max_tokens=max_tokens,
            auto_prefetch=auto_prefetch,
            zoom_glyph_ids=zoom_glyph_ids,
        )

    def hydrate(
        self,
        glyph_id: str,
        query: str = "",
        max_chars: int = 2000,
    ) -> HydratedSlice:
        return self.orchestrator.hydrate(glyph_id=glyph_id, query=query, max_chars=max_chars)

    def export_cartridge(self, output_path: str | Path) -> Path:
        return export_cartridge(self.orchestrator, output_path)

    @classmethod
    def from_cartridge(
        cls,
        cartridge_path: str | Path,
        db_path: str | Path = ":memory:",
        use_ollama: bool = False,
    ) -> "LogosSession":
        payload = load_cartridge(cartridge_path)
        manifest = payload["manifest"]
        substrate = LogosSubstrate(db_path)
        for blk in payload["raw_blocks"]:
            substrate.put_raw_block(
                content=blk["content"],
                token_count=blk["token_count"],
                epistemic_tier=blk["epistemic_tier"],
                storage_uri=blk["storage_uri"],
            )
        embedder = build_embedder(use_ollama=use_ollama)
        orch = LogosOrchestrator(
            substrate=substrate,
            embedder=embedder,
            fanout=int(manifest.get("fanout", 4)),
            context_budget_tokens=int(manifest.get("context_budget_tokens", 250_000)),
        )
        orch.tree = DualPlaneGlyphTree.from_dict(payload["tree_dict"], compiler=orch.compiler)
        orch.active_turns = [TurnRecord.from_dict(t) for t in manifest.get("active_turns", [])]
        orch.total_ingested_tokens = int(manifest.get("total_ingested_tokens", 0))
        orch._persist_tree_nodes()
        for g in orch.tree.frontier_glyphs():
            orch.kv_bank.allocate_slot(g, orch.h2_projector.compile_kv_glyph(g))
        session = cls(orchestrator=orch)
        if str(db_path) != ":memory:":
            session.save()
        return session

    def status(self) -> Dict[str, Any]:
        orch = self.orchestrator
        integrity = orch.tree.verify_integrity()
        return {
            "frontier_notation": orch.tree.frontier_notation(),
            "pua_frontier_notation": orch.tree.pua_frontier_notation(),
            "pua_frontier_hex": orch.tree.pua_frontier_hex(),
            "total_nodes": len(orch.tree.nodes),
            "frontier_nodes": len(orch.tree.active_frontier),
            "anti_glyphs": len(orch.tree.anti_glyphs),
            "active_raw_turns": len(orch.active_turns),
            "active_raw_tokens": orch.active_raw_tokens(),
            "total_ingested_tokens": orch.total_ingested_tokens,
            "context_budget_tokens": orch.context_budget_tokens,
            "flush_count": orch.flush_count,
            "active_truth_slots": orch.live_truth_table(),
            "tree_integrity": integrity,
            "kv_bank": orch.kv_bank.snapshot_stats(),
        }

    def sleep_consolidate(self, autosave: bool = True) -> Dict[str, Any]:
        """Run offline semantic re-clustering of Ground leaves into tighter Elevated chords."""
        orch = self.orchestrator
        report = orch.tree.sleep_consolidate()
        orch._persist_tree_nodes()
        if autosave and orch.substrate.db_path != ":memory:":
            self.save()
        return report

    def query_truth_history(self, key: Optional[str] = None) -> Dict[str, Any]:
        """Inspect active bitemporal truth slots and full historical revision chains."""
        orch = self.orchestrator
        active = orch.live_truth_table()
        ledger = orch.tree.bitemporal_ledger
        if key:
            k_norm = key.strip()
            return {
                "key": k_norm,
                "active": active.get(k_norm),
                "history": list(ledger.get(k_norm, [])),
                "revisions": len(ledger.get(k_norm, [])),
            }
        return {
            "slot_count": len(active),
            "active_truth_table": active,
            "bitemporal_ledger": {k: list(v) for k, v in sorted(ledger.items())},
        }

    def export_hud_json(self, output_path: Optional[str | Path] = None) -> Dict[str, Any]:
        """Export Dual-Plane Constellation HUD JSON telemetry for `web/logos-hud.html`."""
        orch = self.orchestrator
        frontier_set = set(orch.tree.active_frontier)
        nodes_out: List[Dict[str, Any]] = []
        for gid, node in sorted(orch.tree.nodes.items(), key=lambda kv: (kv[1].level, kv[1].created_at, kv[0])):
            flt = BloomFilter10240.from_bytes(node.provenance.bloom_bytes)
            bits_set = flt.bit_count()
            pua_hex = f"U+{ord(node.rytt_pua):04X}" if node.rytt_pua else "NONE"
            nodes_out.append(
                {
                    "glyph_id": node.glyph_id,
                    "symbol": node.symbol,
                    "plane": node.plane,
                    "level": int(node.level),
                    "rytt_pua": pua_hex,
                    "is_frontier": gid in frontier_set,
                    "created_at": float(node.created_at),
                    "layer1": {
                        "summary": node.semantic.summary,
                        "keywords": list(node.semantic.keywords),
                        "backend": node.semantic.backend,
                        "dim": int(node.semantic.vector.shape[0]),
                        "l2_norm": round(float((node.semantic.vector ** 2).sum() ** 0.5), 4),
                        "preview_8d": [round(float(x), 4) for x in node.semantic.vector[:8]],
                    },
                    "layer2": {
                        "live_slots": node.relational.live_slots(),
                        "active_slots": dict(node.relational.active_slots),
                        "superseded_slots": dict(node.relational.superseded_slots),
                        "operator_rank": int(node.relational.rank),
                        "edges": [e.to_dict() for e in node.relational.edges],
                    },
                    "layer3": {
                        "raw_sha256": node.provenance.raw_sha256,
                        "raw_token_count": int(node.provenance.raw_token_count),
                        "raw_char_count": int(node.provenance.raw_char_count),
                        "storage_uri": node.provenance.storage_uri,
                        "epistemic_tier": node.provenance.epistemic_tier.value,
                        "entity_count": int(node.provenance.entity_count),
                        "bloom_bits_set": bits_set,
                        "bloom_total_bits": BLOOM_BITS,
                        "bloom_density": round(bits_set / float(BLOOM_BITS), 4),
                        "parent_ids": list(node.provenance.parent_ids),
                        "child_ids": list(node.provenance.child_ids),
                    },
                }
            )

        anti_out: List[Dict[str, Any]] = []
        for gid, ag in sorted(orch.tree.anti_glyphs.items()):
            flt = BloomFilter10240.from_bytes(ag.provenance.bloom_bytes)
            bits_set = flt.bit_count()
            anti_out.append(
                {
                    "glyph_id": ag.glyph_id,
                    "symbol": "¬",
                    "plane": "Quarantine",
                    "level": 1,
                    "anti_reason": ag.anti_reason,
                    "summary": ag.semantic.summary,
                    "raw_sha256": ag.provenance.raw_sha256,
                    "epistemic_tier": "F",
                    "bloom_bits_set": bits_set,
                    "bloom_density": round(bits_set / float(BLOOM_BITS), 4),
                }
            )

        payload: Dict[str, Any] = {
            "format": "logos-hud-telemetry",
            "version": "0.4.0",
            "frontier_notation": orch.tree.frontier_notation(),
            "fanout": orch.tree.fanout,
            "total_ingested_tokens": orch.total_ingested_tokens,
            "context_budget_tokens": orch.context_budget_tokens,
            "active_raw_tokens": orch.active_raw_tokens(),
            "hot_tail_turns": [t.to_dict() for t in orch.active_turns],
            "active_truth_table": orch.live_truth_table(),
            "bitemporal_ledger": orch.tree.bitemporal_ledger,
            "tree_integrity": orch.tree.verify_integrity(),
            "nodes": nodes_out,
            "anti_glyphs": anti_out,
        }
        if output_path is not None:
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return payload

    def close(self) -> None:
        self.orchestrator.substrate.close()

    @staticmethod
    def verify_cartridge(path: str | Path) -> Dict[str, Any]:
        return verify_cartridge(path)

    @staticmethod
    def merge_cartridges(
        path_a: str | Path,
        path_b: str | Path,
        output_path: str | Path,
        consolidate: bool = False,
    ) -> Dict[str, Any]:
        return merge_cartridges(path_a, path_b, output_path, consolidate=consolidate)
