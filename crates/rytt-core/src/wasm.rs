//! Browser and WASM string-in/string-out JSON boundary.

use crate::{decode, encode, Envelope, RyttSpec};
use wasm_bindgen::prelude::*;

fn error(message: impl std::fmt::Display) -> JsValue {
    JsValue::from_str(&message.to_string())
}

/// Encode text with the embedded canonical spec and return a JSON envelope.
/// This is intentionally string-in/string-out for direct browser and WASM use.
#[wasm_bindgen]
pub fn encode_json(input: &str) -> Result<String, JsValue> {
    let spec = RyttSpec::embedded().map_err(error)?;
    let envelope = encode(&spec, input).map_err(error)?;
    serde_json::to_string(&envelope).map_err(error)
}

/// Decode a JSON RYTT envelope using the embedded canonical spec.
#[wasm_bindgen]
pub fn decode_json(envelope_json: &str) -> Result<String, JsValue> {
    let spec = RyttSpec::embedded().map_err(error)?;
    let envelope: Envelope = serde_json::from_str(envelope_json).map_err(error)?;
    decode(&spec, &envelope).map_err(error)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn json_boundary_round_trips() {
        let encoded = encode_json("RYTT transforms").expect("encode JSON");
        assert_eq!(
            decode_json(&encoded).expect("decode JSON"),
            "RYTT transforms"
        );
    }
}
