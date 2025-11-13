#!/usr/bin/env python3
"""Verify that model names declared in code appear in README and AGENTS.md.

This simple check reduces doc/code drift by failing CI when the model
strings documented in README/AGENTS.md do not match the values in
`app/llm.py`.

Usage: python scripts/verify_models.py
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
AGENTS = ROOT / "AGENTS.md"

try:
    from app import llm
except Exception as e:  # pragma: no cover - defensive in CI
    print(f"Failed to import app.llm: {e}")
    sys.exit(2)


def _check(text_path: Path, needle: str) -> bool:
    if not text_path.exists():
        print(f"Missing file: {text_path}")
        return False
    content = text_path.read_text(encoding="utf-8")
    return needle in content


def main() -> int:
    drafting = getattr(llm, "_DRAFTING_MODEL", None)
    summariser = getattr(llm, "_SUMMARISER_MODEL", None)
    if not drafting or not summariser:
        print("Model names not found in app.llm; check the module.")
        return 2

    errors = 0
    for path in (README, AGENTS):
        if not _check(path, drafting):
            print(f"ERROR: drafting model '{drafting}' not found in {path.name}")
            errors += 1
        if not _check(path, summariser):
            print(f"ERROR: summariser model '{summariser}' not found in {path.name}")
            errors += 1

    if errors:
        print("Model verification failed — please update docs or app/llm.py to match.")
        return 1

    print("Model verification passed: documented model names match app.llm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
