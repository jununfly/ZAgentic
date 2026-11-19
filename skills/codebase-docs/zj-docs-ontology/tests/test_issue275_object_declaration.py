"""Issue #275 Fix 1a: the object of governance is a first-class declaration.

Legacy behavior (L6): ``scope`` meant only the pass topic (the gitignored
checklist output directory). The boundary of *what is being governed* was
inferred from prompt wording, so the same "restructure the docs system"
request could mean the whole docs tree to one executor and a brand-new
ontology directory to another — a parallel second docs system with no
mechanical signal.

Fixed contract:
  - new CLI flag ``--object <declaration>``: the Human declares the governed
    object. A declaration that resolves to an existing directory under the
    repo root is recorded as the object boundary (``source: "declared"``);
    the raw declaration text travels with the report.
  - no ``--object`` → default ``docs`` under the governed repo root with
    ``source: "derived"`` — a derivable default, but never a silent one.
  - report top level gains two fields that split the ambiguity:
    ``object_of_governance`` (what is governed) and ``pass_topic`` (the
    checklist output key). ``scope`` no longer means two things.
This slice wires declaration *visibility* only; scan scoping is unchanged.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "docs_governance.py"
MAP = SKILL_ROOT / "tests" / "fixtures" / "existing-map"

TOOL_SPEC = importlib.util.spec_from_file_location("dg_object_decl", SCRIPT)
assert TOOL_SPEC and TOOL_SPEC.loader
TOOL = importlib.util.module_from_spec(TOOL_SPEC)
sys.modules[TOOL_SPEC.name] = TOOL
TOOL_SPEC.loader.exec_module(TOOL)


def run_cli(repo: Path, cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(repo), *args],
        capture_output=True, text=True, cwd=str(cwd),
    )


class ObjectOfGovernanceFieldTest(unittest.TestCase):
    """API level: the report always answers "what is the governed object?"."""

    def payload(self, repo: Path = MAP, **kwargs) -> dict:
        return TOOL.report(repo, validate_links=True, **kwargs)

    def test_default_object_is_derived_docs(self) -> None:
        payload = self.payload()
        block = payload["object_of_governance"]
        self.assertEqual(block["object"], "docs")
        self.assertEqual(block["source"], "derived")

    def test_derived_object_is_reported_not_silent(self) -> None:
        # Principle 1: a derivable default must be visible in the report.
        block = self.payload()["object_of_governance"]
        self.assertTrue(block.get("declared_by_default") is True)

    def test_declared_directory_is_recorded_as_declared(self) -> None:
        payload = self.payload(object="docs/designs")
        block = payload["object_of_governance"]
        self.assertEqual(block["object"], "docs/designs")
        self.assertEqual(block["source"], "declared")
        self.assertEqual(block["declaration"], "docs/designs")

    def test_declared_object_anchors_to_repo_root_not_cwd(self) -> None:
        # Fix 6's lesson applies to the object boundary too: the launch
        # directory is never an input.
        repo = MAP.resolve()
        block = TOOL.report(repo, validate_links=True, object="docs")["object_of_governance"]
        self.assertEqual(block["source"], "declared")

    def test_pass_topic_field_mirrors_the_topic(self) -> None:
        self.assertEqual(self.payload(topic="docs-redesign")["pass_topic"], "docs-redesign")
        self.assertIsNone(self.payload()["pass_topic"])

    def test_pass_topic_is_not_the_object(self) -> None:
        # The whole point of Fix 1a: the two facts stay two fields.
        payload = self.payload(topic="docs-redesign", object="docs")
        self.assertEqual(payload["pass_topic"], "docs-redesign")
        self.assertEqual(payload["object_of_governance"]["object"], "docs")


class ObjectDeclarationCliTest(unittest.TestCase):
    """CLI level: --object reaches the report; missing declared dir is a fact,
    not a crash; exit semantics are untouched by the declaration."""

    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="object-decl-"))
        self.repo = self._tmp / "existing-map"
        import shutil

        shutil.copytree(MAP, self.repo)
        self.launch_dir = self._tmp / "launch-dir"
        self.launch_dir.mkdir()

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    def report(self, *args: str) -> dict:
        proc = run_cli(self.repo, self.launch_dir, "--proposal", *args)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_cli_flag_lands_in_the_report(self) -> None:
        block = self.report("--object", "docs/designs")["object_of_governance"]
        self.assertEqual(block["source"], "declared")
        self.assertEqual(block["object"], "docs/designs")

    def test_missing_declared_directory_is_recorded_as_a_fact(self) -> None:
        # The tool does not guess a better object; it reports what was declared.
        block = self.report("--object", "docs/no-such-dir")["object_of_governance"]
        self.assertEqual(block["source"], "declared")
        self.assertEqual(block["object"], "docs/no-such-dir")
        self.assertFalse(block["exists"])

    def test_existing_declared_directory_records_existence(self) -> None:
        block = self.report("--object", "docs")["object_of_governance"]
        self.assertTrue(block["exists"])

    def test_declaration_does_not_change_exit_semantics(self) -> None:
        proc = run_cli(self.repo, self.launch_dir, "--validate", "--object", "docs")
        self.assertEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
