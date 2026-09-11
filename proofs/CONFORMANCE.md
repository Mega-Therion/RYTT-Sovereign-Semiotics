# Formal and Executable Conformance Boundary

The repository now maintains two related but distinct verification layers.

The Python reference compiler is checked against `conformance/vectors.json`, which covers empty input, mixed casing, chord-rich text, whitespace, symbols, Unicode passthrough, and the full ASCII alphabet. The browser implementation must consume the same vectors or produce byte-for-byte equivalent token traces.

`proofs/RYTT_standalone.lean` proves the core PUA round-trip behavior for its formally defined constructors. It is intentionally not described as a proof of every Python implementation detail. The bridge milestone is to generate a Lean-readable fixture or theorem input from the canonical specification and then add formal statements for plane disjointness, codepoint uniqueness, and chord decoding.

CI must report both statuses separately: executable conformance vectors and the pinned Lean standalone proof. Neither status may be inferred from the other.
