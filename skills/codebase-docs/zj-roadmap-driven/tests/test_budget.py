"""case 1 契约测试：explore 节点的 budget（结构单位）与 exit_criteria。

主缝是 CLI 契约（参数 + stdout/stderr + 退出码），与 spec 的 Testing 决策一致：
同一套断言在 single-file 与 bundle 两个 carrier 上各跑一遍。

运行：python tests/test_budget.py
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
CLI = SKILL_DIR / "roadmap_cli.py"

E_BUDGET_EXCEEDED = "E_BUDGET_EXCEEDED"
BUDGET_EXIT_CODE = 3


class BudgetContractTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workdir = Path(self.tmp.name)
        self.roadmap = self.workdir / "roadmap.json"

    def tearDown(self):
        self.tmp.cleanup()

    # ── helpers ──────────────────────────────────────────

    def run_cli(self, *args, check=True):
        result = subprocess.run(
            [sys.executable, str(CLI), *map(str, args)],
            cwd=self.workdir,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if check and result.returncode != 0:
            self.fail(
                f"roadmap_cli failed with {result.returncode}\n"
                f"args: {args}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result

    def init_single(self, title="Budget roadmap"):
        self.run_cli("init", self.roadmap, "--title", title)

    def init_bundle(self, title="Bundle budget roadmap"):
        self.bundle = self.workdir / "roadmap.bundle"
        self.run_cli("init", self.bundle, "--storage", "bundle", "--title", title)
        return self.bundle

    def get_node(self, node_id, target=None):
        result = self.run_cli("get", target or self.roadmap, node_id)
        return json.loads(result.stdout)

    # ── max_children ─────────────────────────────────────

    def test_max_children_blocks_the_first_child_over_budget(self):
        self.init_single()
        self.run_cli("update", self.roadmap, "1", "--max-children", "2")
        self.run_cli("add", self.roadmap, "1", "first")
        self.run_cli("add", self.roadmap, "1", "second")

        result = self.run_cli("add", self.roadmap, "1", "third", check=False)

        self.assertEqual(result.returncode, BUDGET_EXIT_CODE)
        self.assertIn(E_BUDGET_EXCEEDED, result.stderr)
        # 断言没有副作用：第三个子节点没有落盘
        parent = self.get_node("1")
        self.assertEqual(parent["children"], ["1-1", "1-2"])

    def test_parent_without_budget_is_unbounded(self):
        """控制例：没有 budget 的父节点行为与今天完全一致。"""
        self.init_single()
        for name in ("first", "second", "third", "fourth"):
            self.run_cli("add", self.roadmap, "1", name)
        self.assertEqual(len(self.get_node("1")["children"]), 4)

    def test_max_children_zero_blocks_every_child(self):
        self.init_single()
        self.run_cli("update", self.roadmap, "1", "--max-children", "0")
        result = self.run_cli("add", self.roadmap, "1", "nope", check=False)
        self.assertEqual(result.returncode, BUDGET_EXIT_CODE)
        self.assertIn(E_BUDGET_EXCEEDED, result.stderr)

    def test_negative_max_children_is_rejected_as_invalid_input(self):
        """负数是参数错误（退出码 1），不是预算触顶（退出码 3）。"""
        self.init_single()
        result = self.run_cli("update", self.roadmap, "1", "--max-children", "-1", check=False)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(E_BUDGET_EXCEEDED, result.stderr)

    def test_clearing_budget_lifts_the_limit(self):
        self.init_single()
        self.run_cli("update", self.roadmap, "1", "--max-children", "1")
        self.run_cli("add", self.roadmap, "1", "first")
        self.run_cli("add", self.roadmap, "1", "second", check=False)

        self.run_cli("update", self.roadmap, "1", "--clear-budget")
        self.run_cli("add", self.roadmap, "1", "second")

        self.assertEqual(len(self.get_node("1")["children"]), 2)

    def test_shrinking_budget_does_not_reject_existing_children(self):
        """改小预算只约束未来新增，不追溯已有子节点。"""
        self.init_single()
        self.run_cli("add", self.roadmap, "1", "first")
        self.run_cli("add", self.roadmap, "1", "second")
        self.run_cli("update", self.roadmap, "1", "--max-children", "2")
        self.assertEqual(len(self.get_node("1")["children"]), 2)

    def test_add_can_set_budget_on_the_new_node(self):
        self.init_single()
        node = json.loads(self.run_cli(
            "add", self.roadmap, "1", "explore me", "--max-children", "3", "--max-rounds", "2"
        ).stdout)
        self.assertEqual(node["budget"], {"max_children": 3, "max_rounds": 2})

    # ── max_rounds ───────────────────────────────────────

    def test_max_rounds_blocks_reopening_a_node(self):
        self.init_single()
        self.run_cli("update", self.roadmap, "1", "--max-rounds", "1")
        self.run_cli("update", self.roadmap, "1", "--status", "completed")
        self.run_cli("update", self.roadmap, "1", "--status", "pending")

        result = self.run_cli("update", self.roadmap, "1", "--status", "in_progress", check=False)

        self.assertEqual(result.returncode, BUDGET_EXIT_CODE)
        self.assertIn(E_BUDGET_EXCEEDED, result.stderr)
        self.assertEqual(self.get_node("1")["status"], "pending")

    def test_max_rounds_allows_reopen_within_budget(self):
        self.init_single()
        self.run_cli("update", self.roadmap, "1", "--max-rounds", "2")
        self.run_cli("update", self.roadmap, "1", "--status", "completed")
        self.run_cli("update", self.roadmap, "1", "--status", "pending")
        self.run_cli("update", self.roadmap, "1", "--status", "in_progress")

        self.assertEqual(self.get_node("1")["rounds"], 2)

    def test_rounds_counter_starts_at_one_on_first_start(self):
        self.init_single()
        self.run_cli("update", self.roadmap, "1", "--max-rounds", "3")
        self.assertEqual(self.get_node("1").get("rounds"), 1)

    def test_node_without_max_rounds_can_reopen_freely(self):
        """控制例：没有 max_rounds 的节点可以任意重开。"""
        self.init_single()
        for _ in range(3):
            self.run_cli("update", self.roadmap, "1", "--status", "completed")
            self.run_cli("update", self.roadmap, "1", "--status", "pending")
            self.run_cli("update", self.roadmap, "1", "--status", "in_progress")
        self.assertEqual(self.get_node("1").get("rounds"), 4)

    # ── exit_criteria ────────────────────────────────────

    def test_exit_criteria_appends_and_clears(self):
        self.init_single()
        self.run_cli("update", self.roadmap, "1", "--exit-criteria", "三项对比跑完")
        self.run_cli("update", self.roadmap, "1", "--exit-criteria", "结论写进 decisions")
        self.assertEqual(
            self.get_node("1")["exit_criteria"], ["三项对比跑完", "结论写进 decisions"]
        )

        self.run_cli("update", self.roadmap, "1", "--clear-exit-criteria")
        self.assertEqual(self.get_node("1")["exit_criteria"], [])

    def test_exit_criteria_does_not_block_completion(self):
        """判据是给 Human/Agent 对照检查的，CLI 不做自然语言判定，因此不阻断完成。"""
        self.init_single()
        self.run_cli("update", self.roadmap, "1", "--exit-criteria", "压测通过")
        self.run_cli("update", self.roadmap, "1", "--status", "completed")
        self.assertEqual(self.get_node("1")["status"], "completed")

    # ── 两个 carrier 同一套契约 ───────────────────────────

    def test_bundle_carrier_enforces_the_same_budget_rule(self):
        bundle = self.init_bundle()
        self.run_cli("update", bundle, "1", "--max-children", "1")
        self.run_cli("add", bundle, "1", "first")

        result = self.run_cli("add", bundle, "1", "second", check=False)

        self.assertEqual(result.returncode, BUDGET_EXIT_CODE)
        self.assertIn(E_BUDGET_EXCEEDED, result.stderr)

    def test_bundle_carrier_records_exit_criteria(self):
        bundle = self.init_bundle()
        self.run_cli("update", bundle, "1", "--exit-criteria", "跑通 smoke")
        self.assertEqual(self.get_node("1", bundle)["exit_criteria"], ["跑通 smoke"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
