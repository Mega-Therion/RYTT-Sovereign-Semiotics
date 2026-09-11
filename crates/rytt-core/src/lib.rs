//! # rytt-core
//!
//! JSON-first portable boundary for the RYTT sovereign semiotics grammar.
//! The canonical spec artifact remains the single source of truth.

pub mod chord;
pub mod codec;
pub mod spec;
pub mod wasm;

pub use chord::{Chord, Plane};
pub use codec::{decode, encode, CodecError, Envelope, Metrics, TokenTrace};
pub use spec::{RyttSpec, SpecError, TokenMapping};

/// Lower PUA compound boundary: U+E020.
pub const PUA_LOWER_BOUND: u32 = 0xE020;
/// Upper PUA compound boundary: U+E820.
pub const PUA_UPPER_BOUND: u32 = 0xE820;
/// Canonical specification version this crate is built against.
pub const SPEC_VERSION: &str = "0.1.0";
