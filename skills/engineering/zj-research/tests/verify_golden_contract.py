#!/usr/bin/env python3
"""Verify the ZAgentic adapter against a configured ZHarness research CLI."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "scripts" / "research_cli.py"
PUBLISHER = ROOT.parent / "zj-research-report" / "scripts" / "publish_report.py"
FIXTURE = Path(__file__).with_name("golden-contract.json")


def main() -> int:
    if not os.environ.get("ZJ_RESEARCH_CLI"):
        raise RuntimeError("set ZJ_RESEARCH_CLI to the ZHarness dsh-research command")
    run([sys.executable, str(ADAPTER), "--check"])
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="zj-research-contract-") as directory:
        root = Path(directory)
        for index, case in enumerate(fixture["cases"]):
            request = root / f"request-{index}.json"
            output = root / f"response-{index}.json"
            request.write_text(json.dumps(case["request"], ensure_ascii=False), encoding="utf-8")
            run([sys.executable, str(ADAPTER), str(request), "--output", str(output)])
            actual = json.loads(output.read_text(encoding="utf-8"))
            if actual != case["expected"]:
                raise AssertionError(f"golden contract case {index} diverged:\n{json.dumps(actual, ensure_ascii=False, indent=2)}")
        compiled_request = fixture["cases"][0]["request"]
        report_ir = root / "report-ir.json"
        ledger = root / "ledger.json"
        markdown = root / "report.md"
        receipt = root / "receipt.json"
        report_ir.write_text(json.dumps(compiled_request["report"], ensure_ascii=False), encoding="utf-8")
        ledger.write_text(json.dumps(compiled_request["ledger"], ensure_ascii=False), encoding="utf-8")
        run([sys.executable, str(PUBLISHER), str(report_ir), str(ledger), str(markdown), "--receipt", str(receipt)])
        publication = json.loads(receipt.read_text(encoding="utf-8"))
        if publication["evaluation"]["healthy"] is not True or not markdown.exists() or not markdown.with_suffix(".html").exists():
            raise AssertionError("compiler-backed publication did not produce a healthy Markdown/HTML pair")
        unhealthy_ledger = dict(compiled_request["ledger"])
        unhealthy_ledger["evidence"] = [{
            "id": "unreferenced",
            "criterionId": "criterion",
            "repository": {"owner": "example", "name": "harness"},
            "revision": "missing-from-repositories",
            "path": "README.md",
            "sourceUrl": "https://github.com/example/harness/blob/revision/README.md",
            "excerpt": "Unreferenced evidence.",
            "kind": "canonical",
        }]
        unhealthy = root / "unhealthy-ledger.json"
        unhealthy.write_text(json.dumps(unhealthy_ledger), encoding="utf-8")
        rejected_markdown = root / "rejected.md"
        rejected_receipt = root / "rejected-receipt.json"
        rejected = subprocess.run(
            [sys.executable, str(PUBLISHER), str(report_ir), str(unhealthy), str(rejected_markdown), "--receipt", str(rejected_receipt)],
            text=True,
            capture_output=True,
            check=False,
        )
        if rejected.returncode == 0 or "research report is unhealthy" not in rejected.stderr:
            raise AssertionError("publisher accepted an unhealthy evaluation")
        if rejected_markdown.exists() or rejected_markdown.with_suffix(".html").exists() or rejected_receipt.exists():
            raise AssertionError("unhealthy publication created an artifact")
        invalid_timeout = dict(os.environ)
        invalid_timeout["ZJ_RESEARCH_CLI_TIMEOUT_SECONDS"] = "0"
        bounded = subprocess.run(
            [sys.executable, str(ADAPTER), "--check"],
            env=invalid_timeout,
            text=True,
            capture_output=True,
            check=False,
        )
        if bounded.returncode == 0 or "must be a positive number" not in bounded.stderr:
            raise AssertionError("adapter accepted a non-positive timeout")
    print("zj-research golden contract: 5 cases passed")
    return 0


def run(command: list[str]) -> None:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"golden contract: {error}", file=sys.stderr)
        raise SystemExit(1)
