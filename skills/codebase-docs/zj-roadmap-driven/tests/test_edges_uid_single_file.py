"""#106 S4 — 边改用 uid 引用 + 存量边迁移（single-file carrier）。

验收（取自 issue #106）：
- 新边落盘存 uid（from/to 不再存显示 id）；读视图 / 列表对 Human 仍给显示 id。
- `edge migrate` 把存量显示 id 边一次性转成 uid；Human 视野不变、且幂等。
- 环检测在 uid 空间正确（迁移后照常拒绝 blocks 成环）。

测试缝：CLI 进程级（与 test_edges_single_file 同款）+ 直接读 carrier 字节验证落盘形状。
本文件覆盖 single-file carrier；bundle 跑同一套断言的文件是 test_edges_uid_bundle.py
（继承本文件的 Slice，不复制）。

运行：python tests/test_edges_uid_single_file.py
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

from roadmap import Roadmap, looks_like_uid  # noqa: E402  （辅缝：Python API + uid 形状判定）
CLI = SKILL_DIR / "roadmap_cli.py"

FIXED_ENV = {**os.environ, "PYTHONHASHSEED": "0"}

E_CYCLE = "E_CYCLE"
E_NODE_NOT_FOUND = "E_NODE_NOT_FOUND"


class UidEdgeContractTest(unittest.TestCase):
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
            env=FIXED_ENV,
        )
        if check and result.returncode != 0:
            self.fail(
                f"CLI 失败 ({' '.join(map(str, args))})\n"
                f"exit={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
            )
        return result

    def init_roadmap(self):
        self.run_cli("init", self.roadmap, "--title", "S4")

    def add_node(self, parent_id, label):
        return json.loads(self.run_cli("add", self.roadmap, parent_id, label).stdout)

    def add_edge(self, from_id, to_id, edge_type):
        return json.loads(
            self.run_cli("edge", "add", self.roadmap, from_id, to_id, "--type", edge_type).stdout
        )

    def list_edges(self, *extra):
        return json.loads(self.run_cli("edge", "list", self.roadmap, *extra).stdout)

    def read_raw(self):
        return json.loads(self.roadmap.read_text(encoding="utf-8"))

    def raw_edge_endpoints(self):
        """落盘字节里的边（single-file：data["edges"]）。bundle 那边会覆盖。"""
        return self.read_raw().get("edges", [])

    def node_uids(self):
        """当前图中所有节点的 uid 集合（single-file）。bundle 那边会覆盖。"""
        return {n["uid"] for n in self.read_raw()["nodes"].values()}

    def seed_display_id_edges(self, edges):
        """手工塞显示 id 边，模拟 P0 之前的存量数据（未跑 migrate）。

        ！！要求调用前已 init 且建好 1-1 / 1-2 两个节点——这里只覆盖 edges。
        """
        r = Roadmap(str(self.roadmap))
        r.load()
        r.data["edges"] = edges
        r.save()


class SliceANewEdgeStoresUidTest(UidEdgeContractTest):
    """新边落盘存 uid；返回 / 列表仍给 Human 显示 id（旧契约不动）。"""

    def test_a_new_edge_is_stored_with_uid_endpoints(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")

        edge = self.raw_edge_endpoints()[0]
        uids = self.node_uids()
        self.assertTrue(looks_like_uid(edge["from"]), f"from 应存 uid，实际 {edge['from']!r}")
        self.assertTrue(looks_like_uid(edge["to"]), f"to 应存 uid，实际 {edge['to']!r}")
        self.assertIn(edge["from"], uids)
        self.assertIn(edge["to"], uids)
        # 显示 id 绝不能落盘：落盘字节里不该出现 "1-1" / "1-2" 这种端点。
        self.assertNotIn("1-1", (edge["from"], edge["to"]))
        self.assertNotIn("1-2", (edge["from"], edge["to"]))

    def test_add_edge_returns_display_ids(self):
        """返回给 Agent/Human 的是显示 id，与 P1 之前逐字段一致。"""
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.assertEqual(
            self.add_edge("1-1", "1-2", "informs"),
            {"id": "e1", "from": "1-1", "to": "1-2", "type": "informs"},
        )

    def test_list_edges_returns_display_ids(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")
        self.assertEqual(
            self.list_edges()["edges"],
            [{"id": "e1", "from": "1-1", "to": "1-2", "type": "blocks"}],
        )

    def test_a_display_id_edge_survives_unmigrated_before_migrate(self):
        """迁移前的存量显示 id 边：不跑 migrate 也照常工作（翻译兼容两种形状）。"""
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.seed_display_id_edges([{"id": "e1", "from": "1-1", "to": "1-2", "type": "blocks"}])
        self.assertEqual(
            self.list_edges()["edges"],
            [{"id": "e1", "from": "1-1", "to": "1-2", "type": "blocks"}],
        )


class SliceBMigrationTest(UidEdgeContractTest):
    """`edge migrate`：存量显示 id 边一次性转成 uid；Human 视野不变、幂等。"""

    def test_migrate_rewrites_display_id_edges_to_uid(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.seed_display_id_edges([{"id": "e1", "from": "1-1", "to": "1-2", "type": "blocks"}])

        result = self.run_cli("edge", "migrate", self.roadmap)
        self.assertIn("Migrated", result.stdout)
        self.assertIn("to uid.", result.stdout)

        edge = self.raw_edge_endpoints()[0]
        uids = self.node_uids()
        self.assertIn(edge["from"], uids)
        self.assertIn(edge["to"], uids)
        self.assertNotIn("1-1", (edge["from"], edge["to"]))

    def test_migrate_preserves_the_human_view(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.seed_display_id_edges([{"id": "e1", "from": "1-1", "to": "1-2", "type": "blocks"}])

        before = self.list_edges()["edges"]
        self.run_cli("edge", "migrate", self.roadmap)
        after = self.list_edges()["edges"]

        self.assertEqual(after, before)

    def test_migrate_is_idempotent(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.seed_display_id_edges([{"id": "e1", "from": "1-1", "to": "1-2", "type": "blocks"}])

        self.run_cli("edge", "migrate", self.roadmap)
        result = self.run_cli("edge", "migrate", self.roadmap)
        self.assertIn("Migrated 0 edge endpoint(s) to uid.", result.stdout)

    def test_migrate_reports_zero_when_there_is_nothing_to_migrate(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.add_edge("1-1", "1-2", "blocks")
        result = self.run_cli("edge", "migrate", self.roadmap)
        self.assertIn("Migrated 0 edge endpoint(s) to uid.", result.stdout)


class SliceCCycleInUidSpaceTest(UidEdgeContractTest):
    """环检测在 uid 空间正确——迁移后 blocks 成环照常被拒，存量环照常保留。"""

    def test_a_blocks_cycle_is_refused_after_migration(self):
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.seed_display_id_edges([{"id": "e1", "from": "1-1", "to": "1-2", "type": "blocks"}])
        self.run_cli("edge", "migrate", self.roadmap)

        result = self.run_cli(
            "edge", "add", self.roadmap, "1-2", "1-1", "--type", "blocks", check=False
        )
        self.assertIn(E_CYCLE, result.stderr)
        self.assertEqual(result.returncode, 1)

    def test_migrate_preserves_an_existing_blocks_cycle(self):
        """外部手改出来的存量成环：迁移只翻端点，环数据不丢、照常显示。"""
        self.init_roadmap()
        self.add_node("1", "设计")
        self.add_node("1", "实现")
        self.seed_display_id_edges([
            {"id": "e1", "from": "1-1", "to": "1-2", "type": "blocks"},
            {"id": "e2", "from": "1-2", "to": "1-1", "type": "blocks"},
        ])
        self.run_cli("edge", "migrate", self.roadmap)

        self.assertEqual(
            self.list_edges()["edges"],
            [
                {"id": "e1", "from": "1-1", "to": "1-2", "type": "blocks"},
                {"id": "e2", "from": "1-2", "to": "1-1", "type": "blocks"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
