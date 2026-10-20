"""Evidence for 1-7-3: the Storybook active local-verify adapter (B1) actually
enumerates stories and verifies the five dimensions, then delegates receipt
aggregation to `ui_stages.run_verify`.

The adapter is a *dependency* of `zj-ui-verify` (S9), not a chain `S` stage, so
it is driven directly here rather than through `run_fixture.STAGES`. The fixtures
under `tests/ui-agent-skills/fixtures/adapters/` are the regression assertions;
the hand-written probes cover the semantics a fixture can only sample (attribution
gate, no fake PASS, chain-field completeness, idempotency).
"""

import json
import pathlib
import re
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
CORE_SCRIPTS = REPO / "skills/ui/zj-ui-core/scripts"
ADAPTER_DIR = CORE_SCRIPTS / "adapters"
FIXTURES = REPO / "tests/ui-agent-skills/fixtures/adapters"

sys.path.insert(0, str(CORE_SCRIPTS))
sys.path.insert(0, str(ADAPTER_DIR))

import storybook_adapter as adapter  # noqa: E402
import ui_skill_core as core  # noqa: E402

CHAIN_FIELDS = ("claim", "threshold", "command", "commit", "fixture_hash",
                "env_hash", "artifact", "status")

EXPECTED_FIXTURES = {
    "FF-SB-01": "OK",
    "FF-SB-02": "BLOCKED",
    "FF-SB-03": "BLOCKED",
}


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


class FixturesMatch(unittest.TestCase):
    def test_every_fixture_matches_its_expectation(self):
        failures = []
        for directory in fixture_dirs():
            name = directory.name
            request = load(directory / "input.json")["request"]
            expected = load(directory / "expected.json")
            result = adapter.run(request)

            problems = []
            if result["adapter_id"] != expected["adapter_id"]:
                problems.append(f"adapter_id: {result['adapter_id']}")
            if result["status"] != expected["status"]:
                problems.append(f"status: expected {expected['status']}, got {result['status']}")
            if bool(result["receipt"] is not None) != expected["receipt_present"]:
                problems.append("receipt presence mismatch")
            if expected.get("stories_count") is not None:
                if len(result["stories"]) != expected["stories_count"]:
                    problems.append(
                        f"stories_count: expected {expected['stories_count']}, "
                        f"got {len(result['stories'])}"
                    )
            got_dims = {c["dimension"]: c["status"] for c in result["checks"]}
            for dim, want in expected.get("dimension_status", {}).items():
                if got_dims.get(dim) != want:
                    problems.append(f"{dim}: expected {want}, got {got_dims.get(dim)}")
            if expected.get("revision_is_sha256") and result["receipt"] is not None:
                revision = result["receipt"].get("revision", "")
                if not re.fullmatch(r"[0-9a-f]{64}", str(revision)):
                    problems.append(f"receipt revision not sha256: {revision!r}")
            if problems:
                failures.append(f"{name}: {problems}")
        self.assertEqual(failures, [])


class Invariants(unittest.TestCase):
    """Hand-written probes for the semantics a fixture can only sample."""

    def _normal_request(self):
        return load(FIXTURES / "FF-SB-01/input.json")["request"]

    def test_missing_fingerprint_is_quarantined_with_no_receipt(self):
        request = self._normal_request()
        request["candidate"]["fingerprint"] = {}
        result = adapter.run(request)
        self.assertEqual(result["status"], core.QUARANTINED)
        self.assertIsNone(result["receipt"], "attribution-less run must not yield a receipt")
        self.assertEqual(result["checks"], [])

    def test_every_check_carries_all_eight_chain_fields_and_evidence_new(self):
        result = adapter.run(self._normal_request())
        self.assertTrue(result["checks"], "must produce checks")
        for check in result["checks"]:
            with self.subTest(dimension=check["dimension"]):
                for field in CHAIN_FIELDS:
                    self.assertIn(field, check, f"{check['dimension']} missing {field}")
                self.assertTrue(check["evidence_new"], "must be real new evidence, not baseline")

    def test_checks_are_attributable_not_fake_pass(self):
        # The default engine derives evidence from canonical data; it must never
        # claim PASS on a check it could not actually evaluate.
        result = adapter.run(self._normal_request())
        self.assertEqual(result["status"], core.OK)
        for check in result["checks"]:
            self.assertEqual(check["status"], "PASS")

    def test_idempotent_run_yields_same_receipt_revision(self):
        request = self._normal_request()
        r1 = adapter.run(request)
        r2 = adapter.run(request)
        self.assertEqual(r1["receipt"]["revision"], r2["receipt"]["revision"])
        self.assertEqual(r1["receipt"]["revision"], r1["receipt"]["revision"])

    def test_stories_are_screen_times_state(self):
        result = adapter.run(self._normal_request())
        # 2 screens × 2 states = 4 stories, each "screen::state".
        self.assertEqual(len(result["stories"]), 4)
        self.assertTrue(all("::" in s for s in result["stories"]))

    def test_receipt_aggregates_the_five_dimension_checks(self):
        result = adapter.run(self._normal_request())
        self.assertIsNotNone(result["receipt"])
        dims = {c["dimension"] for c in result["receipt"]["content"]["checks"]}
        self.assertEqual(dims, set(adapter.DIMENSIONS))


if __name__ == "__main__":
    unittest.main()
