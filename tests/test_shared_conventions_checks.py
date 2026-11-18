#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared-conventions three checks — green on the real repo, red on injected defects.

Pins the mechanism behind roadmap 1-2-6: a closed-schema check, a byte-equal
re-render check, and a validator-binding canary. Each check is probed in both a
green state (real repo) and a red state (a defect injected into a temporary
copy), so a checker that always passes — or always fails — cannot look green.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CHECKER_PATH = REPO / "scripts" / "check-shared-conventions.py"
WORKFLOW = REPO / ".github" / "workflows" / "skill-closure-lint.yml"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CHECKER = _load(CHECKER_PATH, "_shared_conv_checker")


def _temp_repo(root: Path) -> Path:
    """A temp copy of only the paths the checks read (no working-tree writes)."""
    repo = root / "repo"
    repo.mkdir()
    p = repo / CHECKER.RULE_SOURCE_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / CHECKER.RULE_SOURCE_REL, p)
    shutil.copytree(REPO / CHECKER.ARCH_SKILL_REL, repo / CHECKER.ARCH_SKILL_REL)
    (repo / "scripts").mkdir()
    shutil.copy(REPO / "scripts" / "generate-shared-conventions.py",
                repo / "scripts" / "generate-shared-conventions.py")
    return repo


class GreenStateTest(unittest.TestCase):
    """The real repository must pass all three checks as committed."""

    def test_all_checks_pass_on_real_repo(self) -> None:
        results = CHECKER.run_all(REPO)
        for name, errors in results.items():
            self.assertEqual([], errors, f"{name} failed on the real repo: {errors}")

    def test_extension_token_extraction_is_deterministic(self) -> None:
        self.assertEqual(["ta-", "ba-", "pa-"],
                         CHECKER.extension_tokens("page-prefix:ta-/ba-/pa-"))
        self.assertEqual(["topic-batch-token"],
                         CHECKER.extension_tokens("topic-batch-token"))


class RedStateTest(unittest.TestCase):
    """Each check must fail when its specific defect is injected."""

    def test_closed_schema_detects_extension_leak(self) -> None:
        with tempfile.TemporaryDirectory(prefix="scc-test-") as td:
            repo = _temp_repo(Path(td))
            gen = CHECKER.load_generator(repo)
            source = repo / CHECKER.RULE_SOURCE_REL
            data = json.loads(source.read_text(encoding="utf-8"))
            data["core"]["doc-kind"]["summary"] += " (ta- prefix leaked)"
            source.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            errors = CHECKER.check_closed_schema(repo, gen)
            self.assertTrue(any("leaked" in e for e in errors), errors)

    def test_closed_schema_detects_consumes_outside_core(self) -> None:
        with tempfile.TemporaryDirectory(prefix="scc-test-") as td:
            repo = _temp_repo(Path(td))
            gen = CHECKER.load_generator(repo)
            skill = repo / CHECKER.ARCH_SKILL_REL / "SKILL.md"
            text = skill.read_text(encoding="utf-8")
            self.assertIn('"consumes": ["naming-syntax-core", "doc-kind", "authority"]', text)
            text = text.replace(
                '"consumes": ["naming-syntax-core", "doc-kind", "authority"]',
                '"consumes": ["not-a-core-key"]', 1,
            )
            skill.write_text(text, encoding="utf-8")
            errors = CHECKER.check_closed_schema(repo, gen)
            self.assertTrue(any("outside core" in e for e in errors), errors)

    def test_byte_equal_detects_stale_block(self) -> None:
        with tempfile.TemporaryDirectory(prefix="scc-test-") as td:
            repo = _temp_repo(Path(td))
            gen = CHECKER.load_generator(repo)
            skill = repo / CHECKER.ARCH_SKILL_REL / "SKILL.md"
            skill.write_text(
                skill.read_text(encoding="utf-8").replace(
                    '"schema_version": "skill-conventions/v1"',
                    '"schema_version": "skill-conventions/vX"', 1),
                encoding="utf-8",
            )
            errors = CHECKER.check_byte_equal(repo, gen)
            self.assertTrue(any("stale" in e for e in errors), errors)

    def test_canary_detects_hardcoded_enum(self) -> None:
        with tempfile.TemporaryDirectory(prefix="scc-test-") as td:
            repo = _temp_repo(Path(td))
            gen = CHECKER.load_generator(repo)
            validator = repo / CHECKER.ARCH_SKILL_REL / "scripts" / "validate_architecture_docs.py"
            text = validator.read_text(encoding="utf-8")
            derived = ('VALID_ARCHITECTURE_KINDS = {k for k in '
                       '_INLINE_CORE["doc-kind"]["values"] if k.startswith("architecture-")}')
            self.assertIn(derived, text, "validator derivation line changed; update this probe")
            text = text.replace(
                derived,
                'VALID_ARCHITECTURE_KINDS = {"architecture-overview", "architecture-map"}',
                1,
            )
            validator.write_text(text, encoding="utf-8")
            errors = CHECKER.check_canary(repo, gen)
            self.assertTrue(any("hardcoded" in e or "still rejected" in e for e in errors), errors)


class CIWiringContract(unittest.TestCase):
    """Roadmap 1-2-7: the three checks must actually run in the required CI
    job on every push / pull_request. A check nobody calls is a check that
    silently rots — this pins the seam between the script and the workflow.
    """

    def _workflow(self) -> str:
        return WORKFLOW.read_text(encoding="utf-8")

    def _required_job_block(self) -> str:
        body = self._workflow()
        job = body.split("jobs:", 1)[1]
        # closure-lint is the first job; slice up to the next top-level job.
        start = job.index("closure-lint:")
        rest = job[start + len("closure-lint:"):]
        nxt = rest.find("\n  docs-")
        return rest if nxt == -1 else rest[:nxt]

    def test_required_job_calls_the_consistency_check(self) -> None:
        self.assertIn("check-shared-conventions.py", self._required_job_block(),
                      "required job does not run the shared-conventions checks")

    def test_check_is_invoked_with_explicit_root(self) -> None:
        block = self._required_job_block()
        self.assertIn("check-shared-conventions.py --root .", block,
                      "check must be anchored to repo root, not implicit cwd")

    def test_all_three_check_names_are_visible_in_ci_step(self) -> None:
        # The script's docstring names the checks; keep those names discoverable
        # from the workflow comment so a future reader knows what the step guards.
        block = self._required_job_block()
        for name in ("closed-schema", "byte-equal", "canary"):
            self.assertIn(name, block, f"CI step does not advertise the {name!r} check")

    def test_required_job_stays_unfiltered(self) -> None:
        head = self._workflow().split("jobs:", 1)[0]
        self.assertNotIn("paths:", head,
                         "a path-filtered required check blocks unrelated PRs (#211)")


if __name__ == "__main__":
    unittest.main()
