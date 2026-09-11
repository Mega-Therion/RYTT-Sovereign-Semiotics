# Benchmark Arena

Run `python benchmarks/arena.py` to produce `benchmarks/results/arena.json` and `benchmarks/results/arena.html`. Run `python benchmarks/run_benchmarks.py` for the legacy seven-corpus round-trip suite.

The arena intentionally reports characters, UTF-8 bytes, RYTT tokens, RYTT display bytes, runtime, and optional `cl100k_base` tokens as separate metrics. It never presents a combined compression score because those units represent different systems and costs. The `cl100k_base` adapter is optional; when `tiktoken` is unavailable, the report records `null` rather than silently substituting another tokenizer.

Every row must preserve exact round-trip status. A benchmark that produces a lower RYTT ratio but fails exact recovery is a failure, not an optimization.
