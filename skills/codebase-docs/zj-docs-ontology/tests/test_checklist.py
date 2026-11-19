#!/usr/bin/env python3
"""Regression tests for P0 Ruling 2 + 4: confirmation ledger and checklist.

The confirmation ledger is the confirmed proposal itself; `confirmation_id` is
a tool-computed hash, never an executor-supplied claim. The checklist's step
list is tool-derived, and a step marked done must be backed by an artifact.
Step 5's artifact path is declared by the tool, so an honest `skipped` status
still fires the existence ERROR (issue #264's actual case).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = SKILL_ROOT / "tests" / "fixtures"
REPO_ROOT = SKILL_ROOT.parents[2]
TMP = REPO_ROOT / "tmp" / "skills-outputs" / "zj-docs-ontology" / "_test_cases"
SCRIPT = SKILL_ROOT / "scripts" / "docs_governance.py"
SPEC = importlib.util.spec_from_file_location("docs_governance_checklist", SCRIPT)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)

TOPIC = "codebase-docs-redesign"
MAP_FIXTURE = FIXTURES / "existing-map"


def canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def write_case(name: str, *, with_proposal: bool = True, mutate: str | None = None) -> tuple[Path, Path, dict]:
    """Create an isolated pass case under the gitignored output zone."""
    base = TMP / name
    if base.exists():
        shutil.rmtree(base)
    case_dir = base / TOPIC
    case_dir.mkdir(parents=True)
    proposal = {
        "repository": str(MAP_FIXTURE.resolve()),
        "mode": "read-only-proposal",
        "map": "docs/team-map.md",
        "map_origin": "explicit-pointer",
        "diagnostics": [],
        "proposed_actions": [{"action": "create-map", "target": "docs/README.md"}],
        "mutations": [{"action": "create-map", "target": "docs/README.md"}],
        "read_paths": ["AGENTS.md", "docs/team-map.md"],
    }
    if with_proposal:
        (case_dir / "proposal.json").write_text(canonical(proposal), encoding="utf-8")
    cid = TOOL.confirmation_id(proposal)
    if mutate == "bad-id":
        cid = "0" * 64
    artifact = str(case_dir / "step-1.txt")
    (case_dir / "step-1.txt").write_text("step 1 evidence\n", encoding="utf-8")
    checklist = {
        "topic": TOPIC,
        "confirmation_id": cid,
        "steps": [
            {"step": 1, "status": "done", "artifact": artifact, "confirmation_id": cid},
            {"step": 2, "status": "pending", "artifact": None, "confirmation_id": cid},
            {"step": 3, "status": "pending", "artifact": None, "confirmation_id": cid},
            {"step": 4, "status": "pending", "artifact": None, "confirmation_id": cid},
            {
                "step": 5,
                "status": "pending",
                "artifact": str(case_dir / "architecture-validator.txt"),
                "fingerprint": None,
                "confirmation_id": cid,
            },
        ],
    }
    if mutate == "unbacked":
        checklist["steps"][0]["artifact"] = str(case_dir / "missing-artifact.txt")
    if mutate == "skip-honest":
        checklist["steps"][4]["status"] = "skipped"
    if mutate == "fp-mismatch":
        (case_dir / "architecture-validator.txt").write_text("real output\n", encoding="utf-8")
        checklist["steps"][4]["fingerprint"] = "0" * 64
    (case_dir / "checklist.json").write_text(canonical(checklist), encoding="utf-8")
    return base, case_dir, checklist


class TopicConventionTest(unittest.TestCase):
    def test_naming_core_topic_is_valid(self) -> None:
        self.assertTrue(TOOL.valid_topic("codebase-docs-redesign"))
        self.assertTrue(TOOL.valid_topic("knowledge-compounding-pass"))

    def test_date_sha_version_status_tokens_are_rejected(self) -> None:
        for topic in ("2026-11-18-foo", "foo-9f3c1ab", "foo-v2", "foo-done", "Foo-Bar", "foo_bar"):
            with self.subTest(topic=topic):
                self.assertFalse(TOOL.valid_topic(topic))


class ConfirmationIdTest(unittest.TestCase):
    def test_id_is_deterministic_over_canonical_proposal(self) -> None:
        proposal = {"b": 1, "a": 2}
        other_order = {"a": 2, "b": 1}
        self.assertEqual(TOOL.confirmation_id(proposal), TOOL.confirmation_id(other_order))
        expected = hashlib.sha256(canonical(proposal).encode("utf-8")).hexdigest()
        self.assertEqual(expected, TOOL.confirmation_id(proposal))

    def test_id_changes_when_a_mutation_changes(self) -> None:
        before = TOOL.confirmation_id({"mutations": [{"action": "a"}]})
        after = TOOL.confirmation_id({"mutations": [{"action": "b"}]})
        self.assertNotEqual(before, after)


class EmitChecklistTest(unittest.TestCase):
    def tearDown(self) -> None:
        if TMP.exists():
            shutil.rmtree(TMP)

    def run_cli(self, *args: str) -> tuple[int, dict]:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True, text=True,
        )
        return proc.returncode, json.loads(proc.stdout)

    def test_emit_writes_proposal_and_tool_derived_checklist(self) -> None:
        base = TMP / "emit"
        code, payload = self.run_cli(
            str(MAP_FIXTURE), "--proposal", "--topic", TOPIC,
            "--emit-checklist", "--out", str(base),
        )
        self.assertEqual(0, code)
        case_dir = base / TOPIC
        self.assertTrue((case_dir / "proposal.json").is_file())
        self.assertTrue((case_dir / "checklist.json").is_file())
        checklist = json.loads((case_dir / "checklist.json").read_text(encoding="utf-8"))
        proposal = json.loads((case_dir / "proposal.json").read_text(encoding="utf-8"))
        self.assertEqual(TOOL.confirmation_id(proposal), checklist["confirmation_id"])
        self.assertEqual([1, 2, 3, 4, 5], [s["step"] for s in checklist["steps"]])
        step5 = checklist["steps"][4]
        # Single basis (issue #275 defect A): the declared artifact is a bare
        # filename; inspect resolves it against the case dir.
        self.assertEqual("architecture-validator.txt", step5["artifact"])
        self.assertIsNone(step5["fingerprint"])


class ChecklistValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.base, self.case_dir, self.checklist = write_case("validate")

    def tearDown(self) -> None:
        if TMP.exists():
            shutil.rmtree(TMP)

    def inspect(self, base: Path | None = None) -> dict:
        return TOOL.inspect_checklist(base or self.base, TOPIC)

    def codes(self, result: dict) -> set[str]:
        return {item["code"] for item in result["diagnostics"]}

    def test_complete_checklist_has_no_diagnostic(self) -> None:
        (self.case_dir / "architecture-validator.txt").write_text("validator output\n", encoding="utf-8")
        result = self.inspect()
        self.assertEqual(set(), self.codes(result))

    def test_unbacked_done_step_is_an_error(self) -> None:
        base, _, _ = write_case("unbacked", mutate="unbacked")
        result = self.inspect(base)
        self.assertIn("EXEC_CHECKLIST_STEP_UNBACKED", self.codes(result))

    def test_confirmation_lost_is_a_signal(self) -> None:
        base, _, _ = write_case("lost", with_proposal=False)
        result = self.inspect(base)
        self.assertIn("CONFIRMATION_BASELINE_LOST", self.codes(result))
        self.assertNotIn("UNCONFIRMED_MUTATION", self.codes(result))

    def test_tampered_confirmation_id_is_an_error(self) -> None:
        base, _, _ = write_case("bad-id", mutate="bad-id")
        result = self.inspect(base)
        self.assertIn("UNCONFIRMED_MUTATION", self.codes(result))

    def test_honest_step5_skip_still_fires_existence_error(self) -> None:
        base, _, _ = write_case("skip", mutate="skip-honest")
        result = self.inspect(base)
        self.assertIn("EXEC_STEP5_ARTIFACT_MISSING", self.codes(result))

    def test_step5_fingerprint_mismatch_is_a_signal(self) -> None:
        base, _, _ = write_case("fp", mutate="fp-mismatch")
        result = self.inspect(base)
        self.assertIn("EXEC_STEP5_FINGERPRINT_MISMATCH", self.codes(result))
        self.assertNotIn("EXEC_STEP5_ARTIFACT_MISSING", self.codes(result))

    def test_checklist_is_the_only_witness_source(self) -> None:
        """When a checklist is supplied the CLI witness must not override it."""
        base, case_dir, _ = write_case("sole-source")
        (case_dir / "architecture-validator.txt").write_text("real\n", encoding="utf-8")
        result = TOOL.inspect_checklist(base, TOPIC, arch_witness="tmp/does-not-exist.txt")
        self.assertEqual(set(), self.codes(result))
        self.assertEqual(str(case_dir / "architecture-validator.txt"), result["witness"]["artifact"])


class ChecklistCommandLineTest(unittest.TestCase):
    def tearDown(self) -> None:
        if TMP.exists():
            shutil.rmtree(TMP)

    def exit_code(self, *args: str) -> int:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True, text=True,
        ).returncode

    def test_checklist_error_exits_nonzero(self) -> None:
        base, _, _ = write_case("cli-error", mutate="unbacked")
        self.assertNotEqual(
            0,
            self.exit_code(str(MAP_FIXTURE), "--validate", "--topic", TOPIC, "--out", str(base)),
        )

    def test_complete_checklist_exits_zero(self) -> None:
        base, case_dir, _ = write_case("cli-ok")
        (case_dir / "architecture-validator.txt").write_text("ok\n", encoding="utf-8")
        self.assertEqual(
            0,
            self.exit_code(str(MAP_FIXTURE), "--validate", "--topic", TOPIC, "--out", str(base)),
        )

    def test_invalid_topic_is_rejected(self) -> None:
        self.assertNotEqual(
            0,
            self.exit_code(str(MAP_FIXTURE), "--validate", "--topic", "foo-v2"),
        )


class BareValidateDisclosureTest(unittest.TestCase):
    """Issue #264 platform-layer C, tool-layer disclosure slice.

    A `validate` with no pass topic cannot check a checklist, so it must say so
    in the machine-readable report. Strength stays signal (exit 0): the tool
    cannot tell a shape-only check from a full pass that skipped its checklist,
    and escalating would punish legitimate shape-only checks. The *consumer*
    (CI / platform step-gate) decides whether to treat the signal as a gate.
    """

    def report(self, **kwargs: object) -> dict:
        return TOOL.report(MAP_FIXTURE, validate_links=True, **kwargs)

    def codes(self, payload: dict) -> set[str]:
        return {item["code"] for item in payload["diagnostics"]}  # type: ignore[union-attr]

    def test_bare_validate_discloses_absent_checklist(self) -> None:
        self.assertIn("EXEC_CHECKLIST_NOT_DECLARED", self.codes(self.report()))

    def test_disclosure_is_a_signal_not_a_gate(self) -> None:
        self.assertIn("EXEC_CHECKLIST_NOT_DECLARED", TOOL.SIGNAL_CODES)
        self.assertNotIn("EXEC_CHECKLIST_NOT_DECLARED", TOOL.ERROR_CODES)

    def test_disclosure_message_says_green_is_not_full_pass_evidence(self) -> None:
        item = next(
            i for i in self.report()["diagnostics"]
            if i["code"] == "EXEC_CHECKLIST_NOT_DECLARED"
        )
        self.assertIn("green", item["message"].lower())
        self.assertIn("checklist", item["message"].lower())

    def test_declared_topic_suppresses_disclosure_even_when_lost(self) -> None:
        """`CONFIRMATION_BASELINE_LOST` owns 'declared but missing'; the two
        codes are mutually exclusive by the report's branch structure."""
        payload = TOOL.report(
            MAP_FIXTURE, validate_links=True,
            topic=TOPIC, out=TMP / "no-such-case",
        )
        codes = self.codes(payload)
        self.assertIn("CONFIRMATION_BASELINE_LOST", codes)
        self.assertNotIn("EXEC_CHECKLIST_NOT_DECLARED", codes)

    def test_compatible_witness_without_topic_still_discloses(self) -> None:
        """--arch-witness is a Step 5 witness, not a checklist declaration."""
        payload = TOOL.report(
            MAP_FIXTURE, validate_links=True,
            arch_witness=str(MAP_FIXTURE / "AGENTS.md"),
        )
        self.assertIn("EXEC_CHECKLIST_NOT_DECLARED", self.codes(payload))

    def test_proposal_mode_has_no_disclosure(self) -> None:
        payload = TOOL.report(MAP_FIXTURE, validate_links=False)
        self.assertNotIn("EXEC_CHECKLIST_NOT_DECLARED", self.codes(payload))

    def test_bare_validate_reports_not_declared_checklist_status(self) -> None:
        payload = self.report()
        self.assertEqual("not-declared", payload["checklist"]["status"])
        self.assertIsNone(payload["checklist"]["topic"])


class BareValidateCommandLineTest(unittest.TestCase):
    def exit_code(self, *args: str) -> int:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True, text=True,
        ).returncode

    def test_bare_validate_exits_zero(self) -> None:
        self.assertEqual(0, self.exit_code(str(MAP_FIXTURE), "--validate"))

    def test_compatible_witness_still_exits_zero(self) -> None:
        self.assertEqual(
            0,
            self.exit_code(
                str(MAP_FIXTURE), "--validate",
                "--arch-witness", str(MAP_FIXTURE / "AGENTS.md"),
            ),
        )


class WitnessPathBasisTest(unittest.TestCase):
    """Issue #275 defect A: the emit-declared Step 5 path and the
    inspect-resolved path must be the same path (single basis: case_dir).

    The declared artifact is a bare filename resolved against the case dir.
    Regression covers both bases end-to-end: with an absolute `--out` the old
    double-join bug was invisible (absolute paths skip the join), while the
    documented relative workflow (SKILL.md:77-82) always reported
    `EXEC_STEP5_ARTIFACT_MISSING` with the witness sitting at the declared
    path. Falsifiable: remove the witness and the missing ERROR must return.
    """

    TOPIC_X = "witness-path-basis"

    def setUp(self) -> None:
        # Root-cause test hygiene (issue #275 follow-up): the CLI writes its
        # output zone under the governed repo root, so runs against the
        # tracked fixture would mutate it. Every run here targets a
        # throwaway clone; the shared fixture is never written.
        self._tmp = Path(tempfile.mkdtemp(prefix="witness-basis-"))
        self.fixture = self._tmp / "existing-map"
        shutil.copytree(MAP_FIXTURE, self.fixture)

    def tearDown(self) -> None:
        if TMP.exists():
            shutil.rmtree(TMP)
        shutil.rmtree(self._tmp, ignore_errors=True)

    def run_cli(self, *args: str, cwd: Path) -> tuple[int, dict]:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True, text=True, cwd=str(cwd),
        )
        self.assertTrue(proc.stdout.strip(), proc.stderr)
        return proc.returncode, json.loads(proc.stdout)

    def _roundtrip(self, out_arg: str, work: Path) -> tuple[int, str]:
        self.run_cli(
            str(self.fixture), "--proposal", "--topic", self.TOPIC_X,
            "--emit-checklist", "--out", out_arg, cwd=work,
        )
        # Fix 6 (issue #275): a relative --out anchors to the repo root, not
        # the launch directory (work). The absolute case is unchanged.
        out_base = Path(out_arg) if Path(out_arg).is_absolute() else self.fixture / out_arg
        case_dir = out_base / self.TOPIC_X
        checklist = json.loads(
            (case_dir / "checklist.json").read_text(encoding="utf-8")
        )
        declared = [s["artifact"] for s in checklist["steps"] if s["step"] == 5][0]
        # Executor side, single basis: the declared artifact resolves against
        # the case dir — the same basis inspect uses — so emit-declared path
        # and inspect-resolved path are the same path by construction.
        witness = Path(declared) if Path(declared).is_absolute() else case_dir / declared
        witness.write_text("validator output\n", encoding="utf-8")
        code, report = self.run_cli(
            str(MAP_FIXTURE), "--validate", "--topic", self.TOPIC_X,
            "--out", out_arg, cwd=work,
        )
        return code, declared

    def test_relative_out_declared_path_is_found(self) -> None:
        work = TMP / "witness-basis-rel"
        work.mkdir(parents=True)
        code, declared = self._roundtrip("out-rel", work)
        self.assertEqual("architecture-validator.txt", declared)
        self.assertEqual(0, code, "witness at the declared path must validate clean")

    def test_absolute_out_declared_path_is_found(self) -> None:
        work = TMP / "witness-basis-abs"
        work.mkdir(parents=True)
        code, declared = self._roundtrip(str(work / "out-abs"), work)
        self.assertEqual("architecture-validator.txt", declared)
        self.assertEqual(0, code, "witness at the declared path must validate clean")


if __name__ == "__main__":
    unittest.main()
