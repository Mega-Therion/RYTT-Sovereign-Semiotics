//! PyO3 Python extension module for the RYTT engine.
//!
//! Enabled with the `python` feature flag for maturin builds:
//!   maturin develop --features python
//!
//! Provides `rytt._rytt` with `encode()` and `decode()` functions.

#[cfg(feature = "python")]
use pyo3::prelude::*;
#[cfg(feature = "python")]
use crate::{codec, RyttSpec};

#[cfg(feature = "python")]
fn spec() -> Result<RyttSpec, String> {
    RyttSpec::embedded().map_err(|e| e.to_string())
}

/// Encode text into a RYTT token envelope (JSON string).
#[cfg(feature = "python")]
#[pyfunction]
fn encode(input: &str) -> PyResult<String> {
    let spec = spec().map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e))?;
    let envelope = codec::encode(&spec, input)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    serde_json::to_string(&envelope)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

/// Decode a RYTT token envelope (JSON string) back to text.
#[cfg(feature = "python")]
#[pyfunction]
fn decode(envelope_json: &str) -> PyResult<String> {
    let spec = spec().map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e))?;
    let envelope: codec::Envelope = serde_json::from_str(envelope_json)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    codec::decode(&spec, &envelope)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

/// Get the canonical spec version.
#[cfg(feature = "python")]
#[pyfunction]
fn spec_version() -> PyResult<String> {
    let spec = spec().map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e))?;
    spec.version()
        .map(|s| s.to_owned())
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

/// Python module definition.
#[cfg(feature = "python")]
#[pymodule]
fn _rytt(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(encode, m)?)?;
    m.add_function(wrap_pyfunction!(decode, m)?)?;
    m.add_function(wrap_pyfunction!(spec_version, m)?)?;
    Ok(())
}

#[cfg(not(feature = "python"))]
#[allow(dead_code)]
fn _placeholder() {}
