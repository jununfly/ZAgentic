#!/usr/bin/env python3
"""#118 S1 — `layer` 字段 + 迁移 + L1/L2 归口（§2.3）验收。

缝：CLI 契约（subprocess，断言退出码 + 输出）为主，carrier API 为辅（注入 trace /
调 `rebuild_indexes`）。每个负向用例都"抽掉实现就红"：先注入 trace，再断言 plan
遍历输出字节不变——若 `iter_nodes` 不过滤 `layer`，trace 会当场泄进 md / 调度。

覆盖（合并 §2.8 / §2.9 / §4.4 的 S1 切片验收）：
  - `ensure_layer` 给存量（无 `layer`）节点补 `'plan'`。
  - `iter_nodes(layer='plan')` 默认只返回 plan；`iter_nodes(layer='trace')` 返回 trace。
  - 迁移：剥离 `layer` 后 md 输出字节不变；`ensure_layer` 后所有节点 `layer=='plan'`，validate 通过。
  - 每个遍历命令（render / section / stats / validate / ready / critical-path /
    impact / tree / decisions）写入一批 trace 后输出字节不变（single / sqlite 两个 carrier 各跑）。
  - `E_LAYER_VIOLATION`：code 字符串 + 退出码 1，并入 `ERROR_EXIT_CODES`。
  - §2.4 硬前提：`add_node` 把 plan 节点挂到 trace 节点下被拒（两个 carrier 各跑）。

运行：python tests/test_layer_s1.py
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

from roadmap import (  # noqa: E402
    Roadmap,
    LAYER_PLAN,
    LAYER_TRACE,
    ensure_layer,
    assert_plan_layer,
    LayerViolation,
    ERROR_EXIT_CODES,
)
from roadmap_sqlite import RoadmapSqlite  # noqa: E402

CLI = SKILL_DIR / "roadmap_cli.py"
TARGETS = {"single": "roadmap.json", "sqlite": "roadmap.sqlite"}

# 时间戳差异（render / section 的 updated 行）会让逐字节比较假红，统一归一。
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")


def normalize(text: str) -> str:
    return TIMESTAMP.sub("<T>", text)


def make_trace(tid: str, kind: str = "finding", body: str = "...") -> dict:
    """trace 节点的最小合法形状（§2.6）：无 parent / children / status / decisions。

    bundle 的 `safe_node_id` 要求数字型 id，故 trace id 用数字段（如 '9001'），
    不与 plan 的 '1' / '1-1' 冲突即可。
    """
    return {
        "id": tid,
        "uid": f"u-{tid}",
        "label": f"trace {tid}",
        "layer": LAYER_TRACE,
        "kind": kind,
        "body": body,
        "parent": None,
        "children": [],
        "decisions": [],
        "notes": "",
    }


def load_carrier(storage: str, path: Path):
    """三个 carrier 的 `load` 都是实例方法：构造后再 load。"""
    if storage == "single":
        rm = Roadmap(str(path))
    else:
        rm = RoadmapSqlite(str(path))
    rm.load()
    return rm


class LayerUnitTest(unittest.TestCase):
    """纯单元层：迁移补字段 + §2.4 守卫 + 错误码契约。"""

    def test_ensure_layer_backfills_plan_and_reports_count(self):
        nodes = {"a": {"id": "a"}, "b": {"id": "b", "layer": LAYER_PLAN}}
        self.assertEqual(ensure_layer(nodes), 1)
        self.assertTrue(all(n.get("layer") == LAYER_PLAN for n in nodes.values()))

    def test_assert_plan_layer_rejects_trace_and_accepts_plan(self):
        with self.assertRaises(LayerViolation) as ctx:
            assert_plan_layer({"id": "t1", "layer": LAYER_TRACE})
        self.assertEqual(ctx.exception.code, "E_LAYER_VIOLATION")
        self.assertEqual(ctx.exception.exit_code, 1)
        # 存量节点（无 layer）→ 视为 plan，不拒。
        assert_plan_layer({"id": "old"})
        assert_plan_layer({"id": "p", "layer": LAYER_PLAN})

    def test_e_layer_violation_is_in_exit_code_table(self):
        self.assertIn(LayerViolation.code, ERROR_EXIT_CODES)
        self.assertEqual(ERROR_EXIT_CODES[LayerViolation.code], 1)


class LayerMigrationTest(unittest.TestCase):
    """§2.8 最硬验收：迁移（补 `layer`）后 md 字节不变，validate 通过。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workdir = Path(self.tmp.name)
        self.here = self.workdir / "single"
        self.here.mkdir(parents=True, exist_ok=True)
        self.path = self.here / TARGETS["single"]
        (self.here / "plan.md").write_text("# 我的计划\n\n", encoding="utf-8")
        cli = self._cli
        cli("init", self.path, "--title", "迁移验收", "--md-file", "plan.md", cwd=self.here)
        cli("add", self.path, "1", "设计", "--mode", "explore", cwd=self.here)
        cli("add", self.path, "1-1", "实现", "--mode", "exploit", cwd=self.here)
        cli("update", self.path, "1-1", "--status", "in_progress", cwd=self.here)
        cli("decide", self.path, "1-1", "为什么", "因为要测", cwd=self.here)
        cli("render", self.path, cwd=self.here)

    def tearDown(self):
        self.tmp.cleanup()

    def _cli(self, *args, cwd=None, check=True):
        result = subprocess.run(
            [sys.executable, str(CLI), *map(str, args)],
            cwd=str(cwd or self.here), text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        if check and result.returncode != 0:
            self.fail(f"cli failed {result.returncode}\n{result.stdout}\n{result.stderr}")
        return result

    def test_migration_md_is_byte_identical_and_layer_is_plan(self):
        md_with_layer = normalize((self.here / "plan.md").read_text(encoding="utf-8"))

        # 模拟存量 roadmap：剥掉所有节点的 `layer` 字段。
        data = json.loads(self.path.read_text(encoding="utf-8"))
        for node in data["nodes"].values():
            node.pop("layer", None)
        self.path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        self._cli("render", self.path, cwd=self.here)
        md_legacy = normalize((self.here / "plan.md").read_text(encoding="utf-8"))
        self.assertEqual(md_legacy, md_with_layer, "剥掉 layer 不应改变 md 视图")

        # 显式迁移（ensure_layer 在 save 时补字段）。
        rm = load_carrier("single", self.path)
        self.assertTrue(all("layer" not in n for n in rm.data["nodes"].values()),
                         "前提：存量节点确实没有 layer")
        rm.save()
        rm2 = load_carrier("single", self.path)
        self.assertTrue(all(n.get("layer") == LAYER_PLAN for n in rm2.data["nodes"].values()),
                         "迁移后所有节点应带 layer='plan'")

        self._cli("render", self.path, cwd=self.here)
        md_after = normalize((self.here / "plan.md").read_text(encoding="utf-8"))
        self.assertEqual(md_after, md_legacy, "ensure_layer 迁移后 md 字节不变")

        # validate 通过（退出码 0）。
        self._cli("validate", self.path, cwd=self.here)


class LayerTraversalNegativeTest(unittest.TestCase):
    """§2.9 / §4.4 S1 验收：写入 trace 后，每个 plan 遍历命令输出字节不变。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workdir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args, cwd=None, check=True):
        result = subprocess.run(
            [sys.executable, str(CLI), *map(str, args)],
            cwd=str(cwd or self.workdir), text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        if check and result.returncode != 0:
            self.fail(f"roadmap_cli failed {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        return result

    def build(self, storage: str) -> Path:
        name = TARGETS[storage]
        here = self.workdir / storage
        here.mkdir(parents=True, exist_ok=True)
        path = here / name
        (here / "plan.md").write_text("# 我的计划\n\n", encoding="utf-8")
        self.run_cli("init", path, "--storage", storage, "--title", "负向用例", "--md-file", "plan.md", cwd=here)
        self.run_cli("add", path, "1", "设计", "--mode", "explore", "--max-children", "3", cwd=here)
        self.run_cli("add", path, "1", "实现", "--mode", "exploit", "--exit-criteria", "全部通过", cwd=here)
        self.run_cli("add", path, "1-2", "子任务", cwd=here)
        self.run_cli("update", path, "1-2-1", "--status", "in_progress", cwd=here)
        self.run_cli("decide", path, "1-2-1", "先做什么", "先打通链路", "带备注", cwd=here)
        self.run_cli("decide", path, "1-1", "为什么这样切", "因为 carrier 要各自成立", cwd=here)
        self.run_cli("edge", "add", path, "1-1", "1-2", "--type", "blocks", cwd=here)
        self.run_cli("render", path, cwd=here)
        return here

    def inject_trace(self, storage: str, path: Path, n: int = 3) -> None:
        """按 carrier 的物理布局注入 trace：single/sqlite 进 nodes 集合。"""
        rm = load_carrier(storage, path)
        for i in range(1, n + 1):
            rm.data["nodes"][f"900{i}"] = make_trace(f"900{i}")
        rm.save()

    def trace_count(self, storage: str, path: Path) -> int:
        rm = load_carrier(storage, path)
        return len(rm.iter_nodes(layer=LAYER_TRACE))

    def snapshot(self, here: Path, path: Path) -> dict:
        """抓取所有 plan 遍历命令的输出。validate 用 check=True 断言退出码 0。

        stats 解析成 dict 比较（materialized JSON 的 key 顺序不保证稳定，
        但数值必须一致——这才是 S1 要守的命题）。
        """
        out = {}
        out["render"] = normalize((here / "plan.md").read_text(encoding="utf-8"))
        out["section"] = normalize(self.run_cli("section", path, cwd=here).stdout)
        out["stats"] = json.loads(self.run_cli("stats", path, cwd=here).stdout)
        out["validate"] = normalize(self.run_cli("validate", path, cwd=here).stdout)
        out["ready"] = normalize(self.run_cli("ready", path, cwd=here).stdout)
        out["critical-path"] = normalize(self.run_cli("critical-path", path, cwd=here).stdout)
        out["impact"] = normalize(self.run_cli("impact", path, "1", cwd=here).stdout)
        out["tree"] = normalize(self.run_cli("tree", path, cwd=here).stdout)
        out["decisions"] = normalize(self.run_cli("decisions", path, cwd=here).stdout)
        return out

    def _run_negative_for(self, storage: str):
        here = self.build(storage)
        path = here / TARGETS[storage]
        before = self.snapshot(here, path)

        self.inject_trace(storage, path)
        self.assertGreater(self.trace_count(storage, path), 0,
                           "前提：trace 必须确实注入成功，否则字节不变是假阴性")

        after = self.snapshot(here, path)
        self.assertEqual(after, before,
                         f"[{storage}] 写入 trace 后 plan 遍历输出必须字节不变")

    def test_single_file_traversals_unchanged_with_trace(self):
        self._run_negative_for("single")

    def test_sqlite_traversals_unchanged_with_trace(self):
        self._run_negative_for("sqlite")




class LayerHardPremiseTest(unittest.TestCase):
    """§2.4 硬前提：任何把 trace 节点塞进 plan 的 children / parent 的写入路径被拒。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workdir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _cli(self, *args, cwd=None):
        return subprocess.run(
            [sys.executable, str(CLI), *map(str, args)],
            cwd=str(cwd or self.workdir), text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )

    def test_single_file_add_node_under_trace_is_rejected(self):
        here = self.workdir / "single"
        here.mkdir(parents=True, exist_ok=True)
        path = here / TARGETS["single"]
        (here / "plan.md").write_text("# 我的计划\n\n", encoding="utf-8")
        self._cli("init", path, "--title", "硬前提", "--md-file", "plan.md", cwd=here)
        rm = load_carrier("single", path)
        rm.data["nodes"]["9001"] = make_trace("9001")
        rm.save()
        with self.assertRaises(LayerViolation):
            rm.add_node("9001", "不应该成功")


if __name__ == "__main__":
    unittest.main()
