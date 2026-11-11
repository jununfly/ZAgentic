"""Carrier-agnostic loading for the read-only visual review (S1).

A view is a pure projection of roadmap *content*: whether the fact source is a
single-file JSON or a SQLite database must not change one byte of the output.
Reuse the CLI's canonical exporter instead of writing a second reader.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"
SQLITE_SUFFIXES = (".sqlite", ".sqlite3", ".db")


def load_data(path: str | Path) -> dict:
    """Return the canonical single-file layout for either carrier. Read-only."""
    target = Path(path)
    if target.suffix.lower() in SQLITE_SUFFIXES:
        if str(SCRIPTS_DIR) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_DIR))
        from carrier_migration import export_roadmap_data, load_carrier

        return export_roadmap_data(load_carrier(target))
    with open(target, encoding="utf-8") as handle:
        return json.load(handle)
