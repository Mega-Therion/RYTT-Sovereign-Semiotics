# RYTT Format Specification v0.1

## Layers

A RYTT artifact has three layers. The source layer is the original Unicode text. The token layer is an ordered sequence of primitive, chord, or passthrough records. The display layer is a human-readable PUA stream derived from the token layer.

## JSON interchange envelope

The canonical JSON envelope has this shape:

```json
{
  "format": "rytt",
  "format_version": "0.1",
  "spec_version": "0.1",
  "vocabulary_sha256": "...",
  "source_encoding": "utf-8",
  "source_text": "...",
  "encoded_display": "...",
  "tokens": [],
  "metrics": {},
  "verification": {}
}
```

`source_text` is optional for privacy-sensitive bundles but must be present for a verified artifact export. `tokens` preserve source sequence and exact offsets. `encoded_display` is not a binary-safe interchange channel and must not be interpreted without the metadata envelope.

## Token records

Each token record includes `index`, `source`, `kind`, `plane`, `codepoint`, `codepoint_int`, `is_chord`, and `passthrough`. Chord records additionally include `meaning` where available. Passthrough records retain their literal source and have no RYTT codepoint.

## Integrity

The vocabulary hash identifies the canonical `spec/vocabulary.json` file. A verifier must reject an artifact when the declared format version is unsupported, the vocabulary hash does not match the local specification, token offsets are not contiguous, or decoding does not reproduce `source_text` exactly.

## Privacy

Exporters must make source inclusion explicit. A display-only artifact may omit source text, but a verified artifact must state whether source text is embedded. No network access is required to verify a complete bundle.
