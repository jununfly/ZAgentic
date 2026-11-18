#!/usr/bin/env python3
"""Issue #264 acceptance fixture: skip Step 5 AND undeclared deletion in one pass.

The two mechanisms have separate regression tests (test_checklist pins
EXEC_STEP5_ARTIFACT_MISSING; test_ruling1_preset pins UNDECLARED_RETIREMENT).
This test pins the issue's literal acceptance criterion: a single pass that
does BOTH must exit non-zero and name both missing items. It is falsifiable —
each control case drops one condition and asserts that gate goes quiet — so a
future refactor that made the checks mutually exclusive (or constant) fails
here while every individual test stays green.

Fixtures are real temporary git repositories in the gitignored output zone, so
HEAD is a mechanical fact. Assertions go through the public report()/has_error()
and CLI seams.
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
TMP = REPO_ROOT / "tmp" / "skills-outputs" / "zj-docs-ontology" / "_issue264_combined_cases"
SCRIPT = SKILL_ROOT / "scripts" / "docs_governance.py"
GIT_ENV = {k: v for k, v in os.environ.items() if k != "NODE_OPTIONS"}
SPEC = importlib.util.spec_from_file_location("docs_governance_issue264", SCRIPT)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)

TOPIC = "issue-264-combined"
PAGE = "docs/prds/payment.md"


def git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=repo, env=GIT_ENV, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {proc.stderr}")
    return proc.stdout.strip()


def canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def make_pass(name: str, *, delete_page: bool = True, skip_step5: bool = True) -> tuple[Path, Path]:
    """Build a pass whose HEAD contains PAGE and whose checklist may skip Step 5.

    Returns (repo_root, out_dir). The repo is committed so HEAD roster is real;
    out_dir holds proposal.json + a tool-shaped checklist under TOPIC.
    """
    base = TMP / name
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    repo = base / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "AGENTS.md").write_text("docs-map: docs/team-map.md\n", encoding="utf-8")
    (repo / "docs" / "prds").mkdir(parents=True)
    (repo / "docs" / "team-map.md").write_text(
        "# Team map\n\n- [Payment](prds/payment.md)\n", encoding="utf-8"
    )
    (repo / PAGE).write_text(
        "---\ndoc-kind: prd\nauthority: primary\nauthority-id: payment\n---\n"
        "# Payment\n",
        encoding="utf-8",
    )
    git(repo, "add", "-A")
    git(repo, "-c", "user.email=t@e.st", "-c", "user.name=T", "commit", "-qm", "init")
    if delete_page:
        (repo / PAGE).unlink()  # vanished without a retirement declaration

    case_dir = base / "out" / TOPIC
    case_dir.mkdir(parents=True)
    proposal = {
        "repository": str(repo.resolve()),
        "mode": "read-only-proposal",
        "map": "docs/team-map.md",
        "map_origin": "explicit-pointer",
        "diagnostics": [],
        "proposed_actions": [{"action": "create-map", "target": "docs/README.md"}],
        "mutations": [{"action": "create-map", "target": "docs/README.md"}],
        "read_paths": ["AGENTS.md", "docs/team-map.md"],
    }
    cid = TOOL.confirmation_id(proposal)
    artifact = str(case_dir / "step-1.txt")
    (case_dir / "step-1.txt").write_text("step 1 evidence\n", encoding="utf-8")
    checklist = {
        "topic": TOPIC,
        "confirmation_id": cid,
        "steps": [
            {"step": 1, "status": "done", "artifact": artifact, "confirmation_id": cid},
            {"step": 2, "status": "pending", "artifact": None, "confirmation_id": cid},
            {"step": 3, "status": "pending", "artifact": None, "confirmation_id": cid},
            {"step": 4, "status": "pending", "artifact": None, "confirmation_id": cid},
            {
                "step": 5,
                "status": "skipped" if skip_step5 else "pending",
                "artifact": str(case_dir / "architecture-validator.txt"),
                "fingerprint": None,
                "confirmation_id": cid,
            },
        ],
    }
    if not skip_step5:
        (case_dir / "architecture-validator.txt").write_text("real output\n", encoding="utf-8")
    (case_dir / "proposal.json").write_text(canonical(proposal), encoding="utf-8")
    (case_dir / "checklist.json").write_text(canonical(checklist), encoding="utf-8")
    return repo, base / "out"


def codes(payload: dict) -> set[str]:
    return {item["code"] for item in payload["diagnostics"]}


class Issue264CombinedTest(unittest.TestCase):
    def tearDown(self) -> None:
        if TMP.exists():
            shutil.rmtree(TMP)

    def test_both_gates_fire_in_one_pass(self) -> None:
        """The literal acceptance criterion: one pass, both missing items named."""
        repo, out = make_pass("both")
        payload = TOOL.report(repo, validate_links=True, topic=TOPIC, out=out)
        found = codes(payload)
        self.assertIn("UNDECLARED_RETIREMENT", found)
        self.assertIn("EXEC_STEP5_ARTIFACT_MISSING", found)
        self.assertTrue(TOOL.has_error(payload))

    def test_cli_exits_nonzero_and_names_both(self) -> None:
        repo, out = make_pass("cli")
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), str(repo), "--validate",
             "--topic", TOPIC, "--out", str(out)],
            capture_output=True, text=True, env=GIT_ENV,
        )
        self.assertNotEqual(0, proc.returncode)
        text = proc.stdout + proc.stderr
        self.assertIn("UNDECLARED_RETIREMENT", text)
        self.assertIn("EXEC_STEP5_ARTIFACT_MISSING", text)

    def test_deletion_alone_does_not_fire_step5_gate(self) -> None:
        """Falsifiable: deletion is the sole cause of UNDECLARED_RETIREMENT."""
        repo, out = make_pass("deletion-only", skip_step5=False)
        found = codes(TOOL.report(repo, validate_links=True, topic=TOPIC, out=out))
        self.assertIn("UNDECLARED_RETIREMENT", found)
        self.assertNotIn("EXEC_STEP5_ARTIFACT_MISSING", found)

    def test_step5_skip_alone_does_not_fire_retirement_gate(self) -> None:
        """Falsifiable: Step 5 skip is the sole cause of the step-5 gate."""
        repo, out = make_pass("step5-only", delete_page=False)
        found = codes(TOOL.report(repo, validate_links=True, topic=TOPIC, out=out))
        self.assertIn("EXEC_STEP5_ARTIFACT_MISSING", found)
        self.assertNotIn("UNDECLARED_RETIREMENT", found)


if __name__ == "__main__":
    unittest.main()
