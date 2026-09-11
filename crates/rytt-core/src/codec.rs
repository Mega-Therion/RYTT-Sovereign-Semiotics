//! Versioned interchange envelope and encode/decode boundary.

use crate::RyttSpec;
use serde::{Deserialize, Serialize};

/// Versioned RYTT interchange envelope.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Envelope {
    pub spec_version: String,
    pub vocabulary_hash: String,
    pub token_trace: Vec<TokenTrace>,
    pub metrics: Metrics,
    pub verified: bool,
}

/// One chord decision in the compile trace.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TokenTrace {
    pub source_offset: usize,
    pub token: u32,
    pub plane: u8,
    pub token_type: String,
}

/// Named metrics kept separate from character counts.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Metrics {
    pub input_characters: usize,
    pub output_codepoints: usize,
    pub exact_recovery: bool,
}

#[derive(Debug)]
pub enum CodecError {
    NotImplemented,
}

impl std::fmt::Display for CodecError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            CodecError::NotImplemented => write!(
                f,
                "chord mapping not implemented; stage 1 is the contract surface"
            ),
        }
    }
}

impl std::error::Error for CodecError {}

/// Encode input text into a versioned RYTT envelope.
pub fn encode(_spec: &RyttSpec, _input: &str) -> Result<Envelope, CodecError> {
    Err(CodecError::NotImplemented)
}

/// Decode an envelope back to the original text.
pub fn decode(_spec: &RyttSpec, _envelope: &Envelope) -> Result<String, CodecError> {
    Err(CodecError::NotImplemented)
}
