#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S3：dependency 投影与边回溯（只读）。

与 S1 view-ir、roadmap_cli 的 ready / critical-path / impact **共用同一条边界**：
只沿 `blocks` 边走。blocked_by 取自 `doi.rev_bfs`（build_view → doi.select 用的是
同一个函数）；impact / critical_path 与 roadmap.py 的同名查询逐行等价。
`viz/tests/test_s3_s4.py` 直接 import roadmap 做交叉断言，把「同源」变成机械证据，
而不是「看起来像」。viz 运行时不依赖 roadmap.py（安装态零耦合）。

每条边带 `edge_id`（carrier 的 uid；缺失时确定性派生）与 `source`（edges 下标 +
carrier-stem + revision + evidence_ref）。evidence_ref 缺失一律显式 `unknown`：
不编造证据，也不静默留空。
"""
from __future__ import annotations

from .authority import AUTHORITY_ENVELOPE, mermaid_header
from . import doi
from .graph import RoadmapGraph, edge_endpoints

VIEW_KIND = "zj-roadmap-visual-review/dependency-v1"


def edge_id(edge: dict, index: int) -> str:
    """边 id：优先 carrier uid；缺失时按 (from,to,index) 确定性派生。"""
    uid = edge.get("uid") or edge.get("id")
    if uid:
        return str(uid)
    src, dst, _ = edge_endpoints(edge)
    return f"blocks:{src}->{dst}#{index}"


def edge_source(graph: RoadmapGraph, index: int, edge: dict) -> dict:
    """边的来源：可回溯到 carrier 的 edges 数组位置，不引入第二份事实源。"""
    return {
        "field": "edges",
        "index": index,
        "carrier_stem": graph.carrier_stem,
        "carrier_revision": graph.revision,
        "edge_uid": str(edge.get("uid") or edge.get("id") or "unknown"),
        "evidence_ref": edge.get("evidence_ref") or edge.get("source") or "unknown",
    }


def build_edge_meta(graph: RoadmapGraph) -> list:
    """为每条 blocks 边生成可回溯元数据（顺序与 carrier edges 一致，确定性）。"""
    out = []
    for i, e in enumerate(graph.edges):
        src, dst, typ = edge_endpoints(e)
        out.append(
            {
                "edge_id": edge_id(e, i),
                "from": src,
                "to": dst,
                "type": (typ or "blocks").lower(),
                "source": edge_source(graph, i, e),
            }
        )
    return out


def impact_closure(focus: str, graph: RoadmapGraph) -> list:
    """沿 blocks 顺流的传递闭包（不含自身），与 roadmap.impact_node_ids 等价。"""
    seen, stack, result = set(), [focus], []
    while stack:
        cur = stack.pop()
        for v in sorted(graph.succ.get(cur, set())):
            if v in seen:
                continue
            seen.add(v)
            result.append(v)
            stack.append(v)
    return sorted(result)


def critical_path(graph: RoadmapGraph) -> list:
    """最长未完工链（只沿 blocks），与 roadmap.critical_path 逐行等价。

    已完成节点不阻挡任何东西，链经过它也不贡献长度；同长取最小 id，保证确定性。
    这是全局查询，不随焦点漂移。
    """
    active = {nid for nid, n in graph.nodes.items() if n.get("status") != "completed"}
    if not active:
        return []
    adj: dict = {nid: [] for nid in active}
    indeg = {nid: 0 for nid in active}
    for e in graph.edges:
        s, d, t = edge_endpoints(e)
        if (t or "").lower() != "blocks":
            continue
        if s in active and d in active and s != d:
            adj[s].append(d)
            indeg[d] += 1

    ready = sorted(nid for nid in active if indeg[nid] == 0)
    topo: list = []
    while ready:
        u = ready.pop(0)
        topo.append(u)
        for v in sorted(adj[u]):
            indeg[v] -= 1
            if indeg[v] == 0:
                ready.append(v)
                ready.sort()

    best_len = {nid: 1 for nid in active}
    best_prev = {nid: None for nid in active}
    for u in topo:
        for v in adj[u]:
            cand = best_len[u] + 1
            if cand > best_len[v]:
                best_len[v] = cand
                best_prev[v] = u
            elif cand == best_len[v] and (best_prev[v] is None or u < best_prev[v]):
                best_prev[v] = u

    end = min(
        (nid for nid in active if best_len[nid] == max(best_len.values())),
        key=lambda nid: nid,
    )
    path: list = []
    cur = end
    while cur is not None:
        path.append(cur)
        cur = best_prev[cur]
    path.reverse()
    return path


def build_dependency(focus: str, graph: RoadmapGraph, view: dict | None = None) -> dict:
    """构建 dependency 投影（只读）。

    Args:
        focus: 焦点节点 id。
        graph: 归一化图。
        view: 可选 S1 view-ir；给定时直接复用其 selection.pdepth，锁死同源。
    Returns:
        dependency 投影 dict；不修改 graph 或 carrier。
    """
    if focus not in graph.nodes:
        raise KeyError(f"焦点不存在: {focus}")
    pdepth = dict(view["selection"]["pdepth"]) if view else doi.rev_bfs(focus, graph.pred)
    blocked_by = sorted(set(pdepth) - {focus})
    blocking = sorted(graph.succ.get(focus, set()))
    impact = impact_closure(focus, graph)
    cp = critical_path(graph)
    scope = {focus} | set(blocked_by) | set(blocking) | set(impact) | set(cp)
    edges = [m for m in build_edge_meta(graph) if m["from"] in scope and m["to"] in scope]
    envelope = {
        "view_kind": VIEW_KIND,
        "carrier_stem": graph.carrier_stem,
        "node_uid": graph.uid.get(focus),
        "carrier_revision": graph.revision,
        "focus": focus,
        "generated_by": "zj-roadmap-driven/viz",
        "authority": AUTHORITY_ENVELOPE,
    }
    return {
        "envelope": envelope,
        "blocked_by": blocked_by,
        "blocking": blocking,
        "impact": impact,
        "critical_path": cp,
        "blocked_depth": {k: pdepth[k] for k in sorted(pdepth)},
        "edges": edges,
        "edge_count": len(edges),
        "boundary": "only-blocks",
    }


def to_dependency_mermaid(dep: dict) -> str:
    """dependency 投影的文本等价物：只画 blocks 边，边标签即 edge_id。"""
    lines = ["flowchart TB", mermaid_header().strip()]
    lines.append("classDef critical fill:#fff7ed,stroke:#ea580c,stroke-width:2px;")
    ids = set()
    for e in dep["edges"]:
        ids.add(e["from"])
        ids.add(e["to"])
    cp = set(dep["critical_path"])
    for nid in sorted(ids):
        suffix = ":::critical" if nid in cp else ""
        lines.append(f'{nid}["{nid}"]{suffix}')
    for e in dep["edges"]:
        lines.append(f'{e["from"]} -->|{e["edge_id"]}| {e["to"]}')
    return "\n".join(lines) + "\n"
