#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S3（dependency 投影与边回溯）/ S4（context side-pack 与 stale 标记）出口判据测试。

先红后绿：本文件在实现落地前应因 `from viz import dependency, context` 失败而红。

运行（anaconda3 python3）：
  cd skills/codebase-docs/zj-roadmap-driven
  python -m unittest viz.tests.test_viz viz.tests.test_s3_s4 -v

判据来源：docs/designs/zj-roadmap-visual-review-technical.md 的 Consequences 切片表
  S3 | 阻塞链、critical-path、impact 与视图同源；点击边可回溯边 id 与来源
  S4 | 上下文条目增长时主视图字节不变；revision 不符时显式 stale 且不自动刷新
"""
from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent
VIZ = HERE.parent
SKILL = VIZ.parent
if str(SKILL) not in sys.path:
    sys.path.insert(0, str(SKILL))

from viz import context, dependency  # noqa: E402
from viz.graph import RoadmapGraph  # noqa: E402
from viz.ir import build_view  # noqa: E402
from viz.render_html import render_html  # noqa: E402

SAMPLE = VIZ.parent / "demos" / "roadmap_viz_sample.json"


def load_sample() -> dict:
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


class TestS3Dependency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_sample()
        cls.graph = RoadmapGraph.from_data(cls.data, carrier_stem="roadmap_viz_sample")

    def test_blocked_by_matches_s1_ir_pdepth(self):
        """同源证据 1：阻塞链与 S1 的 view-ir selection.pdepth 完全一致。"""
        focus = "1-2"
        dep = dependency.build_dependency(focus, self.graph)
        view = build_view(focus, self.graph)
        self.assertEqual(set(dep["blocked_by"]), set(view["selection"]["pdepth"]) - {focus})
        self.assertEqual(dep["envelope"]["carrier_revision"], view["envelope"]["carrier_revision"])
        self.assertEqual(dep["envelope"]["node_uid"], view["envelope"]["node_uid"])

    def test_impact_matches_roadmap_cli(self):
        """同源证据 2：impact 与 roadmap_cli 的 impact_node_ids 同一边界（只沿 blocks）。"""
        import roadmap
        expected = roadmap.impact_node_ids("1-2", list(self.graph.nodes.values()), self.graph.edges)
        dep = dependency.build_dependency("1-2", self.graph)
        self.assertEqual(dep["impact"], expected)

    def test_critical_path_matches_roadmap_cli(self):
        """同源证据 3：critical-path 与 roadmap_cli 的 critical_path 结果一致。"""
        import roadmap
        expected = roadmap.critical_path(list(self.graph.nodes.values()), self.graph.edges)
        dep = dependency.build_dependency("1-2", self.graph)
        self.assertEqual(dep["critical_path"], expected)

    def test_critical_path_is_focus_independent(self):
        """critical-path 是全局查询，不随焦点漂移（不得被当成焦点的局部链）。"""
        a = dependency.build_dependency("1-2", self.graph)["critical_path"]
        b = dependency.build_dependency("4-1", self.graph)["critical_path"]
        self.assertEqual(a, b)

    def test_edge_meta_covers_every_blocks_edge_with_traceable_source(self):
        meta = dependency.build_edge_meta(self.graph)
        self.assertEqual(len(meta), len(self.graph.edges))
        ids = [m["edge_id"] for m in meta]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids[0], "e-1")  # sample 首条 uid
        for i, m in enumerate(meta):
            self.assertTrue(m["edge_id"])
            self.assertEqual(m["from"], self.graph.edges[i].get("from"))
            self.assertEqual(m["to"], self.graph.edges[i].get("to"))
            self.assertEqual(m["type"], "blocks")
            self.assertEqual(m["source"]["field"], "edges")
            self.assertEqual(m["source"]["index"], i)
            self.assertEqual(m["source"]["carrier_stem"], self.graph.carrier_stem)
            self.assertTrue(m["source"]["evidence_ref"])  # 缺失也必须显式 unknown

    def test_dependency_edges_carry_backtrace(self):
        dep = dependency.build_dependency("1-2", self.graph)
        self.assertTrue(dep["edges"])
        for e in dep["edges"]:
            self.assertIn("edge_id", e)
            self.assertIn("source", e)
            self.assertTrue(e["source"]["field"])
        self.assertTrue(any(e["from"] == "1-1" and e["to"] == "1-2" for e in dep["edges"]))

    def test_dependency_mermaid_mentions_edge_ids(self):
        dep = dependency.build_dependency("1-2", self.graph)
        mmd = dependency.to_dependency_mermaid(dep)
        self.assertTrue(mmd.startswith("flowchart TB"))
        for e in dep["edges"]:
            self.assertIn(e["edge_id"], mmd)

    def test_html_edges_carry_backtrace_hook(self):
        """主视图每条 blocks 边都挂 edge id，点击可回溯来源。"""
        html = render_html(self.graph, "1-2", edge_meta=dependency.build_edge_meta(self.graph))
        self.assertIn("data-edge=", html)
        self.assertIn("EDGE_META", html)
        self.assertIn("e-1", html)

    def test_no_carrier_mutation(self):
        data = load_sample()
        before = deepcopy(data)
        g = RoadmapGraph.from_data(data, carrier_stem="x")
        for f in ("1-2", "4-1"):
            dependency.build_dependency(f, g)
            dependency.build_edge_meta(g)
        self.assertEqual(data, before)


class TestS4Context(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_sample()
        cls.graph = RoadmapGraph.from_data(cls.data, carrier_stem="roadmap_viz_sample")

    @staticmethod
    def _with_context(n: int) -> dict:
        data = load_sample()
        data["context"] = {
            "1-2": [
                {"kind": "trace", "text": f"trace-{i}", "evidence_ref": "self"}
                for i in range(n)
            ]
        }
        return data

    def test_main_view_bytes_stable_when_context_grows(self):
        """S4 硬判据：侧载条目 1 → 12 条，主视图 HTML 逐字节不变。"""
        g1 = RoadmapGraph.from_data(self._with_context(1), carrier_stem="same")
        g2 = RoadmapGraph.from_data(self._with_context(12), carrier_stem="same")
        p1 = context.build_context_pack("1-2", g1)
        p2 = context.build_context_pack("1-2", g2)
        self.assertGreater(p2["entry_count"], p1["entry_count"])
        self.assertEqual(render_html(g1, "1-2"), render_html(g2, "1-2"))

    def test_context_pack_is_side_loaded_not_embedded(self):
        data = deepcopy(self.data)
        data["context"] = {
            "1-2": [{"kind": "trace", "text": "UNIQUE_SIDE_PACK_MARKER", "evidence_ref": "self"}]
        }
        g = RoadmapGraph.from_data(data, carrier_stem="same")
        html = render_html(g, "1-2")
        self.assertNotIn("UNIQUE_SIDE_PACK_MARKER", html)
        pack = json.dumps(context.build_context_pack("1-2", g), ensure_ascii=False)
        self.assertIn("UNIQUE_SIDE_PACK_MARKER", pack)

    def test_every_context_entry_has_source_and_evidence_ref(self):
        pack = context.build_context_pack("1-2", self.graph)
        self.assertEqual(pack["entry_count"], len(pack["entries"]))
        self.assertIn(pack["bfs_radius"], (1, 2, 3))
        for e in pack["entries"]:
            self.assertTrue(e["entry_id"])
            self.assertTrue(e["kind"])
            self.assertTrue(e["source"])
            self.assertTrue(e["evidence_ref"])  # 无证据时也必须显式 unknown，不静默留空

    def test_anchor_roundtrip_deterministic(self):
        env = {
            "view_kind": "zj-roadmap-visual-review/context-v1",
            "carrier_stem": "roadmap_viz_sample",
            "node_uid": "u-1-2",
            "carrier_revision": "viz-sample-1",
        }
        t1 = context.encode_anchor(env)
        t2 = context.encode_anchor(env)
        self.assertEqual(t1, t2)
        self.assertTrue(t1.startswith("zj-roadmap-anchor/v1|"))
        self.assertEqual(context.decode_anchor(t1), env)

    def test_anchor_decode_rejects_foreign_prefix(self):
        with self.assertRaises(ValueError):
            context.decode_anchor("not-an-anchor")

    def test_stale_when_revision_mismatch(self):
        st = context.revision_status(self.graph, expected_revision="OLD-REV")
        self.assertTrue(st["checked"])
        self.assertTrue(st["stale"])
        self.assertEqual(st["expected_revision"], "OLD-REV")
        self.assertEqual(st["carrier_revision"], self.graph.revision)
        self.assertIn("python -m viz.cli", st["refresh_command"])
        self.assertFalse(st["auto_refresh"])
        # ADR 0010：刷新命令不替 Human 编造落 cwd 的默认产物路径
        self.assertIn("<X.html>", st["refresh_command"])
        self.assertNotIn("roadmap_viz_sample.dependency.json", st["refresh_command"])

    def test_fresh_revision_not_stale(self):
        st = context.revision_status(self.graph, expected_revision=self.graph.revision)
        self.assertTrue(st["checked"])
        self.assertFalse(st["stale"])
        self.assertFalse(st["auto_refresh"])

    def test_stale_via_anchor_token(self):
        env = {
            "view_kind": "zj-roadmap-visual-review/context-v1",
            "carrier_stem": "roadmap_viz_sample",
            "node_uid": "u-1-2",
            "carrier_revision": "OLD-REV",
        }
        st = context.revision_status(self.graph, anchor=context.encode_anchor(env))
        self.assertTrue(st["checked"])
        self.assertTrue(st["stale"])
        self.assertFalse(st["auto_refresh"])

    def test_no_expected_revision_is_unchecked_not_stale(self):
        st = context.revision_status(self.graph)
        self.assertFalse(st["checked"])
        self.assertFalse(st["stale"])
        self.assertIsNone(st["refresh_command"])

    def test_stale_is_visible_in_view_only_when_detected(self):
        fresh = render_html(self.graph, "1-2")
        st = context.revision_status(self.graph, expected_revision="OLD-REV")
        stale = render_html(self.graph, "1-2", revision_status=st)
        self.assertIn('"stale": false', fresh)
        self.assertIn('"stale": true', stale)
        self.assertNotEqual(fresh, stale)

    def test_main_view_bytes_stable_when_node_side_fields_grow(self):
        """节点内的 context / traces 增长也必须不改变主视图一个字节。

        这是白名单真正起作用的地方：顶层 context 本来就不在 nodes 里，
        只有节点内侧载字段才能证明 DISPLAY_FIELDS 不是摆设。
        """
        small = deepcopy(self.data)
        big = deepcopy(self.data)
        small["nodes"]["1-2"]["traces"] = ["t0"]
        small["nodes"]["1-2"]["context"] = [{"kind": "trace", "text": "t0"}]
        big["nodes"]["1-2"]["traces"] = [f"t{i}" for i in range(15)]
        big["nodes"]["1-2"]["context"] = [{"kind": "trace", "text": f"t{i}"} for i in range(15)]
        g1 = RoadmapGraph.from_data(small, carrier_stem="same")
        g2 = RoadmapGraph.from_data(big, carrier_stem="same")
        self.assertGreater(
            context.build_context_pack("1-2", g2)["entry_count"],
            context.build_context_pack("1-2", g1)["entry_count"],
        )
        self.assertEqual(render_html(g1, "1-2"), render_html(g2, "1-2"))

    def test_whitelist_guard_is_not_a_vacuous_assertion(self):
        """负向探针：朴素地整 node 内联必然泄漏侧载字段，白名单必须挡住。"""
        data = deepcopy(self.data)
        data["nodes"]["1-2"]["traces"] = ["LEAK_MARKER"]
        naive_embed = json.dumps(data["nodes"], ensure_ascii=False)
        self.assertIn("LEAK_MARKER", naive_embed)  # 缺陷态可观测
        g = RoadmapGraph.from_data(data, carrier_stem="same")
        self.assertNotIn("LEAK_MARKER", render_html(g, "1-2"))  # 当前实现不泄漏
        pack = json.dumps(context.build_context_pack("1-2", g), ensure_ascii=False)
        self.assertIn("LEAK_MARKER", pack)  # 但侧载包必须拿到它

    def test_no_carrier_mutation(self):
        data = self._with_context(3)
        before = deepcopy(data)
        g = RoadmapGraph.from_data(data, carrier_stem="x")
        context.build_context_pack("1-2", g)
        context.revision_status(g, expected_revision="OLD")
        self.assertEqual(data, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
