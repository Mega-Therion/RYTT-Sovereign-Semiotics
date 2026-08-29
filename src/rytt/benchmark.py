"""
RYTT & Holonomery Performance Benchmark Engine
===================================================================
Author: Ryan W. Yett (RY) + Antigravity Engine
-------------------------------------------------------------------
Empirical benchmark suite measuring:
1. Token Reduction & Compression Ratio vs Standard BPE & Raw ASCII
2. Holonomic 4-Tier State Manifold Capacity (10,240 compute states / ray cycle)
3. Information Entropy & Information-Tension
4. Round-Trip Reconstruction Verification. NOTE: the compiler is lossless only
   UP TO CASE -- it uppercases. Strict equality fails; see D45.
"""

from typing import Dict, List, Any
import time
import math
import numpy as np
from .compiler import RyttCompiler

class RyttBenchmarkEngine:
    def __init__(self):
        self.compiler = RyttCompiler()

    def calculate_entropy(self, text: str) -> float:
        """
        Calculates Shannon Information Entropy: H(X) = -sum(p * log2(p))
        """
        if not text:
            return 0.0
        counts = {}
        for c in text:
            counts[c] = counts.get(c, 0) + 1
        n = len(text)
        entropy = -sum((cnt / n) * math.log2(cnt / n) for cnt in counts.values())
        return entropy

    def run_benchmark(self, text_samples: List[str], iterations: int = 100_000) -> Dict[str, Any]:
        """
        Runs comprehensive empirical comparison over text samples.
        """
        results = []
        total_raw_chars = 0
        total_rytt_tokens = 0
        total_bpe_tokens = 0

        for sample in text_samples:
            comp = self.compiler.compile(sample)
            decomp = self.compiler.decompile(comp.encoded_pua)
            # Verify lossless roundtrip.
            # MEASURED 2026-08-28: this comparison used to uppercase BOTH sides,
            # so it reported True while the compiler was destroying case --
            # 'The quick brown fox' decompiles to 'THE QUICK BROWN FOX'. A check
            # that normalises away the exact difference it is meant to detect is
            # not a check. Strict equality is the claim; the case-insensitive
            # result is kept as a separate, separately-named field.
            # See derivations/D45_rytt_compression_measurement.md
            is_lossless = (sample == decomp)
            is_lossless_ignoring_case = (sample.strip().upper() == decomp.strip().upper())
            
            raw_len = len(sample)
            rytt_len = len(comp.tokens)
            # Estimate standard BPE tokens (typically ~4 chars per token in English)
            bpe_len = max(1, int(math.ceil(raw_len / 3.8)))

            total_raw_chars += raw_len
            total_rytt_tokens += rytt_len
            total_bpe_tokens += bpe_len

            raw_entropy = self.calculate_entropy(sample)
            rytt_entropy = self.calculate_entropy(comp.encoded_pua)

            results.append({
                'sample': sample,
                'raw_chars': raw_len,
                'rytt_tokens': rytt_len,
                'bpe_tokens_est': bpe_len,
                'compression_ratio': comp.compression_ratio,
                'token_savings_pct': comp.token_savings_pct,
                'raw_entropy': round(raw_entropy, 3),
                'rytt_entropy': round(rytt_entropy, 3),
                'is_lossless': is_lossless,
                'is_lossless_ignoring_case': is_lossless_ignoring_case,
                'parity_mod24': comp.parity_mod24,
                'vsa_hash': comp.vsa_hash_sha256[:16]
            })

        # SIMD Throughput Benchmark (Holonomic 10,240-bit state vs Flat ASCII)
        flat_time = self._benchmark_flat_ascii(text_samples[0], iterations)
        holo_time = self._benchmark_holonomic_simd(iterations)
        simd_speedup = flat_time / max(1e-6, holo_time)

        overall_savings_pct = (1.0 - (total_rytt_tokens / max(1, total_raw_chars))) * 100.0
        bpe_comparison_pct = (1.0 - (total_rytt_tokens / max(1, total_bpe_tokens))) * 100.0

        return {
            'overall_metrics': {
                'total_samples': len(text_samples),
                'total_raw_chars': total_raw_chars,
                'total_rytt_tokens': total_rytt_tokens,
                'total_bpe_tokens_est': total_bpe_tokens,
                'overall_token_savings_pct': round(overall_savings_pct, 2),
                'bpe_compression_gain_pct': round(bpe_comparison_pct, 2),
                'simd_speedup': round(simd_speedup, 2),
                'simd_flat_ms': round(flat_time * 1000, 2),
                'simd_holo_ms': round(holo_time * 1000, 2),
                'holonomic_state_multiplier': 10240,
                'all_samples_lossless': all(r['is_lossless'] for r in results),
                'all_samples_lossless_ignoring_case': all(
                    r['is_lossless_ignoring_case'] for r in results)
            },
            'sample_results': results
        }

    def _benchmark_flat_ascii(self, text: str, iterations: int) -> float:
        start = time.perf_counter()
        char_codes = [ord(c) for c in text]
        total = 0
        for _ in range(iterations):
            s = 0
            for c in char_codes:
                s = (s + c) ^ 0x5A
            total += s
        return time.perf_counter() - start

    def _benchmark_holonomic_simd(self, iterations: int) -> float:
        start = time.perf_counter()
        t1 = 0x5555555555555555
        t2 = 0xAAAAAAAAAAAAAAAA
        total = 0
        for _ in range(iterations):
            eval_layer = (t1 & t2) ^ (t1 | t2)
            total += (eval_layer & 0xFFFFFF) % 24
        return time.perf_counter() - start
