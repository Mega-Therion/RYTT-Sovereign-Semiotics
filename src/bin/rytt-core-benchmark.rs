//! Emit deterministic RYTT metrics for benchmark-parity verification.

use rytt_core::{encode, RyttSpec};
use serde::{Deserialize, Serialize};
use std::io::{self, Read};

#[derive(Debug, Deserialize)]
struct CorpusInput {
    corpus: String,
    source: String,
}

#[derive(Debug, Serialize)]
struct CorpusMetrics {
    corpus: String,
    source_characters: usize,
    token_count: usize,
    token_savings_pct: f64,
    round_trip_exact: bool,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input)?;
    let corpora: Vec<CorpusInput> = serde_json::from_str(&input)?;
    let spec = RyttSpec::embedded()?;
    let mut metrics = Vec::with_capacity(corpora.len());

    for corpus in corpora {
        let envelope = encode(&spec, &corpus.source)?;
        let source_characters = corpus.source.chars().count();
        let token_count = envelope.token_trace.len();
        metrics.push(CorpusMetrics {
            corpus: corpus.corpus,
            source_characters,
            token_count,
            token_savings_pct: (1.0 - (token_count as f64 / source_characters.max(1) as f64))
                * 100.0,
            round_trip_exact: envelope.metrics.exact_recovery,
        });
    }

    println!("{}", serde_json::to_string(&metrics)?);
    Ok(())
}
