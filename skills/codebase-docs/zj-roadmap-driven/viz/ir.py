#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S1（最小贯通）：view-ir —— 所有投影共享的唯一中间表示 + anchor 信封。

view-ir 是确定性、可逐字节回归的数据；HTML / Mermaid 都从它（或等价的客户端重算）派生。
anchor 信封（zj-roadmap-anchor/v1）携带 view-kind + carrier-stem + node-uid + carrier revision，
保证视图可追溯到源 carrier 而不污染 carrier 本身。
"""
from __future__ import annotations

from . import doi
from .graph import RoadmapGraph


def build_view(focus: str, graph: RoadmapGraph, theta: float | None = None, expand: bool = False) -> dict:
    """构建单个焦点的 view-ir。

    Args:
        focus: 焦点节点 id。
        graph: 归一化图。
        theta: 固定 θ；None 时取该焦点百分位校准的中档（neighborhood）。
        expand: 是否把折叠项（rest）全部展开为独立节点。
    Returns:
        IR dict（envelope + selection + rest + expanded_set + cards + presets）。
    """
    presets = doi.theta_presets(focus, graph)
    if theta is None:
        theta = presets["neighborhood"]
    res = doi.select(focus, theta, graph)

    # 邻域 = 焦点 ∪ 阻塞前驱 ∪ 后继 ∪ blocks 邻居
    nbhd = {focus}
    nbhd |= set(res["pdepth"].keys())
    nbhd |= set(graph.succ.get(focus, set()))
    nbhd |= set(graph.adj.get(focus, []))
    rest = [nid for nid in res["shown"] if nid not in nbhd] + [
        nid for nid in nbhd if nid not in res["shown"]
    ]

    exp_set = set(rest) if expand else set()
    shown_eff = list(res["shown"])
    lod_eff = dict(res["lod"])
    used_eff = res["used"]
    if expand:
        for nid in exp_set:
            if nid not in lod_eff:
                lod_eff[nid] = "L0"
                shown_eff.append(nid)
                used_eff += doi.COST["L0"]

    cards = {}
    for nid in shown_eff:
        n = graph.nodes[nid]
        db = graph.debt.get(nid, {})
        cards[nid] = {
            "id": nid,
            "uid": graph.uid.get(nid),
            "label": n.get("label", ""),
            "status": n.get("status"),
            "mode": n.get("mode"),
            "rounds": n.get("rounds"),
            "parent": n.get("parent"),
            "layer": graph.layer.get(nid, nid.count("-")),
            "notes": n.get("notes", ""),
            "decisions": n.get("decisions", []),
            "exit_criteria": n.get("exit_criteria"),
            "budget": n.get("budget"),
            "lod": lod_eff[nid],
            "doi": res["by_id"][nid]["d"],
            "debt_level": db.get("level", "none"),
            "debt_hits": db.get("hits", []),
            "is_focus": nid == focus,
            "is_block_pred": nid in res["pdepth"],
            "is_sibling": (graph.parent.get(nid) == res["fp"] and nid != focus),
        }

    envelope = {
        "view_kind": "zj-roadmap-visual-review/v1",
        "carrier_stem": graph.carrier_stem,
        "node_uid": graph.uid.get(focus),
        "carrier_revision": graph.revision,
        "focus": focus,
        "theta": theta,
        "generated_by": "zj-roadmap-driven/viz",
    }
    return {
        "envelope": envelope,
        "selection": {
            "shown": shown_eff,
            "lod": lod_eff,
            "compressed": res["compressed"],
            "theta": theta,
            "theta_folded": res["theta_folded"],
            "budget_folded": res["budget_folded"],
            "used": used_eff,
            "budget": doi.BUDGET,
            "mandatory": sorted(res["mandatory"]),
            "pdepth": res["pdepth"],
            "fp": res["fp"],
        },
        "rest": rest,
        "expanded_set": sorted(exp_set),
        "cards": cards,
        "presets": presets,
    }
