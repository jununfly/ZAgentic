#!/usr/bin/env python3
"""Verify the technical decision brief and publication quality-gate contract."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts" / "publish_report.py"
VALIDATOR = ROOT / "scripts" / "validate_technical_report.py"
FIXTURE_ROOT = ROOT.parents[2] / "research" / "multi-device-agent-context"
REPORT_FIXTURE = FIXTURE_ROOT / "report-ir.json"
LEDGER_FIXTURE = FIXTURE_ROOT / "ledger-response-v2.json"


def run(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.pop("NODE_OPTIONS", None)
    completed = subprocess.run(command, env=environment, text=True, capture_output=True, check=False)
    if check and completed.returncode != 0:
        raise AssertionError(completed.stderr or completed.stdout)
    return completed


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def valid_brief() -> dict[str, object]:
    return {
        "schema": "technical-decision-brief/v1",
        "user": {
            "actor": "Human Lead coordinating multiple devices and Agents",
            "job": "Choose a reusable shared memory/context capability without transferring control-plane ownership",
        },
        "baseline": {
            "workflow": "Git, roadmap, Work Packets, and local context are coordinated separately across devices",
            "failureModes": [
                "shared context is stale or loses provenance",
                "a memory layer is mistaken for task ownership or release control",
            ],
        },
        "targetOutcome": "A bounded pilot can retrieve permission-aware, provenance-linked shared context while the existing control plane keeps ownership",
        "goals": [
            "compare serious memory/context options",
            "make the integration seam and retained ownership explicit",
        ],
        "nonGoals": [
            "replace Git or the canonical roadmap",
            "approve production rollout without pilot evidence",
        ],
        "constraints": [
            {"id": "ownership", "statement": "The target base retains task, claim, budget, and release ownership"},
            {"id": "provenance", "statement": "Retrieved context must remain attributable to a source or revision"},
        ],
        "assumptions": [
            "The first landing is an experience-version pilot",
            "The candidate repositories remain available at their sealed revisions",
        ],
        "stage": "experience-version",
        "decisionScope": "Select a shared memory/context unit capability and define its adapter seam",
        "options": [
            {"id": "mine-context", "name": "volcengine/MineContext"},
            {"id": "mycontext", "name": "openTrinity/mycontext"},
            {"id": "tencent-agent-memory", "name": "TencentCloud/TencentDB-Agent-Memory"},
        ],
    }


def assert_no_publication(root: Path, stem: str) -> None:
    for suffix in (".md", ".html", "-receipt.json"):
        path = root / f"{stem}{suffix}"
        if path.exists():
            raise AssertionError(f"quality-gate rejection created {path}")


def main() -> int:
    report = json.loads(REPORT_FIXTURE.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER_FIXTURE.read_text(encoding="utf-8"))
    brief = valid_brief()

    with tempfile.TemporaryDirectory(prefix="technical-report-contract-") as directory:
        root = Path(directory)
        report_path = root / "report-ir.json"
        ledger_path = root / "ledger.json"
        brief_path = root / "brief.json"
        write_json(report_path, report)
        write_json(ledger_path, ledger)
        write_json(brief_path, brief)

        run([sys.executable, str(VALIDATOR), str(report_path), str(ledger_path), str(brief_path)])

        markdown = root / "valid.md"
        receipt = root / "valid-receipt.json"
        run([
            sys.executable,
            str(PUBLISHER),
            str(report_path),
            str(ledger_path),
            str(markdown),
            "--receipt",
            str(receipt),
            "--brief",
            str(brief_path),
        ])
        publication = json.loads(receipt.read_text(encoding="utf-8"))
        quality_gate = publication.get("qualityGate")
        if not markdown.exists() or not markdown.with_suffix(".html").exists():
            raise AssertionError("valid technical report did not publish Markdown and HTML")
        if not isinstance(quality_gate, dict) or quality_gate.get("healthy") is not True:
            raise AssertionError("receipt did not record a healthy technical quality gate")
        if quality_gate.get("schema") != "technical-research-quality-gate/v1":
            raise AssertionError("receipt quality gate used the wrong schema")
        if quality_gate.get("reportFamily") != "technical-c4/v1":
            raise AssertionError("receipt quality gate did not identify technical-c4/v1")

        invalid_brief = copy.deepcopy(brief)
        invalid_brief["stage"] = "not-a-lifecycle-stage"
        invalid_brief_path = root / "invalid-brief.json"
        write_json(invalid_brief_path, invalid_brief)
        rejected_brief = run([
            sys.executable,
            str(PUBLISHER),
            str(report_path),
            str(ledger_path),
            str(root / "invalid-brief.md"),
            "--receipt",
            str(root / "invalid-brief-receipt.json"),
            "--brief",
            str(invalid_brief_path),
        ], check=False)
        if rejected_brief.returncode == 0 or "technical decision brief failed" not in rejected_brief.stderr:
            raise AssertionError("publisher accepted an invalid technical decision brief")
        assert_no_publication(root, "invalid-brief")

        broken_report = copy.deepcopy(report)
        broken_report["claims"][0]["evidenceIds"] = ["missing-evidence-id"]
        broken_report_path = root / "broken-report-ir.json"
        write_json(broken_report_path, broken_report)
        rejected_claim = run([
            sys.executable,
            str(PUBLISHER),
            str(broken_report_path),
            str(ledger_path),
            str(root / "broken-claim.md"),
            "--receipt",
            str(root / "broken-claim-receipt.json"),
            "--brief",
            str(brief_path),
        ], check=False)
        if rejected_claim.returncode == 0 or "missing Evidence ID" not in rejected_claim.stderr:
            raise AssertionError("publisher accepted a report claim with a broken evidence link")
        assert_no_publication(root, "broken-claim")

    print("technical research-report contract passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"technical report contract: {error}", file=sys.stderr)
        raise SystemExit(1)
