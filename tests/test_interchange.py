import json
from pathlib import Path

from rytt import build_envelope, export_bundle, verify_bundle, verify_envelope


def test_envelope_contains_version_and_exact_recovery():
    envelope = build_envelope("RYTT — naïve 東京")
    assert envelope["format"] == "rytt"
    assert envelope["format_version"] == "0.1"
    assert envelope["verification"]["round_trip_exact"] is True
    assert verify_envelope(envelope)["valid"] is True


def test_artifact_bundle_is_offline_replayable(tmp_path: Path):
    bundle = export_bundle("A verified RYTT artifact.", tmp_path / "artifact.zip")
    assert bundle.exists()
    assert verify_bundle(bundle)["valid"] is True


def test_tampered_artifact_fails(tmp_path: Path):
    bundle = export_bundle("original", tmp_path / "artifact.zip")
    import zipfile
    with zipfile.ZipFile(bundle) as archive:
        envelope = json.loads(archive.read("artifact.json"))
    envelope["source_text"] = "tampered"
    assert verify_envelope(envelope)["valid"] is False
