#!/usr/bin/env python3
"""P5-S4 prune + edge-driven `context --include`（§3.3 / §4.4）。

验收：
- prune <trace> --edge <id> 删指定边、节点仍在；不带 --edge 默认删 mainline 边。
- prune 作用于 plan 节点 → E_INVALID_LAYER。
- context 默认（不含 --include trace）输出与 S5 逐字节一致；--include trace 才暴露 trace 边；
  --include decisions 读 node.decisions；--include children 列 children。
- 裸 --include（无值）报错，不静默接受。
- 真实回归：trace add + promote + prune + context 后，plan 视图字节不变。

单元 + 两 carrier（single / sqlite）各跑一遍。
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CLI = SKILL_DIR / "roadmap_cli.py"
sys.path.insert(0, str(SKILL_DIR))

from roadmap import (  # noqa: E402
    Roadmap,
    LAYER_TRACE,
    LAYER_PLAN,
    InvalidLayer,
    ERROR_EXIT_CODES,
)
from roadmap_sqlite import RoadmapSqlite  # noqa: E402


TARGETS = {
    "single": "roadmap.json",
    "sqlite": "roadmap.sqlite",
}


def run_cli(*args: object, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(CLI), *[str(a) for a in args]],
        cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if check and completed.returncode != 0:
        raise AssertionError(
            f"roadmap_cli failed ({completed.returncode})\nargs: {args}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def load_carrier(storage: str, path: Path):
    rm = Roadmap(str(path)) if storage == "single" else RoadmapSqlite(str(path))
    rm.load()
    return rm


# md 头 `最后更新: <timestamp>` 随每次 save 漂移 1 秒；prune 不改变结构但触发 save，
# 故 before/after 的 section 仅时间戳不同。归一化后再比对（与 test_trace.py / test_promote.py 同纪律）。
TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?")


def normalize(s: str) -> str:
    return TS_RE.sub("TS", s)


class PruneSliceTest(unittest.TestCase):
    def _seed(self, storage: str, tmpd: Path):
        path = tmpd / TARGETS[storage]
        if storage == "sqlite":
            run_cli("init", path, "--storage", "sqlite", "--title", "t", cwd=tmpd)
        else:
            run_cli("init", path, "--title", "t", cwd=tmpd)
        run_cli("add", path, "1", "child-A", cwd=tmpd)
        # 9-1：被 1-1 触发
        run_cli("trace", "add", path, "--kind", "finding", "--body", "seed", "--under", "1-1", cwd=tmpd)
        # 9-2：源自 9-1，生成一条 mainline 边 9-2 -> 9-1
        run_cli("trace", "add", path, "--kind", "attempt", "--body", "step2", "--under", "1-1", "--from", "9-1", cwd=tmpd)
        rm = load_carrier(storage, path)
        return path, rm.node_ids(layer=LAYER_TRACE)

    def _prune_specific_edge(self, storage: str):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, _ = self._seed(storage, tmpd)
            rm = load_carrier(storage, path)
            mainline = [e for e in rm.list_edges() if e["type"] == "mainline"]
            self.assertEqual(len(mainline), 1)
            edge_id = mainline[0]["id"]
            before_traces = len(rm.node_ids(layer=LAYER_TRACE))
            p = run_cli("prune", path, "9-2", "--edge", edge_id, cwd=tmpd)
            self.assertEqual(p.returncode, 0)
            rm2 = load_carrier(storage, path)
            self.assertEqual(len(rm2.list_edges()), 0, "指定边应被删")
            self.assertEqual(len(rm2.node_ids(layer=LAYER_TRACE)), before_traces, "节点不应被删")

    def _prune_default_mainline(self, storage: str):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, _ = self._seed(storage, tmpd)
            before_traces = len(load_carrier(storage, path).node_ids(layer=LAYER_TRACE))
            p = run_cli("prune", path, "9-2", cwd=tmpd)  # 默认删 9-2 的 mainline 边
            self.assertEqual(p.returncode, 0)
            rm = load_carrier(storage, path)
            self.assertEqual(len([e for e in rm.list_edges() if e["type"] == "mainline"]), 0)
            self.assertEqual(len(rm.node_ids(layer=LAYER_TRACE)), before_traces, "节点不应被删")

    def _prune_on_plan_node_invalid(self, storage: str):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, _ = self._seed(storage, tmpd)
            p = run_cli("prune", path, "1-1", check=False, cwd=tmpd)
            self.assertEqual(p.returncode, 1)
            self.assertIn("E_INVALID_LAYER", p.stderr)

    def _prune_keeps_plan_views(self, storage: str):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, _ = self._seed(storage, tmpd)
            before = {
                "tree": run_cli("tree", path, "--depth", "10", cwd=tmpd).stdout,
                "section": normalize(run_cli("section", path, cwd=tmpd).stdout),
                "stats": run_cli("stats", path, cwd=tmpd).stdout,
            }
            run_cli("prune", path, "9-2", cwd=tmpd)
            after = {
                "tree": run_cli("tree", path, "--depth", "10", cwd=tmpd).stdout,
                "section": normalize(run_cli("section", path, cwd=tmpd).stdout),
                "stats": run_cli("stats", path, cwd=tmpd).stdout,
            }
            self.assertEqual(before, after, "prune 只删边，plan 视图应字节不变")


class ContextIncludeTest(unittest.TestCase):
    def _seed_with_promotion(self, storage: str, tmpd: Path):
        path = tmpd / TARGETS[storage]
        if storage == "sqlite":
            run_cli("init", path, "--storage", "sqlite", "--title", "t", cwd=tmpd)
        else:
            run_cli("init", path, "--title", "t", cwd=tmpd)
        run_cli("add", path, "1", "child-A", cwd=tmpd)
        run_cli("trace", "add", path, "--kind", "finding", "--body", "seed", "--under", "1-1", cwd=tmpd)
        rm = load_carrier(storage, path)
        trace_id = rm.node_ids(layer=LAYER_TRACE)[0]
        run_cli("promote", path, trace_id, "--under", "1-1", "--label", "Promoted", cwd=tmpd)
        run_cli("promote", path, trace_id, "--accept", cwd=tmpd)
        rm2 = load_carrier(storage, path)
        new_plan = rm2.get_node("1-1")["children"][0]
        return path, trace_id, new_plan

    def _include_trace_shows_derives_from(self, storage: str):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, trace_id, new_plan = self._seed_with_promotion(storage, tmpd)
            out = json.loads(run_cli("context", path, new_plan, "--include", "trace", cwd=tmpd).stdout)
            self.assertIn("trace_edges", out)
            derives = [e for e in out["trace_edges"] if e["type"] == "derives-from"]
            self.assertEqual(len(derives), 1)
            self.assertEqual(derives[0]["from"], trace_id)
            self.assertEqual(derives[0]["other_kind"], "finding")
            self.assertIn("seed", derives[0]["other_body"])

    def _without_include_has_no_trace_key(self, storage: str):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, trace_id, new_plan = self._seed_with_promotion(storage, tmpd)
            base = json.loads(run_cli("context", path, new_plan, cwd=tmpd).stdout)
            self.assertNotIn("trace_edges", base, "不带 --include trace 不应暴露 trace")
            self.assertNotIn("decisions", base)
            self.assertNotIn("children", base)

    def _include_decisions_and_children(self, storage: str):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, trace_id, new_plan = self._seed_with_promotion(storage, tmpd)
            run_cli("decide", path, "1-1", "q", "a", cwd=tmpd)
            dec = json.loads(run_cli("context", path, "1-1", "--include", "decisions", cwd=tmpd).stdout)
            self.assertIn("decisions", dec)
            self.assertEqual(len(dec["decisions"]), 1)
            chi = json.loads(run_cli("context", path, "1", "--include", "children", cwd=tmpd).stdout)
            self.assertIn("children", chi)
            self.assertIn("1-1", chi["children"])

    def _bare_include_errors(self, storage: str):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, trace_id, new_plan = self._seed_with_promotion(storage, tmpd)
            p = run_cli("context", path, new_plan, "--include", check=False, cwd=tmpd)
            self.assertEqual(p.returncode, 1, "裸 --include 应报错而非静默接受")

    def _two_includes(self, storage: str):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, trace_id, new_plan = self._seed_with_promotion(storage, tmpd)
            out = json.loads(run_cli("context", path, new_plan, "--include", "trace", "--include", "children", cwd=tmpd).stdout)
            self.assertIn("trace_edges", out)
            self.assertIn("children", out)


for _storage in ("single", "sqlite"):
    def _make(storage):
        def t1(self): self._prune_specific_edge(storage)
        def t2(self): self._prune_default_mainline(storage)
        def t3(self): self._prune_on_plan_node_invalid(storage)
        def t4(self): self._prune_keeps_plan_views(storage)
        def t5(self): self._include_trace_shows_derives_from(storage)
        def t6(self): self._without_include_has_no_trace_key(storage)
        def t7(self): self._include_decisions_and_children(storage)
        def t8(self): self._bare_include_errors(storage)
        def t9(self): self._two_includes(storage)
        setattr(PruneSliceTest, f"test_prune_specific_edge_{storage}", t1)
        setattr(PruneSliceTest, f"test_prune_default_mainline_{storage}", t2)
        setattr(PruneSliceTest, f"test_prune_plan_node_invalid_{storage}", t3)
        setattr(PruneSliceTest, f"test_prune_keeps_plan_views_{storage}", t4)
        setattr(ContextIncludeTest, f"test_include_trace_{storage}", t5)
        setattr(ContextIncludeTest, f"test_without_include_no_trace_key_{storage}", t6)
        setattr(ContextIncludeTest, f"test_include_decisions_children_{storage}", t7)
        setattr(ContextIncludeTest, f"test_bare_include_errors_{storage}", t8)
        setattr(ContextIncludeTest, f"test_two_includes_{storage}", t9)
    _make(_storage)


if __name__ == "__main__":
    unittest.main(verbosity=2)
