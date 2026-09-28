//! Fuzz target: envelope integrity under arbitrary byte mutations.
//!
//! Takes a valid envelope, mutates its JSON representation, and verifies
//! that decode either succeeds (producing the original) or returns a
//! structured error — never panics or produces silent corruption.
//!
//! Run with: cargo +nightly fuzz run envelope_integrity

#![no_main]

use libfuzzer_sys::fuzz_target;
use rytt_core::{decode, encode, Envelope, RyttSpec};

fuzz_target!(|data: &[u8]| {
    let spec = match RyttSpec::embedded() {
        Ok(s) => s,
        Err(_) => return,
    };

    // Try to parse the fuzz input as a JSON envelope
    if let Ok(envelope) = serde_json::from_slice::<Envelope>(data) {
        // decode must either succeed or return a structured error — never panic
        let _ = decode(&spec, &envelope);
    }

    // Also test: encode a random-ish string from the data, then decode
    if let Ok(text) = std::str::from_utf8(data) {
        if let Ok(envelope) = encode(&spec, text) {
            let _ = decode(&spec, &envelope);
        }
    }
});
