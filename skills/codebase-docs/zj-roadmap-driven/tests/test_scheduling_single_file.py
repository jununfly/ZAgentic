"""#81 调度查询（ready / critical-path / impact）— single-file carrier。

测试缝（沿用 #79 / #80 / #82 与 zj 的既定约定）：
1. CLI 进程级 —— 唯一能同时钉住 stdout 与退出码的缝；
2. 控制例 —— 没有边时 `ready` 与"状态为 pending 的节点集合"一致（AC 第 2 条）；
3. 负向控制例 —— 带未完成 `blocks` 前驱的节点**不得**出现在就绪集（AC 第 1 条）。

本文件只覆盖 single-file carrier；bundle 侧继承这里每个 Slice 类跑同一套契约
（#80 / #82 同款：一个 carrier 没法独自漂移成绿）。

运行：python tests/test_scheduling_single_file.py
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

CLI = SKILL_DIR / "roadmap_cli.py"

# 行首的节点 id：`1-2. 向量化入库 [ ]`
NODE_ID = re.compile(r"^(\d+(?:-\d+)*)\.")


class SchedulingTestBase(unittest.TestCase):
    """建图与解析的脚手架；bundle 侧子类只覆写 STORAGE 与 carrier 读法。"""

    STORAGE = "single"

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

    def init_map(self, title="P"):
        self.run_cli("init", self.roadmap, "--title", title, "--storage", self.STORAGE)

    def add_node(self, parent, label, status="pending"):
        self.run_cli("add", self.roadmap, parent, label, "--status", status)

    def add_edge(self, from_id, to_id, edge_type="blocks"):
        self.run_cli("edge", "add", self.roadmap, from_id, to_id, "--type", edge_type)

    def complete(self, node_id):
        self.run_cli("update", self.roadmap, node_id, "--status", "completed")

    def ready_ids(self):
        out = self.run_cli("ready", self.roadmap).stdout
        return [m.group(1) for m in (NODE_ID.match(line) for line in out.splitlines()) if m]

    def pending_ids_from_carrier(self):
        """控制例的对照真相：carrier 里 status == pending 的节点 id。"""
        data = json.loads((self.workdir / "roadmap.json").read_text(encoding="utf-8"))
        return {nid for nid, n in data["nodes"].items() if n.get("status") == "pending"}


class Slice01Ready(SchedulingTestBase):
    """Slice 01 —— ready：pending 且无未完成 `blocks` 前驱。"""

    def build_three(self):
        self.init_map()
        for label in ("甲", "乙", "丙"):
            self.add_node("1", label)

    def test_pending_nodes_without_edges_are_ready(self):
        self.build_three()
        self.assertEqual({"1-1", "1-2", "1-3"}, set(self.ready_ids()))

    def test_node_with_unfinished_blocks_predecessor_is_not_ready(self):
        """核心负向控制例（AC 第 1 条）：有未完成前驱就不许出现。"""
        self.build_three()
        self.add_edge("1-1", "1-2")
        ready = set(self.ready_ids())
        self.assertIn("1-1", ready)
        self.assertNotIn("1-2", ready)

    def test_predecessor_completing_releases_node_in_the_same_read(self):
        """前驱一完成就进就绪集 —— 派生，不落计数器（Story 24 推迟到 P3）。"""
        self.build_three()
        self.add_edge("1-1", "1-2")
        self.assertNotIn("1-2", set(self.ready_ids()))

        self.complete("1-1")
        ready = set(self.ready_ids())
        self.assertNotIn("1-1", ready)   # 已完成本身不再可取
        self.assertIn("1-2", ready)

    def test_soft_edge_does_not_hold_a_node_back(self):
        """`informs` 是上下文关系，不参与调度（与 #80 的阻塞语义同一条边界）。"""
        self.build_three()
        self.add_edge("1-1", "1-2", "informs")
        self.assertIn("1-2", set(self.ready_ids()))


class Slice02ReadyControl(SchedulingTestBase):
    """Slice 02 —— 控制例：没有边时，`ready` 必须退化为今天的 pending 语义。

    这条存在的意义是防"过度实现"：如果 ready 在没边的图上返回的东西和 pending
    不一致，那它算的是别的什么，而不是就绪集。
    """

    def test_ready_equals_pending_set_when_no_edges(self):
        self.init_map()
        self.add_node("1", "甲")
        self.add_node("1", "乙")
        self.add_node("1-1", "甲子")
        self.assertEqual(set(self.ready_ids()), self.pending_ids_from_carrier())

    def test_ready_on_map_without_children_is_empty_not_an_error(self):
        """空图 / 无边图：不报错、有明确的空结果（AC 第 6 条）。"""
        self.init_map()
        result = self.run_cli("ready", self.roadmap)
        self.assertEqual(0, result.returncode)
        self.assertEqual([], [i for i in self.ready_ids()])


if __name__ == "__main__":
    unittest.main()
