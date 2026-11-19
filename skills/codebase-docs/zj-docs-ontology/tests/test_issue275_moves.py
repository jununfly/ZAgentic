#!/usr/bin/env python3
"""Issue #275 defect B: a compliant rename must be mechanically distinguishable
from an undeclared deletion.

Three-level ruling (revising legacy Ruling v7 "proposal-named moves only"):
  1. confirmed `moves` entry in the proposal  → fully exempt;
  2. git-native rename evidence (porcelain -z / diff -M), not yet confirmed
     → `RENAME_AWAITING_CONFIRMATION` (signal, never an ERROR): Human confirms
     in the proposal, and no tombstone stub is needed;
  3. no rename evidence at all → `UNDECLARED_RETIREMENT` (ERROR, unchanged).

Git evidence boundary: an unstaged filesystem `mv` is indistinguishable from
a deletion (the new path is untracked), so it stays fail-closed until the
rename is staged — git's own declaration is the only accepted evidence.

Fixtures are real temporary git repositories in the gitignored output zone;
every assertion goes through the public `report()` / CLI seam.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parents[2]
TMP = REPO_ROOT / "tmp" / "skills-outputs" / "zj-docs-ontology" / "_issue275_moves"
SCRIPT = SKILL_ROOT / "scripts" / "docs_governance.py"
SPEC = importlib.util.spec_from_file_location("docs_governance_moves", SCRIPT)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)

GIT_ENV = {k: v for k, v in os.environ.items() if k != "NODE_OPTIONS"}
PAGE = "docs/prds/payment.md"
MOVED = "docs/prds/renamed.md"


def git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=repo, env=GIT_ENV,
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {proc.stderr}")
    return proc.stdout.strip()


def make_repo(name: str) -> Path:
    base = TMP / name
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    git(base, "init", "-q")
    (base / "AGENTS.md").write_text("docs-map: docs/team-map.md\n", encoding="utf-8")
    (base / "docs" / "prds").mkdir(parents=True)
    (base / "docs" / "team-map.md").write_text(
        "# Team map\n\n- [Payment](prds/payment.md)\n", encoding="utf-8"
    )
    (base / PAGE).write_text(
        "---\ndoc-kind: prd\nauthority: primary\nauthority-id: payment\n---\n"
        "# Payment\n",
        encoding="utf-8",
    )
    git(base, "add", "-A")
    git(base, "-c", "user.email=t@e.st", "-c", "user.name=T", "commit", "-qm", "init")
    return base


def codes(payload: dict) -> set[str]:
    return {item["code"] for item in payload["diagnostics"]}


def report(repo: Path, **kwargs: object) -> dict:
    return TOOL.report(repo, validate_links=True, **kwargs)


class MovesRulingTest(unittest.TestCase):
    def tearDown(self) -> None:
        if TMP.exists():
            shutil.rmtree(TMP)

    def test_git_mv_without_declaration_is_a_signal_not_an_error(self) -> None:
        """Level 2: git-native rename evidence, Human has not confirmed yet."""
        repo = make_repo("mv-unconfirmed")
        git(repo, "mv", PAGE, MOVED)
        payload = report(repo)
        self.assertIn("RENAME_AWAITING_CONFIRMATION", codes(payload))
        self.assertNotIn("UNDECLARED_RETIREMENT", codes(payload))

    def test_signal_is_not_a_gate_and_pending_moves_are_visible(self) -> None:
        repo = make_repo("mv-signal")
        git(repo, "mv", PAGE, MOVED)
        payload = report(repo)
        self.assertIn("RENAME_AWAITING_CONFIRMATION", TOOL.SIGNAL_CODES)
        self.assertNotIn("RENAME_AWAITING_CONFIRMATION", TOOL.ERROR_CODES)
        pending = payload["pending_moves"]
        self.assertEqual(
            [{"from": PAGE, "to": MOVED}],
            [{k: item[k] for k in ("from", "to")} for item in pending],
        )

    def test_confirmed_move_is_fully_exempt(self) -> None:
        """Level 1: the proposal's moves entry is Human's confirmation."""
        repo = make_repo("mv-confirmed")
        git(repo, "mv", PAGE, MOVED)
        proposal = {"moves": [{"from": PAGE, "to": MOVED}]}
        payload = report(repo, proposal=proposal)
        self.assertNotIn("UNDECLARED_RETIREMENT", codes(payload))
        self.assertNotIn("RENAME_AWAITING_CONFIRMATION", codes(payload))
        self.assertEqual([], payload["pending_moves"])

    def test_plain_deletion_without_rename_evidence_still_errors(self) -> None:
        """Level 3: no rename evidence at all — the ERROR must not regress."""
        repo = make_repo("mv-plain-delete")
        (repo / PAGE).unlink()
        payload = report(repo)
        self.assertIn("UNDECLARED_RETIREMENT", codes(payload))
        self.assertNotIn("RENAME_AWAITING_CONFIRMATION", codes(payload))

    def test_undeclared_git_mv_exits_zero_via_cli(self) -> None:
        """The signal must not flip the exit code: consumer decides escalation.
        A compliant rename pass also updates the map link, so the fixture does
        both — the rename signal is then the only non-shape diagnostic."""
        repo = make_repo("mv-cli-exit")
        git(repo, "mv", PAGE, MOVED)
        (repo / "docs" / "team-map.md").write_text(
            "# Team map\n\n- [Payment](prds/renamed.md)\n", encoding="utf-8"
        )
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), str(repo), "--validate"],
            capture_output=True, text=True,
        )
        self.assertEqual(0, proc.returncode, proc.stdout)
        payload = json.loads(proc.stdout)
        self.assertIn("RENAME_AWAITING_CONFIRMATION", codes(payload))

    def test_unstaged_mv_is_fail_closed_until_staged(self) -> None:
        """A plain filesystem `mv` (unstaged) is indistinguishable from a
        deletion to git — the new path is untracked, so neither porcelain nor
        diff -M can pair it. Fail-closed: ERROR until the rename is staged;
        once `git add -A` records it, git's own rename evidence appears and
        the same state downgrades to the signal."""
        repo = make_repo("mv-unstaged")
        (repo / PAGE).rename(repo / MOVED)
        payload = report(repo)
        self.assertIn("UNDECLARED_RETIREMENT", codes(payload))
        self.assertNotIn("RENAME_AWAITING_CONFIRMATION", codes(payload))
        git(repo, "add", "-A")
        payload = report(repo)
        self.assertIn("RENAME_AWAITING_CONFIRMATION", codes(payload))
        self.assertNotIn("UNDECLARED_RETIREMENT", codes(payload))


if __name__ == "__main__":
    unittest.main()
