"""Evidence for the adapter invocation seam (1-7-5 预置基建).

Proves the three-layer test-subject split actually holds:

* L1 真实运行时（Storybook）能在 seam 上产出真实 outcome；
* L2 故障注入的**保真度**由真实包络形状比对证明，不是自说自话；
* L3 无运行时 adapter 被**声明式排除**，且 deny-first（未声明 = 报错，非静默 skip）；
* 回退矩阵与本地恢复不变量的断言**不会因空集合而假绿**。

刻意不断网、不真的让远程失败：Storybook 是离线确定性引擎，本仓库无法真实观测
这两类故障。``test_network_and_remote_are_seam_contract_only`` 把这个局限写成断言，
防止后人误读为「已真实验证」。
"""

import json
import pathlib
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
CORE_SCRIPTS = REPO / "skills/ui/zj-ui-core/scripts"
ADAPTER_DIR = CORE_SCRIPTS / "adapters"
FIXTURES = REPO / "tests/ui-agent-skills/fixtures/adapters"

sys.path.insert(0, str(REPO / "tests"))
sys.path.insert(0, str(CORE_SCRIPTS))
sys.path.insert(0, str(ADAPTER_DIR))

import storybook_adapter as adapter  # noqa: E402
import ui_skill_core as core  # noqa: E402
import ui_agent_skills_adapter_seam as seam  # noqa: E402
from ui_agent_skills_registry_fixture import ResettableRegistryFixture  # noqa: E402

REGISTRY_SNAPSHOT = FIXTURES / "registry/main-registry.snapshot.json"


def load_request(fixture_id="FF-SB-01"):
    path = FIXTURES / fixture_id / "input.json"
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)["request"]


def load_registry():
    with REGISTRY_SNAPSHOT.open(encoding="utf-8") as handle:
        return json.load(handle)


class SimulatedConnectionError(Exception):
    """Stands in for a real transport error; ``__module__`` is patched below so
    the classifier sees a transport-flavoured name."""


SimulatedConnectionError.__module__ = "http.client"
SimulatedConnectionError.__qualname__ = "ConnectionError"


class OutcomeTaxonomy(unittest.TestCase):
    def test_outcome_classes_map_to_spec_fallback_keys(self):
        self.assertEqual(
            set(seam.FALLBACK_KEY),
            {seam.OUTCOME_FAILURE, seam.OUTCOME_NETWORK_LOSS, seam.OUTCOME_REMOTE_FAILURE},
            "只有三类故障有回退键；成功路径不应被折叠进回退矩阵",
        )
        self.assertEqual(
            seam.FALLBACK_KEY[seam.OUTCOME_FAILURE], "on_failure",
        )
        self.assertEqual(
            seam.FALLBACK_KEY[seam.OUTCOME_NETWORK_LOSS], "on_network_loss",
        )
        self.assertEqual(
            seam.FALLBACK_KEY[seam.OUTCOME_REMOTE_FAILURE], "on_remote_failure",
        )

    def test_network_and_remote_are_seam_contract_only(self):
        """诚实账本：这两类在本仓库无真实运行时支撑，不得声称已真实验证。"""
        self.assertEqual(
            set(seam.SEAM_CONTRACT_ONLY),
            {seam.OUTCOME_NETWORK_LOSS, seam.OUTCOME_REMOTE_FAILURE},
        )
        self.assertTrue(set(seam.SEAM_CONTRACT_ONLY).isdisjoint(seam.REAL_RUNTIME_BACKED))
        self.assertEqual(set(seam.REAL_RUNTIME_BACKED), {seam.OUTCOME_OK, seam.OUTCOME_FAILURE})

    def test_unknown_outcome_class_is_rejected(self):
        with self.assertRaises(ValueError):
            seam.AdapterOutcome("x", "totally-made-up")


class RealRuntimeSeam(unittest.TestCase):
    def test_storybook_success_is_seam_ok(self):
        driver = seam.RealAdapterSeam("storybook-local-verify", adapter.run)
        outcome = driver.invoke(load_request())
        self.assertEqual(outcome.outcome_class, seam.OUTCOME_OK)
        self.assertTrue(outcome.ok)
        self.assertIsNone(outcome.fallback_key, "成功路径没有回退动作")
        self.assertEqual(outcome.receipt_status, "OK")
        self.assertEqual(len(driver.calls), 1)

    def test_quarantined_receipt_does_not_become_a_seam_failure(self):
        """receipt 级 QUARANTINED ≠ seam 级故障，也不等于 adapter lifecycle quarantine。
        这正是 quarantine-disambiguation.md 在 seam 上的落地。"""
        request = load_request()
        request["candidate"].pop("fingerprint", None)
        driver = seam.RealAdapterSeam("storybook-local-verify", adapter.run)
        outcome = driver.invoke(request)
        self.assertEqual(outcome.outcome_class, seam.OUTCOME_OK, "调用本身完成了")
        self.assertEqual(outcome.receipt_status, core.QUARANTINED)
        self.assertNotEqual(outcome.receipt_status, "quarantine", "两级拼写不同")

    def test_adapter_exception_classifies_as_failure(self):
        def boom(_request):
            raise ValueError("malformed ui_flow")

        driver = seam.RealAdapterSeam("storybook-local-verify", boom)
        outcome = driver.invoke(load_request())
        self.assertEqual(outcome.outcome_class, seam.OUTCOME_FAILURE)
        self.assertEqual(outcome.fallback_key, "on_failure")
        self.assertIsNone(outcome.envelope)

    def test_transport_exception_classifies_as_network_loss(self):
        def boom(_request):
            raise SimulatedConnectionError("connection reset")

        driver = seam.RealAdapterSeam("storybook-local-verify", boom)
        outcome = driver.invoke(load_request())
        self.assertEqual(outcome.outcome_class, seam.OUTCOME_NETWORK_LOSS)
        self.assertEqual(outcome.fallback_key, "on_network_loss")


class SeamFidelity(unittest.TestCase):
    def test_simulated_envelope_matches_real_shape(self):
        real = adapter.run(load_request())
        simulated = seam.default_simulated_envelope("storybook-local-verify")
        seam.assert_seam_fidelity(real, simulated)

    def test_fidelity_guard_is_not_vacuous(self):
        """断言护栏真的会失败：抽掉一个 key / 改一个类型都必须被抓到。"""
        real = adapter.run(load_request())
        simulated = seam.default_simulated_envelope("storybook-local-verify")

        missing_key = dict(simulated)
        missing_key.pop("receipt")
        with self.assertRaises(AssertionError):
            seam.assert_seam_fidelity(real, missing_key)

        wrong_type = dict(simulated)
        wrong_type["stories"] = "login::idle"
        with self.assertRaises(AssertionError):
            seam.assert_seam_fidelity(real, wrong_type)


class FaultInjection(unittest.TestCase):
    def test_every_failure_class_is_injectable(self):
        checked = 0
        for outcome_class in (
            seam.OUTCOME_FAILURE,
            seam.OUTCOME_NETWORK_LOSS,
            seam.OUTCOME_REMOTE_FAILURE,
        ):
            with self.subTest(outcome=outcome_class):
                driver = seam.SimulatedAdapterSeam("sim-1", outcome=outcome_class)
                outcome = driver.invoke({"candidate": {}})
                self.assertEqual(outcome.outcome_class, outcome_class)
                self.assertIsNotNone(outcome.fallback_key)
                self.assertFalse(outcome.ok)
                checked += 1
        self.assertEqual(checked, 3, "三类故障必须全部被遍历，避免空循环假绿")

    def test_success_path_carries_receipt_status_orthogonally(self):
        driver = seam.SimulatedAdapterSeam(
            "sim-1", outcome=seam.OUTCOME_OK, receipt_status=core.QUARANTINED
        )
        outcome = driver.invoke({"candidate": {}})
        self.assertEqual(outcome.outcome_class, seam.OUTCOME_OK)
        self.assertEqual(outcome.receipt_status, core.QUARANTINED)

    def test_simulated_seam_rejects_unknown_outcome(self):
        with self.assertRaises(ValueError):
            seam.SimulatedAdapterSeam("sim-1", outcome="nope")


class InvocationSurface(unittest.TestCase):
    def test_every_registry_adapter_declares_its_surface(self):
        registry = load_registry()
        seam.assert_invocation_surface_declared(registry.keys())

    def test_deny_first_on_undeclared_adapter(self):
        with self.assertRaises(AssertionError) as ctx:
            seam.assert_invocation_surface_declared(["brand-new-adapter"])
        self.assertIn("brand-new-adapter", str(ctx.exception))

    def test_no_runtime_adapters_are_excluded(self):
        index = seam.load_invocation_surface_index()
        self.assertEqual(seam.runtime_capable_ids(index), ["storybook-local-verify"])
        self.assertEqual(seam.no_runtime_ids(index), ["a2ui", "json-render-core"])
        self.assertTrue(
            set(seam.no_runtime_ids(index)).isdisjoint(seam.runtime_capable_ids(index))
        )

    def test_no_runtime_adapters_are_those_without_a_projection_engine(self):
        registry = load_registry()
        for adapter_id in seam.no_runtime_ids():
            with self.subTest(adapter=adapter_id):
                self.assertIn(adapter_id, registry)
                reasons = " ".join(registry[adapter_id].get("risk") or [])
                self.assertTrue(reasons, "无运行时的事实必须在 manifest risk[] 里留痕")


class FallbackMatrix(unittest.TestCase):
    def test_matrix_is_complete_and_non_empty(self):
        combos = list(seam.iter_fallback_matrix())
        expected = len(seam.OUTCOME_CLASSES) * len(seam.VALID_LIFECYCLE)
        self.assertEqual(len(combos), expected, "矩阵必须完整（4 outcome × 4 生命周期 = 16）")
        self.assertGreater(len(combos), 0, "空矩阵会让门禁零次迭代却判 PASS")

    def test_every_manifest_resolves_an_action_for_every_failure_class(self):
        registry = load_registry()
        checked = 0
        for adapter_id, manifest in registry.items():
            for outcome_class in seam.FALLBACK_KEY:
                with self.subTest(adapter=adapter_id, outcome=outcome_class):
                    action = seam.expected_fallback_action(manifest, outcome_class)
                    self.assertIn(action, seam.FALLBACK_ACTIONS)
                    checked += 1
        self.assertEqual(checked, len(registry) * 3, "3 adapter × 3 故障类 = 9 组，不得少算")

    def test_success_path_has_no_fallback_action(self):
        registry = load_registry()
        with self.assertRaises(seam.BoundaryError):
            seam.expected_fallback_action(registry["storybook-local-verify"], seam.OUTCOME_OK)

    def test_missing_fallback_key_is_loud(self):
        registry = load_registry()
        broken = dict(registry["storybook-local-verify"])
        broken["fallback"] = {"on_failure": "local-verify"}
        with self.assertRaises(seam.BoundaryError):
            seam.expected_fallback_action(broken, seam.OUTCOME_NETWORK_LOSS)


class LocalRecovery(unittest.TestCase):
    def test_invariant_holds(self):
        snap = seam.CapabilitySnapshot(
            canonical=True, static_preview=True, local_verify=True,
            resolver_status="degraded",
        )
        seam.assert_local_recovery(snap)

    def test_missing_surface_fails_loudly(self):
        snap = seam.CapabilitySnapshot(
            canonical=True, static_preview=False, local_verify=True,
            resolver_status="success",
        )
        with self.assertRaises(seam.BoundaryError) as ctx:
            seam.assert_local_recovery(snap)
        self.assertIn("static_preview", str(ctx.exception))

    def test_resolver_crash_fails_r5(self):
        snap = seam.CapabilitySnapshot(
            canonical=True, static_preview=True, local_verify=True,
            resolver_status="crashed",
        )
        with self.assertRaises(seam.BoundaryError) as ctx:
            seam.assert_local_recovery(snap)
        self.assertIn("R5", str(ctx.exception))


class RegistryIntegration(unittest.TestCase):
    def test_removal_of_no_runtime_adapter_still_keeps_runtime_capable_one(self):
        """L3 adapter 被删：不污染主 registry，且真实运行时 adapter 不受影响。
        复用 1-7-5 预置的可重置夹具。"""
        fx = ResettableRegistryFixture(REGISTRY_SNAPSHOT)
        with fx.scope():
            for adapter_id in seam.no_runtime_ids():
                fx.remove(adapter_id)
            self.assertNotIn("json-render-core", fx.ids())
            self.assertNotIn("a2ui", fx.ids())
            self.assertIn("storybook-local-verify", fx.ids())
        self.assertEqual(sorted(fx.ids()), sorted(load_registry().keys()), "reset 后完全还原")


if __name__ == "__main__":
    unittest.main()
