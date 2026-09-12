//! Canonical specification loading and token mapping derivation.

use serde_json::Value;

#[derive(Debug, Clone)]
pub struct RyttSpec {
    raw: Value,
    raw_text: String,
}

#[derive(Debug, Clone)]
pub struct TokenMapping {
    pub raw: String,
    pub pua: String,
    pub token_type: String,
    pub case_plane: i8,
}

#[derive(Debug)]
pub enum SpecError {
    Parse(String),
    Invalid(String),
}

impl std::fmt::Display for SpecError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Parse(message) => write!(f, "spec parse failed: {message}"),
            Self::Invalid(message) => write!(f, "invalid spec: {message}"),
        }
    }
}
impl std::error::Error for SpecError {}

impl RyttSpec {
    pub fn embedded() -> Result<Self, SpecError> {
        Self::from_json(include_str!("../data/rytt-spec-v0.1.0.json"))
    }
    pub fn from_json(text: &str) -> Result<Self, SpecError> {
        let raw =
            serde_json::from_str(text).map_err(|error| SpecError::Parse(error.to_string()))?;
        let spec = Self {
            raw,
            raw_text: text.to_owned(),
        };
        if spec.encoding_value("space_token").is_none() {
            return Err(SpecError::Invalid("encoding.space_token missing".into()));
        }
        Ok(spec)
    }
    pub fn vocabulary_hash(&self) -> String {
        blake3::hash(self.raw_text.as_bytes()).to_hex().to_string()
    }
    pub fn version(&self) -> Result<&str, SpecError> {
        self.raw
            .get("version")
            .and_then(Value::as_str)
            .ok_or_else(|| SpecError::Invalid("version missing".into()))
    }
    pub fn space_token(&self) -> Result<&str, SpecError> {
        self.encoding_value("space_token")
            .ok_or_else(|| SpecError::Invalid("encoding.space_token missing".into()))
    }
    pub fn mappings(&self) -> Result<Vec<TokenMapping>, SpecError> {
        let mut mappings = Vec::new();
        for section in ["genome", "ligatures"] {
            let entries = self
                .raw
                .get(section)
                .and_then(Value::as_object)
                .ok_or_else(|| SpecError::Invalid(format!("{section} missing")))?;
            for (raw, entry) in entries {
                let pua = entry
                    .get("pua")
                    .and_then(Value::as_str)
                    .ok_or_else(|| SpecError::Invalid(format!("{section}.{raw}.pua missing")))?;
                let token_type = entry
                    .get("family")
                    .and_then(Value::as_str)
                    .unwrap_or("CHORD")
                    .to_owned();
                let case_plane = entry
                    .get("case_plane")
                    .and_then(Value::as_i64)
                    .unwrap_or(-1) as i8;
                mappings.push(TokenMapping {
                    raw: raw.clone(),
                    pua: pua.to_owned(),
                    token_type,
                    case_plane,
                });
            }
        }
        mappings.sort_by(|left, right| {
            right
                .raw
                .len()
                .cmp(&left.raw.len())
                .then_with(|| left.raw.cmp(&right.raw))
        });
        Ok(mappings)
    }
    pub fn raw(&self) -> &Value {
        &self.raw
    }
    fn encoding_value(&self, key: &str) -> Option<&str> {
        self.raw.get("encoding")?.get(key)?.as_str()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{PUA_LOWER_BOUND, PUA_UPPER_BOUND};
    #[test]
    fn embedded_spec_parses() {
        let spec = RyttSpec::embedded().expect("embedded spec must parse");
        assert_eq!(spec.mappings().expect("mappings").len(), 98);
        assert!(!spec.vocabulary_hash().is_empty());
    }
    #[test]
    fn packaged_spec_matches_workspace_canonical_spec() {
        assert_eq!(
            include_str!("../data/rytt-spec-v0.1.0.json"),
            include_str!("../../../src/rytt/data/rytt-spec-v0.1.0.json")
        );
    }
    #[test]
    fn pua_bounds_are_distinct_and_ordered() {
        assert!(PUA_LOWER_BOUND < PUA_UPPER_BOUND);
    }
}
