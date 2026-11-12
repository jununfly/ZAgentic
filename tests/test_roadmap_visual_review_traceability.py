#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Spec -> executable-test traceability for the visual-review contract.

A spec id without a guard is an unenforced claim. This suite pins every
invariant / capability to an independently enumerated, executable test name,
and requires every unguarded id to be recorded with an explicit reason.

The mapping lives in `roadmap_viz_traceability.py` as an independent literal:
it is never recomputed from the spec or from the tests under test.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "codebase-docs" / "zj-roadmap-driven"
for entry in (str(REPO), str(SKILL)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from tests.roadmap_viz_traceability import (  # noqa: E402
    ACCEPTED_UNGOVERNED, MAX_UNGOVERNED, TRACEABILITY,
)

SPEC = REPO / "docs" / "designs" / "zj-roadmap-visual-review.spec.json"
WORKFLOW = REPO / ".github" / "workflows" / "skill-closure-lint.yml"


def _spec_ids() -> set[str]:
    data = json.loads(SPEC.read_text(encoding="utf-8"))
    return {item["id"] for item in data["invariants"]} | {
        item["id"] for item in data["capabilities"]
    }


def _leaf_case(suite):
    """Unwrap a TestSuite down to a single TestCase (or None)."""
    node = suite
    while isinstance(node, unittest.TestSuite):
        if not node._tests:
            return None
        node = node._tests[0]
    return node


class TraceabilityContract(unittest.TestCase):
    def test_every_spec_id_is_registered_and_no_extra_id_is_invented(self):
        self.assertEqual(_spec_ids(), set(TRACEABILITY),
                         "a new spec id must be registered with a guard or a reason")

    def test_every_registered_guard_is_a_real_executable_test(self):
        loader = unittest.TestLoader()
        for spec_id, names in TRACEABILITY.items():
            if names is None:
                continue
            self.assertTrue(names, f"{spec_id} registered an empty guard list")
            for name in names:
                with self.subTest(spec_id=spec_id, guard=name):
                    case = _leaf_case(loader.loadTestsFromName(name))
                    self.assertIsNotNone(case)
                    # loadTestsFromName returns a _FailedTest (count == 1) for
                    # a missing attribute: that would be a silent false green.
                    self.assertNotIn("_FailedTest", type(case).__name__)
                    self.assertIsInstance(case, unittest.TestCase)
                    self.assertTrue(hasattr(case, "runTest") or
                                    type(case).__name__.startswith("test_") or
                                    getattr(case, "_testMethodName", ""),
                                    f"{name} is not an executable test")


def _mapping_errors(mapping, spec_ids, ledger=None) -> list[str]:
    """The single checker used by both the real contract and negative probes."""
    accepted = ACCEPTED_UNGOVERNED if ledger is None else ledger
    errors: list[str] = []
    if set(mapping) != set(spec_ids):
        errors.append("E_ID_SET")
    ungoverned = [key for key, value in mapping.items() if value is None]
    if len(ungoverned) > MAX_UNGOVERNED:
        errors.append("E_TOO_MANY_UNGOVERNED")
    for spec_id in ungoverned:
        if len(accepted.get(spec_id, "")) < 30:
            errors.append("E_UNJUSTIFIED:" + spec_id)
    for spec_id in accepted:
        if spec_id not in mapping or mapping[spec_id] is not None:
            errors.append("E_STALE_LEDGER:" + spec_id)
    loader = unittest.TestLoader()
    for spec_id, names in mapping.items():
        if names is None:
            continue
        if not names:
            errors.append("E_EMPTY_GUARD:" + spec_id)
            continue
        for name in names:
            case = _leaf_case(loader.loadTestsFromName(name))
            if (case is None or "_FailedTest" in type(case).__name__
                    or not isinstance(case, unittest.TestCase)):
                errors.append("E_FAKE_GUARD:" + spec_id)
    return errors


class LedgerAndNegativeProbes(unittest.TestCase):
    def test_the_published_mapping_has_no_errors(self):
        self.assertEqual([], _mapping_errors(TRACEABILITY, _spec_ids()))

    def test_a_dropped_spec_id_is_detected(self):
        broken = dict(TRACEABILITY)
        broken.pop("INV::01")
        self.assertIn("E_ID_SET", _mapping_errors(broken, _spec_ids()))

    def test_a_guard_that_does_not_resolve_is_detected(self):
        broken = dict(TRACEABILITY)
        broken["INV::01"] = ("viz.tests.test_viz.NoSuchClass.no_such_test",)
        self.assertTrue(any(e.startswith("E_FAKE_GUARD")
                            for e in _mapping_errors(broken, _spec_ids())))

    def test_an_unjustified_unguarded_id_is_detected(self):
        broken = dict(TRACEABILITY)
        broken["INV::01"] = None
        self.assertTrue(any(e.startswith("E_UNJUSTIFIED")
                            for e in _mapping_errors(broken, _spec_ids())))

    def test_the_unguarded_set_cannot_grow_silently(self):
        broken = dict(TRACEABILITY)
        for spec_id in ("INV::02", "INV::05", "C::02", "C::03", "C::04", "C::06"):
            broken[spec_id] = None
        self.assertIn("E_TOO_MANY_UNGOVERNED", _mapping_errors(broken, _spec_ids()))

    def test_a_stale_ledger_entry_is_detected(self):
        # With the live ledger empty, an `any(...)` over it would be vacuously
        # true. Inject a deliberately stale entry so the probe still proves
        # the checker can fail (防假绿).
        fake = {"INV::01": "该判据已有可执行守卫，却仍被登记为未守卫，属于陈旧台账条目，必须报错。"}
        self.assertIn("E_STALE_LEDGER:INV::01",
                      _mapping_errors(TRACEABILITY, _spec_ids(), ledger=fake))

    def test_no_spec_id_is_left_ungoverned(self):
        self.assertEqual([], [key for key, value in TRACEABILITY.items()
                              if value is None])
        self.assertEqual({}, ACCEPTED_UNGOVERNED)
        self.assertEqual(0, MAX_UNGOVERNED)

    def test_required_ci_job_runs_this_guard(self):
        body = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("tests.test_roadmap_visual_review_traceability", body,
                      "the traceability guard is not executed by required CI")


if __name__ == "__main__":
    unittest.main()
