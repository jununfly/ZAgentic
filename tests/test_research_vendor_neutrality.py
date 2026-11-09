#!/usr/bin/env python3
"""TDD regression: zj-research must not retain the historical ZDSHarness tie.

Seams under test (same confirmed set as test_research_protocol_gate.py):
  S1 governance -- the research bucket's published source/doc text.
  S3 compiler protocol -- the injection boundary of the golden contract.

Two specifications of one slice:
  1. No installable research skill declares a vendor compiler dependency.
  2. A missing compiler pointer is rejected, never resolved from the retired
     bundled-artifact cache.

Explicitly exempt, with reasons (never a blanket relaxation):
  * zj-research/tests/verify_independent_runtime.py -- holds the detection
    vocabulary itself; a literal hit there is the guard, not a dependency.
  * zj-tech-research-report/tests/golden/multi-device-agent-context/ -- a
    sealed research report whose subject naming is historical evidence, not a
    runtime dependency, and whose bytes are pinned by contract tests.
"""

import importlib.util
import os
import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCAN_ROOTS = (
    REPO_ROOT / "skills/research/zj-research",
    REPO_ROOT / "skills/research/zj-code-research",
    REPO_ROOT / "skills/research/zj-tech-research-report",
)
SCAN_SUFFIXES = {".py", ".md", ".json", ".yaml", ".yml"}
VENDOR_TOKENS = (
    "ZHarness",
    "ZDSHarness",
    "dsh-",
    "DeepSeek",
    "9172aa0",
    "compiler-lock",
    "ZJ_RESEARCH_COMPILER_CACHE",
    ".cache/zj-research/compiler",
)
EXEMPT_FILES = {
    "skills/research/zj-research/tests/verify_independent_runtime.py",
}
EXEMPT_DIR_MARKERS = (
    "skills/research/zj-tech-research-report/tests/golden/multi-device-agent-context/",
)
GOLDEN_CONTRACT = REPO_ROOT / "skills/research/zj-research/tests/verify_golden_contract.py"
ENV_KEYS = ("ZJ_RESEARCH_CLI", "ZJ_RESEARCH_EVAL_CLI", "ZJ_RESEARCH_COMPILER_CACHE")


def vendor_hits():
    hits = []
    for root in SCAN_ROOTS:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in SCAN_SUFFIXES:
                continue
            relative = path.relative_to(REPO_ROOT).as_posix()
            if relative in EXEMPT_FILES or any(marker in relative for marker in EXEMPT_DIR_MARKERS):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for token in VENDOR_TOKENS:
                if token in text:
                    hits.append(f"{relative}: {token}")
    return hits


def load_golden_module():
    spec = importlib.util.spec_from_file_location("vendor_neutral_golden_contract", GOLDEN_CONTRACT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestVendorNeutrality(unittest.TestCase):
    def test_research_bucket_declares_no_vendor_compiler_dependency(self):
        self.assertEqual([], vendor_hits(), "research skills still declare a vendor compiler tie")

    def test_missing_compiler_pointer_is_rejected_not_resolved_from_cache(self):
        saved = {key: os.environ.pop(key, None) for key in ENV_KEYS}
        try:
            with self.assertRaises(RuntimeError) as raised:
                load_golden_module().compiler_env()
            self.assertIn("ZJ_RESEARCH_CLI", str(raised.exception))
        finally:
            for key, value in saved.items():
                if value is not None:
                    os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
