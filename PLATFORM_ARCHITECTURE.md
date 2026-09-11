# RYTT Platform Architecture

## Vision

RYTT is developed as a reversible geometric token language and a reproducible research platform. The platform has five boundaries: a canonical specification, conforming implementations, experimental interfaces, portable artifacts, and applications.

## Capability map

| Capability | Responsibility | Primary interface | Verification |
|---|---|---|---|
| `canonical-spec` | Vocabulary, planes, chords, serialization, versions | JSON schema and generated tables | Schema validation and fixture hashes |
| `reference-python` | Normative compiler and CLI | Python API and `rytt` command | Unit, property, and conformance tests |
| `formal-core` | Verified token algebra and round-trip invariants | Lean definitions and theorem report | Pinned Lean build with no `sorry` |
| `browser-lab` | Interactive compilation, traces, geometry, comparison | Static web application | Browser smoke checks and accessibility audit |
| `benchmark-arena` | Named baseline comparisons and raw reports | CLI, JSON, HTML report | Reproducible corpora and schema validation |
| `portable-core` | Reusable implementation without browser or Python assumptions | WASM-compatible core boundary | Cross-runtime fixture parity |
| `interchange` | Versioned `.rytt` container and metadata | Textual JSON and binary-safe package | Encode/decode and corruption tests |
| `artifact-export` | Self-contained evidence bundle | CLI and browser download | Bundle replay verification |
| `codex-studio` | Flagship authoring and exploration workflow | Browser application | End-to-end user-flow tests |

## Dependency direction

`canonical-spec` → `reference-python` → `formal-core`, `browser-lab`, `benchmark-arena`, `portable-core` → `interchange` → `artifact-export` → `codex-studio`.

The specification owns public identifiers. Implementations may add diagnostics but may not silently redefine mappings. Display serialization is downstream from the token model and is never treated as the normative semantic layer.

## Release gates

| Release | Scope | Required gate |
|---|---|---|
| `0.2.0` | Canonical spec, conformance fixtures, artifact format, richer playground | All implementations agree on fixtures; bundle replay passes |
| `0.3.0` | Benchmark arena and portable core boundary | Named baseline report and cross-runtime parity |
| `0.4.0` | Codex Studio alpha | Create → inspect → export → replay flow passes |
| `1.0.0` | Stable public platform | Compatibility policy, independent implementation, formal core, accessibility and security review |

## Non-goals

RYTT will not claim universal compression, semantic understanding, lower model cost, or replacement of existing tokenizers without controlled evidence. The platform will preserve counterexamples and negative results as first-class research outputs.
