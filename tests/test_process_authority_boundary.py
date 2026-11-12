#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""INV::06 — process-state authority boundary, end to end.

A view/roadmap is process state: it may drive work but must not be cited by
durable docs as proof of product correctness. This guard uses only the
published `roadmap_cli.py authority-check` entrypoint, so internal refactors
cannot silently break it.

Symmetric probes matter: a checker that always rejects, or one that hardcodes
a rejection without scanning, would otherwise look green.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLI = REPO / "skills" / "codebase-docs" / "zj-roadmap-driven" / "scripts" / "roadmap_cli.py"
PLAN_REL = "docs/plans/release/ROADMAP.md"
DURABLE_REL = "docs/architecture/system.md"
DURABLE_TEXT = (
    "Release support is complete; see [roadmap proof](../plans/release/ROADMAP.md).\n"
)


def _project(root: Path, *, with_leak: bool) -> None:
    plan = root / PLAN_REL
    plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text("## ZJ Roadmap\n", encoding="utf-8")
    durable = root / DURABLE_REL
    durable.parent.mkdir(parents=True, exist_ok=True)
    durable.write_text(
        DURABLE_TEXT if with_leak else "Release support is complete; see the ADR.\n",
        encoding="utf-8",
    )


def _authority_check(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "authority-check", str(root), *extra],
        cwd=root, text=True, capture_output=True, check=False,
    )


class ProcessAuthorityBoundaryContract(unittest.TestCase):
    def test_durable_doc_citing_process_state_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _project(root, with_leak=True)
            result = _authority_check(root)
            self.assertEqual(1, result.returncode,
                             f"leak was not rejected: {result.stdout}{result.stderr}")
            self.assertIn("E_PROCESS_AUTHORITY_LEAK", result.stderr)
            self.assertIn(DURABLE_REL, result.stderr)

    def test_clean_project_is_accepted(self):
        """A checker that always rejects is as useless as one that never does."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _project(root, with_leak=False)
            result = _authority_check(root)
            self.assertEqual(0, result.returncode,
                             f"clean project was rejected: {result.stderr}")
            self.assertIn("Authority boundary: clean.", result.stdout)

    def test_explicit_exclusion_is_honoured(self):
        """Prove the scanner really walks files instead of short-circuiting."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _project(root, with_leak=True)
            result = _authority_check(root, "--exclude", DURABLE_REL)
            self.assertEqual(0, result.returncode,
                             f"excluded doc still rejected: {result.stderr}")


if __name__ == "__main__":
    unittest.main()
