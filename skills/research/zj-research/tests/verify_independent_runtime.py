#!/usr/bin/env python3
"""Independence contract: zj-research is a protocol adapter, not a compiler carrier.

The skill must NOT bundle any specific upstream research compiler (no vendored
tgz, no compiler-lock). It requires the caller to supply a zj-research-cli/v1
compatible compiler via ZJ_RESEARCH_CLI (and a zj-research-eval-cli/v1 compiler
via ZJ_RESEARCH_EVAL_CLI). This keeps the skill runnable on any agent that
points at its own compiler implementation, and is vendor-neutral.
"""

import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
ADAPTER = SCRIPTS / "research_cli.py"
EVALUATION_ADAPTER = SCRIPTS / "research_eval_cli.py"
ARTIFACTS = ROOT / "artifacts"

# Ensure the adapter modules can resolve each other (research_eval_cli imports research_cli).
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# Vendor tokens that must not appear anywhere in the skill once it is independent.
FORBIDDEN_TOKENS = ("ZHarness", "dsh-research-compiler-artifact", "DeepSeek Harness", "DeepSeek")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_skill_bundles_no_compiler_artifact():
    if not ARTIFACTS.exists():
        return
    offenders = [p.name for p in ARTIFACTS.iterdir() if p.suffix == ".tgz"]
    if offenders:
        raise AssertionError(f"skill still bundles a compiler artifact: {offenders}")
    if (ARTIFACTS / "compiler-lock.json").exists():
        raise AssertionError("skill still carries a compiler-lock pinning a bundled artifact")


def test_research_command_requires_external_compiler():
    adapter = load_module("research_cli_independent", ADAPTER)
    saved = os.environ.pop("ZJ_RESEARCH_CLI", None)
    try:
        try:
            adapter.command()
        except RuntimeError as error:
            assert "ZJ_RESEARCH_CLI" in str(error), error
            return
        raise AssertionError("command() did not require ZJ_RESEARCH_CLI when unset")
    finally:
        if saved is not None:
            os.environ["ZJ_RESEARCH_CLI"] = saved


def test_evaluation_command_requires_external_compiler():
    adapter = load_module("research_eval_cli_independent", EVALUATION_ADAPTER)
    saved = os.environ.pop("ZJ_RESEARCH_EVAL_CLI", None)
    try:
        try:
            adapter.command()
        except RuntimeError as error:
            assert "ZJ_RESEARCH_EVAL_CLI" in str(error), error
            return
        raise AssertionError("evaluation command() did not require ZJ_RESEARCH_EVAL_CLI when unset")
    finally:
        if saved is not None:
            os.environ["ZJ_RESEARCH_EVAL_CLI"] = saved


def test_no_vendor_dependency_tokens():
    offenders = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path == Path(__file__):
            continue
        if path.suffix in {".pyc"} or path.name == "__pycache__":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for token in FORBIDDEN_TOKENS:
            if token in text:
                offenders.append(f"{path.relative_to(ROOT)}:{token}")
    if offenders:
        raise AssertionError("skill still references vendor tokens:\n" + "\n".join(offenders))


def main() -> int:
    test_skill_bundles_no_compiler_artifact()
    test_research_command_requires_external_compiler()
    test_evaluation_command_requires_external_compiler()
    test_no_vendor_dependency_tokens()
    print("zj-research independence: bundles no compiler, requires external compiler, no vendor tie")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
