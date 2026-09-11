//! Executable replay against the canonical conformance vector artifact.

use rytt_core::{decode, encode, RyttSpec};
use serde_json::Value;

#[test]
fn replay_all_conformance_vectors() {
    let spec = RyttSpec::embedded().expect("embedded spec must parse");
    let vectors: Value = serde_json::from_str(include_str!("../../../conformance/vectors.json")).expect("vectors JSON must parse");
    for vector in vectors["vectors"].as_array().expect("vectors array") {
        let id = vector["id"].as_str().unwrap_or("unnamed");
        let source = vector["source"].as_str().expect("source");
        let expected_display = vector["encoded_display"].as_str().expect("encoded_display");
        let expected_count = vector["token_count"].as_u64().expect("token_count") as usize;
        let envelope = encode(&spec, source).unwrap_or_else(|error| panic!("{id}: encode failed: {error}"));
        assert_eq!(envelope.encoded_display, expected_display, "{id}: display mismatch");
        assert_eq!(envelope.token_trace.len(), expected_count, "{id}: token count mismatch");
        assert_eq!(decode(&spec, &envelope).unwrap(), source, "{id}: decode mismatch");
    }
}

#[test]
fn rejects_unknown_pua() {
    let spec = RyttSpec::embedded().expect("embedded spec");
    let mut envelope = encode(&spec, "a").expect("encode");
    envelope.encoded_display = "\u{E7FF}".to_owned();
    assert!(decode(&spec, &envelope).is_err());
}
