#!/usr/bin/env python3
"""TDD/refactor guard for F6: run_regressions must thread the repo root through
its three helper functions explicitly, not via a module-level global.

Seam under test (S3 — public functions): run_negative_case / run_rejected_case /
run_no_match_case accept an explicit ``root`` argument, and the module no longer
mutates a ``global ROOT`` (which made the functions lie about their
dependencies and break outside the CLI call order).
"""
import importlib.util
import inspect
import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = (
    REPO_ROOT / "skills" / "productivity" / "zj-composer" / "scripts" / "run_regressions.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("rr_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestRootNotGlobal(unittest.TestCase):
    def test_helpers_take_explicit_root(self):
        mod = _load()
        for fn in ("run_negative_case", "run_rejected_case", "run_no_match_case"):
            with self.subTest(fn=fn):
                sig = inspect.signature(getattr(mod, fn))
                self.assertIn("root", sig.parameters, f"{fn} must accept explicit root")

    def test_no_global_root_statement(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("global ROOT", text, "run_regressions must not use global ROOT")
        self.assertNotIn(
            "validate_plan(plan_path, ROOT, None)", text,
            "helpers must use the passed root, not a global",
        )
        self.assertNotIn(
            "validate_plan(path, ROOT, None)", text,
            "helpers must use the passed root, not a global",
        )


if __name__ == "__main__":
    unittest.main()
