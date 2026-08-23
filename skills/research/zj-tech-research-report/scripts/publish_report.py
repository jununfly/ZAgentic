#!/usr/bin/env python3
"""Publish one compiler-backed Markdown/HTML report pair and its health receipt."""

import argparse
import json
import os
import sys
from pathlib import Path

def resolve_research_runtime() -> Path:
    """Find the canonical zj-research skill used by this publisher."""

    sibling = Path(__file__).resolve().parents[2] / "zj-research"
    configured = os.environ.get("ZJ_RESEARCH_RUNTIME")
    candidates = [sibling]
    if configured:
        candidates.append(Path(configured).expanduser())
    for candidate in candidates:
        if (candidate / "scripts" / "research_cli.py").is_file():
            return candidate
    if configured:
        raise RuntimeError(
            "the configured ZJ_RESEARCH_RUNTIME does not contain "
            f"scripts/research_cli.py: {Path(configured).expanduser()}"
        )
    raise RuntimeError(
        "the shared zj-research runtime is unavailable; install the sibling "
        "zj-research skill or set ZJ_RESEARCH_RUNTIME=<path-to-zj-research>"
    )


def load_research_runtime():
    runtime = resolve_research_runtime()
    scripts = str(runtime / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    try:
        import research_cli  # type: ignore[import-not-found]
    except ImportError as error:
        raise RuntimeError(f"could not load shared research runtime from {runtime}") from error
    return research_cli


def read_object(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path} must contain one JSON object")
    return value


def unwrap_ledger(value: dict[str, object], protocol: str) -> dict[str, object]:
    if value.get("protocol") == protocol and value.get("operation") == "collect":
        result = value.get("result")
        if isinstance(result, dict):
            return result
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report_ir", type=Path)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("markdown_path", type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--brief", type=Path, help="technical-decision-brief/v1 JSON for technical-c4 reports")
    args = parser.parse_args()
    report = read_object(args.report_ir)
    runtime = load_research_runtime()
    executable = runtime.command()
    ledger = unwrap_ledger(read_object(args.ledger), runtime.PROTOCOL)
    family = report.get("family")
    if family not in {"technical-c4/v1", "zj-draft/v1"}:
        raise RuntimeError("Report IR has an unsupported family")
    quality_gate = None
    if family == "technical-c4/v1":
        if args.brief is None:
            raise RuntimeError("technical-c4 publication requires --brief technical-decision-brief/v1 JSON")
        # Keep the publisher independently installable for legacy zj-draft/v1
        # publication. The validator is a technical-report-only dependency and
        # is intentionally loaded only when that family is selected.
        try:
            from validate_technical_report import validate_report
        except ImportError as error:
            raise RuntimeError(
                "technical-c4 publication requires the bundled technical report validator"
            ) from error
        quality_gate = validate_report(report, ledger, read_object(args.brief))
    compiled = runtime.invoke(executable, {"protocol": runtime.PROTOCOL, "operation": "compile-report", "report": report, "ledger": ledger})
    compiled_result = compiled.get("result")
    if not isinstance(compiled_result, dict) or not isinstance(compiled_result.get("markdown"), str) or not isinstance(compiled_result.get("reportHash"), str):
        raise RuntimeError("compile-report returned an invalid result")
    markdown = compiled_result["markdown"]
    report_hash = compiled_result["reportHash"]
    rendered = runtime.invoke(executable, {"protocol": runtime.PROTOCOL, "operation": "render-html", "family": family, "markdown": markdown})
    rendered_result = rendered.get("result")
    if not isinstance(rendered_result, dict) or not isinstance(rendered_result.get("html"), str):
        raise RuntimeError("render-html returned an invalid result")
    markdown_path = args.markdown_path.resolve()
    if markdown_path.suffix.lower() != ".md":
        raise RuntimeError("markdown_path must end in .md")
    html_path = markdown_path.with_suffix(".html")
    receipt_path = args.receipt.resolve()
    existing = [path for path in (markdown_path, html_path, receipt_path) if path.exists()]
    if existing:
        raise RuntimeError(f"publication target already exists: {existing[0]}")
    evaluation = runtime.invoke(executable, {
        "protocol": runtime.PROTOCOL,
        "operation": "evaluate",
        "report": report,
        "ledger": ledger,
        "publication": {"reportHash": report_hash, "markdownPath": str(markdown_path), "htmlPath": str(html_path), "publishCount": 1},
    })
    result = evaluation.get("result")
    if not isinstance(result, dict) or result.get("healthy") is not True:
        raise RuntimeError(f"research report is unhealthy: {json.dumps(result, ensure_ascii=False)}")
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    with markdown_path.open("x", encoding="utf-8") as output:
        output.write(markdown)
    try:
        with html_path.open("x", encoding="utf-8") as output:
            output.write(rendered_result["html"])
    except Exception as error:
        raise RuntimeError(f"HTML publication failed; canonical Markdown remains at {markdown_path}: {error}") from error
    receipt = {"markdownPath": str(markdown_path), "htmlPath": str(html_path), "reportHash": report_hash, "publishCount": 1, "evaluation": result}
    if quality_gate is not None:
        receipt["qualityGate"] = quality_gate
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    with receipt_path.open("x", encoding="utf-8") as output:
        json.dump(receipt, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print(json.dumps(receipt, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"research-report publisher: {error}", file=sys.stderr)
        raise SystemExit(1)
