//! Canonical specification loading and validation.

use serde_json::Value;

/// The parsed canonical RYTT specification artifact.
#[derive(Debug, Clone)]
pub struct RyttSpec {
    raw: Value,
}

#[derive(Debug)]
pub enum SpecError {
    Parse(String),
}

impl std::fmt::Display for SpecError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            SpecError::Parse(m) => write!(f, "spec parse failed: {m}"),
        }
    }
}

impl std::error::Error for SpecError {}

impl RyttSpec {
    /// Load the canonical spec shipped with this repository.
    pub fn embedded() -> Result<Self, SpecError> {
        Self::from_json(include_str!(
            "../../../src/rytt/data/rytt-spec-v0.1.0.json"
        ))
    }

    /// Parse a spec artifact from raw JSON text.
    pub fn from_json(text: &str) -> Result<Self, SpecError> {
        let raw: Value =
            serde_json::from_str(text).map_err(|e| SpecError::Parse(e.to_string()))?;
        Ok(Self { raw })
    }

    /// BLAKE3 hash of the spec bytes; the vocabulary hash carried in envelopes.
    pub fn vocabulary_hash(&self) -> String {
        blake3::hash(self.raw.to_string().as_bytes()).to_hex().to_string()
    }

    /// Raw parsed spec, for adapter-specific inspection.
    pub fn raw(&self) -> &Value {
        &self.raw
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{PUA_LOWER_BOUND, PUA_UPPER_BOUND};

    #[test]
    fn embedded_spec_parses() {
        let spec = RyttSpec::embedded().expect("embedded spec must parse");
        assert!(!spec.vocabulary_hash().is_empty());
    }

    #[test]
    fn pua_bounds_are_distinct_and_ordered() {
        assert!(PUA_LOWER_BOUND < PUA_UPPER_BOUND);
    }
}
