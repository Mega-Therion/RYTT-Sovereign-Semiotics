//! Fuzz target: RYTT round-trip reversibility and idempotency.
//!
//! Drives the codec with arbitrary Unicode strings and asserts:
//!   1. decode(encode(s)) == s  (reversibility)
//!   2. encode(decode(encode(s))) == encode(s)  (idempotency)
//!
//! Run with: cargo +nightly fuzz run roundtrip

#![no_main]

use libfuzzer_sys::fuzz_target;
use rytt_core::{decode, encode, RyttSpec};

fuzz_target!(|input: String| {
    let spec = match RyttSpec::embedded() {
        Ok(s) => s,
        Err(_) => return,
    };

    if let Ok(envelope) = encode(&spec, &input) {
        // Reversibility: decode(encode(s)) must equal s
        let decoded = match decode(&spec, &envelope) {
            Ok(d) => d,
            Err(_) => {
                panic!("Decoding must succeed for validly encoded envelope: input = {input:?}")
            }
        };
        assert_eq!(
            input, decoded,
            "Reversibility invariant violated: decode(encode(s)) != s\n  input:    {input:?}\n  decoded:  {decoded:?}"
        );

        // Idempotency: re-encoding the decoded text must produce the same envelope display
        if let Ok(re_encoded) = encode(&spec, &decoded) {
            assert_eq!(
                envelope.encoded_display, re_encoded.encoded_display,
                "Idempotency invariant violated: encode(decode(encode(s))) != encode(s)"
            );
        }
    }
});
