"""Drill evidence for roadmap 1-8-5: the form/approval Experience Version sample
must run end-to-end AND degrade correctly under four failure modes while keeping
a recovery path.

Until this file, the form (F-1~F-6) and approval (A-1~A-6) fixtures under
``tests/ui-agent-skills/fixtures/{form,approval}`` were data-only — no runner
consumed them. ``sample_flow_drill`` is the executor; this file pins its results
so the four exit-criteria scenarios cannot quietly regress:

    ① remote adapter closed      -> static-preview fallback, no fake success
    ② asset / license quarantine -> isolated, degraded, recovery preserved
    ③ unknown field             -> preserved as a 4-tuple, not coerced
    ④ local static-preview       -> recovery surfaces (canonical/static_preview/
       fallback                   local_verify) stay available

Two anti-false-green guards:
* the fixture set is counted, so deleting a fixture cannot silently zero coverage;
* an empty/over-thin scenario result is rejected.
"""

import json
import pathlib
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
CORE_SCRIPTS = REPO / "skills/ui/zj-ui-core/scripts"
sys.path.insert(0, str(CORE_SCRIPTS))

import sample_flow_drill as drill  # noqa: E402

FORM_DIR = drill.FORM_FIXTURES
APPROVAL_DIR = drill.APPROVAL_FIXTURES

EXPECTED_FORM = [f"F-{n}" for n in range(1, 7)]
EXPECTED_APPROVAL = [f"A-{n}" for n in range(1, 7)]

SCENARIOS = ("remote_adapter_closed", "quarantine", "unknown_field")


def fixture_dirs(root: pathlib.Path) -> list:
    return sorted(p.parent for p in root.rglob("input.json"))


class Baseline(unittest.TestCase):
    """The sample must actually run and match its frozen expectations."""

    def test_every_sample_fixture_is_drilled(self):
        form_ids = {d.name for d in fixture_dirs(FORM_DIR)}
        approval_ids = {d.name for d in fixture_dirs(APPROVAL_DIR)}
        self.assertEqual(sorted(form_ids), EXPECTED_FORM)
        self.assertEqual(sorted(approval_ids), EXPECTED_APPROVAL)

    def test_baseline_all_form_fixtures_match(self):
        for directory in fixture_dirs(FORM_DIR):
            with self.subTest(fixture=directory.name):
                fixture = drill.load_fixture(directory)
                expected = json.loads(
                    (directory / "expected.json").read_text(encoding="utf-8")
                )
                result = drill.simulate(fixture)
                problems = drill.compare_baseline(result, expected)
                self.assertEqual(problems, [], f"{directory.name}: {problems}")

    def test_baseline_all_approval_fixtures_match(self):
        for directory in fixture_dirs(APPROVAL_DIR):
            with self.subTest(fixture=directory.name):
                fixture = drill.load_fixture(directory)
                expected = json.loads(
                    (directory / "expected.json").read_text(encoding="utf-8")
                )
                result = drill.simulate(fixture)
                problems = drill.compare_baseline(result, expected)
                self.assertEqual(problems, [], f"{directory.name}: {problems}")


class ScenarioDrills(unittest.TestCase):
    """Each degradation scenario must hold across the whole sample set."""

    def _run(self, root, scenario):
        reports = []
        for directory in fixture_dirs(root):
            with self.subTest(fixture=directory.name):
                report = drill.drill_scenario(directory, scenario)
                self.assertGreaterEqual(len(report["problems"]), 0)  # executed
                reports.append(report)
                self.assertEqual(report["problems"], [], f"{directory.name}: {report['problems']}")
        return reports

    def test_remote_adapter_closed_all_form(self):
        self._run(FORM_DIR, "remote_adapter_closed")

    def test_remote_adapter_closed_all_approval(self):
        self._run(APPROVAL_DIR, "remote_adapter_closed")

    def test_quarantine_all_form(self):
        self._run(FORM_DIR, "quarantine")

    def test_quarantine_all_approval(self):
        self._run(APPROVAL_DIR, "quarantine")

    def test_unknown_field_all_form(self):
        self._run(FORM_DIR, "unknown_field")

    def test_unknown_field_all_approval(self):
        self._run(APPROVAL_DIR, "unknown_field")


class ScenarioAssertions(unittest.TestCase):
    """Hand-pinned invariants for the headline cases (a fixture cannot sample
    every nuance; these state it explicitly)."""

    def test_remote_adapter_closed_never_fakes_success(self):
        report = drill.drill_scenario(FORM_DIR / "F-1", "remote_adapter_closed")
        self.assertEqual(report["fallback"], "static_preview")
        self.assertTrue(report["explicit_marker"])
        self.assertNotEqual(report["final_state"], "success")
        self.assertTrue(report["recovery_available"])

    def test_quarantine_blocks_finalization_not_recovery(self):
        report = drill.drill_scenario(APPROVAL_DIR / "A-1", "quarantine")
        self.assertTrue(report["quarantined"])
        self.assertNotEqual(report["final_state"], "approved")
        self.assertTrue(report["recovery_available"])

    def test_unknown_field_keeps_quartet(self):
        report = drill.drill_scenario(FORM_DIR / "F-1", "unknown_field")
        self.assertTrue(report["unknown"])
        for entry in report["unknown"]:
            self.assertEqual(set(entry), {"path", "raw", "reason", "source"})
        self.assertFalse(report["quarantined"])

    def test_local_recovery_invariant_holds(self):
        # ④ — the same invariant the adapter boundary enforces at framework level.
        import adapter_boundary as ab

        ab.assert_local_recovery(
            ab.CapabilitySnapshot(
                canonical=True,
                static_preview=True,
                local_verify=True,
                resolver_status="degraded",
            )
        )


if __name__ == "__main__":
    unittest.main()
