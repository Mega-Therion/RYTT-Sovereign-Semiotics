//! Property and malformed-envelope tests for the portable RYTT boundary.

use proptest::prelude::*;
use rytt_core::{decode, encode, RyttSpec};

fn representative_unicode() -> impl Strategy<Value = String> {
    prop::collection::vec(
        prop::sample::select(vec![
            'a', 'e', 'i', 'o', 't', 'r', 'n', 'z', 'A', 'E', 'I', 'O', 'T', 'R', 'Y', 'Z', ' ',
            '\n', '\t', '!', '?', '%', '[', ']', '{', '}', '0', '9', '—', 'é', 'ï', 'α', 'Δ', '東',
            '京', '😀', '🧪', '🧬',
            // Reserved display codepoints, which encode behind the escape: the space token, a ground
            // glyph, an elevated glyph, a chord, unallocated PUA, and both ends of the PUA range.
            '·', '\u{E000}', '\u{E800}', '\u{E840}', '\u{E7FF}', '\u{F8FF}',
        ]),
        0..160,
    )
    .prop_map(|characters| characters.into_iter().collect())
}

proptest! {
    #![proptest_config(ProptestConfig {
        cases: 10_000,
        max_shrink_iters: 0,
        .. ProptestConfig::default()
    })]

    #[test]
    fn encode_then_decode_recovers_representative_unicode(input in representative_unicode()) {
        let spec = RyttSpec::embedded().expect("embedded spec must parse");
        let envelope = encode(&spec, &input).expect("representative input must encode");
        prop_assert_eq!(decode(&spec, &envelope).expect("generated envelope must decode"), input);
    }
}

#[test]
fn rejects_truncated_encoded_display() {
    let spec = RyttSpec::embedded().expect("embedded spec must parse");
    let mut envelope = encode(&spec, "RYTT keeps exact recovery").expect("input must encode");
    envelope.encoded_display.pop();

    let error = decode(&spec, &envelope).expect_err("truncated display must be rejected");
    assert!(error.to_string().contains("envelope integrity"));
}

#[test]
fn rejects_mismatched_spec_version() {
    let spec = RyttSpec::embedded().expect("embedded spec must parse");
    let mut envelope = encode(&spec, "version check").expect("input must encode");
    envelope.spec_version = "0.0.0".to_owned();

    let error = decode(&spec, &envelope).expect_err("mismatched version must be rejected");
    assert!(error.to_string().contains("version"));
}

#[test]
fn rejects_tampered_vocabulary_hash() {
    let spec = RyttSpec::embedded().expect("embedded spec must parse");
    let mut envelope = encode(&spec, "hash check").expect("input must encode");
    envelope.vocabulary_hash = "00".repeat(32);

    let error = decode(&spec, &envelope).expect_err("tampered hash must be rejected");
    assert!(error.to_string().contains("vocabulary hash"));
}

#[test]
fn empty_input_retains_a_valid_empty_envelope() {
    let spec = RyttSpec::embedded().expect("embedded spec must parse");
    let envelope = encode(&spec, "").expect("empty input must encode");

    assert!(envelope.encoded_display.is_empty());
    assert!(envelope.token_trace.is_empty());
    assert_eq!(
        decode(&spec, &envelope).expect("empty envelope must decode"),
        ""
    );
}

#[test]
fn reserved_codepoints_round_trip_behind_the_escape() {
    let spec = RyttSpec::embedded().expect("embedded spec must parse");
    let input = "a\u{B7}b \u{E000}\u{E840}\u{F8FF}";
    let envelope = encode(&spec, input).expect("input must encode");
    assert_eq!(
        envelope.encoded_display,
        "\u{E000} \u{B7}\u{E001}\u{B7} \u{E000} \u{E840} \u{F8FF}"
    );
    assert_eq!(
        decode(&spec, &envelope).expect("envelope must decode"),
        input
    );
}

#[test]
fn rejects_dangling_escape() {
    let spec = RyttSpec::embedded().expect("embedded spec must parse");
    let mut envelope = encode(&spec, "\u{B7}").expect("input must encode");
    envelope.encoded_display = " ".to_owned();
    envelope.token_trace[0].pua = " ".to_owned();
    envelope.metrics.output_codepoints = 1;

    let error = decode(&spec, &envelope).expect_err("dangling escape must be rejected");
    assert!(error.to_string().contains("envelope integrity"));
}

#[test]
fn rejects_escape_token_whose_literal_differs_from_its_source() {
    let spec = RyttSpec::embedded().expect("embedded spec must parse");
    let mut envelope = encode(&spec, "\u{B7}").expect("input must encode");
    envelope.encoded_display = " \u{E000}".to_owned();
    envelope.token_trace[0].pua = " \u{E000}".to_owned();
    envelope.token_trace[0].token = 0xE000;

    let error = decode(&spec, &envelope).expect_err("mismatched escape literal must be rejected");
    assert!(error.to_string().contains("escape token literal"));
}
