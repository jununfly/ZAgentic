#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""zj-roadmap-driven / viz —— S0 + S2 出口判据与只读不变式测试。

运行：
  /Users/bilibili/anaconda3/bin/python3 viz/tests/test_viz.py
或直接：
  cd skills/codebase-docs/zj-roadmap-driven && /Users/bilibili/anaconda3/bin/python3 -m viz.tests.test_viz

覆盖：
  S0 出口判据
    - DOI 权重和 == 1.0
    - 阈值严格递降（overview > neighborhood > expand）
    - 预算溢出不静默（budget_folded 显式报数；used 不超 BUDGET）
    - 三类必备项（焦点 / 阻塞前驱 / 后继 / 高严重度债务）全在可见集 V
    - receipt 不进 carrier（build_view 不污染传入 data）
    - 三档 LOD 单调 + 预算 ≤ 40
  S2 投影正确 + 不污染源
    - 默认焦点、IR 关键字段、Mermaid 文本等价物、compound 折叠节点
"""
from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path

# 把 viz 包的父目录加入 import 路径（与 skill 测试约定一致：插入包根，直接 import viz.*）
HERE = Path(__file__).resolve().parent
VIZ = HERE.parent  # .../zj-roadmap-driven/viz
SKILL = VIZ.parent  # .../zj-roadmap-driven（viz 在此作为包被发现）
if str(SKILL) not in sys.path:
    sys.path.insert(0, str(SKILL))

from viz import doi  # noqa: E402
from viz.graph import RoadmapGraph, layer_of, edge_endpoints, debt_signal, build_debt  # noqa: E402
from viz.ir import build_view  # noqa: E402
from viz.render_mermaid import to_mermaid  # noqa: E402

SAMPLE = VIZ.parent / "demos" / "roadmap_viz_sample.json"


def load_sample() -> dict:
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


class TestS0Constants(unittest.TestCase):
    def test_weights_sum_to_one(self):
        s = sum(doi.WEIGHTS.values())
        self.assertAlmostEqual(s, 1.0, places=9)

    def test_weights_keys_complete(self):
        expected = {
            "T1_graph_proximity", "T2_blocking_criticality", "T3_shared_context",
            "T4_debt_severity", "T5_recency", "T6_stability_penalty",
        }
        self.assertEqual(set(doi.WEIGHTS.keys()), expected)

    def test_thresholds_strictly_decreasing(self):
        t = doi.THRESHOLDS
        self.assertGreater(t["overview"], t["neighborhood"])
        self.assertGreater(t["neighborhood"], t["expand"])
        # 且都落在 (0,1]
        for v in t.values():
            self.assertTrue(0 < v <= 1.0)

    def test_cost_and_budget_positive(self):
        self.assertTrue(all(v > 0 for v in doi.COST.values()))
        self.assertGreater(doi.BUDGET, 0)


class TestS0Selection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_sample()
        cls.graph = RoadmapGraph.from_data(cls.data, carrier_stem="roadmap_viz_sample")

    def test_mandatory_all_in_shown(self):
        """三类必备项（焦点 + 阻塞前驱 + 后继 + 高严重度债务）必须全部进入可见集 V。"""
        for focus in self.graph.nodes:
            presets = doi.theta_presets(focus, self.graph)
            for theta in (None, presets["overview"], presets["neighborhood"], presets["expand"]):
                th = theta if theta is not None else presets["neighborhood"]
                res = doi.select(focus, th, self.graph)
                shown = set(res["shown"])
                # 焦点自身
                self.assertIn(focus, shown)
                # 阻塞前驱（pdepth 非空键）
                for p in res["pdepth"]:
                    self.assertIn(p, shown)
                # 后继
                for s in self.graph.succ.get(focus, set()):
                    self.assertIn(s, shown)
                # 高严重度债务
                for nid, db in self.graph.debt.items():
                    if db.get("level") == "high":
                        self.assertIn(nid, shown)

    def test_budget_not_silent_and_bounded(self):
        """预算溢出不静默：budget_folded 显式报数；used 不超 BUDGET。"""
        for focus in self.graph.nodes:
            presets = doi.theta_presets(focus, self.graph)
            th = presets["neighborhood"]
            res = doi.select(focus, th, self.graph)
            self.assertLessEqual(res["used"], doi.BUDGET)
            # 折叠项分类守恒：theta 截 + 预算截 == 总压缩
            self.assertEqual(
                res["theta_folded"] + res["budget_folded"], len(res["compressed"])
            )
            # 压缩集合内的节点 d<theta 必归 theta_folded（否则归 budget_folded）
            by_id = res["by_id"]
            for nid in res["compressed"]:
                if by_id[nid]["d"] < th:
                    self.assertEqual(res["lod"][nid], "COMPRESSED")
            self.assertGreaterEqual(res["budget_folded"], 0)

    def test_lod_three_tier_monotonic(self):
        """三档 LOD 取值集合合法；focus=L2，必备非焦点=L1；候选层级单调（d 越高不应越被压）。"""
        allowed = {"L2", "L1", "L0", "COMPRESSED"}
        for focus in self.graph.nodes:
            presets = doi.theta_presets(focus, self.graph)
            res = doi.select(focus, presets["neighborhood"], self.graph)
            for nid, lod in res["lod"].items():
                self.assertIn(lod, allowed)
                if nid == focus:
                    self.assertEqual(lod, "L2")
                elif nid in res["mandatory"]:
                    self.assertEqual(lod, "L1")
            # 单调：任意两候选，DOI 高者 LOD 档位不低于 DOI 低者
            rank = {"COMPRESSED": 0, "L0": 1, "L1": 2, "L2": 3}
            cand = [(by["d"], rank[res["lod"][by["id"]]]) for by in res["scores"]
                    if by["id"] not in res["mandatory"]]
            cand.sort(key=lambda x: x[0])
            for i in range(1, len(cand)):
                self.assertLessEqual(cand[i - 1][1], cand[i][1])

    def test_determinism(self):
        """同输入同输出（无随机 / 无 LLM）。"""
        focus = "1-2"
        presets = doi.theta_presets(focus, self.graph)
        a = doi.select(focus, presets["neighborhood"], self.graph)
        b = doi.select(focus, presets["neighborhood"], self.graph)
        self.assertEqual(a["shown"], b["shown"])
        self.assertEqual(a["lod"], b["lod"])
        self.assertEqual(a["compressed"], b["compressed"])


class TestS0Debt(unittest.TestCase):
    def test_explicit_debt_wins(self):
        """显式 debts 优先于文本启发。"""
        nodes = {
            "a": {"id": "a", "notes": "风险很高", "decisions": []},
            "b": {"id": "b", "notes": "", "decisions": []},
        }
        debt = build_debt(nodes, [{"anchor": "b", "kind": "gap", "severity": "high"}])
        # b 无文本命中，但显式 high → level=high
        self.assertEqual(debt["b"]["level"], "high")
        # a 文本命中「风险」→ high
        self.assertEqual(debt["a"]["level"], "high")

    def test_notes_alone_not_debt(self):
        """节点有 notes 但无债务关键词 → 不计债务（不自动晋升）。"""
        # 注意避开债务关键词：风险/risk/缺口/gap/缺失/不一致/返工/错误 + todo/待/sweep/清理/核对/跟进/补/未覆盖/隐患
        node = {"id": "x", "notes": "本节点已完成常规实现，需要后续评审。", "decisions": []}
        sig = debt_signal(node)
        self.assertEqual(sig["level"], "none")
        self.assertEqual(sig["score"], 0.0)

    def test_keyword_heuristic_medium(self):
        node = {"id": "x", "notes": "", "decisions": [{"text": "todo 待核对"}]}
        sig = debt_signal(node)
        self.assertEqual(sig["level"], "medium")
        self.assertGreater(sig["score"], 0.0)

    def test_high_severity_flagged(self):
        graph = RoadmapGraph.from_data(load_sample())
        # sample 显式 high 债务：4-1-1 / 3-1-1
        for nid in ("4-1-1", "3-1-1"):
            self.assertEqual(graph.debt[nid]["level"], "high")


class TestS0ReadonlyContract(unittest.TestCase):
    def test_no_carrier_mutation(self):
        """receipt 不进 carrier：build_view 不得修改传入 data / 其内部节点。"""
        data = load_sample()
        before = deepcopy(data)
        graph = RoadmapGraph.from_data(data, carrier_stem="roadmap_viz_sample")
        # 反复构建多个焦点的 view，确认 data 始终不变
        for focus in list(data["nodes"].keys())[:5]:
            build_view(focus, graph)
        self.assertEqual(data, before)

    def test_graph_from_data_keeps_nodes(self):
        data = load_sample()
        g = RoadmapGraph.from_data(deepcopy(data))
        self.assertEqual(set(g.nodes.keys()), set(data["nodes"].keys()))
        # 原始 data 的 nodes 字段不应被改写（仍是 dict）
        self.assertIsInstance(data["nodes"], dict)

    def test_edge_endpoints_both_forms(self):
        self.assertEqual(edge_endpoints({"from": "a", "to": "b", "type": "blocks"}), ("a", "b", "blocks"))
        self.assertEqual(edge_endpoints({"from_uid": "a", "to_uid": "b", "type": "blocks"}), ("a", "b", "blocks"))

    def test_layer_of(self):
        self.assertEqual(layer_of("1"), 0)
        self.assertEqual(layer_of("1-2"), 1)
        self.assertEqual(layer_of("1-2-3"), 2)


class TestS2Projection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_sample()
        cls.graph = RoadmapGraph.from_data(cls.data, carrier_stem="roadmap_viz_sample")

    def test_view_keys(self):
        view = build_view("1-2", self.graph)
        for key in ("envelope", "selection", "rest", "expanded_set", "cards", "presets"):
            self.assertIn(key, view)
        self.assertEqual(view["envelope"]["view_kind"], "zj-roadmap-visual-review/v1")
        self.assertEqual(view["envelope"]["focus"], "1-2")
        self.assertEqual(view["envelope"]["carrier_stem"], "roadmap_viz_sample")

    def test_cards_match_shown(self):
        view = build_view("1-2", self.graph)
        self.assertEqual(set(view["cards"].keys()), set(view["selection"]["shown"]))
        # 焦点卡片标注 is_focus
        self.assertTrue(view["cards"]["1-2"]["is_focus"])

    def test_mermaid_equiv(self):
        view = build_view("1-2", self.graph)
        mmd = to_mermaid(view, self.graph)
        self.assertTrue(mmd.startswith("flowchart TB"))
        # 可见节点都在 mermaid 里
        for nid in view["selection"]["shown"]:
            self.assertIn(nid, mmd)
        # 有折叠项时出现复合节点
        if view["rest"]:
            self.assertIn("COMPOSITE", mmd)

    def test_focus_default_exists(self):
        from viz.cli import default_focus
        self.assertIsNotNone(default_focus(self.graph))
        self.assertIn(default_focus(self.graph), self.graph.nodes)

    def test_expand_adds_rest(self):
        view = build_view("1", self.graph, expand=True)
        self.assertEqual(set(view["expanded_set"]), set(view["rest"]))
        # 展开后 shown 包含全部 rest
        for nid in view["rest"]:
            self.assertIn(nid, view["selection"]["shown"])


class TestS0TinyGraphFallback(unittest.TestCase):
    """极小图（无候选）→ theta_presets 退化为 spec 声明阈值。"""

    def test_presets_fallback(self):
        data = {
            "nodes": {"1": {"id": "1", "parent": None}},
            "edges": [],
            "debts": [],
        }
        g = RoadmapGraph.from_data(data)
        presets = doi.theta_presets("1", g)
        self.assertEqual(presets, dict(doi.THRESHOLDS))


if __name__ == "__main__":
    unittest.main(verbosity=2)
