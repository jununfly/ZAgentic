"""Evidence for 1-6-2: the S1..S4 stage skills actually refuse the things they claim.

The SKILL.md files promise behaviours that are easy to write and impossible to
falsify — "missing required field becomes NEEDS_CONTEXT with zero writes",
"unregistered field is rejected", "unknown keeps its quartet", "contrast failure
blocks and does not substitute a nearby colour". This file turns each promise into
a checked-in fixture plus a hand-written assertion, so the promise cannot drift
away from the implementation without turning something red.

Two deliberate anti-false-green measures:

* a fixture whose `expected.json` is empty would compare zero assertions and pass;
  `EachExpectationIsNotEmpty` fails on that.
* the fixtures are counted and matched to stages, so deleting a fixture directory
  cannot quietly reduce coverage to zero.
"""

import contextlib
import io
import json
import pathlib
import re
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
CORE_SCRIPTS = REPO / "skills/ui/zj-ui-core/scripts"
FIXTURES = REPO / "tests/ui-agent-skills/fixtures/skills"

sys.path.insert(0, str(CORE_SCRIPTS))

import run_fixture  # noqa: E402
import ui_skill_core as core  # noqa: E402
import ui_stages  # noqa: E402

EXPECTED_FIXTURES = {
    "FF-BRIEF-01": "brief",
    "FF-BRIEF-02": "brief",
    "FF-BRIEF-03": "brief",
    "FF-DISC-01": "discover",
    "FF-DISC-02": "discover",
    "FF-DISC-03": "discover",
    "FF-DIR-01": "direction",
    "FF-DIR-02": "direction",
    "FF-DIR-03": "direction",
    "FF-DS-01": "design_system",
    "FF-DS-02": "design_system",
    "FF-DS-03": "design_system",
}

REQUIRED_EXPECTATION_KEYS = ("status", "writes")


def load(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def fixture_dirs():
    return sorted(path.parent for path in FIXTURES.rglob("input.json"))


class FixtureInventory(unittest.TestCase):
    def test_every_documented_fixture_exists_with_both_files(self):
        found = {directory.name: directory for directory in fixture_dirs()}
        self.assertEqual(sorted(found), sorted(EXPECTED_FIXTURES))
        for name, directory in found.items():
            with self.subTest(fixture=name):
                self.assertTrue((directory / "input.json").is_file())
                self.assertTrue((directory / "expected.json").is_file())

    def test_declared_stage_has_an_implementation(self):
        found = {directory.name: directory for directory in fixture_dirs()}
        for name, stage in EXPECTED_FIXTURES.items():
            with self.subTest(fixture=name):
                self.assertEqual(load(found[name] / "input.json")["stage"], stage)
                self.assertIn(stage, ui_stages.STAGES)

    def test_skill_manifests_point_at_fixtures_that_exist(self):
        found = {directory.name for directory in fixture_dirs()}
        for stage in ui_stages.STAGES:
            with self.subTest(stage=stage):
                skill_md = REPO / "skills/ui" / f"zj-ui-{stage.replace('_', '-')}" / "SKILL.md"
                self.assertTrue(skill_md.is_file(), skill_md)
                declared = json.loads(
                    re.search(
                        r"^## Capability Manifest\s*\n+```json\n(.*?)\n```",
                        skill_md.read_text(encoding="utf-8"),
                        re.MULTILINE | re.DOTALL,
                    ).group(1)
                )["failure_fixtures"]
                self.assertEqual(len(declared), 3, declared)
                self.assertTrue(set(declared) <= found, f"{stage}: {set(declared) - found}")


class EachExpectationIsNotEmpty(unittest.TestCase):
    def test_every_expected_file_asserts_status_and_writes(self):
        for directory in fixture_dirs():
            with self.subTest(fixture=directory.name):
                expected = load(directory / "expected.json")
                for key in REQUIRED_EXPECTATION_KEYS:
                    self.assertIn(key, expected, f"{directory.name} does not pin {key}")
                # status+writes alone would let a mis-wired fixture pass; demand at
                # least one more structural assertion per case.
                self.assertGreaterEqual(len(expected), 4, f"{directory.name} is too thin")


class FixturesMatch(unittest.TestCase):
    def test_every_fixture_matches_its_expectation(self):
        directories = fixture_dirs()
        self.assertEqual(len(directories), len(EXPECTED_FIXTURES))
        failures = []
        for directory in directories:
            report = run_fixture.run_fixture(directory)
            if report["problems"]:
                failures.append(f"{report['fixture_id']}: {report['problems']}")
        self.assertEqual(failures, [])

    def test_runner_exit_code_reflects_failures(self):
        with contextlib.redirect_stdout(io.StringIO()):
            code = run_fixture.main(["run_fixture.py", str(FIXTURES), "--recursive"])
        self.assertEqual(code, 0)


class Invariants(unittest.TestCase):
    """Hand-written probes for the semantics a fixture can only sample."""

    def test_empty_list_is_a_gap_not_a_filled_field(self):
        # The classic false green: `goal_users: []` looks present in JSON but means
        # "we know nothing". Treating it as filled would silently close the gap.
        result = ui_stages.run_brief(
            {
                "input_revision": "rev-empty",
                "candidate": {
                    "goal_users": [],
                    "goal_task": "提交报销单",
                    "constraints": ["必须复用现有 SSO"],
                    "success_criteria": ["3 秒内看到状态"],
                },
            }
        )
        self.assertEqual(result["status"], core.NEEDS_CONTEXT)
        self.assertEqual(result["writes"], 0)
        self.assertEqual([entry["path"] for entry in result["unknown"]], ["goal_users"])

    def test_unknown_quartet_missing_a_key_is_rejected(self):
        result = ui_stages.run_brief(
            {
                "input_revision": "rev-quartet",
                "candidate": {
                    "goal_users": ["审批人"],
                    "goal_task": "提交报销单",
                    "constraints": ["SSO"],
                    "success_criteria": ["3 秒"],
                    "unknown": [{"path": "x", "raw": None, "reason": "缺 source"}],
                },
            }
        )
        self.assertEqual(result["status"], core.REJECTED)
        self.assertEqual(result["writes"], 0)
        self.assertIn("unknown[0]", [entry["field"] for entry in result["rejected"]])

    def test_idempotent_replay_writes_once_and_keeps_the_revision(self):
        request = load(FIXTURES / "FF-BRIEF-01/input.json")["request"]
        store = {}
        revisions = set()
        writes = 0
        for _ in range(100):
            result = ui_stages.run_brief(dict(request), store)
            self.assertEqual(result["status"], core.OK)
            writes += result["writes"]
            revisions.add(result["artifact"]["revision"])
        self.assertEqual(writes, 1, "replaying the same idempotency key must not write twice")
        self.assertEqual(len(revisions), 1)

    def test_same_key_with_different_content_is_rejected_not_overwritten(self):
        request = load(FIXTURES / "FF-BRIEF-01/input.json")["request"]
        store = {}
        ui_stages.run_brief(dict(request), store)
        tampered = json.loads(json.dumps(request))
        tampered["candidate"]["goal_task"] = "被改写过的任务"
        result = ui_stages.run_brief(tampered, store)
        self.assertEqual(result["status"], core.REJECTED)
        self.assertEqual(result["writes"], 0)

    def test_contrast_failure_does_not_substitute_a_nearby_colour(self):
        request = load(FIXTURES / "FF-DS-03/input.json")["request"]
        result = ui_stages.run_design_system(dict(request))
        self.assertEqual(result["status"], core.BLOCKED)
        self.assertIsNone(result["artifact"], "blocked runs must not hand back a fixed palette")
        self.assertEqual(request["tokens"]["color"]["on_surface"], "#777777")

    def test_contrast_maths_matches_wcag_reference_values(self):
        self.assertEqual(core.contrast_ratio("#000000", "#FFFFFF"), 21.0)
        self.assertEqual(core.contrast_ratio("#FFFFFF", "#FFFFFF"), 1.0)
        self.assertLess(core.contrast_ratio("#777777", "#FFFFFF"), core.CONTRAST_MIN)

    def test_unsourced_evidence_never_becomes_a_value(self):
        result = ui_stages.run_discover(
            {
                "brief_revision": "rev-x",
                "brief": {"goal_users": ["审批人"]},
                "evidence": [{"path": "goal_task", "value": "猜的", "source": ""}],
            }
        )
        self.assertEqual(result["status"], core.OK)
        self.assertNotIn("goal_task", result["artifact"]["content"])
        self.assertEqual(result["unknown"][0]["raw"], "猜的", "raw keeps the claim verbatim")


if __name__ == "__main__":
    unittest.main()
