# RYTT Sovereign Semiotics

[![CI](https://github.com/Mega-Therion/RYTT-Sovereign-Semiotics/actions/workflows/ci.yml/badge.svg)](https://github.com/Mega-Therion/RYTT-Sovereign-Semiotics/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/rytt-sovereign-semiotics)](https://pypi.org/project/rytt-sovereign-semiotics/)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![ORCID](https://img.shields.io/badge/ORCID-0009--0001--1303--7190-brightgreen)](https://orcid.org/0009-0001-1303-7190)
[![Tests: 24 passed](https://img.shields.io/badge/tests-24%20passed-6be49a)](tests/)

> *A formal, lossless semiotic grammar mapping language into radial glyph primitives,
> compound chord ligatures, and reversible geometric invariants.*

**Core invariant:** `D(C(S)) ≡ S` — the decoded form of any compiled source is byte-identical to the original.

---

## Specification

| Dimension | Value |
|---|---|
| Glyph primitives | 52 (26 lower Ground Plane + 26 upper Elevated Plane) |
| Chord ligatures | 23 (high-frequency character sequences) |
| Ground Plane PUA range | U+E000 – U+E019 |
| Elevated Plane PUA range | U+E800 – U+E819 |
| Non-Latin characters | Pass through unchanged |
| Round-trip guarantee | D(C(S)) ≡ S for all inputs |
| Formal verification | Lean 4, in progress — see `proofs/RYTTProofs/TODO.md` for current build status |

Full details in [`SPECIFICATION.md`](SPECIFICATION.md).

---

## Interactive playground

Open **[`web/playground.html`](web/playground.html)** in any browser for client-side
encode/decode/round-trip with token inspection and exact metrics.

---

## Installation

```bash
pip install rytt-sovereign-semiotics
```

Or directly from source:

```bash
git clone https://github.com/Mega-Therion/RYTT-Sovereign-Semiotics.git
cd RYTT-Sovereign-Semiotics
pip install -e ".[dev]"
```

---

## CLI quick-start

```bash
# Encode
echo "Hello RYTT" | rytt encode

# Decode (round-trip)
echo "Hello RYTT" | rytt encode | rytt decode

# Inspect compilation result (JSON)
echo "sovereign" | rytt inspect --json
```

---

## Python API

```python
from rytt import RyttCompiler

compiler = RyttCompiler()
result = compiler.compile("Hello RYTT")
print(result.encoded_pua)        # PUA-encoded string
print(result.compression_ratio)  # float
print(result.token_savings_pct)  # float

# Round-trip
recovered = compiler.decompile(result.encoded_pua)
assert recovered == "Hello RYTT"  # always true by invariant
```

---

## Metrics

| Field | Description |
|---|---|
| `source_chars` | Original character count |
| `token_count` | RYTT token count after encoding |
| `chord_count` | Chord ligature tokens |
| `compression_ratio` | `source_chars / token_count` |
| `token_savings_pct` | `(1 − token_count/source_chars) × 100` |
| `utf8_bytes_source` | Source UTF-8 byte count |
| `utf8_bytes_encoded` | Encoded PUA UTF-8 byte count |
| `parity_mod24` | 24-character parity block |
| `round_trip_exact` | Boolean — `D(C(S)) == S` |

See [`SPECIFICATION.md`](SPECIFICATION.md) § Metric Boundary Table for the distinction
between *semantic* compression (token reduction) and *byte* compression.

---

## Benchmark

```bash
python benchmarks/run_benchmarks.py
```

Seven corpora (prose, code, mixed casing, punctuation, whitespace, Unicode passthrough, ligature-rich).
Results written to `benchmarks/results/benchmark_results.json`.

---

## Tests

```bash
pytest tests/ -v
```

24 property-style invariant tests covering:

- Round-trip fidelity (8 inputs)
- PUA plane disjointness (2 checks)
- Token uniqueness (3 checks)
- Ligature precedence (1 check)
- Fixture consistency (3 checks)
- Public interface contracts (4 checks)
- Non-Latin passthrough (1 check)
- Compiler instance isolation (2 checks)

---

## Repository layout

```
RYTT-Sovereign-Semiotics/
├── src/rytt/                 Compiler, tokenizer, CLI
├── tests/                    24 invariant tests
├── benchmarks/               7-corpus benchmark runner
├── web/                      Browser playground + generated vocabulary data
├── fixtures/                 Versioned vocabulary JSON
├── renderers/                Glyph atlas, Blake loop, holonomic stack
├── proofs/                   Lean 4 formal verification
├── monograph/                Full treatise PDF
├── SPECIFICATION.md          Capability map + implementation plan
├── CHANGELOG.md              Version history
└── pyproject.toml            Package metadata + CLI entry points
```

---

## Canonical versioned vocabulary

The machine-readable grammar contract is [`src/rytt/data/rytt-spec-v0.1.0.json`](src/rytt/data/rytt-spec-v0.1.0.json). It contains the complete genome and chord vocabulary and is checked against the Python compiler at import time. The fixture and browser data are generated projections:

```bash
python scripts/generate_web_data.py
```

Commit the canonical specification, `fixtures/rytt_vocabulary.json`, and
`web/rytt-data.js` whenever the vocabulary changes. The Lean definitions are
currently checked independently and are not yet generated from the JSON
artifact.

---

## License & author

Content: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) ·
Code: MIT

**R. W. Yett** · [ORCID 0009-0001-1303-7190](https://orcid.org/0009-0001-1303-7190)
