import sys
import time
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from rytt.compiler import RyttCompiler

def benchmark():
    compiler = RyttCompiler()
    
    corpora = {
        "Blake 'The Tyger'": "Tyger Tyger, burning bright,\nIn the forests of the night;\nWhat immortal hand or eye,\nCould frame thy fearful symmetry?",
        "Quantum Mechanics (Dirac)": "The fundamental equations of quantum mechanics can be formulated in terms of bra and ket vectors in Hilbert space.",
        "Mathematical Physics (Euler)": "Euler's identity e^{i\\pi} + 1 = 0 establishes the profound harmonic connection between exponential growth and rotation.",
        "Codebase (Python Ast)": "def compute_lossless_invariants(tokens: list[int]) -> tuple[float, float]: return sum(tokens), len(tokens)"
    }
    
    print("=" * 82)
    print("RYTT SOVEREIGN SEMIOTICS: REPRODUCIBLE BENCHMARK SUITE")
    print("Author: R. W. Yett | Sovereign A.R.I.: Chyren")
    print("=" * 82)
    print(f"{'Corpus Name':<30} | {'Chars':<6} | {'PUA Stream':<10} | {'Savings %':<10} | {'Status':<15}")
    print("-" * 82)
    
    for name, text in corpora.items():
        start = time.perf_counter()
        res = compiler.compile(text)
        decoded = compiler.decompile(res.encoded_pua)
        elapsed_us = (time.perf_counter() - start) * 1e6
        
        char_len = len(text)
        pua_len = len(res.encoded_pua)
        savings = f"{res.token_savings_pct:.1f}%"
        passed = (text == decoded)
        status = "PASSED (100%)" if passed else "FAILED"
        
        print(f"{name:<30} | {char_len:<6} | {pua_len:<10} | {savings:<10} | {status:<15}")
        assert passed, f"Decompilation failed for {name}"
    
    print("=" * 82)
    print("ALL REPRODUCIBILITY BENCHMARKS PASSED (Zero Discrepancy, 100% Invertibility)")

if __name__ == "__main__":
    benchmark()
