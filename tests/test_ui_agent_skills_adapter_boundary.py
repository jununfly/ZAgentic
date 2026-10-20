"""Evidence for the AdapterBoundary orchestration layer (roadmap 1-7-5, a1).

覆盖四个子节点：
* 1-7-5-1 边界 registry + 四态状态机（含 disabled/quarantine 调用守卫）
* 1-7-5-2 回退分发器（outcome_class → fallback action，接 seam 契约）
* 1-7-5-3 removal_test 执行器（R1–R5 + 本地恢复不变量）
* 1-7-5-4 端到端：删除 / 断网 / 远程故障三场景

防假绿：回退矩阵与 removal 循环都断言 `checked == 期望`；「永不调用」用
`seam.calls` 长度证明，而不是靠没抛错来推断。
"""

import copy
import json
import pathlib
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
CORE_SCRIPTS = REPO / "skills/ui/zj-ui-core/scripts"
FIXTURES = REPO / "tests/ui-agent-skills/fixtures/adapters"

sys.path.insert(0, str(REPO / "tests"))
sys.path.insert(0, str(CORE_SCRIPTS))

import adapter_boundary as boundary  # noqa: E402
from ui_agent_skills_adapter_seam import (  # noqa: E402
    SimulatedAdapterSeam,
)
from ui_agent_skills_registry_fixture import ResettableRegistryFixture  # noqa: E402

REGISTRY_SNAPSHOT = FIXTURES / "registry/main-registry.snapshot.json"


def load_registry():
    with REGISTRY_SNAPSHOT.open(encoding="utf-8") as handle:
        return json.load(handle)


def fresh_registry():
    """每次断言都拿一份干净的 registry —— 回退会改 lifecycle，必须隔离。"""
    return boundary.BoundaryRegistry(copy.deepcopy(load_registry()))


def healthy_probe(_adapter_id=None, _action=None):
    """回退后本地能力面仍然齐备的探针。"""
    return boundary.CapabilitySnapshot(
        canonical=True, static_preview=True, local_verify=True,
        resolver_status="degraded",
    )


def synthetic_manifest(**fallback):
    """合成 manifest，用于覆盖真实 snapshot 里没有的回退动作（degrade/disable/quarantine）。"""
    base = {
        "id": "synth-1",
        "role": "active-verify",
        "lifecycle": "active",
        "fallback": {
            "on_failure": fallback.get("on_failure", "static-preview"),
            "on_network_loss": fallback.get("on_network_loss", "static-preview"),
            "on_remote_failure": fallback.get("on_remote_failure", "static-preview"),
        },
        "removal_test": {"invariants": [{"id": r} for r in boundary.REMOVAL_INVARIANTS]},
    }
    return base


# ---------------------------------------------------------------------------
# 1-7-5-1 registry + 四态状态机
# ---------------------------------------------------------------------------
class LifecycleStateMachine(unittest.TestCase):
    def test_all_four_states_are_valid(self):
        reg = fresh_registry()
        checked = 0
        for state in boundary.VALID_LIFECYCLE:
            with self.subTest(state=state):
                reg.set_lifecycle("storybook-local-verify", state)
                self.assertEqual(reg.lifecycle("storybook-local-verify"), state)
                checked += 1
        self.assertEqual(checked, 4)

    def test_invalid_lifecycle_is_rejected(self):
        reg = fresh_registry()
        with self.assertRaises(boundary.BoundaryError):
            reg.set_lifecycle("storybook-local-verify", "removed")
        with self.assertRaises(boundary.BoundaryError):
            reg.set_lifecycle("storybook-local-verify", "QUARANTINED")

    def test_only_active_and_degraded_are_invocable(self):
        reg = fresh_registry()
        checked = 0
        for state, expected in (
            ("active", True), ("degraded", True),
            ("disabled", False), ("quarantine", False),
        ):
            with self.subTest(state=state):
                reg.set_lifecycle("storybook-local-verify", state)
                self.assertEqual(reg.invocable("storybook-local-verify"), expected)
                checked += 1
        self.assertEqual(checked, 4)

    def test_guard_invoke_blocks_disabled_and_quarantine(self):
        reg = fresh_registry()
        for state in ("disabled", "quarantine"):
            with self.subTest(state=state):
                reg.set_lifecycle("storybook-local-verify", state)
                with self.assertRaises(boundary.BoundaryError) as ctx:
                    reg.guard_invoke("storybook-local-verify")
                self.assertIn("never be invoked", str(ctx.exception))

    def test_unknown_adapter_is_loud(self):
        reg = fresh_registry()
        with self.assertRaises(boundary.BoundaryError):
            reg.manifest("nope-not-registered")


# ---------------------------------------------------------------------------
# 1-7-5-2 回退分发器
# ---------------------------------------------------------------------------
class FallbackDispatch(unittest.TestCase):
    def test_every_failure_class_resolves_an_action(self):
        reg = fresh_registry()
        manifest = reg.manifest("storybook-local-verify")
        checked = 0
        for outcome in boundary.FALLBACK_KEY:
            with self.subTest(outcome=outcome):
                action = boundary.dispatch_fallback(manifest, outcome)
                self.assertIn(action, boundary.FALLBACK_ACTIONS)
                checked += 1
        self.assertEqual(checked, 3)
        # Storybook 的声明：本地优先，网络/远程回落静态 preview
        self.assertEqual(
            boundary.dispatch_fallback(manifest, boundary.OUTCOME_FAILURE), "local-verify"
        )
        self.assertEqual(
            boundary.dispatch_fallback(manifest, boundary.OUTCOME_NETWORK_LOSS),
            "static-preview",
        )
        self.assertEqual(
            boundary.dispatch_fallback(manifest, boundary.OUTCOME_REMOTE_FAILURE),
            "static-preview",
        )

    def test_success_path_has_no_action(self):
        reg = fresh_registry()
        with self.assertRaises(boundary.BoundaryError):
            boundary.dispatch_fallback(
                reg.manifest("storybook-local-verify"), boundary.OUTCOME_OK
            )

    def test_missing_fallback_key_is_loud(self):
        with self.assertRaises(boundary.BoundaryError):
            boundary.dispatch_fallback(
                {"id": "x", "fallback": {"on_failure": "local-verify"}},
                boundary.OUTCOME_NETWORK_LOSS,
            )

    def test_lifecycle_mutating_actions_change_state(self):
        checked = 0
        for action, expected in (
            ("degrade", "degraded"), ("disable", "disabled"), ("quarantine", "quarantine"),
        ):
            with self.subTest(action=action):
                reg = boundary.BoundaryRegistry({"synth-1": synthetic_manifest()})
                new_state = reg.apply_fallback_action("synth-1", action)
                self.assertEqual(new_state, expected)
                self.assertEqual(reg.lifecycle("synth-1"), expected)
                checked += 1
        self.assertEqual(checked, 3)

    def test_capability_switch_actions_do_not_change_state(self):
        checked = 0
        for action in ("static-preview", "local-verify"):
            with self.subTest(action=action):
                reg = boundary.BoundaryRegistry({"synth-1": synthetic_manifest()})
                self.assertIsNone(reg.apply_fallback_action("synth-1", action))
                self.assertEqual(reg.lifecycle("synth-1"), "active")
                checked += 1
        self.assertEqual(checked, 2)


class OrchestrationInvoke(unittest.TestCase):
    def test_success_path_is_served_with_no_fallback(self):
        reg = fresh_registry()
        seam = SimulatedAdapterSeam("storybook-local-verify", outcome=boundary.OUTCOME_OK)
        decision = boundary.invoke(reg, seam, "storybook-local-verify", {"candidate": {}})
        self.assertTrue(decision.invoked)
        self.assertEqual(decision.outcome_class, boundary.OUTCOME_OK)
        self.assertIsNone(decision.action)
        self.assertEqual(decision.reason, "served")

    def test_quarantined_adapter_is_never_called(self):
        """「永不调用」用 seam.calls 长度证明，不靠没抛错推断。"""
        for state in ("disabled", "quarantine"):
            with self.subTest(state=state):
                reg = fresh_registry()
                reg.set_lifecycle("storybook-local-verify", state)
                seam = SimulatedAdapterSeam("storybook-local-verify")
                decision = boundary.invoke(
                    reg, seam, "storybook-local-verify", {"candidate": {}}
                )
                self.assertFalse(decision.invoked)
                self.assertEqual(len(seam.calls), 0, f"{state} adapter 被调用了")
                self.assertEqual(decision.reason, f"lifecycle-not-invocable:{state}")
                self.assertIsNone(decision.action)

    def test_failure_dispatches_declared_action(self):
        reg = fresh_registry()
        seam = SimulatedAdapterSeam(
            "storybook-local-verify", outcome=boundary.OUTCOME_FAILURE
        )
        decision = boundary.invoke(
            reg, seam, "storybook-local-verify", {"candidate": {}},
            capability_probe=healthy_probe,
        )
        self.assertEqual(decision.action, "local-verify")
        self.assertEqual(decision.reason, "fallback:local-verify")
        self.assertEqual(decision.lifecycle, "active", "local-verify 不改 lifecycle")

    def test_network_and_remote_fall_back_to_static_preview(self):
        checked = 0
        for outcome in (boundary.OUTCOME_NETWORK_LOSS, boundary.OUTCOME_REMOTE_FAILURE):
            with self.subTest(outcome=outcome):
                reg = fresh_registry()
                seam = SimulatedAdapterSeam("storybook-local-verify", outcome=outcome)
                decision = boundary.invoke(
                    reg, seam, "storybook-local-verify", {"candidate": {}},
                    capability_probe=healthy_probe,
                )
                self.assertEqual(decision.action, "static-preview")
                self.assertIsNotNone(decision.local_recovery)
                checked += 1
        self.assertEqual(checked, 2)

    def test_quarantine_action_moves_adapter_to_quarantine(self):
        reg = boundary.BoundaryRegistry(
            {"synth-1": synthetic_manifest(on_failure="quarantine")}
        )
        seam = SimulatedAdapterSeam("synth-1", outcome=boundary.OUTCOME_FAILURE)
        decision = boundary.invoke(
            reg, seam, "synth-1", {"candidate": {}}, capability_probe=healthy_probe
        )
        self.assertEqual(decision.action, "quarantine")
        self.assertEqual(decision.lifecycle, "quarantine")
        self.assertFalse(reg.invocable("synth-1"), "回退后应永不再被调用")

    def test_local_recovery_is_enforced_after_fallback(self):
        reg = fresh_registry()
        seam = SimulatedAdapterSeam(
            "storybook-local-verify", outcome=boundary.OUTCOME_NETWORK_LOSS
        )

        def broken_probe(_adapter_id, _action):
            return boundary.CapabilitySnapshot(
                canonical=True, static_preview=False, local_verify=True,
                resolver_status="success",
            )

        with self.assertRaises(boundary.BoundaryError) as ctx:
            boundary.invoke(
                reg, seam, "storybook-local-verify", {"candidate": {}},
                capability_probe=broken_probe,
            )
        self.assertIn("static_preview", str(ctx.exception))

    def test_unknown_outcome_class_is_rejected(self):
        reg = fresh_registry()

        class BadSeam:
            def invoke(self, _request):
                class O:
                    outcome_class = "totally-made-up"
                    receipt_status = None
                    error = None
                return O()

        with self.assertRaises(boundary.BoundaryError):
            boundary.invoke(reg, BadSeam(), "storybook-local-verify", {"candidate": {}})


# ---------------------------------------------------------------------------
# 1-7-5-3 removal_test 执行器
# ---------------------------------------------------------------------------
class RemovalExecutor(unittest.TestCase):
    def _probes(self, failing=()):
        return {
            rid: (lambda _a, rid=rid: rid not in failing)
            for rid in boundary.REMOVAL_INVARIANTS
        }

    def test_all_invariants_pass(self):
        reg = fresh_registry()
        executor = boundary.RemovalExecutor(reg, self._probes())
        result = executor.run("storybook-local-verify")
        self.assertTrue(result["ok"])
        self.assertEqual(result["failed"], [])
        self.assertFalse(result["residue"])
        self.assertEqual(len(result["invariants"]), 5)

    def test_failing_invariant_is_reported(self):
        reg = fresh_registry()
        executor = boundary.RemovalExecutor(reg, self._probes(failing=("R4",)))
        result = executor.run("storybook-local-verify")
        self.assertFalse(result["ok"])
        self.assertEqual(result["failed"], ["R4"])

    def test_missing_probe_is_rejected_at_construction(self):
        reg = fresh_registry()
        probes = self._probes()
        probes.pop("R5")
        with self.assertRaises(boundary.BoundaryError) as ctx:
            boundary.RemovalExecutor(reg, probes)
        self.assertIn("R5", str(ctx.exception))

    def test_removal_is_transient_and_leaves_no_state_bit(self):
        """§6.1：删除后 adapter 消失，不留 `removed` 状态位。"""
        reg = fresh_registry()
        removed = reg.remove("json-render-core")
        self.assertIsInstance(removed, dict)
        self.assertNotIn("json-render-core", reg.ids())
        self.assertNotIn("removed", removed)
        for manifest in (reg.manifest(i) for i in reg.ids()):
            self.assertNotIn("removed", manifest)

    def test_removal_of_absent_adapter_is_loud(self):
        reg = fresh_registry()
        reg.remove("a2ui")
        with self.assertRaises(boundary.BoundaryError):
            reg.remove("a2ui")

    def test_removal_does_not_pollute_the_base_snapshot(self):
        """接可重置夹具：执行器删掉的条目 reset 后必须原样回来。"""
        fx = ResettableRegistryFixture(REGISTRY_SNAPSHOT)
        with fx.scope():
            reg = boundary.BoundaryRegistry(fx.all())
            boundary.RemovalExecutor(reg, self._probes()).run("storybook-local-verify")
            self.assertNotIn("storybook-local-verify", reg.ids())
        self.assertIn("storybook-local-verify", fx.ids(), "base 被污染了")


# ---------------------------------------------------------------------------
# 1-7-5-4 端到端三场景
# ---------------------------------------------------------------------------
class EndToEndScenarios(unittest.TestCase):
    def _probes(self):
        return {rid: (lambda _a: True) for rid in boundary.REMOVAL_INVARIANTS}

    def test_scenario_removal(self):
        """删除 adapter → R1–R5 全过 → 其它 adapter 仍可服务。"""
        reg = fresh_registry()
        result = boundary.RemovalExecutor(reg, self._probes()).run("storybook-local-verify")
        self.assertTrue(result["ok"])
        self.assertEqual(result["failed"], [])
        self.assertTrue(reg.invocable("a2ui"), "删一个不影响其它")

    def test_scenario_network_loss(self):
        """断网 → static-preview → 本地三项能力面仍在（不真断网，走 seam 注入）。"""
        reg = fresh_registry()
        seam = SimulatedAdapterSeam(
            "storybook-local-verify", outcome=boundary.OUTCOME_NETWORK_LOSS
        )
        decision = boundary.invoke(
            reg, seam, "storybook-local-verify", {"candidate": {}},
            capability_probe=healthy_probe,
        )
        self.assertEqual(decision.action, "static-preview")
        self.assertTrue(decision.local_recovery["canonical"])
        self.assertTrue(decision.local_recovery["static_preview"])
        self.assertTrue(decision.local_recovery["local_verify"])
        self.assertEqual(decision.local_recovery["resolver_status"], "degraded")

    def test_scenario_remote_failure(self):
        """远程服务失败 → static-preview → 本地恢复不变量仍成立。"""
        reg = fresh_registry()
        seam = SimulatedAdapterSeam(
            "storybook-local-verify", outcome=boundary.OUTCOME_REMOTE_FAILURE
        )
        decision = boundary.invoke(
            reg, seam, "storybook-local-verify", {"candidate": {}},
            capability_probe=healthy_probe,
        )
        self.assertEqual(decision.action, "static-preview")
        self.assertIsNotNone(decision.local_recovery)

    def test_receipt_quarantine_stays_orthogonal_to_lifecycle(self):
        """seam 成功 + receipt QUARANTINED ≠ adapter lifecycle quarantine。"""
        reg = fresh_registry()
        seam = SimulatedAdapterSeam(
            "storybook-local-verify",
            outcome=boundary.OUTCOME_OK,
            receipt_status="QUARANTINED",
        )
        decision = boundary.invoke(reg, seam, "storybook-local-verify", {"candidate": {}})
        self.assertEqual(decision.outcome_class, boundary.OUTCOME_OK)
        self.assertEqual(decision.receipt_status, "QUARANTINED")
        self.assertEqual(decision.lifecycle, "active", "receipt 隔离不得写回 lifecycle")
        self.assertEqual(decision.action, None)

    def test_full_matrix_covers_every_outcome_and_lifecycle(self):
        """回退矩阵全遍历；不可调用状态必须产出 not-invoked 且零调用。"""
        checked = 0
        for outcome in boundary.OUTCOME_CLASSES:
            for lifecycle in boundary.VALID_LIFECYCLE:
                with self.subTest(outcome=outcome, lifecycle=lifecycle):
                    reg = fresh_registry()
                    reg.set_lifecycle("storybook-local-verify", lifecycle)
                    seam = SimulatedAdapterSeam(
                        "storybook-local-verify", outcome=outcome
                    )
                    decision = boundary.invoke(
                        reg, seam, "storybook-local-verify", {"candidate": {}},
                        capability_probe=healthy_probe,
                    )
                    if lifecycle in boundary.INVOCABLE_LIFECYCLE:
                        self.assertTrue(decision.invoked)
                        self.assertEqual(len(seam.calls), 1)
                        if outcome == boundary.OUTCOME_OK:
                            self.assertIsNone(decision.action)
                        else:
                            self.assertIn(decision.action, boundary.FALLBACK_ACTIONS)
                    else:
                        self.assertFalse(decision.invoked)
                        self.assertEqual(len(seam.calls), 0)
                    checked += 1
        self.assertEqual(
            checked,
            len(boundary.OUTCOME_CLASSES) * len(boundary.VALID_LIFECYCLE),
            "空矩阵会让门禁零次迭代却判 PASS",
        )


if __name__ == "__main__":
    unittest.main()
