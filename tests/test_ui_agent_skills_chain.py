"""Evidence for 1-6-5: the resolver contract and the closed-loop orchestrator.

Two surfaces are asserted, both matching `resolver-contract.md`
and `stage-engine.md §6/§8` (skills/ui/zj-ui-core/contracts/):

* The resolver's hard gates (R4 owner conflict, R5 ambiguity, R3 unsupported
  capability, R6 human gate) actually freeze a plan with `permitted_writes == 0`
  and a stable `plan_hash`.
* The orchestrator wires the ten stages into one loop: `PLANNED -> execute`,
  freeze or non-OK stops with zero downstream writes, and the three checked-in
  chain fixtures (normal / conflict / fail) all match.

Anti-false-green: `plan_hash` is replayed 100x and compared byte-for-byte, the
registry is asserted to pass its own static check, and the chain fixtures are
counted and matched to a declared inventory.
"""

import json
import pathlib
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
CORE_SCRIPTS = REPO / "skills/ui/zj-ui-core/scripts"
CHAIN_FIXTURES = REPO / "tests/ui-agent-skills/fixtures/chain"

sys.path.insert(0, str(CORE_SCRIPTS))

import run_chain_fixture  # noqa: E402
import ui_chain  # noqa: E402
import ui_registry as reg  # noqa: E402
import ui_resolver as res  # noqa: E402
import ui_skill_core as core  # noqa: E402


EXPECTED_CHAIN_FIXTURES = {
    "CHAIN-NORMAL-01": "OK",
    "CHAIN-CONFLICT-01": "FROZEN",
    "CHAIN-FAIL-01": "STOPPED",
}


def load(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def chain_fixture_dirs():
    return sorted(path.parent for path in CHAIN_FIXTURES.rglob("input.json"))


# --------------------------------------------------------------------------- #
# Resolver gates (FF-ORCH-01 / 04 / 05, G-1 / G-4 / G-7)
# --------------------------------------------------------------------------- #


def _two_write_owners_registry():
    """Two write owners for the `brief` artifact -> R4 BLOCKED_OWNER_CONFLICT."""
    base = reg.MANIFESTS
    briefs = [m for m in base if m["stage"] == "brief"]
    evild = dict(briefs[0])
    evild = dict(evild)
    evild["skill_id"] = "zj-ui-brief-evil"
    others = [m for m in base if m["stage"] != "brief"]
    return others + briefs + [evild]


def _ambiguous_registry():
    """Two emit-only `prototype` candidates with equal precedence -> R5 AMBIGUOUS."""
    base = reg.MANIFESTS
    proto = next(m for m in base if m["stage"] == "prototype")
    a = dict(proto); a["skill_id"] = "zj-ui-proto-a"; a["owner_scope"] = "emit"; a["writes"] = []; a["precedence"] = 60
    b = dict(proto); b["skill_id"] = "zj-ui-proto-b"; b["owner_scope"] = "emit"; b["writes"] = []; b["precedence"] = 60
    others = [m for m in base if m["stage"] != "prototype"]
    return others + [a, b]


class ResolverGates(unittest.TestCase):
    def test_registry_passes_its_own_static_check(self):
        clean, problems = reg.registry_static_check(reg.MANIFESTS)
        self.assertEqual(problems, [])
        self.assertEqual(len(clean), 10)

    def test_get_registry_does_not_raise(self):
        self.assertEqual(len(reg.get_registry()), 10)

    def test_ff_orch_01_owner_conflict_freezes(self):
        plan = res.resolve({}, {}, _two_write_owners_registry(), res.GATE_APPROVED, target_stage="brief")
        self.assertEqual(plan["status"], res.FROZEN_CONFLICT)
        self.assertIn("BLOCKED_OWNER_CONFLICT", plan["reason"])
        self.assertEqual(plan["permitted_writes"], 0)

    def test_ff_orch_04_precedence_tie_is_ambiguous(self):
        plan = res.resolve({}, {}, _ambiguous_registry(), res.GATE_APPROVED, target_stage="prototype")
        self.assertEqual(plan["status"], res.AMBIGUOUS)
        self.assertEqual(plan["permitted_writes"], 0)

    def test_ff_orch_05_unsupported_input(self):
        # No candidate for an unregistered stage.
        plan = res.resolve({}, {}, reg.MANIFESTS, res.GATE_APPROVED, target_stage="nonexistent")
        self.assertEqual(plan["status"], res.UNSUPPORTED_INPUT)
        # All candidates eliminated by missing capability. An empty list is
        # falsy and falls back to "all capabilities", so pass a non-empty but
        # insufficient set to actually drive the elimination.
        plan2 = res.resolve(
            {"available_capabilities": ["unrelated_cap"]}, {}, reg.MANIFESTS, res.GATE_APPROVED, target_stage="flow"
        )
        self.assertEqual(plan2["status"], res.UNSUPPORTED_INPUT)
        self.assertEqual(plan2["permitted_writes"], 0)

    def test_g1_route_fingerprint_is_deterministic_and_request_id_blind(self):
        req_a = {"foo": "bar", "request_id": "xyz"}
        req_b = {"foo": "bar", "request_id": "different"}
        fp_a = res.route_fingerprint(
            res.canonicalize_request(req_a, {}), {}, {"x": "0.1.0"}, "pv", res.GATE_APPROVED
        )
        fp_b = res.route_fingerprint(
            res.canonicalize_request(req_b, {}), {}, {"x": "0.1.0"}, "pv", res.GATE_APPROVED
        )
        self.assertEqual(fp_a, fp_b)

    def test_g4_plan_hash_changes_when_route_fingerprint_changes(self):
        # `flow` is human_gate=none, so both gate states stay PLANNED but the
        # route_fingerprint (which includes gate_state) differs -> plan_hash differs.
        p_approved = res.resolve({}, {}, reg.MANIFESTS, res.GATE_APPROVED, target_stage="flow")
        p_pending = res.resolve({}, {}, reg.MANIFESTS, res.GATE_PENDING, target_stage="flow")
        self.assertEqual(p_approved["status"], res.PLANNED)
        self.assertEqual(p_pending["status"], res.PLANNED)
        self.assertNotEqual(p_approved["plan_hash"], p_pending["plan_hash"])

    def test_g7_frozen_plan_permits_zero_writes(self):
        plan = res.resolve({}, {}, reg.MANIFESTS, res.GATE_PENDING, target_stage="direction")
        self.assertEqual(plan["status"], res.WAITING_FOR_HUMAN)
        self.assertEqual(plan["permitted_writes"], 0)
        self.assertEqual(plan["plan_hash"], "")

    def test_g2_plan_hash_is_byte_stable_over_100_replays(self):
        hashes = {
            res.resolve({}, {}, reg.MANIFESTS, res.GATE_APPROVED, target_stage=stage)["plan_hash"]
            for stage in reg.CHAIN_ORDER
        }
        self.assertTrue(all(hashes))
        for stage in reg.CHAIN_ORDER:
            seen = {
                res.resolve({}, {}, reg.MANIFESTS, res.GATE_APPROVED, target_stage=stage)["plan_hash"]
                for _ in range(100)
            }
            self.assertEqual(len(seen), 1, f"{stage}: plan_hash not stable across replays")


# --------------------------------------------------------------------------- #
# Closed-loop orchestrator (chain fixtures + anti-false-green)
# --------------------------------------------------------------------------- #


class ChainFixtureInventory(unittest.TestCase):
    def test_every_declared_chain_fixture_exists_with_both_files(self):
        found = {directory.name: directory for directory in chain_fixture_dirs()}
        self.assertEqual(sorted(found), sorted(EXPECTED_CHAIN_FIXTURES))
        for name, directory in found.items():
            with self.subTest(fixture=name):
                self.assertTrue((directory / "input.json").is_file())
                self.assertTrue((directory / "expected.json").is_file())
                expected = load(directory / "expected.json")
                # refuse empty expectations (anti-false-green)
                self.assertGreaterEqual(len(expected), 4, f"{name} expectation too thin")

    def test_every_chain_fixture_matches_its_expectation(self):
        failures = []
        for directory in chain_fixture_dirs():
            report = run_chain_fixture.run_chain_fixture(directory)
            if report["problems"]:
                failures.append(f"{report['fixture_id']}: {report['problems']}")
        self.assertEqual(failures, [])

    def test_chain_harness_exit_code_reflects_success(self):
        import io
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            code = run_chain_fixture.main(
                ["run_chain_fixture.py", str(CHAIN_FIXTURES), "--recursive"]
            )
        self.assertEqual(code, 0)


class ChainClosedLoop(unittest.TestCase):
    def test_normal_chain_closes_to_handoff(self):
        request = load(CHAIN_FIXTURES / "CHAIN-NORMAL-01" / "input.json")
        outcome = ui_chain.run_chain(request)
        self.assertEqual(outcome["chain_status"], "OK")
        self.assertIsNone(outcome["stopped_at"])
        self.assertEqual(outcome["total_writes"], 10)
        self.assertEqual(len(outcome["plan_hashes"]), 10)
        self.assertEqual(outcome["produced_artifacts"][-1], core.HANDOFF)

    def test_conflict_chain_freezes_with_zero_downstream_writes(self):
        request = load(CHAIN_FIXTURES / "CHAIN-CONFLICT-01" / "input.json")
        outcome = ui_chain.run_chain(request)
        self.assertEqual(outcome["chain_status"], "FROZEN")
        self.assertEqual(outcome["stopped_at"], "direction")
        self.assertEqual(outcome["total_writes"], 2)  # only brief + discover
        # downstream of the freeze (direction..handoff) produced nothing
        self.assertNotIn(core.HANDOFF, outcome["produced_artifacts"])

    def test_fail_chain_stops_before_handoff(self):
        request = load(CHAIN_FIXTURES / "CHAIN-FAIL-01" / "input.json")
        outcome = ui_chain.run_chain(request)
        self.assertEqual(outcome["chain_status"], "STOPPED")
        self.assertEqual(outcome["stopped_at"], "design_system")
        self.assertEqual(outcome["total_writes"], 3)
        self.assertNotIn(core.HANDOFF, outcome["produced_artifacts"])

    def test_chain_plan_hashes_stable_over_100_runs(self):
        request = load(CHAIN_FIXTURES / "CHAIN-NORMAL-01" / "input.json")
        seen = {tuple(ui_chain.run_chain(request)["plan_hashes"]) for _ in range(100)}
        self.assertEqual(len(seen), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
