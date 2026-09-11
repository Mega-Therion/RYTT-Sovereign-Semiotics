import argparse
import json
import sys
from .compiler import RyttCompiler
from .interchange import export_bundle, verify_bundle

_compiler = RyttCompiler()


def _read_text(value):
    return value if value is not None else sys.stdin.read()


def _cmd_encode(args):
    text = _read_text(args.text)
    result = _compiler.compile(text)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2) if args.json else result.encoded_pua)


def _cmd_decode(args):
    print(_compiler.decompile(_read_text(args.pua).rstrip("\n")))


def _cmd_inspect(args):
    text = _read_text(args.text)
    result = _compiler.compile(text)
    info = result.to_dict()
    info.update({
        "chord_count": sum(1 for t in result.tokens if t.is_chord),
        "decoded_text": _compiler.decompile(result.encoded_pua),
        "round_trip_exact": _compiler.decompile(result.encoded_pua) == result.source_text,
    })
    print(json.dumps(info, ensure_ascii=False, indent=2))


def _cmd_artifact_export(args):
    path = export_bundle(_read_text(args.text), args.output, _compiler)
    print(path)


def _cmd_artifact_verify(args):
    result = verify_bundle(args.bundle)
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


def main():
    parser = argparse.ArgumentParser(prog="rytt", description="RYTT Sovereign Semiotics CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    enc = sub.add_parser("encode", help="Encode plain text to RYTT PUA stream")
    enc.add_argument("text", nargs="?", help="Text to encode (default: stdin)")
    enc.add_argument("--json", action="store_true", help="Full JSON compilation result")
    enc.set_defaults(func=_cmd_encode)

    dec = sub.add_parser("decode", help="Decode RYTT PUA stream back to plain text")
    dec.add_argument("pua", nargs="?", help="PUA stream to decode (default: stdin)")
    dec.set_defaults(func=_cmd_decode)

    ins = sub.add_parser("inspect", help="Inspect compilation metrics for text")
    ins.add_argument("text", nargs="?", help="Text to inspect (default: stdin")
    ins.set_defaults(func=_cmd_inspect)

    export = sub.add_parser("artifact-export", help="Export a verified offline artifact bundle")
    export.add_argument("output", help="Output ZIP path")
    export.add_argument("text", nargs="?", help="Source text (default: stdin)")
    export.set_defaults(func=_cmd_artifact_export)

    verify = sub.add_parser("artifact-verify", help="Verify an offline artifact bundle")
    verify.add_argument("bundle", help="Artifact ZIP path")
    verify.set_defaults(func=_cmd_artifact_verify)

    args = parser.parse_args()
    return args.func(args) or 0


if __name__ == "__main__":
    raise SystemExit(main())
