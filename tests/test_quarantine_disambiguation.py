"""Guard: spec `quarantine` (adapter lifecycle) ≠ receipt `QUARANTINED` (1-7-5 risk).

These assert the two near-homonyms are distinct, live in different namespaces, and
stay independent — so the 1-7-5 boundary orchestration layer can never silently
treat an adapter's *administrative* isolation as a *receipt* verdict, or vice versa.

See docs/designs/ui-agent-skills/quarantine-disambiguation.md for the prose.
"""
import json
import pathlib
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
CORE_SCRIPTS = REPO / "skills/ui/zj-ui-core/scripts"
ADAPTER_DIR = CORE_SCRIPTS / "adapters"
FIXTURES = REPO / "tests/ui-agent-skills/fixtures/adapters"

sys.path.insert(0, str(CORE_SCRIPTS))
sys.path.insert(0, str(ADAPTER_DIR))
sys.path.insert(0, str(REPO / "tests"))

import ui_skill_core as core  # noqa: E402
import storybook_adapter as adapter  # noqa: E402
from ui_agent_skills_registry_fixture import ResettableRegistryFixture  # noqa: E402

SCHEMA = REPO / "skills/ui/zj-ui-core/contracts/adapter-manifest.schema.json"
REGISTRY = FIXTURES / "registry/main-registry.snapshot.json"


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


class QuarantineDisambiguationTest(unittest.TestCase):
    def test_tokens_are_distinct_even_by_spelling(self):
        # adapter lifecycle value is the lowercase string "quarantine"
        # receipt status is the uppercase constant "QUARANTINED" (note the D)
        self.assertNotEqual(core.QUARANTINED, "quarantine")
        self.assertNotEqual(core.QUARANTINED, "quarantine".upper())  # "QUARANTINE" != "QUARANTINED"
        self.assertEqual(core.QUARANTINED, "QUARANTINED")

    def test_lifecycle_enum_excludes_receipt_status(self):
        schema = load(SCHEMA)
        lifecycle_enum = schema["properties"]["lifecycle"]["enum"]
        self.assertIn("quarantine", lifecycle_enum)
        # the receipt-level status is NOT a legal adapter lifecycle value
        self.assertNotIn("QUARANTINED", lifecycle_enum)
        self.assertNotIn("QUARANTINE", lifecycle_enum)

    def test_receipt_status_not_a_lifecycle_transition(self):
        # An adapter in active lifecycle can still emit a QUARANTINED receipt; the
        # two states are orthogonal. Drive the real adapter with no fingerprint.
        result = adapter.run({
            "candidate": {"ui_flow": {}, "design": {}, "break_cell": {}, "fingerprint": {}},
            "input_revision": "",
            "engine": "deterministic",
        })
        self.assertEqual(result["status"], core.QUARANTINED)
        # Yet the adapter's administrative lifecycle in the registry is untouched.
        fx = ResettableRegistryFixture(REGISTRY)
        self.assertEqual(fx.get("storybook-local-verify")["lifecycle"], "active")

    def test_setting_lifecycle_quarantine_does_not_touch_receipt_constants(self):
        fx = ResettableRegistryFixture(REGISTRY)
        # administrative isolation of a tool
        fx.set_lifecycle("a2ui", "quarantine")
        self.assertEqual(fx.get("a2ui")["lifecycle"], "quarantine")
        # the receipt-level verdict constant is a completely separate token
        self.assertEqual(core.QUARANTINED, "QUARANTINED")
        # and a quarantined adapter, if it were somehow invoked, could still only
        # ever report receipt-level verdicts — the lifecycle string is never a
        # receipt status.
        self.assertNotIn(fx.get("a2ui")["lifecycle"], (core.QUARANTINED, "OK", "FAIL"))

    def test_receipt_quarantine_is_transient_not_persisted_to_registry(self):
        fx = ResettableRegistryFixture(REGISTRY)
        before = fx.all()
        # A QUARANTINED run verdict has no side effect on the adapter registry.
        result = adapter.run({
            "candidate": {"ui_flow": {}, "design": {}, "break_cell": {}, "fingerprint": {}},
            "input_revision": "",
            "engine": "deterministic",
        })
        self.assertEqual(result["status"], core.QUARANTINED)
        self.assertEqual(fx.all(), before)  # registry unchanged across a quarantined run


if __name__ == "__main__":
    unittest.main()
