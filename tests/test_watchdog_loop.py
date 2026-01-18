import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from rsi_watchdog_loop import (
    MAX_ROUNDS,
    TRIALS_PER_ROUND,
    normalize_caps,
    run_watchdog_snippet,
    snapshot_artifacts,
)


def test_loop_respects_caps():
    rounds, trials = normalize_caps(MAX_ROUNDS + 5, TRIALS_PER_ROUND + 10)
    assert rounds == MAX_ROUNDS
    assert trials == TRIALS_PER_ROUND


def test_watchdog_timeout_enforced():
    code = """
while True:
    pass
"""
    result = run_watchdog_snippet(code, timeout=0.5)
    assert result.get("killed") is True


def test_persistence_roundtrip(tmp_path, monkeypatch):
    meta = tmp_path / "rsi_meta_weights.json"
    registry = tmp_path / "rsi_primitive_registry.json"
    meta.write_text(json.dumps({"a": 1}), encoding="utf-8")
    registry.write_text(json.dumps({"primitives": {}}), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    output_dir = tmp_path / "snapshot"
    snapshot_artifacts(output_dir)

    assert (output_dir / "rsi_meta_weights.json").exists()
    assert (output_dir / "rsi_primitive_registry.json").exists()
