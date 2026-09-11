"""#80 — `blocked` / `blocked_reason` 读取时派生，永不落盘。

测试缝（本次确认）：
1. CLI 进程级 `get <node>` —— Agent 的真实入口，也是唯一能同时钉住"派生字段
   出现/消失"与退出码的缝；
2. 落盘内容（carrier 字节）—— 钉住"status 从未被写成 blocked"。派生字段只在
   读视图里，回读 JSON 输出看不见它是不是偷偷被存了；
3. `tree` / `section` 的渲染输出 —— Human 视图那道缝：`blocked` 必须显示成
   `[!]`，否则 md 里看到的是"没开工"而 `get` 里看到的是"被挡住"，两份视图打架；
4. 控制例 —— 软边（informs / derives-from）不产生 blocked；没有边的 roadmap
   读出来的 status 与今天一致。

本文件只覆盖 single-file carrier；bundle 跑同一套断言的文件是第二刀。

运行：python tests/test_blocked_single_file.py
"""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

from roadmap import (  # noqa: E402  （错误码表这道缝只在 Python API 上看得见）
    ERROR_EXIT_CODES,
    InvalidStatus,
    RoadmapError,
)

CLI = SKILL_DIR / "roadmap_cli.py"

E_INVALID_STATUS = "E_INVALID_STATUS"


class BlockedContractTest(unittest.TestCase):
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
                f"CLI 失败 ({' '.join(map(str, args))})\n"
                f"exit={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
            )
        return result

    def init_roadmap(self):
        self.run_cli("init", self.roadmap, "--title", "P1 阻塞派生")

    def add_node(self, parent_id, label):
        return json.loads(self.run_cli("add", self.roadmap, parent_id, label).stdout)

    def add_edge(self, from_id, to_id, edge_type):
        return json.loads(
            self.run_cli("edge", "add", self.roadmap, from_id, to_id, "--type", edge_type).stdout
        )

    def get_node(self, node_id):
        """读缝：`get` 的输出，派生的 blocked / blocked_reason 就在这里出现。"""
        return json.loads(self.run_cli("get", self.roadmap, node_id).stdout)

    def complete(self, node_id):
        self.run_cli("update", self.roadmap, node_id, "--status", "completed")

    def on_disk_nodes(self):
        """落盘缝：carrier 里真实存着的节点，不含任何派生字段。"""
        return json.loads(self.roadmap.read_text(encoding="utf-8"))["nodes"]

    def tree_text(self, *extra):
        return self.run_cli("tree", self.roadmap, *extra).stdout

    def icon_for(self, tree_text, node_id):
        """取某个节点那一行的状态图标（`[!]` / `[ ]` / `[~]` / `[x]`）。

        走 tree 的文本行而不是节点字典：md 渲染对 Human 的全部意义就在这一行里。
        """
        for line in tree_text.splitlines():
            stripped = line.strip()
            if f" {node_id}. " not in stripped:
                continue
            # 图标本身含空格（`[ ]`），不能按空格切字段；格子线字符要剥掉。
            match = re.match(r"(\[[!x~ ]\])", stripped.lstrip("├└│─ "))
            if match:
                return match.group(1)
        self.fail(f"tree 输出里找不到节点 {node_id}：\n{tree_text}")


class Slice01BlockedIsDerivedAtReadTest(BlockedContractTest):
    """有未完成 blocks 前驱的节点，读出来 blocked 且给出阻塞它的边 id。"""

    def test_a_node_with_an_unfinished_blocks_predecessor_reads_as_blocked(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")

        node = self.get_node("1-2")

        self.assertTrue(node["blocked"])

    def test_the_reason_names_the_edges_that_block_it(self):
        self.init_roadmap()
        for label in ("设计", "实现", "验收"):
            self.add_node("1", label)
        self.add_edge("1-1", "1-3", "blocks")
        self.add_edge("1-2", "1-3", "blocks")

        node = self.get_node("1-3")

        self.assertEqual(node["blocked_reason"], ["e1", "e2"])


class Slice02PredecessorCompletesTest(BlockedContractTest):
    """前驱一完成，blocked 与 blocked_reason 在同一次读里就消失。

    这两条是"永不落盘"的判别力所在：落盘实现要么根本不更新（陈旧），要么
    依赖某个重算触发点（漏一个就漏一次）。派生实现没有触发点可言。
    """

    def test_completing_the_predecessor_drops_both_fields_in_the_same_read(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")
        self.assertTrue(self.get_node("1-2")["blocked"])

        self.complete("1-1")

        node = self.get_node("1-2")
        self.assertNotIn("blocked", node)
        self.assertNotIn("blocked_reason", node)

    def test_only_the_edges_whose_predecessor_is_unfinished_keep_blocking(self):
        self.init_roadmap()
        for label in ("设计", "实现", "验收"):
            self.add_node("1", label)
        self.add_edge("1-1", "1-3", "blocks")
        self.add_edge("1-2", "1-3", "blocks")

        self.complete("1-1")

        node = self.get_node("1-3")
        self.assertTrue(node["blocked"])
        self.assertEqual(node["blocked_reason"], ["e2"])


class Slice03EdgeRemovedTest(BlockedContractTest):
    """删掉那条阻塞边后同样立即消失——不许有需要手工重算的残留。"""

    def test_removing_the_edge_drops_both_fields_in_the_same_read(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")
        self.assertTrue(self.get_node("1-2")["blocked"])

        self.run_cli("edge", "remove", self.roadmap, "e1")

        node = self.get_node("1-2")
        self.assertNotIn("blocked", node)
        self.assertNotIn("blocked_reason", node)

    def test_the_blocked_node_keeps_its_own_status_when_the_edge_goes_away(self):
        """被阻塞期间节点的 status 也不是 blocked——它从来没被改写过。"""
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.run_cli("update", self.roadmap, "1-2", "--status", "in_progress")
        self.add_edge("1-1", "1-2", "blocks")

        self.assertEqual(self.get_node("1-2")["status"], "in_progress")


class Slice04NeverPersistedTest(BlockedContractTest):
    """断言 carrier 里 status 从未被写成 blocked——加边前后直接检查落盘内容。

    不查读命令：派生字段本来就在读命令里，看它等于自己证明自己。唯一的证据
    是落盘字节。
    """

    def test_adding_a_blocking_edge_does_not_touch_the_persisted_status(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.run_cli("update", self.roadmap, "1-2", "--status", "in_progress")
        before = self.on_disk_nodes()["1-2"]["status"]

        self.add_edge("1-1", "1-2", "blocks")

        self.assertEqual(self.on_disk_nodes()["1-2"]["status"], before)

    def test_the_derived_fields_never_reach_the_carrier(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")
        self.assertTrue(self.get_node("1-2")["blocked"])

        node = self.on_disk_nodes()["1-2"]

        self.assertNotIn("blocked", node)
        self.assertNotIn("blocked_reason", node)

    def test_no_node_on_disk_is_ever_status_blocked(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")

        statuses = {node["status"] for node in self.on_disk_nodes().values()}

        self.assertNotIn("blocked", statuses)


class Slice05BlockedIsNotSettableTest(BlockedContractTest):
    """`--status blocked` 移出可设枚举：人工设置返回 E_INVALID_STATUS + 退出码。

    留着它等于允许"人设的 blocked"与"边推导的 blocked"并存——那又是一个真相源。
    """

    def test_update_refuses_to_set_blocked(self):
        self.init_roadmap()
        self.add_node("1", "设计")

        result = self.run_cli("update", self.roadmap, "1-1", "--status", "blocked", check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(E_INVALID_STATUS, result.stderr)

    def test_the_refusal_exit_code_is_the_one_the_error_table_declares(self):
        self.init_roadmap()
        self.add_node("1", "设计")

        result = self.run_cli("update", self.roadmap, "1-1", "--status", "blocked", check=False)

        self.assertEqual(result.returncode, ERROR_EXIT_CODES[E_INVALID_STATUS])

    def test_add_refuses_to_create_a_blocked_node_and_creates_nothing(self):
        self.init_roadmap()

        result = self.run_cli("add", self.roadmap, "1", "设计", "--status", "blocked", check=False)

        self.assertIn(E_INVALID_STATUS, result.stderr)
        self.assertEqual(list(self.on_disk_nodes()), ["1"])

    def test_the_refused_node_keeps_the_status_it_had(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.run_cli("update", self.roadmap, "1-1", "--status", "in_progress")

        self.run_cli("update", self.roadmap, "1-1", "--status", "blocked", check=False)

        self.assertEqual(self.on_disk_nodes()["1-1"]["status"], "in_progress")


class Slice06ErrorCodeRegistrationTest(unittest.TestCase):
    """E_INVALID_STATUS 登记进统一错误码表，而不是在 CLI 里另写一句 exit。"""

    def test_the_code_is_registered_in_the_shared_table(self):
        self.assertEqual(InvalidStatus.code, E_INVALID_STATUS)
        self.assertIn(E_INVALID_STATUS, ERROR_EXIT_CODES)

    def test_the_registered_exit_code_is_the_one_the_cli_uses(self):
        self.assertEqual(ERROR_EXIT_CODES[E_INVALID_STATUS], 1)
        self.assertEqual(InvalidStatus.exit_code, ERROR_EXIT_CODES[E_INVALID_STATUS])

    def test_it_shares_the_base_mechanism_instead_of_adding_one(self):
        self.assertTrue(issubclass(InvalidStatus, RoadmapError))


class Slice07SoftEdgesDoNotBlockTest(BlockedContractTest):
    """负向控制例：软依赖不是硬依赖。

    informs / derives-from / supersedes 的边就算前驱没完成，也不产生 blocked。
    防的是"按端点过滤、忘了按类型过滤"——那种实现会让下面每条都红，而 Slice01
    一条也不会红，因为那边只测了 blocks。
    """

    def test_an_informs_edge_does_not_block(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "informs")

        self.assertNotIn("blocked", self.get_node("1-2"))

    def test_a_derives_from_edge_does_not_block(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "derives-from")

        self.assertNotIn("blocked", self.get_node("1-2"))

    def test_a_supersedes_edge_does_not_block_the_node_it_archives(self):
        self.init_roadmap()
        self.add_node("1", "旧方案")
        self.add_node("1", "新方案")
        self.add_edge("1-2", "1-1", "supersedes")

        node = self.get_node("1-1")

        self.assertTrue(node["archived"])
        self.assertNotIn("blocked", node)


class Slice08NoEdgeControlTest(BlockedContractTest):
    """控制例：没有边的 roadmap，读出来的东西与派生之前一致。

    #79 的 Slice08 用 P1 之前的 commit 做基线，已经逐字节比过全部命令；这里
    补的是那条基线覆盖不到的方向——派生开关加进去以后，无边路径上不能凭空
    多出字段。
    """

    def test_a_node_with_no_predecessors_has_no_derived_fields(self):
        self.init_roadmap()
        self.add_node("1", "设计")

        self.assertEqual(self.get_node("1-1"), self.on_disk_nodes()["1-1"])

    def test_an_unrelated_blocks_edge_does_not_block_anyone_else(self):
        self.init_roadmap()
        for label in ("设计", "实现", "验收"):
            self.add_node("1", label)
        self.add_edge("1-1", "1-2", "blocks")

        self.assertNotIn("blocked", self.get_node("1-3"))
        self.assertNotIn("blocked", self.get_node("1-1"))


class Slice10TreeRendersTheDerivedIconTest(BlockedContractTest):
    """md / tree 视图里被挡住的节点显示 `[!]`。

    没有这一刀，`get` 说"被挡住"而 md 说"没开工"——同一个事实在两份视图里
    打架，而 Human 只看 md。
    """

    def test_a_blocked_node_renders_with_the_blocked_icon(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")

        self.assertEqual(self.icon_for(self.tree_text(), "1-2"), "[!]")

    def test_the_icon_comes_from_the_edges_not_from_the_stored_status(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")

        self.assertEqual(self.on_disk_nodes()["1-2"]["status"], "pending")
        self.assertEqual(self.icon_for(self.tree_text(), "1-2"), "[!]")

    def test_the_icon_goes_away_when_the_predecessor_completes(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")

        self.complete("1-1")

        self.assertEqual(self.icon_for(self.tree_text(), "1-2"), "[ ]")

    def test_only_the_blocked_node_gets_the_icon(self):
        self.init_roadmap()
        for label in ("设计", "实现", "验收"):
            self.add_node("1", label)
        self.add_edge("1-1", "1-2", "blocks")

        tree = self.tree_text()

        self.assertEqual(self.icon_for(tree, "1-1"), "[ ]")
        self.assertEqual(self.icon_for(tree, "1-3"), "[ ]")

    def test_a_roadmap_without_edges_never_renders_the_blocked_icon(self):
        """控制例：没边的 roadmap 的 tree 与派生之前一致。"""
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")

        self.assertNotIn("[!]", self.tree_text())

    def test_the_markdown_section_renders_the_blocked_icon(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")

        section = self.run_cli("section", self.roadmap).stdout

        self.assertEqual(self.icon_for(section, "1-2"), "[!]")


if __name__ == "__main__":
    unittest.main()
