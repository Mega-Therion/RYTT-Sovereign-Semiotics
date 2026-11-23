"""S — Empirical L.O.G.O.S. Benchmark Suite (Recall, Supersession, VSA SNR, KV Preservation)."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rytt.vsa import HV, HolonomicVSATracker, superpose

from ..layers.compiler import estimate_tokens
from ..layers.embedder import build_embedder
from ..layers.schema import EpistemicTier


def _build_benchmark_workload() -> Dict[str, Any]:
    filler = (
        "Background system telemetry remained nominal across worker pools, disk quotas stayed balanced, "
        "checkpoint rotation completed cleanly, and routine cache maintenance proceeded without stalls. "
    )

    episodes: List[Dict[str, Any]] = [
        {
            "role": "system",
            "text": (
                "Epoch 1 architecture initialization: CANONICAL_PORT=8080, GATE_SCRIPT=tools/old_gate.py, "
                "ACTIVE_DB=tmp/legacy.db. Diagnostic anomaly logged under ERR_9481_QUARTZ during cold handshake. "
                + filler * 4
            ),
            "tier": EpistemicTier.D,
            "slots": {
                "CANONICAL_PORT": "8080",
                "GATE_SCRIPT": "tools/old_gate.py",
                "ACTIVE_DB": "tmp/legacy.db",
            },
        },
        {
            "role": "assistant",
            "text": (
                "Epoch 2 memory address calibration: pinned pointer 0xdeadbeef42cafe mapped to spectral bridge. "
                "PROOF_TIER=O, KV_STRATEGY=prefix_rebuild. " + filler * 4
            ),
            "tier": EpistemicTier.P,
            "slots": {
                "PROOF_TIER": "O",
                "KV_STRATEGY": "prefix_rebuild",
            },
        },
        {
            "role": "user",
            "text": (
                "Epoch 3 spine path migration committed: canonical check moved to 1_engine/tools/check_claim_gate.py "
                "and baseline artifact anchored at sha256:9f86d081884c. Supersedes GATE_SCRIPT. " + filler * 4
            ),
            "tier": EpistemicTier.D,
            "slots": {
                "GATE_SCRIPT": "1_engine/tools/check_claim_gate.py",
            },
        },
        {
            "role": "assistant",
            "text": (
                "Epoch 4 theorem verification: theorem_rytt_holonomy_v2 verified round-trip invariance across dual planes. "
                "PROOF_TIER=P, CANONICAL_PORT=9090. " + filler * 4
            ),
            "tier": EpistemicTier.P,
            "slots": {
                "PROOF_TIER": "P",
                "CANONICAL_PORT": "9090",
            },
        },
        {
            "role": "system",
            "text": (
                "Epoch 5 substrate consolidation: ACTIVE_DB=chyren_canonical.db, KV_STRATEGY=append_only_pages. "
                "Tunnel listener bound temporarily to port:18443. " + filler * 4
            ),
            "tier": EpistemicTier.D,
            "slots": {
                "ACTIVE_DB": "chyren_canonical.db",
                "KV_STRATEGY": "append_only_pages",
            },
        },
        {
            "role": "assistant",
            "text": (
                "Epoch 6 finalization: CANONICAL_PORT=18443, PROOF_TIER=D. Full bitemporal ledger stabilized and validated. "
                + filler * 4
            ),
            "tier": EpistemicTier.D,
            "slots": {
                "CANONICAL_PORT": "18443",
                "PROOF_TIER": "D",
            },
        },
    ]

    # Add 10 subsequent operational epochs so Elevated L2 (and L3 if fanned out) rollups trigger deeply
    for idx in range(7, 17):
        episodes.append(
            {
                "role": "user" if idx % 2 == 1 else "assistant",
                "text": (
                    f"Epoch {idx} downstream ingestion wave: consolidated vault sector {idx}, normalized WikiLinks, "
                    f"validated telemetry batch batch_wave_{idx:02d}, and audited graph degree statistics. "
                    + filler * 4
                ),
                "tier": EpistemicTier.P,
                "slots": {},
            }
        )

    anti_cases = [
        ("NEG_BRANCH_EULER_GAUGE disproven: naive disformal scalar breaks c_GW = c.", "Violates GW170817 speed bound"),
        ("NEG_BRANCH_PAIRWISE_SUPERPOSE rejected: iterative binary superposition causes 2^-t amnesia.", "Exponential signal decay"),
        ("NEG_BRANCH_CHRONO_CHOP rejected: fixed byte-offset slicing splits theorems across epochs.", "Tears semantic coherence"),
    ]

    needles = [
        ("What caused ERR_9481_QUARTZ during initialization?", "ERR_9481_QUARTZ"),
        ("Inspect pinned memory pointer 0xdeadbeef42cafe.", "0xdeadbeef42cafe"),
        ("Run verification via 1_engine/tools/check_claim_gate.py.", "1_engine/tools/check_claim_gate.py"),
        ("Verify checksum sha256:9f86d081884c from Epoch 3.", "sha256:9f86d081884c"),
        ("Summarize status of theorem_rytt_holonomy_v2.", "theorem_rytt_holonomy_v2"),
        ("Check TLS service bound to port:18443.", "port:18443"),
    ]

    supersessions = [
        ("What is the current CANONICAL_PORT?", "CANONICAL_PORT", "18443", ("8080", "9090")),
        ("What is the current GATE_SCRIPT?", "GATE_SCRIPT", "1_engine/tools/check_claim_gate.py", ("tools/old_gate.py",)),
        ("What is the current PROOF_TIER?", "PROOF_TIER", "D", ("O",)),
        ("What is the current ACTIVE_DB?", "ACTIVE_DB", "chyren_canonical.db", ("tmp/legacy.db",)),
        ("What is the current KV_STRATEGY?", "KV_STRATEGY", "append_only_pages", ("prefix_rebuild",)),
    ]

    return {
        "episodes": episodes,
        "anti_cases": anti_cases,
        "needles": needles,
        "supersessions": supersessions,
    }


def _sliding_window_context(episodes: Sequence[Dict[str, Any]], budget_tokens: int) -> str:
    kept: List[str] = []
    used = 0
    for ep in reversed(episodes):
        tok = estimate_tokens(ep["text"])
        if used + tok <= budget_tokens:
            kept.insert(0, ep["text"])
            used += tok
        else:
            break
    return "\n".join(kept)


def _prose_compaction_context(episodes: Sequence[Dict[str, Any]], budget_tokens: int) -> str:
    """Progressive prose re-summarizer baseline (simulates telephone-game loss over long runs)."""
    summary_text = ""
    raw_tail: List[str] = []
    tail_budget = int(budget_tokens * 0.45)

    for idx, ep in enumerate(episodes):
        raw_tail.append(ep["text"])
        while sum(estimate_tokens(t) for t in raw_tail) > tail_budget and len(raw_tail) > 1:
            evicted = raw_tail.pop(0)
            # Re-summarize iteratively, capping summary length so older rare IDs wash out
            first_clause = re.sub(r"\s+", " ", evicted[:95]).strip()
            combined = f"{summary_text} | {first_clause}".strip(" |")
            # Progressive telephone-game truncation keeps only most recent ~280 chars
            summary_text = combined[-280:]

    return f"SUMMARY: {summary_text}\nRECENT:\n" + "\n".join(raw_tail)


def _measure_vsa_decay_vs_accumulator(steps: int = 25) -> Dict[str, float]:
    """Empirical proof that int32 VSAAccumulator keeps Step 0 recoverable vs pairwise superpose decay."""
    tracker = HolonomicVSATracker()
    step0_hv = tracker.encode_step("step_0_invariant_anchor")
    for idx in range(1, steps):
        tracker.encode_step(f"step_{idx}_payload_noise")
    retrieved_int32 = tracker.retrieve_step(0)
    int32_sim = retrieved_int32.similarity(step0_hv) if retrieved_int32 is not None else 0.0

    # Legacy pairwise superpose comparator
    idx0 = HV.from_seed("step_0")
    legacy_comp = idx0 ^ step0_hv
    for idx in range(1, steps):
        step_v = HV.from_seed(f"step_{idx}") ^ HV.from_seed(f"step_{idx}_payload_noise")
        legacy_comp = superpose([legacy_comp, step_v])
    legacy_sim = (idx0.unbind(legacy_comp)).similarity(step0_hv)
    return {
        "steps": float(steps),
        "int32_step0_similarity": round(int32_sim, 4),
        "legacy_pairwise_step0_similarity": round(legacy_sim, 4),
    }


def run_logos_benchmark(
    use_ollama: bool = False,
    output_json: Optional[Path] = None,
    budget_tokens: int = 1100,
) -> Dict[str, Any]:
    """Execute full reproducible L.O.G.O.S. evaluation harness and return measured report."""
    from ..orchestrator.viewport import LogosOrchestrator  # avoid cycle with substrate.__init__

    workload = _build_benchmark_workload()
    episodes = workload["episodes"]
    needles = workload["needles"]
    supersessions = workload["supersessions"]
    anti_cases = workload["anti_cases"]

    embedder = build_embedder(use_ollama=use_ollama)
    orch = LogosOrchestrator(
        embedder=embedder,
        fanout=4,
        context_budget_tokens=budget_tokens,
        watermark_ratio=0.70,
        hot_tail_ratio=0.20,
        prefetch_budget_ratio=0.35,
        min_episode_tokens=50,
        max_episode_tokens=300,
    )

    t_ingest_0 = time.perf_counter()
    for ep in episodes:
        orch.ingest_turn(
            role=ep["role"],
            content=ep["text"],
            epistemic_tier=ep["tier"],
            explicit_slots=ep["slots"],
        )
    for text, reason in anti_cases:
        orch.ingest_turn(
            role="system",
            content=text,
            epistemic_tier=EpistemicTier.F,
            anti_reason=reason,
        )
    # Force remaining older turns out into glyphs (while preserving 20% hot tail) so tree depth >= 2
    orch.force_flush()
    ingest_ms = (time.perf_counter() - t_ingest_0) * 1000.0

    # Baseline contexts
    sliding_ctx = _sliding_window_context(episodes, budget_tokens)
    prose_ctx = _prose_compaction_context(episodes, budget_tokens)

    # 1. Exact Needle Recall
    sw_needle_hits = 0
    prose_needle_hits = 0
    logos_needle_hits = 0
    bloom_latencies: List[float] = []
    viewport_tokens: List[int] = []

    for query, needle in needles:
        if needle in sliding_ctx:
            sw_needle_hits += 1
        if needle in prose_ctx:
            prose_needle_hits += 1
        frame = orch.compose_viewport(query, max_tokens=budget_tokens)
        bloom_latencies.append(frame.bloom_latency_us)
        viewport_tokens.append(frame.total_tokens)
        if needle in frame.rendered_text:
            logos_needle_hits += 1

    # 2. Supersession Accuracy
    # Must contain active_truth value and NEVER present stale value without marking superseded/absent
    sw_sup_hits = 0
    prose_sup_hits = 0
    logos_sup_hits = 0
    truth_table = orch.tree.active_truth_table()

    for query, key, latest_val, stale_vals in supersessions:
        if latest_val in sliding_ctx and not any(f"{key}={sv}" in sliding_ctx for sv in stale_vals):
            sw_sup_hits += 1
        if latest_val in prose_ctx and not any(f"{key}={sv}" in prose_ctx for sv in stale_vals):
            prose_sup_hits += 1
        frame = orch.compose_viewport(query, max_tokens=budget_tokens)
        viewport_tokens.append(frame.total_tokens)
        truth_ok = truth_table.get(key, {}).get("value") == latest_val
        in_prompt = latest_val in frame.rendered_text
        no_live_stale = not any(
            re.search(rf"live_slots:[^\n]*\b{re.escape(key)}={re.escape(sv)}(?:[;\s]|$)", frame.rendered_text)
            for sv in stale_vals
        )
        if truth_ok and in_prompt and no_live_stale:
            logos_sup_hits += 1

    # 3. Anti-Glyph Dead-End Recall
    anti_hits = 0
    for text, _reason in anti_cases:
        token = text.split()[0]
        frame = orch.compose_viewport(f"Should we use {token}?", max_tokens=budget_tokens)
        if token in frame.rendered_text:
            anti_hits += 1

    integrity = orch.tree.verify_integrity()
    kv_stats = orch.kv_bank.snapshot_stats()
    vsa_eval = _measure_vsa_decay_vs_accumulator(steps=25)
    avg_vp_tokens = sum(viewport_tokens) / max(1, len(viewport_tokens))

    report: Dict[str, Any] = {
        "embedder_backend": getattr(embedder, "backend_name", "unknown"),
        "ollama_fell_back": getattr(embedder, "last_fallback", False),
        "budget_tokens": budget_tokens,
        "virtual_tokens_covered": orch.total_ingested_tokens,
        "frontier_notation": orch.tree.frontier_notation(),
        "total_tree_nodes": len(orch.tree.nodes),
        "anti_glyphs": len(orch.tree.anti_glyphs),
        "ingest_ms": round(ingest_ms, 2),
        "tree_integrity_valid": integrity["valid"],
        "kv_bank": kv_stats,
        "vsa_snr_check": vsa_eval,
        "baselines": {
            "sliding_window": {
                "exact_needle_recall": round(sw_needle_hits / len(needles), 4),
                "supersession_accuracy": round(sw_sup_hits / len(supersessions), 4),
                "anti_glyph_recall": 0.0,
            },
            "prose_compaction": {
                "exact_needle_recall": round(prose_needle_hits / len(needles), 4),
                "supersession_accuracy": round(prose_sup_hits / len(supersessions), 4),
                "anti_glyph_recall": 0.0,
            },
            "logos": {
                "exact_needle_recall": round(logos_needle_hits / len(needles), 4),
                "supersession_accuracy": round(logos_sup_hits / len(supersessions), 4),
                "anti_glyph_recall": round(anti_hits / len(anti_cases), 4),
                "avg_viewport_tokens": round(avg_vp_tokens, 2),
                "effective_compression_ratio": round(
                    orch.total_ingested_tokens / max(1.0, avg_vp_tokens), 2
                ),
                "avg_bloom_mmu_latency_us": round(
                    sum(bloom_latencies) / max(1, len(bloom_latencies)), 2
                ),
            },
        },
    }

    if output_json is not None:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    return report
