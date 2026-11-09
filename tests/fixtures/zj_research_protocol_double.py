#!/usr/bin/env python3
"""Protocol test double for the zj-research CLI seam (CI test layer only).

This is NOT a compiler and is never shipped with the skill. It lives under the
repository's test layer so the publisher quality-gate contract can run in CI
without any vendor compiler. It returns protocol-shaped responses only; exact
rendered output stays the responsibility of the real compiler, exercised by
verify_golden_contract.py when the caller injects one.

Injected at the system boundary via:
    ZJ_RESEARCH_CLI="python3 tests/fixtures/zj_research_protocol_double.py"
    ZJ_RESEARCH_EVAL_CLI="python3 tests/fixtures/zj_research_protocol_double.py"
"""

import hashlib
import html
import json
import sys

RESEARCH = "zj-research-cli/v1"
EVALUATION = "zj-research-eval-cli/v1"
RESEARCH_OPERATIONS = ["collect", "compile-report", "render-html", "evaluate"]
EVALUATION_OPERATIONS = ["validate-assets", "calibrate-judge"]


def research_result(request: dict) -> dict:
    operation = request.get("operation")
    if operation == "describe":
        return {"operations": list(RESEARCH_OPERATIONS)}
    if operation == "compile-report":
        report = request.get("report") or {}
        markdown = f"# {report.get('title', '')}\n\n{report.get('summary', '')}\n"
        return {
            "markdown": markdown,
            "reportHash": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
        }
    if operation == "render-html":
        return {"html": f"<html><body><pre>{html.escape(str(request.get('markdown', '')))}</pre></body></html>"}
    if operation == "evaluate":
        return {
            "healthy": True,
            "correctness": {
                "revisionPinned": True,
                "provenanceComplete": True,
                "criticalClaimsEvidence": True,
                "scoringAxesSeparated": True,
                "publishExactlyOnce": True,
                "receiptConsistent": True,
            },
            "compilerVersion": "protocol-double/v1",
        }
    raise RuntimeError(f"protocol double does not implement research operation: {operation}")


def evaluation_result(request: dict) -> dict:
    operation = request.get("operation")
    if operation == "describe":
        return {"operations": list(EVALUATION_OPERATIONS)}
    if operation in EVALUATION_OPERATIONS:
        return {
            "qualityCaseCount": 0,
            "calibration": {
                "sampleCount": 0,
                "scoreMeanAbsoluteError": 0,
                "withinToleranceRate": 1,
                "recommendationAgreement": 1,
                "riskCountMeanAbsoluteError": 0,
                "passed": True,
            },
        }
    raise RuntimeError(f"protocol double does not implement evaluation operation: {operation}")


def main() -> int:
    try:
        request = json.loads(sys.stdin.read())
    except json.JSONDecodeError as error:
        print(f"protocol double: invalid request JSON: {error}", file=sys.stderr)
        return 1
    if not isinstance(request, dict):
        print("protocol double: request must be a JSON object", file=sys.stderr)
        return 1
    protocol = request.get("protocol")
    try:
        if protocol == RESEARCH:
            result = research_result(request)
        elif protocol == EVALUATION:
            result = evaluation_result(request)
        else:
            raise RuntimeError(f"unsupported protocol: {protocol}")
    except RuntimeError as error:
        print(f"protocol double: {error}", file=sys.stderr)
        return 1
    response = {"protocol": protocol, "operation": request.get("operation"), "result": result}
    sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
