# L.O.G.O.S. — Layered Operator-Glyph Orchestration System (`v0.1.0`)

> **L**ayered **O**perator-**G**lyph **O**rchestration **S**ystem: A holographic, dual-plane virtual-memory architecture built over the canonical RYTT Sovereign Semiotics grammar.

---

## 1. Architecture Overview (5 Submodules)

L.O.G.O.S. solves the 1-glyph = 1-token bottleneck and long-context forgetting by encoding semantically coherent context epochs into 3-layer **Tensor-Glyphs** arranged in a logarithmic Dual-Plane RYTT Merkle-VSA tree:

| Submodule | Package Path | Role |
|---|---|---|
| **L — Layers** | `src/logos/layers/` | Compiles episodes into `(SemanticLayer V, RelationalLayer M=(U,V), ProvenanceLayer A)` packets `[D]`. Layer 3 embeds a deterministic **10,240-bit (`160 × uint64`) Bloom filter** + SHA-256 raw block hash `[D]`. |
| **O — Operators** | `src/logos/operators/` | **Horizon 1** renders compact structured glyph packets (`⟦L2:R(U+E811)\|...⟧`) for any LLM API `[D]`. **Horizon 2** projects glyphs into `(S, D)` soft tokens, depth-specialized per-layer KV-Glyph slices, rank-$r$ fast-weight adapters, and an append-only `KVGlyphBank` `[P]`. |
| **G — Glyphs** | `src/logos/glyphs/` | Maintains the Dual-Plane RYTT rollup tree (`1r → 2ry → 3ryt → 1R → 1R^L3`) with bounded fanout (`2 ≤ fanout ≤ 8`), bitemporal supersession ledger, QR+SVD relational operator compression, exact `int32` `VSAAccumulator`, and Anti-Glyph dead-end quarantines `[D]`. |
| **O — Orchestrator** | `src/logos/orchestrator/` | Splits overflows along semantic transitions (`SemanticEpisodeSplitter`), preserves a verbatim 20% Hot Tail, runs hierarchical Layer-3 Bloom MMU auto-prefetching, renders Dynamic LOD viewports inside strict token caps, and performs fail-closed SHA-256 `hydrate()` `[D]`. |
| **S — Substrate** | `src/logos/substrate/` | Append-only SQLite WAL + FTS5 raw/glyph store (`LogosSubstrate`), verifiable portable `.logos` ZIP cartridges (`export_cartridge`, `verify_cartridge`, `load_cartridge`), and comparative evaluation benchmark (`run_logos_benchmark`) `[D]`. |

---

## 2. VSA Exponential-Forgetting Fix (`src/rytt/vsa.py`)

Iterative pairwise `superpose([composite, step_vector])` weighted older items by $2^{-t}$, causing Step 0 to decay to noise across 25 steps (`0.5035` similarity). `VSAAccumulator` maintains exact `int32[10240]` bit counts and thresholds only at readout, restoring Step 0 similarity to `0.5790` across 25 steps (`tests/test_logos_vsa_fix.py`) `[D]`.

---

## 3. Measured Benchmark Results (`logos benchmark`)

Run on the 16-episode multi-overflow workload (`context_budget_tokens=1100`, `fanout=4`, 6 rare Epoch-1–5 exact needles, 5 bitemporal slot supersessions, 3 Tier-F Anti-Glyphs) `[D]`:

| System / Backend | Exact Needle Recall | Supersession Accuracy | Anti-Glyph Recall | KV Prefix Preservation | Step-0 VSA Similarity (25 steps) |
|---|---:|---:|---:|---:|---:|
| Sliding Window Baseline | `0.00` (`0/6`) | `0.00` (`0/5`) | `0.00` (`0/3`) | — | — |
| Progressive Prose Compaction | `0.00` (`0/6`) | `0.00` (`0/5`) | `0.00` (`0/3`) | — | — |
| **L.O.G.O.S.** (`deterministic-spectral`) | **`1.00` (`6/6`)** | **`1.00` (`5/5`)** | **`1.00` (`3/3`)** | **`1.00`** (`42/42` prefix slots preserved) | **`0.5790`** (`0.5035` legacy) |
| **L.O.G.O.S.** (`ollama:nomic-embed-text:latest`) | **`1.00` (`6/6`)** | **`1.00` (`5/5`)** | **`1.00` (`3/3`)** | **`1.00`** (`42/42` prefix slots preserved) | **`0.5790`** (`0.5035` legacy) |

- Tree frontier reached: `3RYT+3ryt` (`18` total nodes + `3` Anti-Glyphs, Merkle & Bloom superset integrity verified `true`).
- Virtual tokens covered: `3,745` tokens rendered into `876.09` average viewport tokens (`4.27×` effective compression at the small `1,100`-token toy stress budget; uncompressed frontier metadata grows logarithmically $O(\log N)$).
- Hierarchical Bloom MMU lookup latency: `5.39 ms` (`deterministic-spectral`) / `3.01 ms` (`ollama:nomic-embed-text:latest`).

*Epistemic boundary note*: `Horizon2MatrixProjector` projection math, per-layer KV-Glyph compilation, fast-weight deltas, and PyTorch tensor conversion are unit-tested (`tests/test_logos_operators_and_substrate.py`) `[D]`, while end-to-end closed-loop fine-tuning against live Transformer weights remains a downstream research step (`[O]`).

---

## 4. Quick Usage (CLI, Python API & MCP Server)

```bash
# Self-contained 1r -> 2ry -> 3ryt -> 1R + Bloom MMU demo
logos demo

# Reproducible benchmark (deterministic or local Ollama)
logos benchmark
logos benchmark --ollama

# Persistent SQLite workflow & portable cartridge
logos ingest --db session.db --role system "CANONICAL_PORT=18443; ERR_4912 fixed."
logos compose --db session.db --query "Status of ERR_4912?" --max-tokens 4096
logos status --db session.db
logos export --db session.db session.logos
logos verify session.logos

# Stdio MCP server (FastMCP when mcp is installed, or zero-dep JSON-RPC 2.0)
logos-mcp --db session.db
```

### Exposed MCP Tools (`logos-mcp`)
1. `logos_ingest_turn`
2. `logos_compose_viewport`
3. `logos_hydrate_glyph`
4. `logos_register_anti_glyph`
5. `logos_status`
6. `logos_export_cartridge`
