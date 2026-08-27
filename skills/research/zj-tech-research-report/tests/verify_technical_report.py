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

        positive_gaps = copy.deepcopy(report)
        positive_gaps["informationGaps"] = {
            "status": "has-gaps",
            "rationale": "Cross-device permission enforcement remains an evidence gap in this run.",
        }
        positive_gaps_ledger = copy.deepcopy(ledger)
        positive_gaps_ledger["result"]["unknownCriteria"] = [
            {
                "criterionId": "cross-device-permission-enforcement",
                "repository": {"owner": "TencentCloud", "name": "TencentDB-Agent-Memory"},
            }
        ]
        positive_gaps_path = root / "positive-information-gaps-report-ir.json"
        positive_gaps_ledger_path = root / "positive-information-gaps-ledger.json"
        write_json(positive_gaps_path, positive_gaps)
        write_json(positive_gaps_ledger_path, positive_gaps_ledger)
        run([
            sys.executable,
            str(VALIDATOR),
            str(positive_gaps_path),
            str(positive_gaps_ledger_path),
            str(brief_path),
        ])
        positive_markdown = root / "positive-information-gaps.md"
        positive_receipt_path = root / "positive-information-gaps-receipt.json"
        run([
            sys.executable,
            str(PUBLISHER),
            str(positive_gaps_path),
            str(positive_gaps_ledger_path),
            str(positive_markdown),
            "--receipt",
            str(positive_receipt_path),
            "--brief",
            str(brief_path),
        ])
        positive_receipt = json.loads(positive_receipt_path.read_text(encoding="utf-8"))
        positive_quality_gate = positive_receipt.get("qualityGate")
        if not isinstance(positive_quality_gate, dict) or positive_quality_gate.get("healthy") is not True:
            raise AssertionError("positive has-gaps report did not pass the quality gate")
        if positive_quality_gate.get("counts", {}).get("ledgerUnknownCriteria") != 1:
            raise AssertionError("positive has-gaps receipt did not count the unknown criterion")

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

        empty_gaps = copy.deepcopy(report)
        empty_gaps["informationGaps"] = {}
        empty_gaps_path = root / "empty-information-gaps-report-ir.json"
        write_json(empty_gaps_path, empty_gaps)
        rejected_empty_gaps = run([
            sys.executable,
            str(PUBLISHER),
            str(empty_gaps_path),
            str(ledger_path),
            str(root / "empty-information-gaps.md"),
            "--receipt",
            str(root / "empty-information-gaps-receipt.json"),
            "--brief",
            str(brief_path),
        ], check=False)
        if rejected_empty_gaps.returncode == 0 or "informationGaps.status" not in rejected_empty_gaps.stderr:
            raise AssertionError("publisher accepted an empty informationGaps object")
        assert_no_publication(root, "empty-information-gaps")

        invalid_gaps = copy.deepcopy(report)
        invalid_gaps["informationGaps"] = {"status": "unknown", "rationale": "The evidence is complete."}
        invalid_gaps_path = root / "invalid-information-gaps-report-ir.json"
        write_json(invalid_gaps_path, invalid_gaps)
        rejected_invalid_gaps = run([
            sys.executable,
            str(PUBLISHER),
            str(invalid_gaps_path),
            str(ledger_path),
            str(root / "invalid-information-gaps.md"),
            "--receipt",
            str(root / "invalid-information-gaps-receipt.json"),
            "--brief",
            str(brief_path),
        ], check=False)
        if rejected_invalid_gaps.returncode == 0 or "informationGaps.status must" not in rejected_invalid_gaps.stderr:
            raise AssertionError("publisher accepted an invalid informationGaps status")
        assert_no_publication(root, "invalid-information-gaps")

        mismatched_gaps = copy.deepcopy(report)
        mismatched_gaps["informationGaps"] = {
            "status": "no-gaps",
            "rationale": "No information gap is known.",
        }
        mismatched_gaps_path = root / "mismatched-information-gaps-report-ir.json"
        mismatched_ledger = copy.deepcopy(ledger)
        mismatched_ledger["result"]["unknownCriteria"] = [{"id": "open-question"}]
        mismatched_ledger_path = root / "mismatched-information-gaps-ledger.json"
        write_json(mismatched_gaps_path, mismatched_gaps)
        write_json(mismatched_ledger_path, mismatched_ledger)
        rejected_mismatched_gaps = run([
            sys.executable,
            str(PUBLISHER),
            str(mismatched_gaps_path),
            str(mismatched_ledger_path),
            str(root / "mismatched-information-gaps.md"),
            "--receipt",
            str(root / "mismatched-information-gaps-receipt.json"),
            "--brief",
            str(brief_path),
        ], check=False)
        if rejected_mismatched_gaps.returncode == 0 or "status='no-gaps'" not in rejected_mismatched_gaps.stderr:
            raise AssertionError("publisher accepted informationGaps status mismatched with ledger")
        assert_no_publication(root, "mismatched-information-gaps")

    print("technical research-report contract passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"technical report contract: {error}", file=sys.stderr)
        raise SystemExit(1)
