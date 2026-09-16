#!/usr/bin/env python3
"""P5-S2 `trace add` + provenance —— TDD 套件（§3.3 / §4.4）。

验收（来自 `docs/plans/zj-roadmap-execution-graph.md`）：
- trace 可自由追加；plan 侧输出字节不变；trace 不进 `children`（§2.4）。
- 每个新错误码一条用例，断言 code 字符串（不是文案）。
- 红绿双向：抽掉实现会红。
- 字节级不变断言用于"trace 不泄进视图"。

两个 carrier（single / sqlite）各跑一遍；sqlite 继承 single-file 路径。
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
    LAYER_PLAN,
    LAYER_TRACE,
    TRACE_KINDS,
    InvalidKind,
    TraceNotFound,
    InvalidLayer,
    PromoteTargetInvalid,
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
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and completed.returncode != 0:
        raise AssertionError(
            f"roadmap_cli failed ({completed.returncode})\n"
            f"args: {args}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?")


def normalize(s: str) -> str:
    """归一时间戳，让两次快照的字节比较不受"现在"影响。"""
    return TS_RE.sub("TS", s)


def load_carrier(storage: str, path: Path):
    if storage == "single":
        rm = Roadmap(str(path))
    else:
        rm = RoadmapSqlite(str(path))
    rm.load()
    return rm


class TraceUnitTest(unittest.TestCase):
    def test_trace_kinds_enum(self):
        self.assertEqual(
            set(TRACE_KINDS),
            {"turn", "finding", "doubt", "attempt", "artifact"},
        )

    def test_invalid_kind_raises_e_invalid_kind(self):
        rm = Roadmap(str(Path(tempfile.mkdtemp()) / "r.json"))
        rm.init(title="t", description="")
        with self.assertRaises(InvalidKind) as ctx:
            rm.add_trace("not-a-kind", "body")
        self.assertEqual(ctx.exception.code, "E_INVALID_KIND")
        self.assertEqual(ERROR_EXIT_CODES["E_INVALID_KIND"], 1)

    def test_error_codes_present_in_exit_table(self):
        for code in ("E_INVALID_KIND", "E_TRACE_NOT_FOUND", "E_INVALID_LAYER", "E_PROMOTE_TARGET_INVALID"):
            self.assertIn(code, ERROR_EXIT_CODES, code)
            self.assertEqual(ERROR_EXIT_CODES[code], 1, code)


class TraceAddNegativeTest(unittest.TestCase):
    """跨 carrier：trace add 之后，所有 plan 遍历命令输出字节不变（§2.9 / §3.6）。"""

    def _seed(self, storage: str, tmpd: Path):
        path = tmpd / TARGETS[storage]
        md = tmpd / "view.md"
        if storage == "sqlite":
            run_cli("init", path, "--storage", "sqlite", "--title", "t", "--md-file", md, cwd=tmpd)
        else:
            run_cli("init", path, "--title", "t", "--md-file", md, cwd=tmpd)
        run_cli("add", path, "1", "child-A", cwd=tmpd)
        run_cli("add", path, "1", "child-B", cwd=tmpd)
        return path, md

    def _snapshot(self, path: Path, md: Path) -> dict:
        out = {
            "section": run_cli("section", path, cwd=md.parent).stdout,
            "tree": run_cli("tree", path, "--depth", "10", cwd=md.parent).stdout,
            "stats": run_cli("stats", path, cwd=md.parent).stdout,
            "validate": run_cli("validate", path, cwd=md.parent).stdout,
            "ready": run_cli("ready", path, cwd=md.parent).stdout,
            "critical": run_cli("critical-path", path, cwd=md.parent).stdout,
            "impact": run_cli("impact", path, "1-1", cwd=md.parent).stdout,
            "decisions": run_cli("decisions", path, cwd=md.parent).stdout,
            "get": run_cli("get", path, "1-1", cwd=md.parent).stdout,
        }
        if md.exists():
            out["render"] = md.read_text(encoding="utf-8")
        return out

    def _assert_byte_identical(self, before: dict, after: dict):
        self.assertEqual(set(before), set(after))
        for key in before:
            self.assertEqual(normalize(before[key]), normalize(after[key]), f"{key} 输出因 trace 而变化")

    def test_single_file_traversal_unchanged_after_trace_add(self):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, md = self._seed("single", tmpd)
            before = self._snapshot(path, md)
            run_cli("trace", "add", path, "--kind", "finding", "--body", "a thought", cwd=tmpd)
            after = self._snapshot(path, md)
            self._assert_byte_identical(before, after)


    def test_sqlite_traversal_unchanged_after_trace_add(self):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, md = self._seed("sqlite", tmpd)
            before = self._snapshot(path, md)
            run_cli("trace", "add", path, "--kind", "finding", "--body", "a thought", cwd=tmpd)
            after = self._snapshot(path, md)
            self._assert_byte_identical(before, after)


class TraceAddStructureTest(unittest.TestCase):
    """trace 节点结构：layer=trace、parent=None、不进任何 plan children、provenance。"""

    def _add(self, storage: str, tmpd: Path, extra=None):
        path = tmpd / TARGETS[storage]
        md = tmpd / "view.md"
        if storage == "sqlite":
            run_cli("init", path, "--storage", "sqlite", "--title", "t", "--md-file", md, cwd=tmpd)
        else:
            run_cli("init", path, "--title", "t", "--md-file", md, cwd=tmpd)
        run_cli("add", path, "1", "child-A", cwd=tmpd)
        args = ["trace", "add", path, "--kind", "finding", "--body", "b", "--under", "1-1"]
        if extra:
            args += extra
        run_cli(*args, cwd=tmpd)
        return path, md

    def test_single_file_trace_structure_and_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, _ = self._add("single", tmpd)
            rm = load_carrier("single", path)
            traces = rm.iter_nodes(layer=LAYER_TRACE)
            self.assertEqual(len(traces), 1)
            t = traces[0]
            self.assertEqual(t["layer"], LAYER_TRACE)
            self.assertIsNone(t["parent"])
            self.assertEqual(t["children"], [])
            self.assertEqual(t["kind"], "finding")
            self.assertEqual(t["prompted_by"], "1-1")
            # 不进任何 plan 节点的 children
            self.assertNotIn(t["id"], rm.get_node("1-1").get("children", []))
            self.assertIn(t["id"], rm.node_ids(layer=LAYER_TRACE))



    def test_provenance_edge_written_for_from(self):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, _ = self._add("single", tmpd)
            # 第一条 trace
            run_cli("trace", "add", path, "--kind", "finding", "--body", "first", cwd=tmpd)
            rm = load_carrier("single", path)
            first = rm.node_ids(layer=LAYER_TRACE)[0]
            # 第二条 trace 引用第一条
            run_cli("trace", "add", path, "--kind", "attempt", "--body", "second",
                    "--under", "1-1", "--from", first, cwd=tmpd)
            rm2 = load_carrier("single", path)
            edges = rm2.list_edges()
            mainline = [e for e in edges if e["type"] == "mainline"]
            self.assertEqual(len(mainline), 1)
            self.assertEqual(mainline[0]["from"], rm2.node_ids(layer=LAYER_TRACE)[2])
            self.assertEqual(mainline[0]["to"], first)


class TraceGuardTest(unittest.TestCase):
    """§3.6 / §3.4 负向：非法 trace 写入路径当场被拒，断言 code。"""

    def _seed(self, storage: str, tmpd: Path):
        path = tmpd / TARGETS[storage]
        if storage == "sqlite":
            run_cli("init", path, "--storage", "sqlite", "--title", "t", cwd=tmpd)
        else:
            run_cli("init", path, "--title", "t", cwd=tmpd)
        run_cli("add", path, "1", "child-A", cwd=tmpd)
        run_cli("trace", "add", path, "--kind", "finding", "--body", "b", "--under", "1-1", cwd=tmpd)
        return path

    def test_under_a_trace_node_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path = self._seed("single", tmpd)
            rm = load_carrier("single", path)
            trace_id = rm.node_ids(layer=LAYER_TRACE)[0]
            p = run_cli("trace", "add", path, "--kind", "finding", "--body", "x",
                        "--under", trace_id, check=False, cwd=tmpd)
            self.assertEqual(p.returncode, 1)
            self.assertIn("E_PROMOTE_TARGET_INVALID", p.stderr)

    def test_from_missing_trace_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path = self._seed("single", tmpd)
            p = run_cli("trace", "add", path, "--kind", "finding", "--body", "x",
                        "--under", "1-1", "--from", "9-999", check=False, cwd=tmpd)
            self.assertEqual(p.returncode, 1)
            self.assertIn("E_TRACE_NOT_FOUND", p.stderr)

    def test_invalid_kind_rejected_with_code(self):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path = self._seed("sqlite", tmpd)
            p = run_cli("trace", "add", path, "--kind", "bogus", "--body", "x",
                        "--under", "1-1", check=False, cwd=tmpd)
            self.assertEqual(p.returncode, 1)
            self.assertIn("E_INVALID_KIND", p.stderr)


class TraceReadTest(unittest.TestCase):
    """trace list / trace get 能取回 trace 节点。"""

    def test_list_and_get_return_trace(self):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path = tmpd / TARGETS["single"]
            run_cli("init", path, "--title", "t", cwd=tmpd)
            run_cli("add", path, "1", "child-A", cwd=tmpd)
            run_cli("trace", "add", path, "--kind", "doubt", "--body", "hmm", "--under", "1-1", cwd=tmpd)
            lst = json.loads(run_cli("trace", "list", path, cwd=tmpd).stdout)
            self.assertEqual(len(lst), 1)
            self.assertEqual(lst[0]["layer"], LAYER_TRACE)
            tid = lst[0]["id"]
            got = json.loads(run_cli("trace", "get", path, tid, cwd=tmpd).stdout)
            self.assertEqual(got["id"], tid)
            self.assertEqual(got["kind"], "doubt")


if __name__ == "__main__":
    unittest.main(verbosity=2)
