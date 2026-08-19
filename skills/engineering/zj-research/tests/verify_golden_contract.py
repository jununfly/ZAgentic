#!/usr/bin/env python3
"""Verify the ZAgentic adapter against a configured ZHarness research CLI."""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "scripts" / "research_cli.py"
EVALUATION_ADAPTER = ROOT / "scripts" / "research_eval_cli.py"
PUBLISHER = ROOT.parent / "zj-research-report" / "scripts" / "publish_report.py"
FIXTURE = Path(__file__).with_name("golden-contract.json")
EVALUATION_ASSETS = ROOT.parents[2] / "research" / "evaluation" / "controlled-quality-v1"


def main() -> int:
    run([sys.executable, str(ADAPTER), "--check"])
    run([sys.executable, str(EVALUATION_ADAPTER), "--check"])
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
        verify_artifact_failures(root)
        verify_evaluation_assets(root)
    print("zj-research golden contract: 7 compiler cases and 10 evaluation cases passed")
    return 0


def verify_artifact_failures(root: Path) -> None:
    spec = importlib.util.spec_from_file_location("research_cli_contract", ADAPTER)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load research adapter")
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    source = ROOT / "artifacts"
    copied = root / "artifacts"
    shutil.copytree(source, copied)
    adapter.ARTIFACTS = copied
    lock = json.loads((copied / "compiler-lock.json").read_text(encoding="utf-8"))
    lock["schema"] = adapter.LOCK_SCHEMA
    lock["protocols"] = {"research": adapter.PROTOCOL, "evaluation": "zj-research-eval-cli/v1"}
    lock["executables"] = {"research": "lib/bin.js", "evaluation": "lib/eval.js"}
    (copied / "compiler-lock.json").write_text(json.dumps(lock), encoding="utf-8")
    artifact = copied / lock["artifact"]
    artifact.write_bytes(artifact.read_bytes() + b"tampered")
    try:
        adapter.artifact_command("research", adapter.PROTOCOL)
    except RuntimeError as error:
        if "SHA-256 mismatch" not in str(error):
            raise
    else:
        raise AssertionError("adapter accepted a tampered compiler artifact")
    artifact.unlink()
    try:
        adapter.artifact_command("research", adapter.PROTOCOL)
    except RuntimeError as error:
        if "artifact is unavailable" not in str(error):
            raise
    else:
        raise AssertionError("adapter accepted a missing compiler artifact")


def verify_evaluation_assets(root: Path) -> None:
    validation = root / "asset-validation.json"
    run([
        sys.executable,
        str(EVALUATION_ADAPTER),
        "validate-assets",
        str(EVALUATION_ASSETS / "manifest.json"),
        str(EVALUATION_ASSETS / "rubrics.json"),
        str(EVALUATION_ASSETS / "annotations.json"),
        str(EVALUATION_ASSETS / "calibration.json"),
        "--output",
        str(validation),
    ])
    result = json.loads(validation.read_text(encoding="utf-8"))["result"]
    expected = {
        "qualityCaseCount": 10,
        "calibration": {
            "sampleCount": 10,
            "scoreMeanAbsoluteError": 2.4,
            "withinToleranceRate": 1,
            "recommendationAgreement": 1,
            "riskCountMeanAbsoluteError": 0.1,
            "passed": True,
        },
    }
    if result["qualityCaseCount"] != expected["qualityCaseCount"] or result["calibration"] != expected["calibration"]:
        raise AssertionError(f"evaluation assets diverged:\n{json.dumps(result, ensure_ascii=False, indent=2)}")
    calibration = root / "judge-calibration.json"
    run([
        sys.executable,
        str(EVALUATION_ADAPTER),
        "calibrate-judge",
        str(EVALUATION_ASSETS / "rubrics.json"),
        str(EVALUATION_ASSETS / "calibration.json"),
        "--output",
        str(calibration),
    ])
    if json.loads(calibration.read_text(encoding="utf-8"))["result"] != expected["calibration"]:
        raise AssertionError("standalone Judge calibration diverged from asset validation")


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
