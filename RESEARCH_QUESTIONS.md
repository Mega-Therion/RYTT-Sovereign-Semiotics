# RYTT Research Agenda

RYTT is strongest when its claims are specific, reproducible, and falsifiable. Contributions should include the corpus, command, version, raw output, and negative cases.

| Question | Contribution type | Evidence of progress |
|---|---|---|
| Which domains benefit from chord vocabulary? | Corpus analysis | Named corpora, per-domain metrics, and counterexamples |
| How does RYTT behave across scripts and normalization forms? | Unicode study | Exact-recovery matrix and explicit passthrough policy |
| Does geometry improve human recall or editing? | User study | Pre-registered task, participants, and error analysis |
| Can the core be independently implemented? | Portability | Conforming Rust, Zig, JavaScript, or WASM implementation |
| Can the token algebra be fully verified? | Formal methods | Proof report tied to the canonical vocabulary hash |
| What should the native interchange format guarantee? | Protocol design | Versioning, corruption, and compatibility experiments |
| Does explainable token tracing improve learning? | Education study | Controlled comparison with standard tokenizer visualization |
| Where does RYTT lose? | Falsification | Public negative results and boundary conditions |

## Contribution protocol

Open a focused issue or pull request containing the research question, the exact RYTT specification version, the vocabulary hash, the corpus license, the command used, and raw machine-readable output. Do not report a single aggregate score when the underlying units are characters, bytes, and model tokens.
