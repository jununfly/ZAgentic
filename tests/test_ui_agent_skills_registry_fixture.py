"""Tests for the resettable registry fixture (roadmap 1-7-5 removal isolation).

These prove the three guarantees the 1-7-5 removal/fallback tests depend on:

1. **Removal is transient and reversible in tests** — ``remove`` drops the entry,
   ``reset`` brings it back with no lingering ``removed`` state bit.
2. **The base / main registry is never mutated** — neither the caller's dict nor a
   loaded snapshot file is touched by test operations.
3. **Tests are independent** — two fixtures from the same base, or a context
   manager, keep one test's mutations from polluting the next.
"""
import json
import os
import pathlib
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests"))

from ui_agent_skills_registry_fixture import ResettableRegistryFixture  # noqa: E402

BASE = {
    "storybook-local-verify": {
        "id": "storybook-local-verify",
        "role": "active-verify",
        "lifecycle": "active",
        "fallback": {
            "on_failure": "local-verify",
            "on_network_loss": "static-preview",
            "on_remote_failure": "static-preview",
        },
        "removal_test": {
            "invariants": [
                {"id": "R1", "description": "canonical 可解析", "verify": "ui-flow/v1 解析"},
                {"id": "R2", "description": "静态 preview 可服务", "verify": "preview 构建"},
                {"id": "R3", "description": "本地验证可跑", "verify": "verify-local.sh"},
                {"id": "R4", "description": "无悬空引用", "verify": "grep registry"},
                {"id": "R5", "description": "resolver 仍可解析", "verify": "resolver 返回 degraded"},
            ]
        },
    },
    "json-render-core": {
        "id": "json-render-core",
        "role": "opt-in-projection",
        "lifecycle": "active",
        "fallback": {
            "on_failure": "static-preview",
            "on_network_loss": "static-preview",
            "on_remote_failure": "static-preview",
        },
        "removal_test": {"invariants": [
            {"id": "R1", "description": "canonical 可解析", "verify": "ui-flow/v1 解析"},
            {"id": "R2", "description": "静态 preview 可服务", "verify": "preview 构建"},
            {"id": "R3", "description": "本地验证可跑", "verify": "verify-local.sh"},
            {"id": "R4", "description": "无悬空引用", "verify": "grep registry"},
            {"id": "R5", "description": "resolver 仍可解析", "verify": "resolver 返回 degraded"},
        ]},
    },
    "a2ui": {
        "id": "a2ui",
        "role": "opt-in-protocol",
        "lifecycle": "active",
        "fallback": {
            "on_failure": "static-preview",
            "on_network_loss": "static-preview",
            "on_remote_failure": "static-preview",
        },
        "removal_test": {"invariants": [
            {"id": "R1", "description": "canonical 可解析", "verify": "ui-flow/v1 解析"},
            {"id": "R2", "description": "静态 preview 可服务", "verify": "preview 构建"},
            {"id": "R3", "description": "本地验证可跑", "verify": "verify-local.sh"},
            {"id": "R4", "description": "无悬空引用", "verify": "grep registry"},
            {"id": "R5", "description": "resolver 仍可解析", "verify": "resolver 返回 degraded"},
        ]},
    },
}


class ResettableRegistryFixtureTest(unittest.TestCase):
    def test_reset_restores_exact(self):
        fx = ResettableRegistryFixture(BASE)
        fx.set_lifecycle("a2ui", "quarantine")
        fx.remove("json-render-core")
        self.assertNotEqual(fx.all(), BASE)
        fx.reset()
        self.assertEqual(fx.all(), BASE)

    def test_removal_is_transient_and_reversible(self):
        fx = ResettableRegistryFixture(BASE)
        removed = fx.remove("a2ui")
        self.assertEqual(removed["id"], "a2ui")
        self.assertFalse(fx.has("a2ui"))
        # transient: reset brings it back, no removed state bit lingers
        fx.reset()
        self.assertTrue(fx.has("a2ui"))
        self.assertEqual(fx.get("a2ui")["lifecycle"], "active")

    def test_base_dict_never_mutated(self):
        fx = ResettableRegistryFixture(BASE)
        fx.remove("a2ui")
        fx.set_lifecycle("storybook-local-verify", "disabled")
        # the original dict passed in must be untouched
        self.assertIn("a2ui", BASE)
        self.assertEqual(BASE["storybook-local-verify"]["lifecycle"], "active")
        self.assertTrue(fx.base_equals(BASE))

    def test_get_returns_copy(self):
        fx = ResettableRegistryFixture(BASE)
        m = fx.get("a2ui")
        m["lifecycle"] = "quarantine"
        # mutating the returned copy must not affect the working store
        self.assertEqual(fx.get("a2ui")["lifecycle"], "active")

    def test_context_manager_resets_on_exit(self):
        fx = ResettableRegistryFixture(BASE)
        with fx.scope():
            fx.remove("a2ui")
            self.assertFalse(fx.has("a2ui"))
        self.assertTrue(fx.has("a2ui"))

    def test_context_manager_resets_on_exception(self):
        fx = ResettableRegistryFixture(BASE)
        with self.assertRaises(RuntimeError):
            with fx.scope():
                fx.remove("a2ui")
                raise RuntimeError("boom")
        self.assertTrue(fx.has("a2ui"))

    def test_lifecycle_mutation_isolated(self):
        fx = ResettableRegistryFixture(BASE)
        fx.set_lifecycle("a2ui", "degraded")
        self.assertEqual(fx.get("a2ui")["lifecycle"], "degraded")
        fx.reset()
        self.assertEqual(fx.get("a2ui")["lifecycle"], "active")

    def test_loads_from_snapshot_file_untouched(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(BASE, f)
            path = f.name
        try:
            fx = ResettableRegistryFixture(path)
            self.assertEqual(set(fx.ids()), set(BASE.keys()))
            # file is untouched
            with open(path, encoding="utf-8") as handle:
                reread = json.loads(handle.read())
            self.assertEqual(reread, BASE)
        finally:
            os.unlink(path)

    def test_independent_fixtures_from_same_base(self):
        fx1 = ResettableRegistryFixture(BASE)
        fx2 = ResettableRegistryFixture(BASE)
        fx1.remove("a2ui")
        self.assertFalse(fx1.has("a2ui"))
        self.assertTrue(fx2.has("a2ui"))

    def test_removal_keeps_other_adapters(self):
        # spirit of R1–R5: removing one adapter leaves the rest resolvable
        fx = ResettableRegistryFixture(BASE)
        fx.remove("a2ui")
        self.assertEqual(
            set(fx.ids()), {"storybook-local-verify", "json-render-core"}
        )
        fx.reset()
        self.assertEqual(set(fx.ids()), set(BASE.keys()))


if __name__ == "__main__":
    unittest.main()
