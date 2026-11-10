#!/usr/bin/env python3
"""Golden contract tests for the zj-research protocol adapters.

zj-research is a protocol adapter and supplies no compiler and no publisher.
These tests exercise the adapters against a compiler the caller injects through
ZJ_RESEARCH_CLI / ZJ_RESEARCH_EVAL_CLI, and a report publisher through
ZJ_RESEARCH_PUBLISHER. A missing pointer is a setup failure: the runner fails
with injection instructions and never resolves any fallback, including a retired
bundled-artifact cache or a hard-coded sibling-skill path.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "scripts" / "research_cli.py"
RUNTIME_CONTRACT = ROOT / "tests" / "verify_runtime_contract.py"
EVALUATION_ADAPTER = ROOT / "scripts" / "research_eval_cli.py"
FIXTURE = Path(__file__).with_name("golden-contract.json")
EVALUATION_ASSETS = ROOT / "tests" / "golden" / "controlled-quality-v1"


def publisher_path() -> Path:
    """Return the caller-injected publish_report.py, with no sibling fallback.

    The publisher lives in a separate skill (zj-tech-research-report). This
    contract owns no publisher and must not reach into a sibling skill by a
    hard-coded parent-path assumption — that hidden coupling reintroduces
    exactly the install-time fragility the vendor-neutral refactor removed.
    The caller injects the path; a missing pointer is a setup failure.
    """

    raw = os.environ.get("ZJ_RESEARCH_PUBLISHER")
    if not raw:
        raise RuntimeError(
            "No publisher injected: set ZJ_RESEARCH_PUBLISHER to the publish_report.py "
            "path (e.g. export ZJ_RESEARCH_PUBLISHER="
            '"python /path/to/zj-tech-research-report/scripts/publish_report.py"). '
            "zj-research owns no publisher and resolves no sibling-skill fallback."
        )
    path = Path(raw)
    if not path.exists():
        raise RuntimeError(f"ZJ_RESEARCH_PUBLISHER points to a missing file: {path}")
    return path


def compiler_env() -> dict[str, str]:
    """Return the caller-owned compiler environment, with no fallback of any kind.

    zj-research bundles no compiler and owns no compiler cache. Silently
    resolving a compiler from a local directory would reintroduce exactly the
    hidden coupling this skill was refactored to remove.
    """

    env = dict(os.environ)
    missing = [name for name in ("ZJ_RESEARCH_CLI", "ZJ_RESEARCH_EVAL_CLI") if not env.get(name)]
    if missing:
        raise RuntimeError(
            "No external compiler injected: " + ", ".join(missing) + ". "
            'Export ZJ_RESEARCH_CLI="node /path/to/compiler/lib/bin.js" and '
            'ZJ_RESEARCH_EVAL_CLI="node /path/to/compiler/lib/eval.js" before running '
            "the golden contract. zj-research supplies no compiler and has no cache fallback."
        )
    return env


def main() -> int:
    env = compiler_env()
    run([sys.executable, str(RUNTIME_CONTRACT)], env=env)
    run([sys.executable, str(ADAPTER), "--check"], env=env)
    run([sys.executable, str(EVALUATION_ADAPTER), "--check"], env=env)
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="zj-research-contract-") as directory:
        root = Path(directory)
        for index, case in enumerate(fixture["cases"]):
            request = root / f"request-{index}.json"
            output = root / f"response-{index}.json"
            request.write_text(json.dumps(case["request"], ensure_ascii=False), encoding="utf-8")
            run([sys.executable, str(ADAPTER), str(request), "--output", str(output)], env=env)
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
        run([sys.executable, str(publisher_path()), str(report_ir), str(ledger), str(markdown), "--receipt", str(receipt)], env=env)
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
            [sys.executable, str(publisher_path()), str(report_ir), str(unhealthy), str(rejected_markdown), "--receipt", str(rejected_receipt)],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        if rejected.returncode == 0 or "research report is unhealthy" not in rejected.stderr:
            raise AssertionError("publisher accepted an unhealthy evaluation")
        if rejected_markdown.exists() or rejected_markdown.with_suffix(".html").exists() or rejected_receipt.exists():
            raise AssertionError("unhealthy publication created an artifact")
        verify_independent_report_runtime(root, report_ir, ledger, env)
        invalid_timeout = dict(env)
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
        verify_evaluation_assets(root, env)
    print(
        "zj-research golden contract: runtime contract, "
        f"{len(fixture['cases'])} golden compiler cases, publisher path, and 10 evaluation cases passed"
    )
    return 0


def verify_independent_report_runtime(root: Path, report_ir: Path, ledger: Path, env: dict[str, str]) -> None:
    """The renamed report skill must work through an external compiler runtime."""

    independent_publisher = root / "independent-report-skill" / "scripts" / "publish_report.py"
    independent_publisher.parent.mkdir(parents=True)
    shutil.copy2(publisher_path(), independent_publisher)
    missing_env = dict(env)
    missing_env.pop("ZJ_RESEARCH_RUNTIME", None)
    missing = subprocess.run(
        [
            sys.executable,
            str(independent_publisher),
            str(report_ir),
            str(ledger),
            str(root / "missing-runtime.md"),
            "--receipt",
            str(root / "missing-runtime-receipt.json"),
        ],
        env=missing_env,
        text=True,
        capture_output=True,
        check=False,
    )
    if missing.returncode == 0 or "ZJ_RESEARCH_RUNTIME=<path-to-zj-research>" not in missing.stderr:
        raise AssertionError("independent report publisher did not provide its runtime setup pointer")
    configured_env = dict(missing_env)
    configured_env["ZJ_RESEARCH_RUNTIME"] = str(ROOT)
    markdown = root / "independent-runtime.md"
    receipt = root / "independent-runtime-receipt.json"
    run(
        [
            sys.executable,
            str(independent_publisher),
            str(report_ir),
            str(ledger),
            str(markdown),
            "--receipt",
            str(receipt),
        ],
        env=configured_env,
    )
    publication = json.loads(receipt.read_text(encoding="utf-8"))
    if publication["evaluation"]["healthy"] is not True or not markdown.with_suffix(".html").exists():
        raise AssertionError("explicit research runtime did not enable independent report publication")


def verify_evaluation_assets(root: Path, env: dict[str, str]) -> None:
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
    ], env=env)
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
    ], env=env)
    if json.loads(calibration.read_text(encoding="utf-8"))["result"] != expected["calibration"]:
        raise AssertionError("standalone Judge calibration diverged from asset validation")


def run(command: list[str], env: dict[str, str] | None = None) -> None:
    completed = subprocess.run(command, env=env, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"golden contract: {error}", file=sys.stderr)
        raise SystemExit(1)
