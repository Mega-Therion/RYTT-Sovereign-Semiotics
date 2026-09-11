//! Conformance vector replay against conformance/vectors.json.

use rytt_core::RyttSpec;

#[test]
fn vectors_artifact_parses() {
    let text = include_str!("../../../conformance/vectors.json");
    let parsed: serde_json::Value = serde_json::from_str(text).expect("vectors.json must parse");
    assert!(parsed.is_object() || parsed.is_array());
}

#[test]
#[ignore = "chord mapping not implemented yet; unignore after stage 2"]
fn replay_conformance_vectors() {
    let spec = RyttSpec::embedded().expect("embedded spec");
    let _ = spec; // encode/decode replay lands with the chord mapping PR
}
