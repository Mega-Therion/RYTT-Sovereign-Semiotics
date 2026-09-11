# RYTT Interoperability Contract

The portable boundary is JSON-first and intentionally independent of Python-specific classes. An encoder accepts either plain source text or `{ "operation": "encode", "source_text": "..." }` and returns the versioned RYTT interchange envelope. A decoder accepts that envelope and returns `{ "valid": true|false, "errors": [], "decoded_text": "..." }`.

Implementations must preserve the declared specification version, format version, vocabulary hash, source text, display serialization, token sequence, and exact-recovery result. They must not infer a different vocabulary from the display stream or silently replace unsupported characters.

The current browser implementation is a practical client-side adapter. The Python package is the reference implementation. A future Rust or WebAssembly core can target `spec/portable-api.schema.json` and `spec/format.md` without depending on the Python package layout.
