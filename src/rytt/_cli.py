"""rytt CLI — encode, decode, inspect."""
import argparse
import json
import sys
from .compiler import RyttCompiler

_compiler = RyttCompiler()


def _cmd_encode(args):
    text = args.text if args.text else sys.stdin.read()
    result = _compiler.compile(text)
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(result.encoded_pua)


def _cmd_decode(args):
    pua = args.pua if args.pua else sys.stdin.read().rstrip("\n")
    print(_compiler.decompile(pua))


def _cmd_inspect(args):
    text = args.text if args.text else sys.stdin.read()
    result = _compiler.compile(text)
    info = {
        "source_chars": len(result.source_text),
        "token_count": len(result.tokens),
        "utf8_bytes_source": len(result.source_text.encode()),
        "utf8_bytes_encoded": len(result.encoded_pua.encode()),
        "parity_mod24": result.parity_mod24,
        "compression_ratio": round(result.compression_ratio, 4),
        "token_savings_pct": round(result.token_savings_pct, 2),
        "chord_count": sum(1 for t in result.tokens if t.is_chord),
        "decoded_text": _compiler.decompile(result.encoded_pua),
        "round_trip_exact": _compiler.decompile(result.encoded_pua) == result.source_text,
        "vsa_hash_sha256": result.vsa_hash_sha256,
    }
    print(json.dumps(info, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(
        prog="rytt",
        description="RYTT Sovereign Semiotics CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    enc = sub.add_parser("encode", help="Encode plain text to RYTT PUA stream")
    enc.add_argument("text", nargs="?", help="Text to encode (default: stdin)")
    enc.add_argument("--json", action="store_true", help="Full JSON compilation result")
    enc.set_defaults(func=_cmd_encode)

    dec = sub.add_parser("decode", help="Decode RYTT PUA stream back to plain text")
    dec.add_argument("pua", nargs="?", help="PUA stream to decode (default: stdin)")
    dec.set_defaults(func=_cmd_decode)

    ins = sub.add_parser("inspect", help="Inspect compilation metrics for text")
    ins.add_argument("text", nargs="?", help="Text to inspect (default: stdin)")
    ins.set_defaults(func=_cmd_inspect)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
