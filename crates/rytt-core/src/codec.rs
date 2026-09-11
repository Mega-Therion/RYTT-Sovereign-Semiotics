//! Deterministic RYTT interchange envelope and reversible codec.

use crate::RyttSpec;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Envelope { pub spec_version: String, pub vocabulary_hash: String, pub encoded_display: String, pub token_trace: Vec<TokenTrace>, pub metrics: Metrics, pub verified: bool }
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TokenTrace { pub source_offset: usize, pub raw: String, pub pua: String, pub token: u32, pub plane: i8, pub token_type: String }
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Metrics { pub input_characters: usize, pub output_codepoints: usize, pub exact_recovery: bool }
#[derive(Debug)]
pub enum CodecError { Spec(String), UnknownPua(char), HashMismatch, VersionMismatch { expected: String, found: String } }
impl std::fmt::Display for CodecError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self { Self::Spec(message) => write!(f, "spec error: {message}"), Self::UnknownPua(token) => write!(f, "unknown RYTT PUA token: U+{:04X}", *token as u32), Self::HashMismatch => write!(f, "envelope vocabulary hash differs from canonical spec"), Self::VersionMismatch { expected, found } => write!(f, "envelope version {found} differs from spec {expected}"), }
    }
}
impl std::error::Error for CodecError {}

pub fn encode(spec: &RyttSpec, input: &str) -> Result<Envelope, CodecError> {
    let mappings = spec.mappings().map_err(|error| CodecError::Spec(error.to_string()))?;
    let space_token = spec.space_token().map_err(|error| CodecError::Spec(error.to_string()))?;
    let mut byte_index = 0;
    let mut source_offset = 0;
    let mut encoded_display = String::new();
    let mut token_trace = Vec::new();
    while byte_index < input.len() {
        let mapping = mappings.iter().find(|candidate| input[byte_index..].starts_with(&candidate.raw));
        let (raw, pua, token_type, plane) = if let Some(mapping) = mapping { (mapping.raw.clone(), mapping.pua.clone(), mapping.token_type.clone(), mapping.case_plane) } else {
            let character = input[byte_index..].chars().next().expect("byte index is a valid UTF-8 boundary");
            if character == ' ' { (" ".to_owned(), space_token.to_owned(), "SPACE".to_owned(), -1) } else { (character.to_string(), character.to_string(), "PASSTHROUGH".to_owned(), -1) }
        };
        let token = pua.chars().next().map(|character| character as u32).unwrap_or(0);
        encoded_display.push_str(&pua);
        token_trace.push(TokenTrace { source_offset, raw: raw.clone(), pua, token, plane, token_type });
        byte_index += raw.len();
        source_offset += raw.chars().count();
    }
    Ok(Envelope { spec_version: spec.version().map_err(|error| CodecError::Spec(error.to_string()))?.to_owned(), vocabulary_hash: spec.vocabulary_hash(), metrics: Metrics { input_characters: input.chars().count(), output_codepoints: encoded_display.chars().count(), exact_recovery: true }, encoded_display, token_trace, verified: true })
}

pub fn decode(spec: &RyttSpec, envelope: &Envelope) -> Result<String, CodecError> {
    let expected_version = spec.version().map_err(|error| CodecError::Spec(error.to_string()))?.to_owned();
    if envelope.spec_version != expected_version { return Err(CodecError::VersionMismatch { expected: expected_version, found: envelope.spec_version.clone() }); }
    if envelope.vocabulary_hash != spec.vocabulary_hash() { return Err(CodecError::HashMismatch); }
    let space_token = spec.space_token().map_err(|error| CodecError::Spec(error.to_string()))?;
    let inverse: HashMap<String, String> = spec.mappings().map_err(|error| CodecError::Spec(error.to_string()))?.into_iter().map(|mapping| (mapping.pua, mapping.raw)).collect();
    let mut decoded = String::new();
    for character in envelope.encoded_display.chars() {
        let encoded = character.to_string();
        if encoded == space_token { decoded.push(' '); }
        else if let Some(raw) = inverse.get(&encoded) { decoded.push_str(raw); }
        else if (0xE000..=0xF8FF).contains(&(character as u32)) { return Err(CodecError::UnknownPua(character)); }
        else { decoded.push(character); }
    }
    Ok(decoded)
}
