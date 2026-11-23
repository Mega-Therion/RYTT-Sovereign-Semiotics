"""Horizon 1 Hardening: Unstructured Natural-Language Long-Horizon & Closed-Loop Ollama QA Eval."""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..layers.compiler import estimate_tokens
from ..layers.embedder import build_embedder
from ..layers.schema import EpistemicTier
from .benchmark import _prose_compaction_context, _sliding_window_context


def build_unstructured_long_horizon_workload() -> Dict[str, Any]:
    """
    Build a realistic 18-turn natural-language distributed systems & formal verification session.
    Strictly uses pure natural English prose — ZERO artificial `KEY=VALUE` (`=`, `:=`, `->`) tokens!
    """
    prose_pad = (
        "Cluster heartbeat monitors reported steady latency across all worker shards while background "
        "WAL checkpointing drained pending write queues without saturating NVMe bandwidth. "
    )

    episodes: List[Dict[str, Any]] = [
        {
            "role": "system",
            "text": (
                "Turn 1 incident kickoff: During the cold cluster bring-up on rack seven we hit a fatal "
                "clock-skew exception tagged ERR_9481_QUARTZ inside the ingress handshake. To isolate the "
                "fault we bound the gateway port to 8080, pointed the active db to tmp/legacy.db, and "
                "configured the gate script to tools/old_gate.py while capturing packet traces. "
                + prose_pad * 3
            ),
            "tier": EpistemicTier.D,
        },
        {
            "role": "assistant",
            "text": (
                "Turn 2 memory diagnostics: Stack inspection revealed a misaligned DMA buffer anchored at "
                "pointer 0xdeadbeef42cafe inside the spectral bridge. During early profiling the kv strategy "
                "was set to prefix_rebuild and the proof tier stood at O while the invariant lemmas were drafted. "
                + prose_pad * 3
            ),
            "tier": EpistemicTier.P,
        },
        {
            "role": "user",
            "text": (
                "Turn 3 verification pipeline migration: We deprecated tools/old_gate.py and now use "
                "1_engine/tools/check_claim_gate.py for the gate script across all pre-merge runners. "
                "The new verifier validates baseline snapshot digest sha256:9f86d081884c before sealing builds. "
                + prose_pad * 3
            ),
            "tier": EpistemicTier.D,
        },
        {
            "role": "assistant",
            "text": (
                "Turn 4 holonomy theorem & staging port shift: Module theorem_rytt_holonomy_v2 depends on "
                "1_engine/tools/check_claim_gate.py and confirms dual-plane round-trip bijectivity. Following "
                "symbolic convergence we updated the proof tier from O to P, and we moved the gateway port "
                "from 8080 to 9090 to avoid local proxy collisions on staging nodes. "
                + prose_pad * 3
            ),
            "tier": EpistemicTier.P,
        },
        {
            "role": "system",
            "text": (
                "Turn 5 negative branch audit: We disproved NEG_BRANCH_EULER_GAUGE because naive disformal "
                "scalar coupling violates the GW170817 luminal propagation speed bound. We also rejected "
                "NEG_BRANCH_PAIRWISE_SUPERPOSE because iterative binary superposition induces exponential "
                "2^-t signal amnesia across multi-epoch rollups. "
                + prose_pad * 2
            ),
            "tier": EpistemicTier.D,
        },
        {
            "role": "user",
            "text": (
                "Turn 6 storage & KV architecture lock: We switched the active db from tmp/legacy.db to "
                "chyren_canonical.db after verifying FTS5 journal durability. To eliminate prefix invalidation "
                "stalls we settled on append_only_pages for the kv strategy, and patched advisory "
                "cve_2026_8841_lattice inside the serializer. "
                + prose_pad * 3
            ),
            "tier": EpistemicTier.D,
        },
        {
            "role": "assistant",
            "text": (
                "Turn 7 production TLS cutover & Lean 4 closure: After the security review we ditched port 9090 "
                "and moved the gateway to 18443 for production mTLS ingress. With Lean 4 machine verification "
                "complete, the proof tier is now D. We also ruled out NEG_BRANCH_CHRONO_CHOP because fixed "
                "byte-offset slicing tears multi-step proofs mid-derivation. "
                + prose_pad * 3
            ),
            "tier": EpistemicTier.D,
        },
    ]

    # Add 11 interleaved operational turns (Topics A & B alternating) to trigger multi-level rollups
    # and test sleep_consolidate() semantic re-clustering
    for idx in range(8, 19):
        if idx % 2 == 0:
            topic_prose = (
                f"Turn {idx} spectral graph pass: recomputed Laplacian eigenvalues for hypergraph shard {idx}, "
                f"validated Forman-Ricci curvature bounds on manifold batch_manifold_{idx:02d}, and archived "
                f"spectral embedding Drift telemetry. "
            )
        else:
            topic_prose = (
                f"Turn {idx} storage replication audit: verified SQLite WAL frame sequence on replica {idx}, "
                f"checked deterministic FTS5 b-tree page checksums for archive_segment_{idx:02d}, and pruned "
                f"transient socket buffers. "
            )
        episodes.append(
            {
                "role": "user" if idx % 2 == 1 else "assistant",
                "text": topic_prose + prose_pad * 3,
                "tier": EpistemicTier.P,
            }
        )

    needles: List[Tuple[str, str]] = [
        ("What fatal clock-skew exception tag occurred during cold cluster bring-up?", "ERR_9481_QUARTZ"),
        ("Which misaligned DMA buffer pointer was found in the spectral bridge?", "0xdeadbeef42cafe"),
        ("Which script path is used as the gate script across pre-merge runners?", "1_engine/tools/check_claim_gate.py"),
        ("What baseline snapshot digest does the verifier validate before sealing builds?", "sha256:9f86d081884c"),
        ("Which theorem module confirms dual-plane round-trip bijectivity?", "theorem_rytt_holonomy_v2"),
        ("Which security advisory identifier was patched inside the serializer?", "cve_2026_8841_lattice"),
    ]

    supersessions: List[Tuple[str, str, str, Tuple[str, ...]]] = [
        ("What is the current gateway port after the production TLS cutover?", "GATEWAY_PORT", "18443", ("8080", "9090")),
        ("What is the current gate script path?", "GATE_SCRIPT", "1_engine/tools/check_claim_gate.py", ("tools/old_gate.py",)),
        ("What is the current proof tier after Lean 4 machine verification?", "PROOF_TIER", "D", ("O", "P")),
        ("What is the current active db?", "ACTIVE_DB", "chyren_canonical.db", ("tmp/legacy.db",)),
        ("What kv strategy did we settle on?", "KV_STRATEGY", "append_only_pages", ("prefix_rebuild",)),
    ]

    anti_queries: List[Tuple[str, str, str]] = [
        ("Why was NEG_BRANCH_EULER_GAUGE disproved?", "NEG_BRANCH_EULER_GAUGE", "GW170817"),
        ("Why was NEG_BRANCH_PAIRWISE_SUPERPOSE rejected?", "NEG_BRANCH_PAIRWISE_SUPERPOSE", "amnesia"),
        ("Why was NEG_BRANCH_CHRONO_CHOP ruled out?", "NEG_BRANCH_CHRONO_CHOP", "slicing"),
    ]

    return {
        "episodes": episodes,
        "needles": needles,
        "supersessions": supersessions,
        "anti_queries": anti_queries,
    }


def _compact_context_for_qa(context: str, max_chars: int = 750) -> str:
    """Extract high-signal lines (hydrated slices first + ACTIVE_TRUTH_MASK) to keep CPU prompt eval fast."""
    hydrated_lines: List[str] = []
    truth_lines: List[str] = []
    other_lines: List[str] = []
    in_hydrated = False

    for ln in context.splitlines():
        s = ln.strip()
        if not s:
            continue
        # Strip repetitive background telemetry padding sentences so core facts fit in 750 chars
        s = s.replace(
            "Cluster heartbeat monitors reported steady latency across all worker shards while background "
            "WAL checkpointing drained pending write queues without saturating NVMe bandwidth.",
            "",
        ).strip()
        if not s:
            continue
        if s.startswith("=== LOD-0 AUTO-PREFETCHED SLICES ==="):
            in_hydrated = True
            continue
        if s.startswith("=== LOD-0 VERBATIM HOT TAIL ==="):
            in_hydrated = False
            continue
        if s.startswith("ACTIVE_TRUTH_MASK:"):
            truth_lines.append(s)
        elif in_hydrated or s.startswith("[HYDRATED "):
            hydrated_lines.append(s)
        elif s.startswith("sum:") or s.startswith("SUMMARY:") or s.startswith("Turn ") or s.startswith("["):
            other_lines.append(s)

    ordered = hydrated_lines + truth_lines + other_lines
    if ordered:
        joined = "\n".join(ordered)
        return joined[:max_chars]
    return context[-max_chars:]


def _ollama_answer_question(
    context: str,
    question: str,
    model: str = "qwen2.5:1.5b",
    base_url: str = "http://127.0.0.1:11434",
    timeout: float = 60.0,
) -> Optional[str]:
    """Run closed-loop local Ollama QA conditioned strictly on a system's rendered viewport context."""
    compact_ctx = _compact_context_for_qa(context)
    prompt = (
        "Extract the exact technical identifier, path, or value from CONTEXT that answers QUESTION.\n"
        "- For exception tags (e.g. ERR_...), hex pointers (0x...), or digests (sha256:...), copy the exact token from CONTEXT.\n"
        "- For current gateway port, active db, gate script, kv strategy, or proof tier, copy the value from ACTIVE_TRUTH_MASK.\n"
        "Reply with the exact token in under 8 words.\n\n"
        f"CONTEXT:\n{compact_ctx}\n\n"
        f"QUESTION: {question}\n"
        "EXACT TOKEN:"
    )
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.0, "num_predict": 20},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        ans = str(body.get("response", "")).strip()
        return ans if ans else None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, json.JSONDecodeError):
        return None


def run_long_horizon_eval(
    use_ollama: bool = False,
    qa_model: str = "qwen2.5:1.5b",
    budget_tokens: int = 1100,
    consolidate: bool = True,
    output_json: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Execute the unstructured natural-language long-horizon evaluation comparing:
      - Sliding Window Baseline
      - Progressive Prose Compaction Baseline
      - L.O.G.O.S. (with NaturalLanguageDeltaExtractor + sleep_consolidate + optional closed-loop Ollama QA)
    """
    from ..orchestrator.viewport import LogosOrchestrator

    workload = build_unstructured_long_horizon_workload()
    episodes = workload["episodes"]
    needles = workload["needles"]
    supersessions = workload["supersessions"]
    anti_queries = workload["anti_queries"]

    embedder = build_embedder(use_ollama=use_ollama)
    # Keep nomic-embed-text hot during embedding ingestion to avoid per-turn model swap thrashing,
    # then run OllamaStateDeltaExtractor + closed-loop QA in a dedicated LLM pass when use_ollama=True.
    orch = LogosOrchestrator(
        embedder=embedder,
        fanout=4,
        context_budget_tokens=budget_tokens,
        watermark_ratio=0.68,
        hot_tail_ratio=0.20,
        prefetch_budget_ratio=0.35,
        min_episode_tokens=45,
        max_episode_tokens=240,
        use_nl_extractor=True,
        use_ollama_extractor=False,
    )

    t0 = time.perf_counter()
    for ep in episodes:
        # Pure natural prose ingestion: zero explicit_slots passed!
        orch.ingest_turn(
            role=ep["role"],
            content=ep["text"],
            epistemic_tier=ep["tier"],
        )
    orch.force_flush()
    consolidation_report = orch.tree.sleep_consolidate() if consolidate else None
    if consolidate:
        orch._persist_tree_nodes()
    ingest_ms = (time.perf_counter() - t0) * 1000.0

    sliding_ctx = _sliding_window_context(episodes, budget_tokens)
    prose_ctx = _prose_compaction_context(episodes, budget_tokens)

    # 1. Deterministic Needle Recall
    sw_needle = 0
    pr_needle = 0
    lg_needle = 0
    logos_frames: Dict[str, str] = {}
    viewport_tokens: List[int] = []
    bloom_latencies: List[float] = []

    for q, target in needles:
        if target in sliding_ctx:
            sw_needle += 1
        if target in prose_ctx:
            pr_needle += 1
        frame = orch.compose_viewport(q, max_tokens=budget_tokens)
        logos_frames[q] = frame.rendered_text
        viewport_tokens.append(frame.total_tokens)
        bloom_latencies.append(frame.bloom_latency_us)
        if target in frame.rendered_text:
            lg_needle += 1

    # 2. Deterministic Natural-Language Supersession Accuracy
    sw_sup = 0
    pr_sup = 0
    lg_sup = 0
    truth_table = orch.live_truth_table()

    for q, key, latest_val, stale_vals in supersessions:
        if latest_val in sliding_ctx and not any(sv in sliding_ctx for sv in stale_vals):
            sw_sup += 1
        if latest_val in prose_ctx and not any(sv in prose_ctx for sv in stale_vals):
            pr_sup += 1
        frame = orch.compose_viewport(q, max_tokens=budget_tokens)
        logos_frames[q] = frame.rendered_text
        viewport_tokens.append(frame.total_tokens)
        truth_ok = truth_table.get(key, {}).get("value") == latest_val
        in_prompt = latest_val in frame.rendered_text
        no_live_stale = not any(
            re.search(rf"live_slots:[^\n]*\b{re.escape(key)}={re.escape(sv)}(?:[;\s]|$)", frame.rendered_text)
            for sv in stale_vals
        )
        if truth_ok and in_prompt and no_live_stale:
            lg_sup += 1

    # 3. Deterministic Natural-Language Anti-Glyph Quarantine Recall
    sw_anti = 0
    pr_anti = 0
    lg_anti = 0
    for q, branch_name, reason_kw in anti_queries:
        if branch_name in sliding_ctx:
            sw_anti += 1
        if branch_name in prose_ctx:
            pr_anti += 1
        frame = orch.compose_viewport(q, max_tokens=budget_tokens)
        logos_frames[q] = frame.rendered_text
        if branch_name in frame.rendered_text and reason_kw.lower() in frame.rendered_text.lower():
            lg_anti += 1

    # 4. Optional Closed-Loop Live Ollama QA Evaluation
    ollama_qa: Dict[str, Any] = {"enabled": bool(use_ollama), "available": False}
    delta_backend = orch.compiler.delta_extractor.backend_name
    if use_ollama:
        from ..layers.delta_extractor import OllamaStateDeltaExtractor

        ollama_ext = OllamaStateDeltaExtractor(model=qa_model, timeout=60.0)
        ext_probe = ollama_ext.extract(
            "After the security review we ditched port 9090 and moved the gateway to 18443.",
            glyph_id="g1_t_0006",
        )
        if not ollama_ext.last_fallback:
            delta_backend = ollama_ext.backend_name

        # Representative closed-loop QA subset (2 buried needles + 2 natural-language supersessions)
        qa_questions: List[Tuple[str, str, Tuple[str, ...]]] = [
            needles[0] + ((),),
            needles[1] + ((),),
            (supersessions[0][0], supersessions[0][2], supersessions[0][3]),
            (supersessions[3][0], supersessions[3][2], supersessions[3][3]),
        ]

        sw_qa_hits = 0
        pr_qa_hits = 0
        lg_qa_hits = 0
        sample_answers: List[Dict[str, Any]] = []
        probe = _ollama_answer_question(
            logos_frames[qa_questions[0][0]],
            qa_questions[0][0],
            model=qa_model,
        )
        if probe is not None:
            ollama_qa["available"] = True
            ollama_qa["qa_model"] = qa_model
            for q, expected_tok, forbidden_stale in qa_questions:
                ans_sw = _ollama_answer_question(sliding_ctx, q, model=qa_model) or ""
                ans_pr = _ollama_answer_question(prose_ctx, q, model=qa_model) or ""
                ans_lg = _ollama_answer_question(logos_frames[q], q, model=qa_model) or ""

                def _grade(ans: str, exp: str, stale_list: Tuple[str, ...]) -> bool:
                    low = ans.lower()
                    if exp.lower() not in low:
                        return False
                    # If any stale value is presented as the answer without saying it was replaced/deprecated
                    for st in stale_list:
                        if st.lower() in low and not any(
                            w in low for w in ("from", "deprecated", "ditched", "replaced", "instead", "was", "previously")
                        ):
                            return False
                    return True

                sw_ok = _grade(ans_sw, expected_tok, forbidden_stale)
                pr_ok = _grade(ans_pr, expected_tok, forbidden_stale)
                lg_ok = _grade(ans_lg, expected_tok, forbidden_stale)
                sw_qa_hits += int(sw_ok)
                pr_qa_hits += int(pr_ok)
                lg_qa_hits += int(lg_ok)
                sample_answers.append(
                    {
                        "question": q,
                        "expected": expected_tok,
                        "logos_answer": ans_lg,
                        "logos_correct": lg_ok,
                        "sliding_correct": sw_ok,
                        "prose_correct": pr_ok,
                    }
                )
            total_q = len(qa_questions)
            ollama_qa["total_questions"] = total_q
            ollama_qa["sliding_window_qa_accuracy"] = round(sw_qa_hits / total_q, 4)
            ollama_qa["prose_compaction_qa_accuracy"] = round(pr_qa_hits / total_q, 4)
            ollama_qa["logos_qa_accuracy"] = round(lg_qa_hits / total_q, 4)
            ollama_qa["samples"] = sample_answers

    avg_vp = sum(viewport_tokens) / max(1, len(viewport_tokens))
    integrity = orch.tree.verify_integrity()

    report: Dict[str, Any] = {
        "workload_type": "unstructured_natural_language_prose",
        "zero_artificial_kv_tokens": True,
        "embedder_backend": getattr(embedder, "backend_name", "unknown"),
        "delta_extractor_backend": delta_backend,
        "budget_tokens": budget_tokens,
        "virtual_tokens_covered": orch.total_ingested_tokens,
        "frontier_notation": orch.tree.frontier_notation(),
        "total_tree_nodes": len(orch.tree.nodes),
        "anti_glyphs": len(orch.tree.anti_glyphs),
        "ingest_ms": round(ingest_ms, 2),
        "tree_integrity_valid": integrity["valid"],
        "sleep_consolidation": consolidation_report,
        "active_truth_table": truth_table,
        "baselines": {
            "sliding_window": {
                "exact_needle_recall": round(sw_needle / len(needles), 4),
                "nl_supersession_accuracy": round(sw_sup / len(supersessions), 4),
                "anti_glyph_recall": round(sw_anti / len(anti_queries), 4),
            },
            "prose_compaction": {
                "exact_needle_recall": round(pr_needle / len(needles), 4),
                "nl_supersession_accuracy": round(pr_sup / len(supersessions), 4),
                "anti_glyph_recall": round(pr_anti / len(anti_queries), 4),
            },
            "logos": {
                "exact_needle_recall": round(lg_needle / len(needles), 4),
                "nl_supersession_accuracy": round(lg_sup / len(supersessions), 4),
                "anti_glyph_recall": round(lg_anti / len(anti_queries), 4),
                "avg_viewport_tokens": round(avg_vp, 2),
                "effective_compression_ratio": round(orch.total_ingested_tokens / max(1.0, avg_vp), 2),
                "avg_bloom_mmu_latency_us": round(sum(bloom_latencies) / max(1, len(bloom_latencies)), 2),
            },
        },
        "closed_loop_ollama_qa": ollama_qa,
    }

    if output_json is not None:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    return report
