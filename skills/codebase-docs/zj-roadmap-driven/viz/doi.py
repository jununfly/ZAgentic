#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S0：确定性 DOI 选择 + 阅读预算 + 债务 schema + receipt 契约。

对应 spec `information-selection`：DOI 函数（确定性、非 LLM）、阅读预算（硬上限、不静默丢弃）、
债务 schema（gap/todo/risk/sweep 一等建模，不自动晋升）、reentry receipt（不进 carrier）。

DOI = 六权重加权，权重与 spec `doi-function.terms` 严格一致（sum == 1.0）：
  T1 图邻近  0.30  焦点自身 = 1.0（spec DOI::T1 graph-proximity）
  T2 阻塞关键 0.25  blocks 上游距离（spec DOI::T2 blocking-criticality）
  T3 共享上下文 0.15 同父兄弟 / 同层（spec DOI::T3 shared-context）
  T4 债务严重度 0.15 节点债务分数（spec DOI::T4 debt-severity）
  T5 新鲜度  0.10  status/rounds（spec DOI::T5 recency）
  T6 稳定性惩罚 0.05 远处已完结节点的轻微抑制（spec DOI::T6 stability-penalty）

θ 单一旋钮（A 方案）：θ = 最低可见 DOI 下限。低于 θ → 直接 COMPRESSED（按 θ 折叠）；
高于 θ → 候选 L2，再由 40 行预算逐级降为 L1/L0/COMPRESSED（三档 LOD 仍在）。
强制项（焦点 / 阻塞前驱 / 后继 / 高严重度债务）必在可见集 V 中，不占满预算。
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

# 与 spec information-selection.doi-function.terms 一致，sum == 1.0
WEIGHTS: dict[str, float] = {
    "T1_graph_proximity": 0.30,
    "T2_blocking_criticality": 0.25,
    "T3_shared_context": 0.15,
    "T4_debt_severity": 0.15,
    "T5_recency": 0.10,
    "T6_stability_penalty": 0.05,
}

BUDGET = 40  # reading-budget.max（行）
COST = {"L2": 4, "L1": 2, "L0": 1}  # 三档 LOD 行成本

# spec 声明的默认阈值（R13 要求严格递降）；运行时按焦点百分位校准覆盖（见 theta_presets）
THRESHOLDS: dict[str, float] = {"overview": 0.75, "neighborhood": 0.45, "expand": 0.20}

DEBT_SEVERITIES = ("high", "medium", "low")
DEBT_KINDS = ("gap", "todo", "risk", "sweep")
DEBT_REQUIRED_FIELDS = ("kind", "severity", "anchor_ref", "discovered_revision", "evidence_ref", "state")
DEBT_STATES = ("open", "acknowledged", "mitigated", "resolved")


def bfs_hop(src: str, adj: dict) -> dict[str, int]:
    dist = {src: 0}
    q = [(src, 0)]
    while q:
        u, d = q.pop(0)
        for v in adj.get(u, []):
            if v not in dist:
                dist[v] = d + 1
                q.append((v, d + 1))
    return dist


def rev_bfs(src: str, pred: dict) -> dict[str, int]:
    depth = {src: 0}
    q = [(src, 0)]
    while q:
        u, d = q.pop(0)
        for p in pred.get(u, []):
            if p not in depth:
                depth[p] = d + 1
                q.append((p, d + 1))
    return depth


def recency(node: dict) -> float:
    st = node.get("status")
    b = 0.85 if st == "in_progress" else 0.6 if st == "blocked" else 0.30 if st == "completed" else 0.15
    return min(1.0, b + min(0.10, 0.02 * (node.get("rounds") or 1)))


def doi(node: dict, focus_id: str, hop: dict, pdepth: dict, graph) -> float:
    """确定性 DOI；所有项在 [0,1]，焦点自身 = 1.0。"""
    nid = node["id"]
    if nid == focus_id:
        return 1.0
    t1 = 1 / (1 + hop.get(nid, 99))
    t2 = max(0.2, 1 - 0.2 * (pdepth[nid] - 1)) if nid in pdepth else 0.0
    fp = graph.parent.get(focus_id)
    fl = graph.layer.get(focus_id, focus_id.count("-"))
    t3 = 1.0 if (graph.parent.get(nid) == fp and fp is not None) else (0.4 if graph.layer.get(nid, nid.count("-")) == fl else 0.0)
    t4 = graph.debt.get(nid, {}).get("score", 0.0)
    t5 = recency(node)
    t6 = -1.0 if (node.get("status") == "completed" and nid not in pdepth) else 0.0
    raw = (
        WEIGHTS["T1_graph_proximity"] * t1
        + WEIGHTS["T2_blocking_criticality"] * t2
        + WEIGHTS["T3_shared_context"] * t3
        + WEIGHTS["T4_debt_severity"] * t4
        + WEIGHTS["T5_recency"] * t5
        + WEIGHTS["T6_stability_penalty"] * t6
    )
    return max(0.0, min(1.0, raw))


def mandatory_set(focus: str, pdepth: dict, graph) -> set:
    """三类必备项（spec：焦点 + 阻塞前驱 + 后继 + 高严重度债务）必须全部进入可见集 V。"""
    m = {focus}
    for p in (pdepth or {}):
        m.add(p)
    for s in graph.succ.get(focus, set()):
        m.add(s)
    for nid, db in graph.debt.items():
        if db.get("level") == "high":
            m.add(nid)
    return m


def theta_presets(focus: str, graph) -> dict:
    """按当前焦点下非强制项 DOI 分布取百分位（0.85/0.50/0.15），保证三档在任意焦点下都有可观测差异。

    DOI 是焦点相对量，绝对值随焦点漂移；写死阈值会在部分焦点退化成等价。
    当候选为空（图极小）退化为 spec 声明阈值。
    """
    hop = bfs_hop(focus, graph.adj)
    pdepth = rev_bfs(focus, graph.pred)
    mand = mandatory_set(focus, pdepth, graph)
    cand = sorted(
        doi(graph.nodes[nid], focus, hop, pdepth, graph)
        for nid in graph.nodes
        if nid not in mand
    )
    if not cand:
        return dict(THRESHOLDS)
    pct = lambda p: cand[min(len(cand) - 1, int(p * len(cand)))]
    return {"overview": pct(0.85), "neighborhood": pct(0.50), "expand": pct(0.15)}


def select(focus: str, theta: float, graph) -> dict:
    """DOI 选择 + 三档 LOD + 40 行预算分配。返回选择结果字典。

    出口判据校验点：
      - 三类必备项全在 V（mandatory ⊆ shown）
      - 预算溢出不静默丢失（budget_folded 显式报数）
      - 预算 ≤ BUDGET；必备项物理超限时以 budget_overflow 显式报数
    """
    hop = bfs_hop(focus, graph.adj)
    pdepth = rev_bfs(focus, graph.pred)
    fp = graph.parent.get(focus)
    fl = graph.layer.get(focus, focus.count("-"))
    scores = [
        {"id": nid, "d": doi(graph.nodes[nid], focus, hop, pdepth, graph)}
        for nid in graph.nodes
    ]
    by_id = {s["id"]: s for s in scores}
    mand = mandatory_set(focus, pdepth, graph)

    lod: dict[str, str] = {}
    for s in scores:
        nid = s["id"]
        if nid in mand:
            lod[nid] = "L2" if nid == focus else "L1"
        else:
            lod[nid] = "L2" if s["d"] >= theta else "COMPRESSED"

    used = 0
    shown: list[str] = []
    for nid in mand:
        used += COST[lod[nid]]
        shown.append(nid)

    # scope 旋钮语义：候选（非强制、d>=theta）先按 L0（1 行）塞入预算，最大化「可见数量」；
    # 再按 DOI 降序把同档节点整体升 L1/L2。
    # 严格单调不变式：d 越高，LOD 档位 ≥ d 越低者。一旦某 DOI 桶无法「整体」升到下一档即停手，
    # 禁止更低 d 节点越级——否则会出现「低 d 节点 L2、高 d 节点 L1」的反转。预算是硬上限而非填充目标，
    # 停手造成的预算余量允许闲置（正确性优先于把行数塞满）。
    cand_list = [s for s in scores if s["id"] not in mand and lod[s["id"]] == "L2"]
    by_d = defaultdict(list)
    for s in cand_list:
        by_d[s["d"]].append(s["id"])
    # L0 阶段：降序，整桶塞入；首个塞不下的桶及其后全部 COMPRESSED。
    exhausted = False
    for d in sorted(by_d.keys(), reverse=True):
        ids = by_d[d]
        if not exhausted and used + COST["L0"] * len(ids) <= BUDGET:
            for nid in ids:
                lod[nid] = "L0"
                used += COST["L0"]
                shown.append(nid)
        else:
            exhausted = True
            for nid in ids:
                lod[nid] = "COMPRESSED"
    # L1 / L2 升级：降序，整桶一起升；首个升不动的桶即停手，禁止更低 d 越级。
    # 注意：强制项（非焦点）恒为 L1，不参与 L1→L2 升级（spec：mandatory→L2(focus) 或 L1）。
    for tier_from, tier_to, step in (
        ("L0", "L1", COST["L1"] - COST["L0"]),
        ("L1", "L2", COST["L2"] - COST["L1"]),
    ):
        by_d2 = defaultdict(list)
        for nid in lod:
            if lod[nid] == tier_from and not (tier_to == "L2" and nid in mand):
                by_d2[by_id[nid]["d"]].append(nid)
        for d in sorted(by_d2.keys(), reverse=True):
            ids = by_d2[d]
            if used + step * len(ids) <= BUDGET:
                for nid in ids:
                    lod[nid] = tier_to
                    used += step
            else:
                break  # 更低 d 桶不得越级

    # 必备项恒见，物理上可能击穿 40 行上限；此时不得静默（INV::09）。
    budget_overflow = max(0, used - BUDGET)
    compressed = [nid for nid in lod if lod[nid] == "COMPRESSED"]
    theta_folded = sum(1 for nid in compressed if by_id[nid]["d"] < theta)
    budget_folded = len(compressed) - theta_folded
    return {
        "focus": focus,
        "theta": theta,
        "shown": shown,
        "lod": lod,
        "scores": scores,
        "by_id": by_id,
        "used": used,
        "mandatory": mand,
        "pdepth": pdepth,
        "compressed": compressed,
        "theta_folded": theta_folded,
        "budget_folded": budget_folded,
        "budget_overflow": budget_overflow,
        "fp": fp,
        "fl": fl,
    }
