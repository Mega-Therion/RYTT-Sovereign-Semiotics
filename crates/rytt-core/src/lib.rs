//! # rytt-core
//!
//! JSON-first portable boundary for the RYTT sovereign semiotics grammar.
//! Contract surface for future Rust, Zig, and WASM adapters.
//!
//! The grammar is not vendored here. The canonical spec artifact at
//! `src/rytt/data/rytt-spec-v0.1.0.json` is the single source of truth.

pub mod chord;
pub mod codec;
pub mod spec;

pub use chord::{Chord, Plane};
pub use codec::{decode, encode, CodecError, Envelope, Metrics, TokenTrace};
pub use spec::{RyttSpec, SpecError};

/// Lower PUA compound boundary: U+E020.
pub const PUA_LOWER_BOUND: u32 = 0xE020;
/// Upper PUA compound boundary: U+E820.
pub const PUA_UPPER_BOUND: u32 = 0xE820;

/// Specification version this crate is built against.
pub const SPEC_VERSION: &str = "v0.1.0";
