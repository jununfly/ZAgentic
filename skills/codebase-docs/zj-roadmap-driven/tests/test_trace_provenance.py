#!/usr/bin/env python3
"""#119 身份 provenance —— TDD 套件（spec §8.3）。

P5-S2 的 trace add（#133）只落了**因果** provenance（prompted_by + from→mainline
边）。本套件补 #133 没做的**身份** provenance：trace 节点诞生即写
`agent_id` / `device_id` / `session_ref` / `compressed_from`，CLI 暴露对应参数。

验收（来自 spec §8.3 + 项目「两 carrier 同语义」不变式）：
- `trace add` 接受 --session-ref / --agent-id / --device-id / --compressed-from，
  写进节点；`trace get` 返回。
- 缺省时字符串字段为 ""，compressed_from 不出现。
- 带 provenance 追加后，所有 plan 遍历输出字节不变（trace 不泄进视图）。

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
    LAYER_TRACE,
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


def load_carrier(storage: str, path: Path):
    if storage == "single":
        rm = Roadmap(str(path))
    else:
        rm = RoadmapSqlite(str(path))
    rm.load()
    return rm


TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?")


def normalize(s: str) -> str:
    """归一时间戳，让两次快照的字节比较不受"现在"影响。"""
    return TS_RE.sub("TS", s)


class TraceProvenanceSessionRefTest(unittest.TestCase):
    """Slice 1: --session-ref 写进 trace 节点，trace get 返回。"""

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

    def test_single_file_session_ref_written(self):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, _ = self._add("single", tmpd, extra=["--session-ref", "sess-42"])
            rm = load_carrier("single", path)
            t = rm.iter_nodes(layer=LAYER_TRACE)[0]
            self.assertEqual(t["session_ref"], "sess-42")
            # CLI trace get 也返回
            out = run_cli("trace", "get", path, t["id"], cwd=tmpd)
            self.assertEqual(json.loads(out.stdout)["session_ref"], "sess-42")


    def test_sqlite_session_ref_written(self):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, _ = self._add("sqlite", tmpd, extra=["--session-ref", "sess-42"])
            rm = load_carrier("sqlite", path)
            t = rm.iter_nodes(layer=LAYER_TRACE)[0]
            self.assertEqual(t["session_ref"], "sess-42")
            out = run_cli("trace", "get", path, t["id"], cwd=tmpd)
            self.assertEqual(json.loads(out.stdout)["session_ref"], "sess-42")


class TraceProvenanceAgentDeviceTest(unittest.TestCase):
    """Slice 2: --agent-id / --device-id 写进 trace 节点，缺省为 ""。"""

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

    def test_single_file_agent_device_written(self):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, _ = self._add("single", tmpd, extra=["--agent-id", "a7", "--device-id", "win"])
            t = load_carrier("single", path).iter_nodes(layer=LAYER_TRACE)[0]
            self.assertEqual(t["agent_id"], "a7")
            self.assertEqual(t["device_id"], "win")


    def test_sqlite_agent_device_written(self):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, _ = self._add("sqlite", tmpd, extra=["--agent-id", "a7", "--device-id", "win"])
            t = load_carrier("sqlite", path).iter_nodes(layer=LAYER_TRACE)[0]
            self.assertEqual(t["agent_id"], "a7")
            self.assertEqual(t["device_id"], "win")

    def test_single_file_agent_device_default_empty(self):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, _ = self._add("single", tmpd)
            t = load_carrier("single", path).iter_nodes(layer=LAYER_TRACE)[0]
            self.assertEqual(t["agent_id"], "")
            self.assertEqual(t["device_id"], "")
            self.assertEqual(t["session_ref"], "")


class TraceProvenanceCompressedFromTest(unittest.TestCase):
    """Slice 3: --compressed-from <id[,id]> 解析为 uid 列表写进节点。"""

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

    def _assert_compressed(self, storage: str, tmpd: Path, path: Path):
        rm = load_carrier(storage, path)
        # 压缩两条 plan 子节点；compressed_from 存的是经 resolve_node 解析后的引用
        expected = [rm.resolve_node("1-1"), rm.resolve_node("1-2")]
        run_cli("trace", "add", path, "--kind", "finding", "--body", "merged",
                "--compressed-from", "1-1,1-2", cwd=tmpd)
        # 子进程写盘，必须重新加载
        rm2 = load_carrier(storage, path)
        t = rm2.iter_nodes(layer=LAYER_TRACE)[0]
        self.assertEqual(t["compressed_from"], expected)
        # 顺序保留、数量正确、每个引用可回解到原节点（carrier 无关）
        self.assertEqual(len(t["compressed_from"]), 2)
        self.assertEqual(
            {rm2.resolve_node(i) for i in t["compressed_from"]},
            {rm.resolve_node("1-1"), rm.resolve_node("1-2")},
        )

    def test_single_file_compressed_from(self):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, _ = self._seed("single", tmpd)
            self._assert_compressed("single", tmpd, path)


    def test_sqlite_compressed_from(self):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, _ = self._seed("sqlite", tmpd)
            self._assert_compressed("sqlite", tmpd, path)

    def test_single_file_compressed_from_default_empty_list(self):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, _ = self._seed("single", tmpd)
            run_cli("trace", "add", path, "--kind", "finding", "--body", "x", cwd=tmpd)
            t = load_carrier("single", path).iter_nodes(layer=LAYER_TRACE)[0]
            self.assertEqual(t["compressed_from"], [])


class TraceProvenanceInvarianceTest(unittest.TestCase):
    """Slice 4: 带全部身份 provenance 追加 trace 后，plan 遍历输出字节不变（§2.9）。"""

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
            self.assertEqual(normalize(before[key]), normalize(after[key]), f"{key} 输出因 trace provenance 而变化")

    def test_single_file_traversal_unchanged_with_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, md = self._seed("single", tmpd)
            before = self._snapshot(path, md)
            run_cli("trace", "add", path, "--kind", "finding", "--body", "b", "--under", "1-1",
                    "--session-ref", "sess-9", "--agent-id", "a7", "--device-id", "win",
                    "--compressed-from", "1-2", cwd=tmpd)
            after = self._snapshot(path, md)
            self._assert_byte_identical(before, after)


    def test_sqlite_traversal_unchanged_with_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            tmpd = Path(d)
            path, md = self._seed("sqlite", tmpd)
            before = self._snapshot(path, md)
            run_cli("trace", "add", path, "--kind", "finding", "--body", "b", "--under", "1-1",
                    "--session-ref", "sess-9", "--agent-id", "a7", "--device-id", "win",
                    "--compressed-from", "1-2", cwd=tmpd)
            after = self._snapshot(path, md)
            self._assert_byte_identical(before, after)


if __name__ == "__main__":
    unittest.main()
