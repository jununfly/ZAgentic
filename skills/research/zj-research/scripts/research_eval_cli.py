#!/usr/bin/env python3
"""Validated adapter for the versioned ZHarness research evaluation CLI."""

import argparse
import json
import os
import shlex
import sys
from pathlib import Path

from research_cli import artifact_command, invoke

PROTOCOL = "zj-research-eval-cli/v1"
REQUIRED_OPERATIONS = {"validate-assets", "calibrate-judge"}


def command() -> list[str]:
    configured = os.environ.get("ZJ_RESEARCH_EVAL_CLI")
    if configured:
        return shlex.split(configured)
    return artifact_command("evaluation", PROTOCOL)


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", nargs="?", choices=sorted(REQUIRED_OPERATIONS))
    parser.add_argument("inputs", nargs="*", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    executable = command()
    if args.check:
        response = invoke(executable, {"protocol": PROTOCOL, "operation": "describe"})
        operations = set(response.get("result", {}).get("operations", []))
        missing = sorted(REQUIRED_OPERATIONS - operations)
        if missing:
            raise RuntimeError(f"evaluation runtime is missing required operations: {', '.join(missing)}")
        print(f"{PROTOCOL}: {', '.join(sorted(operations))}")
        return 0
    if args.operation is None:
        parser.error("operation is required unless --check is used")
    expected_inputs = 4 if args.operation == "validate-assets" else 2
    if len(args.inputs) != expected_inputs:
        parser.error(f"{args.operation} requires {expected_inputs} JSON input files")
    if args.operation == "validate-assets":
        keys = ("manifest", "rubrics", "annotations", "calibration")
    else:
        keys = ("rubrics", "calibration")
    request: dict[str, object] = {"protocol": PROTOCOL, "operation": args.operation}
    request.update({key: read_json(path) for key, path in zip(keys, args.inputs)})
    response = invoke(executable, request)
    rendered = json.dumps(response, ensure_ascii=False, indent=2) + "\n"
    if args.output is None:
        sys.stdout.write(rendered)
    else:
        args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"research-eval adapter: {error}", file=sys.stderr)
        raise SystemExit(1)
