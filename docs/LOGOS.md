# L.O.G.O.S. — Layered Operator-Glyph Orchestration System (`v0.4.0`)

> **L**ayered **O**perator-**G**lyph **O**rchestration **S**ystem: A holographic, dual-plane virtual-memory architecture built over the canonical RYTT Sovereign Semiotics grammar across Horizons 1–3 (`v0.1.0` → `v0.4.0`).

---

## 1. Architecture Overview (5 Submodules · Horizons 1–3)

L.O.G.O.S. solves the 1-glyph = 1-token bottleneck, long-context forgetting, and multi-agent context fragmentation by encoding semantically coherent context epochs into 3-layer **Tensor-Glyphs** arranged in a logarithmic Dual-Plane RYTT Merkle-VSA tree:

| Submodule | Package Path | Role |
|---|---|---|
| **L — Layers** | `src/logos/layers/` | Compiles episodes into `(SemanticLayer V, RelationalLayer M=(U,V), ProvenanceLayer A)` packets `[D]`. Layer 2 includes `NaturalLanguageDeltaExtractor` and `OllamaStateDeltaExtractor` for unstructured prose slot/supersession/anti-claim extraction `[D]`. Layer 3 embeds a deterministic **10,240-bit (`160 × uint64`) Bloom filter** + SHA-256 raw block hash `[D]`. |
| **O — Operators** | `src/logos/operators/` | **Horizon 1** renders compact structured glyph packets (`⟦L2:R(U+E811)\|...⟧`) for any LLM API `[D]`. **Horizon 2** (`Horizon2MatrixProjector`, `TorchMatrixGlyphProjector`, `NumpyMatrixGlyphTrainer`, `GlyphConditionedAttentionLM`) projects glyphs into continuous `(batch, k, hidden_dim)` soft tokens (`0` archived text tokens), depth-specialized per-layer `(K_l, V_l)` KV-Glyph slices, rank-$r$ fast-weight adapters `(A, B)`, and an append-only `KVGlyphBank` `[D]`. |
| **G — Glyphs** | `src/logos/glyphs/` | Maintains the Dual-Plane RYTT rollup tree (`1r → 2ry → 3ryt → 1R → 1R^L3`) with bounded fanout (`2 ≤ fanout ≤ 8`), offline semantic re-clustering (`sleep_consolidate()`), bitemporal supersession ledger, QR+SVD relational operator compression, exact `int32` `VSAAccumulator`, and Anti-Glyph dead-end quarantines `[D]`. |
| **O — Orchestrator** | `src/logos/orchestrator/` | Splits overflows along semantic transitions (`SemanticEpisodeSplitter`), preserves a verbatim 20% Hot Tail, runs hierarchical Layer-3 Bloom MMU auto-prefetching with leaf hit+cosine ranking, renders Dynamic LOD viewports inside strict token caps, and performs fail-closed SHA-256 `hydrate()` `[D]`. |
| **S — Substrate** | `src/logos/substrate/` | Append-only SQLite WAL + FTS5 raw/glyph store (`LogosSubstrate`), verifiable portable `.logos` ZIP cartridges (`export_cartridge`, `verify_cartridge`, `load_cartridge`), cross-agent CRDT/bitemporal merge bus (`merge_cartridges`), structured benchmark (`run_logos_benchmark`), and unstructured natural-language long-horizon eval (`run_long_horizon_eval`) `[D]`. |

---

## 2. VSA Exponential-Forgetting Fix (`src/rytt/vsa.py`)

Iterative pairwise `superpose([composite, step_vector])` weighted older items by $2^{-t}$, causing Step 0 to decay to noise across 25 steps (`0.5035` similarity). `VSAAccumulator` maintains exact `int32[10240]` bit counts and thresholds only at readout, restoring Step 0 similarity to `0.5790` across 25 steps (`tests/test_logos_vsa_fix.py`) `[D]`.

---

## 3. Horizon 1 Hardening (`v0.2`): Unstructured Natural-Language Eval & Sleep Consolidation

### 3.1 Structured 16-Episode Benchmark (`logos benchmark`)
Run on the 16-episode multi-overflow workload (`context_budget_tokens=1100`, `fanout=4`, 6 rare Epoch-1–5 exact needles, 5 bitemporal slot supersessions, 3 Tier-F Anti-Glyphs) `[D]`:

| System / Backend | Exact Needle Recall | Supersession Accuracy | Anti-Glyph Recall | KV Prefix Preservation | Step-0 VSA Similarity (25 steps) |
|---|---:|---:|---:|---:|---:|
| Sliding Window Baseline | `0.00` (`0/6`) | `0.00` (`0/5`) | `0.00` (`0/3`) | — | — |
| Progressive Prose Compaction | `0.00` (`0/6`) | `0.00` (`0/5`) | `0.00` (`0/3`) | — | — |
| **L.O.G.O.S.** (`deterministic-spectral`) | **`1.00` (`6/6`)** | **`1.00` (`5/5`)** | **`1.00` (`3/3`)** | **`1.00`** (`42/42` prefix slots preserved) | **`0.5790`** (`0.5035` legacy) |
| **L.O.G.O.S.** (`ollama:nomic-embed-text:latest`) | **`1.00` (`6/6`)** | **`1.00` (`5/5`)** | **`1.00` (`3/3`)** | **`1.00`** (`42/42` prefix slots preserved) | **`0.5790`** (`0.5035` legacy) |

### 3.2 Unstructured Natural-Language Long-Horizon Eval (`logos long-eval`)
Evaluated on an 18-turn distributed systems & formal verification incident log containing **zero** artificial `KEY=VALUE` strings (`zero_artificial_kv_tokens=true`), 6 buried technical needles, 5 natural-language supersessions (*"ditched port 9090 and moved the gateway to 18443"*, *"deprecated tools/old_gate.py and now use 1_engine/tools/check_claim_gate.py"*), 3 natural-language disproven branches, and offline `sleep_consolidate()` semantic re-clustering (`3,418` virtual tokens into a `1,100`-token budget) `[D]`:

| System / Backend | Exact Needle Recall | NL Supersession Accuracy | Anti-Glyph Recall | Intra-Cluster Cosine (`Before → After`) | Closed-Loop Ollama QA (`qwen2.5:1.5b`) |
|---|---:|---:|---:|---:|---:|
| Sliding Window Baseline | `0.00` (`0/6`) | `0.20` (`1/5`) | `0.00` (`0/3`) | — | `0.00` |
| Progressive Prose Compaction | `0.00` (`0/6`) | `0.20` (`1/5`) | `0.00` (`0/3`) | — | `0.00` |
| **L.O.G.O.S.** (`deterministic-spectral` + `deterministic-nl`) | **`1.00` (`6/6`)** | **`1.00` (`5/5`)** | **`1.00` (`3/3`)** | **`0.6980 → 0.7522` (`+0.0542`)** | — |
| **L.O.G.O.S.** (`ollama:nomic-embed-text` + `qwen2.5:1.5b`) | **`1.00` (`6/6`)** | **`1.00` (`5/5`)** | **`1.00` (`3/3`)** | **`0.7971 → 0.8205` (`+0.0235`)** | **`0.75` – `1.00`** |

- On interleaved multi-topic workloads (`tests/test_logos_horizons.py`), `DualPlaneGlyphTree.sleep_consolidate()` raises mean intra-cluster cosine coherence by **`+0.15+`** while preserving 100% of raw Layer-3 SHA-256 hashes, bitemporal truth slots, and Merkle + Bloom superset invariants (`verify_integrity()["valid"] == True`) `[D]`.

---

## 4. Horizon 2 Completion (`v0.3`): Trainable Matrix-Glyph Projector & Tokenization Bypass

`TorchMatrixGlyphProjector` (with PyTorch `nn.Module` autograd + pure-NumPy analytical twin `NumpyMatrixGlyphTrainer`) and `GlyphConditionedAttentionLM` (`src/logos/operators/torch_projector.py`, `scripts/train_logos_projector.py`) project each 3-layer `TensorGlyph` directly into continuous soft tokens `(batch, k, hidden_dim)`, depth-specialized per-layer `(K_l, V_l)` KV-cache slices (Early = Layer-3 Bloom/RYTT geometry, Middle = Layer-2 relational `(U, V)`, Late = Layer-1 semantic), and low-rank fast-weight deltas `(A, B)` `[D]`:

| Metric (`python scripts/train_logos_projector.py --epochs 40 --hidden-dim 128`) | Initial (Epoch 0) | Trained (Epoch 40) | Status / Invariant |
|---|---:|---:|---|
| Archived Text Tokens Tokenized | `0` | **`0`** | Direct continuous soft-token + KV bypass `[D]` |
| Sequence Compression (`3,206 raw / 40 soft tokens`) | `80.15×` | **`80.15×`** | `4` soft tokens per glyph across `10` nodes `[D]` |
| Joint Continuation + Reconstruction Total Loss | `7.8354` | **`0.0808`** | Monotonic convergence (`PyTorch` & `NumPy`) `[D]` |
| Continuation Cross-Entropy Perplexity | `127.3659` | **`1.0003`** | **`127.33×` perplexity reduction** `[D]` |
| Layer-1 Semantic Cosine Reconstruction | `0.0263` | **`0.9902`** | Near-unit semantic recovery `[D]` |
| Layer-2 Relational Operator Cosine Reconstruction | `-0.0185` | **`0.9562`** | High-fidelity relational recovery `[D]` |
| `KVGlyphBank` Prefix Byte-Invariance | `1.0000` | **`1.0000`** | `kv_prefix_byte_invariance = true` `[D]` |

*Epistemic boundary note*: `TorchMatrixGlyphProjector` and `GlyphConditionedAttentionLM` prove end-to-end differentiable training, zero-text-token archived conditioning, and prefix byte-invariance on self-contained causal attention layers `[D]`; grafting adapters into external multi-billion-parameter pretrained checkpoints remains an open scale-up track `[O]`.

---

## 5. Horizon 3 Completion (`v0.4`): Sovereign Multi-Agent Cartridge Bus & Constellation HUD

1. **Cross-Agent Bitemporal Cartridge Merge Bus (`src/logos/substrate/cartridge_bus.py`)** `[D]`:
   - `merge_cartridges(path_a, path_b, output_path, consolidate=...)` performs fail-closed verification of independent `.logos` archives, deduplicates raw blocks by SHA-256, merges Ground leaves and Anti-Glyph quarantines, and resolves slot conflicts deterministically by `(epistemic_tier_rank, valid_from, glyph_id)` (ensuring verified `[D]` truths are never overwritten by `[O]` speculations while preserving the full revision chain in `bitemporal_ledger`).
2. **Interactive Dual-Plane Constellation HUD (`web/logos-hud.html`)** `[D]`:
   - Zero-dependency static HTML/SVG/JS radial constellation visualizer rendering the Hot Tail core, Ground ring (`r, y, t, t`), Elevated ring (`R, Y`), Super ring (`R^L3`), and Quarantined Anti-Glyph ring (`¬`), with live Layer 1–3 node inspection, Bloom MMU entity probing, and `logos hud-export` JSON file loading. Permanently guarded by `scripts/audit_static_site.py` `[D]`.

---

## 6. CLI & MCP Reference (`logos` / `logos-mcp`)

```bash
# Self-contained 1r -> 2ry -> 3ryt -> 1R + Bloom MMU demo
logos demo

# Structured & unstructured long-horizon benchmarks (deterministic or local Ollama)
logos benchmark [--ollama]
logos long-eval [--ollama]

# Persistent SQLite workflow, sleep consolidation, truth history & HUD export
logos ingest --db session.db --role system "We switched the gateway port from 8080 to 18443."
logos compose --db session.db --query "Current gateway port?" --max-tokens 4096
logos consolidate --db session.db
logos history --db session.db --key GATEWAY_PORT
logos hud-export --db session.db --out session-hud.json
logos status --db session.db

# Portable .logos cartridges & multi-agent CRDT merge
logos export --db session.db agent_a.logos
logos merge agent_a.logos agent_b.logos merged.logos --consolidate
logos verify merged.logos

# Trainable Horizon 2 Matrix-Glyph Projector proof script
python scripts/train_logos_projector.py --epochs 40 --hidden-dim 128

# Stdio MCP server (10 tools via FastMCP or zero-dep JSON-RPC 2.0)
logos-mcp --db session.db
```

### Exposed MCP Tools (`logos-mcp`)
1. `logos_ingest_turn`
2. `logos_compose_viewport`
3. `logos_hydrate_glyph`
4. `logos_register_anti_glyph`
5. `logos_status`
6. `logos_export_cartridge`
7. `logos_merge_cartridges`
8. `logos_sleep_consolidate`
9. `logos_query_truth_history`
10. `logos_export_hud_json`
