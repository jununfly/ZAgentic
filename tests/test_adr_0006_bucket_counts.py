#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ADR 0006 records dated bucket counts, not live counts (review finding #6).

The ADR's `research (5)` was true on 2026-10-23; the live tree has 6. The fix
is *not* to rewrite history: keep the number, mark it as a snapshot, and add
an Amendment that names the authoritative live source and its current value.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ADR = REPO / "docs" / "zj-adr" / "0006-ui-public-bucket-addition.md"
OVERVIEW = REPO / "docs" / "architecture" / "ta-zagentic-overview.md"
RESEARCH = REPO / "skills" / "research"
WORKFLOW = REPO / ".github" / "workflows" / "skill-closure-lint.yml"
AMENDMENT = "## Amendment (2026-11-12)"


def _live_research_count() -> int:
    """Two independent sources: the live directory and the overview table."""
    dirs = [p for p in RESEARCH.iterdir() if p.is_dir() and not p.name.startswith(".")]
    table = re.search(r"\|\s*`research/`\s*\|\s*(\d+)\s*\|",
                      OVERVIEW.read_text(encoding="utf-8"))
    if table is None:
        raise AssertionError("overview bucket table has no research row")
    return len(dirs), int(table.group(1))


def _adr_errors(text: str, live_count: int) -> list[str]:
    errors: list[str] = []
    if AMENDMENT not in text:
        errors.append("E_NO_AMENDMENT")
    amendment = text.split(AMENDMENT, 1)[1] if AMENDMENT in text else ""
    if "历史快照" not in amendment:
        errors.append("E_NO_SNAPSHOT_NOTE")
    # Match only the explicit live-count statement. The Amendment also quotes
    # the historical `research` (5); matching any (N) there would let a stale
    # live count pass (a negative probe caught exactly that false green).
    if f"活树为 `research` ({live_count})" not in amendment:
        errors.append("E_WRONG_LIVE_COUNT")
    if "historical snapshot" not in text.lower():
        errors.append("E_CONSEQUENCES_NOT_MARKED")
    if "as of 2026-10-23" not in text:
        errors.append("E_DATE_REMOVED")
    return errors


class DatedSnapshotContract(unittest.TestCase):
    def test_live_count_is_derived_from_two_independent_sources(self):
        tree_count, table_count = _live_research_count()
        self.assertEqual(table_count, tree_count,
                         "architecture overview bucket count drifted from the tree")

    def test_the_published_adr_has_no_errors(self):
        tree_count, table_count = _live_research_count()
        self.assertEqual(table_count, tree_count)
        self.assertEqual([], _adr_errors(ADR.read_text(encoding="utf-8"), tree_count))

    def test_a_missing_amendment_is_detected(self):
        broken = ADR.read_text(encoding="utf-8").split(AMENDMENT, 1)[0]
        self.assertIn("E_NO_AMENDMENT", _adr_errors(broken, 6))

    def test_a_stale_live_count_is_detected(self):
        text = ADR.read_text(encoding="utf-8")
        self.assertIn("E_WRONG_LIVE_COUNT", _adr_errors(text, 5))

    def test_removing_the_snapshot_marker_from_consequences_is_detected(self):
        broken = ADR.read_text(encoding="utf-8").replace("historical snapshot", "")
        self.assertIn("E_CONSEQUENCES_NOT_MARKED", _adr_errors(broken, 6))

    def test_required_ci_job_runs_this_guard(self):
        self.assertIn("tests.test_adr_0006_bucket_counts",
                      WORKFLOW.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
