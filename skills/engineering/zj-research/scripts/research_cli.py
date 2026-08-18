#!/usr/bin/env python3
"""Validated adapter for the versioned ZHarness research CLI protocol."""

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

PROTOCOL = "zj-research-cli/v1"
REQUIRED_OPERATIONS = {"collect", "compile-report", "render-html", "evaluate"}
DEFAULT_TIMEOUT_SECONDS = 300.0


def command() -> list[str]:
    configured = os.environ.get("ZJ_RESEARCH_CLI")
    if configured:
        return shlex.split(configured)
    installed = shutil.which("dsh-research")
    if installed:
        return [installed]
    raise RuntimeError(
        "dsh-research is unavailable. Install a supported @deepseek-ai/dsh-research-cli "
        "artifact or set ZJ_RESEARCH_CLI to a local ZHarness build; no fallback is used."
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("request", nargs="?", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    executable = command()
    if args.check:
        response = invoke(executable, {"protocol": PROTOCOL, "operation": "describe"})
        operations = set(response.get("result", {}).get("operations", []))
        missing = sorted(REQUIRED_OPERATIONS - operations)
        if missing:
            raise RuntimeError(f"compiler is missing required operations: {', '.join(missing)}")
        print(f"{PROTOCOL}: {', '.join(sorted(operations))}")
        return 0
    if args.request is None:
        parser.error("request is required unless --check is used")
    request = json.loads(args.request.read_text(encoding="utf-8"))
    if request.get("protocol") != PROTOCOL:
        raise RuntimeError(f"request protocol must be {PROTOCOL}")
    response = invoke(executable, request)
    rendered = json.dumps(response, ensure_ascii=False, indent=2) + "\n"
    if args.output is None:
        sys.stdout.write(rendered)
    else:
        args.output.write_text(rendered, encoding="utf-8")
    return 0


def invoke(executable: list[str], request: dict[str, object]) -> dict[str, object]:
    configured_timeout = os.environ.get("ZJ_RESEARCH_CLI_TIMEOUT_SECONDS")
    try:
        timeout = DEFAULT_TIMEOUT_SECONDS if configured_timeout is None else float(configured_timeout)
    except ValueError as error:
        raise RuntimeError("ZJ_RESEARCH_CLI_TIMEOUT_SECONDS must be a positive number") from error
    if timeout <= 0:
        raise RuntimeError("ZJ_RESEARCH_CLI_TIMEOUT_SECONDS must be a positive number")
    try:
        completed = subprocess.run(
            executable,
            input=json.dumps(request, separators=(",", ":")),
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"dsh-research exceeded the {timeout:g}s adapter timeout") from error
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"dsh-research exited {completed.returncode}")
    response = json.loads(completed.stdout)
    if response.get("protocol") != PROTOCOL:
        raise RuntimeError(f"compiler response protocol must be {PROTOCOL}")
    if response.get("operation") != request.get("operation"):
        raise RuntimeError("compiler response operation does not match the request")
    return response


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"research-cli adapter: {error}", file=sys.stderr)
        raise SystemExit(1)
