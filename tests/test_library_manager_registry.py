import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from library_manager import LibraryManager


def test_legacy_registry_fallback_loads(tmp_path, monkeypatch):
    legacy_path = tmp_path / "rsi_library_registry.json"
    legacy_path.write_text(
        json.dumps({"version": "2.0", "timestamp": 0, "primitives": {}}),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    lib = LibraryManager()
    assert lib.primitives == {}
    assert lib.registry_path == "rsi_primitive_registry.json"


def test_primary_registry_loads(tmp_path, monkeypatch):
    primary_path = tmp_path / "rsi_primitive_registry.json"
    primary_path.write_text(
        json.dumps({"version": "2.0", "timestamp": 0, "primitives": {}}),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    lib = LibraryManager()
    assert lib.primitives == {}
    assert lib.registry_path == "rsi_primitive_registry.json"
