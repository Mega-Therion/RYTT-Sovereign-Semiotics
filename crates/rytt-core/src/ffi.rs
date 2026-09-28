//! C ABI for foreign-runtime integration (cbindgen-compatible).
//!
//! Provides explicit `rytt_encode` / `rytt_decode` / `rytt_free_envelope`
//! functions with balanced allocators so C, C++, and FFI consumers can
//! use the RYTT engine without Rust toolchains.
//!
//! Generate headers with:
//!   cbindgen --crate rytt-core --output rytt_core.h

use std::ffi::CStr;
use std::os::raw::{c_char, c_int};

use crate::codec::{self, CodecError, Envelope};
use crate::RyttSpec;

/// Opaque envelope returned by `rytt_encode`. Caller must free with
/// `rytt_free_envelope`.
#[repr(C)]
pub struct RyttTokenEnvelope {
    /// JSON-encoded envelope string (null-terminated).
    pub data: *mut c_char,
    /// Length in bytes (excluding null terminator).
    pub length: usize,
}

impl RyttTokenEnvelope {
    fn empty() -> Self {
        Self {
            data: std::ptr::null_mut(),
            length: 0,
        }
    }
}

fn spec() -> Result<RyttSpec, String> {
    RyttSpec::embedded().map_err(|e| e.to_string())
}

/// Encode a UTF-8 string into a RYTT token envelope (JSON).
///
/// Returns 0 on success, negative on error:
///   -1: null pointer
///   -2: invalid UTF-8
///   -3: encoding failure
#[no_mangle]
pub unsafe extern "C" fn rytt_encode(
    input: *const c_char,
    out_envelope: *mut RyttTokenEnvelope,
) -> c_int {
    if input.is_null() || out_envelope.is_null() {
        return -1;
    }
    let c_str = match CStr::from_ptr(input).to_str() {
        Ok(s) => s,
        Err(_) => return -2,
    };
    let spec = match spec() {
        Ok(s) => s,
        Err(_) => return -3,
    };
    match codec::encode(&spec, c_str) {
        Ok(envelope) => {
            let json = match serde_json::to_string(&envelope) {
                Ok(j) => j,
                Err(_) => return -3,
            };
            let c_string = std::ffi::CString::new(json).unwrap_or_default();
            (*out_envelope).length = c_string.as_bytes().len();
            (*out_envelope).data = c_string.into_raw();
            0
        }
        Err(_) => -3,
    }
}

/// Decode a RYTT token envelope (JSON) back to a UTF-8 string.
///
/// Returns 0 on success, negative on error.
#[no_mangle]
pub unsafe extern "C" fn rytt_decode(
    envelope_json: *const c_char,
    out_text: *mut *mut c_char,
) -> c_int {
    if envelope_json.is_null() || out_text.is_null() {
        return -1;
    }
    let c_str = match CStr::from_ptr(envelope_json).to_str() {
        Ok(s) => s,
        Err(_) => return -2,
    };
    let envelope: Envelope = match serde_json::from_str(c_str) {
        Ok(e) => e,
        Err(_) => return -3,
    };
    let spec = match spec() {
        Ok(s) => s,
        Err(_) => return -3,
    };
    match codec::decode(&spec, &envelope) {
        Ok(text) => {
            let c_string = std::ffi::CString::new(text).unwrap_or_default();
            *out_text = c_string.into_raw();
            0
        }
        Err(_) => -3,
    }
}

/// Free a string returned by `rytt_decode`.
#[no_mangle]
pub unsafe extern "C" fn rytt_free_string(s: *mut c_char) {
    if !s.is_null() {
        let _ = std::ffi::CString::from_raw(s);
    }
}

/// Free an envelope returned by `rytt_encode`.
#[no_mangle]
pub unsafe extern "C" fn rytt_free_envelope(envelope: *mut RyttTokenEnvelope) {
    if !envelope.is_null() && !(*envelope).data.is_null() {
        let _ = std::ffi::CString::from_raw((*envelope).data);
        (*envelope).data = std::ptr::null_mut();
        (*envelope).length = 0;
    }
}
