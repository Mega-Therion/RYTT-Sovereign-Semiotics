import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rytt import RyttCompiler


def test_canonical_spec_and_vectors_are_current():
    subprocess.run([sys.executable, "scripts/generate_canonical_spec.py", "--check"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "scripts/generate_conformance_vectors.py", "--check"], cwd=ROOT, check=True)


def test_reference_compiler_replays_shared_vectors():
    payload = json.loads((ROOT / "conformance" / "vectors.json").read_text())
    compiler = RyttCompiler()
    for vector in payload["vectors"]:
        result = compiler.compile(vector["source"])
        assert result.encoded_pua == vector["encoded_display"]
        assert compiler.decompile(result.encoded_pua) == vector["source"]
        assert len(result.tokens) == vector["token_count"]
