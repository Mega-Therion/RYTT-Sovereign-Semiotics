#!/usr/bin/env python3
"""
Horizon 2 Proof Script: Trainable Multi-Layer Tensor-Glyph Projector & Direct Tokenization Bypass.

Compiles multi-epoch L.O.G.O.S. TensorGlyphs and trains `TorchMatrixGlyphProjector` +
`GlyphConditionedAttentionLM` to minimize continuation cross-entropy + semantic/relational
reconstruction loss from ONLY continuous Matrix-Glyph soft tokens & depth-specialized KV slices
(`0` raw text tokens tokenized for archived episodes).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from logos.glyphs import DualPlaneGlyphTree
from logos.layers import DeterministicSpectralEmbedder, EpistemicTier, LogosLayerCompiler
from logos.operators.torch_projector import train_projector_on_glyphs
from logos.substrate.eval_long_horizon import build_unstructured_long_horizon_workload


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Train Horizon 2 L.O.G.O.S. Matrix-Glyph Projector & verify 0-token archived attention conditioning"
    )
    parser.add_argument("--epochs", type=int, default=40, help="Training epochs (default: 40)")
    parser.add_argument("--hidden-dim", type=int, default=128, help="Projector/LM hidden dimension (default: 128)")
    parser.add_argument("--soft-tokens", type=int, default=4, help="Soft tokens per glyph (default: 4)")
    parser.add_argument("--layers", type=int, default=6, help="Transformer attention layers (default: 6)")
    parser.add_argument("--lr", type=float, default=0.08, help="Base learning rate (default: 0.08)")
    parser.add_argument("--numpy", action="store_true", help="Force pure-NumPy analytical trainer even if torch is installed")
    parser.add_argument("--json-out", default=None, help="Optional JSON file path to save training metrics")
    args = parser.parse_args(argv)

    embedder = DeterministicSpectralEmbedder(dim=args.hidden_dim)
    compiler = LogosLayerCompiler(embedder=embedder, rank=4, use_nl_extractor=True)
    tree = DualPlaneGlyphTree(compiler=compiler, fanout=4)

    workload = build_unstructured_long_horizon_workload()
    for ep in workload["episodes"][:8]:
        tree.append_episode(ep["text"], epistemic_tier=ep["tier"])

    # Train over all compiled Ground + Elevated nodes in the Dual-Plane tree
    glyphs = [tree.nodes[gid] for gid in sorted(tree.nodes.keys())]

    metrics = train_projector_on_glyphs(
        glyphs=glyphs,
        epochs=args.epochs,
        lr=args.lr,
        hidden_dim=args.hidden_dim,
        num_soft_tokens=args.soft_tokens,
        num_layers=args.layers,
        num_heads=4,
        vocab_size=128,
        prefer_torch=not args.numpy,
        seed=42,
    )

    summary = {
        "backend": metrics["backend"],
        "epochs": metrics["epochs"],
        "glyph_count": metrics["glyph_count"],
        "frontier_notation": tree.frontier_notation(),
        "num_soft_tokens_per_glyph": metrics["num_soft_tokens_per_glyph"],
        "raw_archived_tokens": metrics["raw_archived_tokens"],
        "injected_soft_tokens": metrics["injected_soft_tokens"],
        "archived_text_tokens_tokenized": metrics["archived_text_tokens_tokenized"],
        "sequence_compression_factor": metrics["sequence_compression_factor"],
        "initial_total_loss": metrics["initial_total_loss"],
        "final_total_loss": metrics["final_total_loss"],
        "initial_ce_loss": metrics["initial_ce_loss"],
        "final_ce_loss": metrics["final_ce_loss"],
        "initial_perplexity": metrics["initial_perplexity"],
        "final_perplexity": metrics["final_perplexity"],
        "perplexity_reduction_ratio": metrics["perplexity_reduction_ratio"],
        "initial_semantic_cosine": metrics["initial_semantic_cosine"],
        "final_semantic_cosine": metrics["final_semantic_cosine"],
        "initial_relational_cosine": metrics["initial_relational_cosine"],
        "final_relational_cosine": metrics["final_relational_cosine"],
        "kv_prefix_byte_invariance": metrics["kv_prefix_byte_invariance"],
        "kv_append_preservation_ratio": metrics["kv_append_preservation_ratio"],
    }

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))

    # Fail-closed invariant gates
    if summary["archived_text_tokens_tokenized"] != 0:
        raise SystemExit("FAIL: archived_text_tokens_tokenized must be strictly 0")
    if not summary["kv_prefix_byte_invariance"]:
        raise SystemExit("FAIL: KVGlyphBank prefix byte invariance violated")
    if summary["final_total_loss"] >= summary["initial_total_loss"]:
        raise SystemExit("FAIL: training total_loss did not decrease")
    if summary["final_perplexity"] >= summary["initial_perplexity"]:
        raise SystemExit("FAIL: continuation perplexity did not decrease")
    if summary["final_semantic_cosine"] <= summary["initial_semantic_cosine"]:
        raise SystemExit("FAIL: semantic cosine reconstruction fidelity did not improve")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
