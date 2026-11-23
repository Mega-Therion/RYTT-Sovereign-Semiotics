"""Horizon 1 Text Operator: Universal Structured Tensor-Glyph Headers for Any LLM."""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from ..layers.compiler import estimate_tokens
from ..layers.schema import TensorGlyph


class Horizon1TextOperator:
    """
    Renders TensorGlyphs as ultra-compact structured glyph packets usable on any
    closed API or local model today with zero model-weight changes.
    """

    def render_glyph(
        self,
        glyph: TensorGlyph,
        include_slots: bool = True,
        include_summary: bool = True,
        superseded_keys: Optional[Dict[str, str] | set[str]] = None,
    ) -> str:
        if isinstance(superseded_keys, dict):
            sup_map: Dict[str, str] = dict(superseded_keys)
        else:
            sup_map = {k: "superseded" for k in (superseded_keys or set())}

        sha8 = glyph.provenance.raw_sha256[:8]
        pua_hex = f"U+{ord(glyph.rytt_pua):04X}" if glyph.rytt_pua else "NONE"
        tier = glyph.provenance.epistemic_tier.value
        header = (
            f"⟦L{glyph.level}:{glyph.symbol}({pua_hex})|id={glyph.glyph_id}|"
            f"tier={tier}|sha={sha8}|cov={glyph.provenance.raw_token_count}tok⟧"
        )
        parts = [header]
        if include_summary and glyph.semantic.summary:
            parts.append(f"  sum: {glyph.semantic.summary}")

        if include_slots:
            live = {
                k: v
                for k, v in glyph.relational.live_slots().items()
                if k not in sup_map
            }
            if live:
                rendered_slots = "; ".join(f"{k}={v}" for k, v in list(live.items())[:8])
                parts.append(f"  live_slots: {rendered_slots}")
            combined_masked = dict(glyph.relational.superseded_slots)
            for k, target in sup_map.items():
                if k in glyph.relational.active_slots:
                    combined_masked.setdefault(k, target)
            if combined_masked:
                masked = [f"{k}(->{target})" for k, target in combined_masked.items()]
                parts.append(f"  masked_stale: {', '.join(masked[:6])}")

        if glyph.provenance.child_ids:
            parts.append(f"  children: [{', '.join(glyph.provenance.child_ids)}]")
        return "\n".join(parts)

    def render_anti_glyph(self, glyph: TensorGlyph) -> str:
        sha8 = glyph.provenance.raw_sha256[:8]
        return (
            f"⟦¬ANTI:{glyph.glyph_id}|sha={sha8}|reason={glyph.anti_reason}⟧\n"
            f"  dead_end: {glyph.semantic.summary}"
        )

    def render_frontier(
        self,
        glyphs: Sequence[TensorGlyph],
        truth_table: Optional[Dict[str, Dict[str, Any]]] = None,
        anti_glyphs: Sequence[TensorGlyph] = (),
        notation: str = "",
    ) -> str:
        lines: List[str] = []
        if notation:
            lines.append(f"=== L.O.G.O.S. PINNED GLYPHS [{notation}] ===")
        else:
            lines.append("=== L.O.G.O.S. PINNED GLYPHS ===")

        tt = truth_table or {}
        for g in glyphs:
            stale_for_g = {
                k: str(tt[k]["glyph_id"])
                for k, v in g.relational.active_slots.items()
                if k in tt and tt[k]["value"] != v
            }
            lines.append(
                self.render_glyph(
                    g,
                    include_slots=True,
                    include_summary=True,
                    superseded_keys=stale_for_g,
                )
            )

        if tt:
            live_pairs = "; ".join(
                f"{k}={info['value']}@{info['glyph_id']}[{info['epistemic_tier']}]"
                for k, info in sorted(tt.items())
            )
            lines.append(f"ACTIVE_TRUTH_MASK: {live_pairs}")

        if anti_glyphs:
            lines.append("=== QUARANTINED DEAD-ENDS (DO NOT REPEAT) ===")
            for ag in anti_glyphs:
                lines.append(self.render_anti_glyph(ag))

        return "\n".join(lines)

    def measure_compression(
        self,
        rendered_text: str,
        raw_token_count: int,
    ) -> Dict[str, float]:
        rendered_tokens = max(1, estimate_tokens(rendered_text))
        ratio = raw_token_count / float(rendered_tokens) if raw_token_count > 0 else 1.0
        return {
            "rendered_tokens": float(rendered_tokens),
            "raw_tokens": float(raw_token_count),
            "compression_ratio": ratio,
        }
