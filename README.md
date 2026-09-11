# RYTT Sovereign Semiotics

[![CI](https://github.com/Mega-Therion/RYTT-Sovereign-Semiotics/actions/workflows/ci.yml/badge.svg)](https://github.com/Mega-Therion/RYTT-Sovereign-Semiotics/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/rytt-sovereign-semiotics)](https://pypi.org/project/rytt-sovereign-semiotics/)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![ORCID](https://img.shields.io/badge/ORCID-0009--0001--1303--7190-brightgreen)](https://orcid.org/0009-0001-1303-7190)
[![Tests: 45 passed](https://img.shields.io/badge/tests-45%20passed-6be49a)](tests/)

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
| Formal verification | Lean 4 standalone core, separately gated from executable conformance |

Full details in [`SPECIFICATION.md`](SPECIFICATION.md).

---

## Interactive research lab

Open **[`web/codex.html`](web/codex.html)** for the flagship Codex Studio workspace. It embeds the client-side compiler with token inspection, explainable trace output, named metrics, and JSON artifact export. The direct **[`web/playground.html`](web/playground.html)** route remains available for the focused compiler surface. The public deployment is available at [rytt-sovereign-semiotics.vercel.app](https://rytt-sovereign-semiotics.vercel.app/).

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
echo "sovereign" | rytt inspect

# Export and verify a portable offline artifact
printf "RYTT — naïve 東京" | rytt artifact-export artifact.zip
rytt artifact-verify artifact.zip
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

## Benchmark arena

```bash
python benchmarks/run_benchmarks.py
python benchmarks/arena.py
```

The first command runs the seven-corpus exact round-trip suite. The second creates the named-baseline report at `benchmarks/results/arena.html` and `benchmarks/results/arena.json`, keeping characters, UTF-8 bytes, RYTT tokens, runtime, and optional `cl100k_base` tokens as separate metrics. Read the [benchmark methodology](benchmarks/README.md).

---

## Verification

```bash
pytest -q
python scripts/generate_canonical_spec.py --check
python scripts/generate_conformance_vectors.py --check
python scripts/verify_conformance.py
python scripts/check_formal_alignment.py
python scripts/audit_static_site.py
```

The suite now covers 45 tests spanning property invariants, shared vectors, package interfaces, interchange integrity, renderer data, and the 4Leibniz bridge. The executable conformance vectors and standalone Lean proof are reported as separate verification layers. Legacy coverage includes:

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
├── src/rytt/                 Reference compiler, portable API, interchange, CLI
├── tests/                    Conformance, property, interface, and artifact tests
├── benchmarks/               Seven-corpus suite and named-baseline arena
├── web/                      Playground, Codex Studio, and generated data
├── fixtures/                 Versioned vocabulary JSON
├── conformance/              Shared cross-implementation vectors
├── spec/                     Canonical schema, format, and portable API contracts
├── renderers/                Glyph atlas, Blake loop, holonomic stack
├── proofs/                   Lean 4 verified core and conformance boundary
├── monograph/                Full treatise PDF
├── PLATFORM_ARCHITECTURE.md  Capability map and dependency direction
├── IMPLEMENTATION_PLAN.md    End-to-end roadmap and release gates
├── RESEARCH_QUESTIONS.md     Falsifiable external research agenda
├── OPERATIONS.md              Security, accessibility, performance, and release guide
├── CHANGELOG.md               Version history
└── pyproject.toml             Package metadata + CLI entry points
```

---

## Versioned vocabulary

The fixtures and browser data are generated from the live compiler:

```bash
python scripts/generate_web_data.py
```

Commit `fixtures/rytt_vocabulary.json` and `web/rytt-data.js` whenever the
vocabulary changes.

---

## License & author

Content: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) ·
Code: MIT

**R. W. Yett** · [ORCID 0009-0001-1303-7190](https://orcid.org/0009-0001-1303-7190)
