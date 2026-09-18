#!/usr/bin/env python3
"""
Honest Token-Level Benchmark: RYTT Encoding Scheme vs Standard BPE Tokenization
================================================================================
Compares RYTT native tokenization and BPE (tiktoken gpt2) across 6 representative corpora.
Includes round-trip verification, native character-per-token efficiency, and
BPE out-of-vocabulary (OOV) byte-fallback penalty on RYTT PUA strings.
"""

import sys
import os
import json
import re

# Import the live compiler from the repo's src/ package
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src_dir = os.path.join(_repo_root, "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from rytt.compiler import RyttCompiler

# -----------------------------------------------------------------------------
# 1. BUNDLED CORPORA (6 Public Domain / Synthetic Representative Samples)
# -----------------------------------------------------------------------------
CORPORA = {
    "poetry_blake": """Tyger! Tyger! burning bright
In the forests of the night,
What immortal hand or eye
Could frame thy fearful symmetry?

In what distant deeps or skies
Burnt the fire of thine eyes?
On what wings dare he aspire?
What the hand dare seize the fire?""",

    "poetry_shakespeare": """Shall I compare thee to a summer's day?
Thou art more lovely and more temperate:
Rough winds do shake the darling buds of May,
And summer's lease hath all too short a date:
Sometime too hot the eye of heaven shines,
And often is his gold complexion dimm'd;
And every fair from fair sometime declines,
By chance or nature's changing course untrimm'd;""",

    "prose_gettysburg": """Four score and seven years ago our fathers brought forth on this continent, a new nation, conceived in Liberty, and dedicated to the proposition that all men are created equal. Now we are engaged in a great civil war, testing whether that nation, or any nation so conceived and so dedicated, can long endure. We are met on a great battle-field of that war.""",

    "code_python": """def calculate_fibonacci(n: int) -> list[int]:
    \"\"\"Generate Fibonacci sequence up to n terms.\"\"\"
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    
    sequence = [0, 1]
    while len(sequence) < n:
        next_val = sequence[-1] + sequence[-2]
        sequence.append(next_val)
    
    return sequence

if __name__ == "__main__":
    result = calculate_fibonacci(10)
    print(f"Fibonacci(10): {result}\")""",

    "mixed_case_ligatures": """THE THEORY AND CONSTITUTION OF STANDING NATIONS: The creation and testing of the structural foundation is generating strong opposition. Everything standing in the path of the state and the nation demands attention and processing. ST ST TH TH TION TION ING ING THE THE AND AND. The theory and the testing, standing and thinking, constitution and information.""",

    "unicode_passthrough": """Sovereign Semiotics & Unicode Passthrough Test: Café, naïve, façade, and résumé. Greek geometry: αβγδε, πr², and Σ(x_i). Chinese translation: 龍 漢字 & 自由. Extended accents: über, señor, and Crème brûlée. All non-ASCII characters pass through the RYTT compiler unchanged while surrounding English uses ligatures."""
}

# -----------------------------------------------------------------------------
# 2. TOKENIZER INITIALIZATION (Tiktoken GPT-2 with Fallback)
# -----------------------------------------------------------------------------
TOKENIZER_NAME = "gpt2"
IS_FALLBACK = False

def get_bpe_encoder():
    global TOKENIZER_NAME, IS_FALLBACK
    try:
        import tiktoken
        encoder = tiktoken.get_encoding("gpt2")
        TOKENIZER_NAME = "tiktoken (gpt2)"
        IS_FALLBACK = False
        return lambda text: encoder.encode(text)
    except Exception as e:
        TOKENIZER_NAME = f"FALLBACK_REGEX_TOKENIZER (Error: {e})"
        IS_FALLBACK = True
        # Regex word+punct tokenizer fallback
        regex_pat = re.compile(r'\w+|[^\w\s]', re.UNICODE)
        return lambda text: regex_pat.findall(text)

# -----------------------------------------------------------------------------
# 3. MAIN BENCHMARK EXECUTION
# -----------------------------------------------------------------------------
def run_benchmark():
    compiler = RyttCompiler()
    bpe_encode = get_bpe_encoder()
    
    results = []
    
    print(f"==========================================================================================================")
    print(f"HONEST TOKEN-LEVEL BENCHMARK: RYTT ENCODING SCHEME VS BPE TOKENIZATION")
    print(f"BPE Tokenizer: {TOKENIZER_NAME}")
    if IS_FALLBACK:
        print(f"WARNING: Tiktoken unavailable; using regex fallback tokenizer as marked.")
    print(f"==========================================================================================================")
    
    # Verify round-trips first
    for name, text in CORPORA.items():
        res = compiler.compile(text)
        decomp = compiler.decompile(res.encoded_pua)
        if decomp != text:
            raise ValueError(f"CRITICAL: Roundtrip failed for corpus '{name}'!")
            
    table_headers = [
        "Corpus", "Src Chars", "Src Bytes", "RYTT Toks", "RYTT Ratio", 
        "PUA Bytes", "BPE Raw", "BPE PUA", "Ch/BPE", "Ch/RYTT", "BPE Penalty"
    ]
    
    # Prepare rows
    rows_data = []
    json_results = {}
    
    for name, text in CORPORA.items():
        try:
            res = compiler.compile(text)
            encoded_pua = res.encoded_pua
            
            src_chars = len(text)
            utf8_bytes_source = len(text.encode('utf-8'))
            rytt_token_count = len(res.tokens)
            rytt_compression_ratio = res.compression_ratio
            utf8_bytes_encoded = len(encoded_pua.encode('utf-8'))
            
            bpe_tokens_source = len(bpe_encode(text))
            bpe_tokens_rytt_encoded = len(bpe_encode(encoded_pua))
            
            chars_per_bpe = src_chars / max(1, bpe_tokens_source)
            chars_per_rytt = src_chars / max(1, rytt_token_count)
            bpe_penalty_ratio = bpe_tokens_rytt_encoded / max(1, bpe_tokens_source)
            
            row_dict = {
                "corpus": name,
                "source_chars": src_chars,
                "utf8_bytes_source": utf8_bytes_source,
                "rytt_token_count": rytt_token_count,
                "rytt_compression_ratio": round(rytt_compression_ratio, 3),
                "utf8_bytes_encoded": utf8_bytes_encoded,
                "bpe_tokens_source": bpe_tokens_source,
                "bpe_tokens_rytt_encoded": bpe_tokens_rytt_encoded,
                "chars_per_bpe_token": round(chars_per_bpe, 3),
                "chars_per_rytt_token": round(chars_per_rytt, 3),
                "bpe_penalty_ratio": round(bpe_penalty_ratio, 2)
            }
            json_results[name] = row_dict
            
            rows_data.append([
                name,
                str(src_chars),
                str(utf8_bytes_source),
                str(rytt_token_count),
                f"{rytt_compression_ratio:.3f}",
                str(utf8_bytes_encoded),
                str(bpe_tokens_source),
                str(bpe_tokens_rytt_encoded),
                f"{chars_per_bpe:.3f}",
                f"{chars_per_rytt:.3f}",
                f"{bpe_penalty_ratio:.2f}x"
            ])
            
        except Exception as err:
            err_str = f"ERR: {err}"
            json_results[name] = {"error": str(err)}
            rows_data.append([name, err_str, err_str, err_str, err_str, err_str, err_str, err_str, err_str, err_str, err_str])

    # Format Fixed-Width Table
    col_widths = [len(h) for h in table_headers]
    for row in rows_data:
        for idx, cell in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(cell))
            
    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(table_headers))
    separator_line = "-+-".join("-" * col_widths[i] for i in range(len(table_headers)))
    
    print(header_line)
    print(separator_line)
    for row in rows_data:
        print(" | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row)))
    print(f"==========================================================================================================")
    
    # Save JSON output
    output_dir = os.path.join(_repo_root, "benchmarks", "results")
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, "token_benchmark.json")
    
    payload = {
        "metadata": {
            "bpe_tokenizer": TOKENIZER_NAME,
            "is_fallback": IS_FALLBACK,
            "compiler": "RyttCompiler (Sovereign Semiotics main branch)"
        },
        "corpora": json_results
    }
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        
    print(f"Benchmark results successfully written to: {json_path}")

if __name__ == "__main__":
    run_benchmark()
