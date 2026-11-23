"""Command-line interface for L.O.G.O.S. (Layered Operator-Glyph Orchestration System)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from .session import LogosSession
from .substrate.benchmark import run_logos_benchmark
from .substrate.cartridge import verify_cartridge
from .substrate.cartridge_bus import merge_cartridges
from .substrate.eval_long_horizon import run_long_horizon_eval


def _cmd_demo(args: argparse.Namespace) -> int:
    session = LogosSession(context_budget_tokens=220, fanout=4)
    orch = session.orchestrator
    orch.splitter.min_episode_tokens = 25
    orch.splitter.max_episode_tokens = 90
    orch.watermark_ratio = 0.65

    steps = [
        ("Epoch 1 telemetry: ERR_4912_QUARTZ observed on node alpha; CANONICAL_PORT=8080.", {"CANONICAL_PORT": "8080"}),
        ("Epoch 2 calibration: RYTT dual-plane alignment locked; CANONICAL_PORT=9090.", {"CANONICAL_PORT": "9090"}),
        ("Epoch 3 formal gate: verifier path updated to 1_engine/tools/check_claim_gate.py.", {"GATE_SCRIPT": "1_engine/tools/check_claim_gate.py"}),
        ("Epoch 4 finality: CANONICAL_PORT=18443 verified clean on local runner.", {"CANONICAL_PORT": "18443"}),
        ("Epoch 5 live continuation inside verbatim hot tail with active work.", {}),
    ]
    progression: List[str] = []
    for idx, (text, slots) in enumerate(steps, start=1):
        res = session.ingest(role="system" if idx % 2 else "assistant", content=text + " " * 5 + ("pad_context " * 22), explicit_slots=slots)
        progression.append(f"t{idx}:{res['frontier']}")
    session.force_flush()
    progression.append(f"post_flush:{orch.tree.frontier_notation()}")

    frame = session.compose("Investigate ERR_4912_QUARTZ and CANONICAL_PORT", max_tokens=220)
    out = {
        "frontier_progression": progression,
        "final_frontier": frame.frontier_notation,
        "bloom_hits": [
            {"glyph_id": h.glyph_id, "entities": list(h.matched_entities)}
            for h in frame.bloom_hits
        ],
        "lod0_hydrated_ids": [s.glyph_id for s in frame.lod0_hydrated],
        "active_truth": frame.active_truth_table,
        "compression_ratio": round(frame.compression_ratio, 2),
        "rendered_preview": frame.rendered_text[:500],
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    session.close()
    return 0


def _cmd_ingest(args: argparse.Namespace) -> int:
    text = args.text if args.text is not None else sys.stdin.read()
    session = LogosSession.from_db(
        args.db,
        use_ollama=args.ollama,
        context_budget_tokens=args.budget,
        fanout=args.fanout,
    )
    res = session.ingest(
        role=args.role,
        content=text,
        epistemic_tier=args.tier,
        anti_reason=args.anti_reason or "",
    )
    print(json.dumps(res, indent=2, ensure_ascii=False))
    session.close()
    return 0


def _cmd_compose(args: argparse.Namespace) -> int:
    session = LogosSession.from_db(args.db, use_ollama=args.ollama, context_budget_tokens=args.budget)
    frame = session.compose(
        query=args.query,
        max_tokens=args.max_tokens,
        zoom_glyph_ids=args.zoom or (),
    )
    if args.json:
        payload = {
            "frontier_notation": frame.frontier_notation,
            "total_tokens": frame.total_tokens,
            "budget_tokens": frame.budget_tokens,
            "virtual_tokens_covered": frame.virtual_tokens_covered,
            "compression_ratio": round(frame.compression_ratio, 2),
            "bloom_latency_us": round(frame.bloom_latency_us, 2),
            "lod0_hydrated": [
                {"glyph_id": s.glyph_id, "trigger": s.trigger, "sha256": s.raw_sha256}
                for s in frame.lod0_hydrated
            ],
            "rendered_text": frame.rendered_text,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(frame.rendered_text)
    session.close()
    return 0


def _cmd_hydrate(args: argparse.Namespace) -> int:
    session = LogosSession.from_db(args.db, use_ollama=args.ollama)
    sl = session.hydrate(glyph_id=args.glyph_id, query=args.query, max_chars=args.max_chars)
    print(
        json.dumps(
            {
                "glyph_id": sl.glyph_id,
                "raw_sha256": sl.raw_sha256,
                "verified_sha256": sl.verified_sha256,
                "token_count": sl.token_count,
                "content": sl.content,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    session.close()
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    session = LogosSession.from_db(args.db)
    print(json.dumps(session.status(), indent=2, ensure_ascii=False))
    session.close()
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    session = LogosSession.from_db(args.db)
    out = session.export_cartridge(args.output)
    print(str(out))
    session.close()
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    res = verify_cartridge(args.cartridge)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0 if res["valid"] else 1


def _cmd_benchmark(args: argparse.Namespace) -> int:
    out_path = Path(args.json_out) if args.json_out else None
    report = run_logos_benchmark(
        use_ollama=args.ollama,
        output_json=out_path,
        budget_tokens=args.budget,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def _cmd_merge(args: argparse.Namespace) -> int:
    res = merge_cartridges(
        path_a=args.cart_a,
        path_b=args.cart_b,
        output_path=args.output,
        consolidate=args.consolidate,
    )
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0 if res.get("valid") else 1


def _cmd_consolidate(args: argparse.Namespace) -> int:
    session = LogosSession.from_db(args.db, use_ollama=args.ollama)
    res = session.sleep_consolidate()
    print(json.dumps(res, indent=2, ensure_ascii=False))
    session.close()
    return 0


def _cmd_history(args: argparse.Namespace) -> int:
    session = LogosSession.from_db(args.db)
    res = session.query_truth_history(key=args.key)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    session.close()
    return 0


def _cmd_hud_export(args: argparse.Namespace) -> int:
    session = LogosSession.from_db(args.db)
    out_path = Path(args.out) if args.out else None
    payload = session.export_hud_json(output_path=out_path)
    if out_path is not None:
        print(str(out_path))
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    session.close()
    return 0


def _cmd_long_eval(args: argparse.Namespace) -> int:
    out_path = Path(args.json_out) if args.json_out else None
    report = run_long_horizon_eval(
        use_ollama=args.ollama,
        qa_model=args.qa_model,
        budget_tokens=args.budget,
        consolidate=not args.no_consolidate,
        output_json=out_path,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="logos",
        description="L.O.G.O.S. — Layered Operator-Glyph Orchestration System CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    demo_p = sub.add_parser("demo", help="Run self-contained 1r->2ry->3ryt->1R demo with Bloom MMU")
    demo_p.set_defaults(func=_cmd_demo)

    ing_p = sub.add_parser("ingest", help="Ingest a raw turn into persistent L.O.G.O.S. SQLite DB")
    ing_p.add_argument("--db", required=True, help="Path to SQLite session DB")
    ing_p.add_argument("--role", default="user", help="Turn role (user|assistant|system|tool)")
    ing_p.add_argument("--tier", default="P", choices=["D", "P", "O", "F"], help="Epistemic tier")
    ing_p.add_argument("--anti-reason", default="", help="Quarantine reason for failed hypotheses")
    ing_p.add_argument("--budget", type=int, default=250_000, help="Active context budget in tokens")
    ing_p.add_argument("--fanout", type=int, default=4, help="Rollup fanout [2..8]")
    ing_p.add_argument("--ollama", action="store_true", help="Use local Ollama embeddings")
    ing_p.add_argument("text", nargs="?", help="Turn text (default: stdin)")
    ing_p.set_defaults(func=_cmd_ingest)

    cmp_p = sub.add_parser("compose", help="Compose Dynamic LOD Viewport for query")
    cmp_p.add_argument("--db", required=True, help="Path to SQLite session DB")
    cmp_p.add_argument("--query", required=True, help="Active prompt/query")
    cmp_p.add_argument("--budget", type=int, default=250_000, help="Session budget")
    cmp_p.add_argument("--max-tokens", type=int, default=None, help="Viewport token cap")
    cmp_p.add_argument("--zoom", action="append", help="Glyph ID to explicitly zoom to LOD-0")
    cmp_p.add_argument("--ollama", action="store_true", help="Use local Ollama embeddings")
    cmp_p.add_argument("--json", action="store_true", help="Emit full JSON frame telemetry")
    cmp_p.set_defaults(func=_cmd_compose)

    hyd_p = sub.add_parser("hydrate", help="Fail-closed SHA-256 hydration of a glyph slice")
    hyd_p.add_argument("--db", required=True, help="Path to SQLite session DB")
    hyd_p.add_argument("glyph_id", help="Glyph ID to hydrate")
    hyd_p.add_argument("--query", default="", help="Optional needle query inside block")
    hyd_p.add_argument("--max-chars", type=int, default=2000, help="Excerpt cap")
    hyd_p.add_argument("--ollama", action="store_true", help="Use local Ollama embeddings")
    hyd_p.set_defaults(func=_cmd_hydrate)

    st_p = sub.add_parser("status", help="Inspect frontier notation, truth slots & Merkle integrity")
    st_p.add_argument("--db", required=True, help="Path to SQLite session DB")
    st_p.set_defaults(func=_cmd_status)

    exp_p = sub.add_parser("export", help="Export verified .logos cartridge archive")
    exp_p.add_argument("--db", required=True, help="Path to SQLite session DB")
    exp_p.add_argument("output", help="Output .logos file path")
    exp_p.set_defaults(func=_cmd_export)

    ver_p = sub.add_parser("verify", help="Verify a .logos cartridge archive fail-closed")
    ver_p.add_argument("cartridge", help="Path to .logos cartridge")
    ver_p.set_defaults(func=_cmd_verify)

    ben_p = sub.add_parser("benchmark", help="Run comparative L.O.G.O.S. recall & supersession benchmark")
    ben_p.add_argument("--ollama", action="store_true", help="Benchmark using local Ollama embeddings")
    ben_p.add_argument("--budget", type=int, default=1100, help="Context window budget for stress test")
    ben_p.add_argument("--json-out", default=None, help="Optional JSON output path")
    ben_p.set_defaults(func=_cmd_benchmark)

    mrg_p = sub.add_parser("merge", help="Deterministically merge two .logos cartridges via bitemporal CRDT bus")
    mrg_p.add_argument("cart_a", help="First .logos cartridge path")
    mrg_p.add_argument("cart_b", help="Second .logos cartridge path")
    mrg_p.add_argument("output", help="Output merged .logos cartridge path")
    mrg_p.add_argument("--consolidate", action="store_true", help="Run sleep_consolidate after merge")
    mrg_p.set_defaults(func=_cmd_merge)

    con_p = sub.add_parser("consolidate", help="Run offline sleep consolidation on a persistent session DB")
    con_p.add_argument("--db", required=True, help="Path to SQLite session DB")
    con_p.add_argument("--ollama", action="store_true", help="Use local Ollama embeddings")
    con_p.set_defaults(func=_cmd_consolidate)

    his_p = sub.add_parser("history", help="Query bitemporal truth history and supersession chain")
    his_p.add_argument("--db", required=True, help="Path to SQLite session DB")
    his_p.add_argument("--key", default=None, help="Optional specific slot key to inspect")
    his_p.set_defaults(func=_cmd_history)

    hud_p = sub.add_parser("hud-export", help="Export Dual-Plane Constellation HUD JSON file")
    hud_p.add_argument("--db", required=True, help="Path to SQLite session DB")
    hud_p.add_argument("--out", default=None, help="Optional output JSON file path")
    hud_p.set_defaults(func=_cmd_hud_export)

    lev_p = sub.add_parser("long-eval", help="Run unstructured natural-language long-horizon evaluation")
    lev_p.add_argument("--ollama", action="store_true", help="Use live Ollama embeddings, delta extractor & closed-loop QA")
    lev_p.add_argument("--qa-model", default="qwen2.5:1.5b", help="Local Ollama model for closed-loop QA")
    lev_p.add_argument("--budget", type=int, default=1100, help="Viewport token budget")
    lev_p.add_argument("--no-consolidate", action="store_true", help="Skip sleep_consolidate step")
    lev_p.add_argument("--json-out", default=None, help="Optional JSON output path")
    lev_p.set_defaults(func=_cmd_long_eval)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
