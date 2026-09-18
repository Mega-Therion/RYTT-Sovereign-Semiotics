---
license: mit
pretty_name: RYTT Sovereign Semiotics Conformance Benchmarks
tags:
  - tokenization
  - formal-verification
  - semiotics
---

# RYTT Sovereign Semiotics Conformance Benchmarks

This dataset mirrors the conformance vectors and vocabulary specification of
**RYTT** (Recursive Yield Token Transform), a sovereign semiotic encoding
scheme with a Lean-verified round-trip guarantee.

**Source of truth is the GitHub repository — this Hub dataset is a mirror,
not the canonical copy:**
https://github.com/Mega-Therion/RYTT-Sovereign-Semiotics

## Splits

- **`vocabulary_spec`** (`rytt-spec-v0.1.0.json`) — the versioned RYTT
  vocabulary: 52 genome symbols + 46 ligatures, matched by
  greedy-longest-match. Spaces are rendered as the display token `·`.
  Non-letter Unicode characters pass through unchanged (they are outside the
  ASCII-letter genome this vocabulary covers). Encoded tokens occupy the
  Private Use Area in two planes: **ground** (base `U+E000`, elevation
  `z=0`) and **elevated** (base `U+E800`, elevation `z=25`).
- **`conformance_vectors`** (`vectors.json`) — 7 fixed test vectors used to
  check any RYTT implementation against the spec: `empty`,
  `ascii_mixed_case`, `chord_rich`, `whitespace`, `symbols`,
  `unicode_passthrough`, `all_ascii`.

Both files are copied byte-for-byte from the GitHub repository; nothing here
has been regenerated, summarized, or rewritten.

## What this dataset does not claim

This card does not report a token-compression percentage. An earlier,
unverified compression claim for RYTT was checked against `tiktoken` and
found false — RYTT produced *more* tokens, not fewer — so no savings figure
is stated here, verified or otherwise. Treat any compression number for RYTT
you encounter elsewhere as unverified until measured directly against the
vectors in this dataset.

## Related

- `rytt-core` (Rust crate, in the source repo) exposes WASM-bindgen
  `encode_json` / `decode_json` entry points for round-tripping the vectors
  above from JavaScript/WASM hosts.
- License: MIT, matching the source repository's `crates/rytt-core/LICENSE`.

## Loading

```python
import json
from huggingface_hub import hf_hub_download

vectors_path = hf_hub_download(
    repo_id="ChyrenAI/rytt-sovereign-semiotics-benchmarks",
    filename="vectors.json",
    repo_type="dataset",
)
vectors = json.load(open(vectors_path))

spec_path = hf_hub_download(
    repo_id="ChyrenAI/rytt-sovereign-semiotics-benchmarks",
    filename="rytt-spec-v0.1.0.json",
    repo_type="dataset",
)
spec = json.load(open(spec_path))
```
