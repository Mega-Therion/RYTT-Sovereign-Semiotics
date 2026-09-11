"""Named-baseline benchmark arena and static report generator."""
from __future__ import annotations

import argparse
import html
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rytt.compiler import RyttCompiler  # noqa: E402

CORPUS = {
    "prose": "The quick brown fox jumps over the lazy dog. Sovereign intelligence requires formal structure and semantic depth.",
    "code": "def encode(text: str) -> str:\n    return compiler.compile(text).encoded_pua",
    "mixed_casing": "RYTT The Quick Brown Fox JUMPS over THE lazy DOG",
    "punctuation": "...wait—what?! (yes, really.) Score: 100% — exact.",
    "whitespace": "  leading   spaces   and   trailing  \n\ttabs\t and\nnewlines\n",
    "unicode_passthrough": "α β γ → ∞ ⊕ ∇ é ñ ü 中文 日本語",
    "ligature_rich": "RYTT TION MENT ING STR THE AND NOT FOR CON PRO rytt tion ment ing",
}


def optional_tiktoken(text: str) -> int | None:
    try:
        import tiktoken
    except ImportError:
        return None
    tokenizer = tiktoken.get_encoding("cl100k_base")
    return len(tokenizer.encode(text))


def run() -> dict:
    compiler = RyttCompiler()
    rows = []
    for name, text in CORPUS.items():
        start = time.perf_counter_ns()
        result = compiler.compile(text)
        elapsed = (time.perf_counter_ns() - start) / 1_000
        rows.append({
            "corpus": name,
            "source_characters": len(text),
            "source_utf8_bytes": len(text.encode("utf-8")),
            "rytt_tokens": len(result.tokens),
            "rytt_encoded_utf8_bytes": len(result.encoded_pua.encode("utf-8")),
            "rytt_chord_tokens": sum(token.is_chord for token in result.tokens),
            "rytt_encode_runtime_us": round(elapsed, 2),
            "round_trip_exact": compiler.decompile(result.encoded_pua) == text,
            "named_baselines": {
                "raw_characters": len(text),
                "utf8_bytes": len(text.encode("utf-8")),
                "cl100k_base_tokens": optional_tiktoken(text),
            },
        })
    return {
        "arena_version": "0.1",
        "metric_policy": "Each baseline is reported independently; no score combines characters, bytes, and model tokens.",
        "tokenizer_notes": {"cl100k_base_tokens": "Optional; present only when tiktoken is installed."},
        "results": rows,
    }


def render_html(payload: dict) -> str:
    rows = []
    for row in payload["results"]:
        rows.append("<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in [row["corpus"], row["source_characters"], row["rytt_tokens"], row["source_utf8_bytes"], row["rytt_encoded_utf8_bytes"], row["named_baselines"]["cl100k_base_tokens"] or "n/a", "yes" if row["round_trip_exact"] else "NO"]) + "</tr>")
    return "<!doctype html><meta charset='utf-8'><title>RYTT Benchmark Arena</title><style>body{font:16px system-ui;background:#080d18;color:#eef2f7;max-width:1100px;margin:3rem auto;padding:0 1rem}h1{font:2.6rem Georgia}p{color:#a9b4c7}table{width:100%;border-collapse:collapse;background:#111a2b}th,td{padding:.7rem;border:1px solid #2a3b55;text-align:left}th{color:#5fecff}td:last-child{color:#83e6b3}</style><h1>RYTT Benchmark Arena</h1><p>Named metrics are intentionally kept separate. RYTT encoded UTF-8 bytes are not model-token counts.</p><table><thead><tr><th>Corpus</th><th>Source chars</th><th>RYTT tokens</th><th>Source bytes</th><th>Encoded bytes</th><th>cl100k_base</th><th>Exact</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", default="benchmarks/results/arena.json")
    parser.add_argument("--html", default="benchmarks/results/arena.html")
    args = parser.parse_args()
    payload = run()
    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    Path(args.html).write_text(render_html(payload))
    print(f"wrote {args.json} and {args.html}")
    return 0 if all(row["round_trip_exact"] for row in payload["results"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
