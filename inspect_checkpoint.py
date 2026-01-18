"""Utility to inspect a single RSI checkpoint file."""
from __future__ import annotations

import argparse
import pickle
from pathlib import Path
from typing import Any, Dict


def load_checkpoint(path: Path) -> Dict[str, Any]:
    with path.open("rb") as handle:
        payload = pickle.load(handle)
    if not isinstance(payload, dict):
        return {"raw": payload}
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect a checkpoint pickle")
    parser.add_argument("path", type=Path, help="Path to checkpoint .pkl file")
    args = parser.parse_args()

    if not args.path.exists():
        print(f"Checkpoint not found: {args.path}")
        return 1

    payload = load_checkpoint(args.path)
    print(f"Checkpoint: {args.path}")
    for key in sorted(payload.keys()):
        value = payload[key]
        preview = value
        if isinstance(value, (str, bytes)) and len(value) > 200:
            preview = f"{value[:200]}..."
        print(f"- {key}: {preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
