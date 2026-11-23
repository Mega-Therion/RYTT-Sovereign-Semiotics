"""Unified High-Level LogosSession Facade with SQLite Persistence & Cartridge Recovery."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from .glyphs.tree import DualPlaneGlyphTree
from .layers.embedder import build_embedder
from .layers.schema import EpistemicTier
from .orchestrator.splitter import TurnRecord
from .orchestrator.viewport import HydratedSlice, LogosOrchestrator, ViewportFrame
from .substrate.cartridge import export_cartridge, load_cartridge, verify_cartridge
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

    def close(self) -> None:
        self.orchestrator.substrate.close()

    @staticmethod
    def verify_cartridge(path: str | Path) -> Dict[str, Any]:
        return verify_cartridge(path)
