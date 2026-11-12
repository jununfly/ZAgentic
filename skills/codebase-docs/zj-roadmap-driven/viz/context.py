#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S4：context side-pack（侧载）与 revision stale 标记（只读）。

两条硬判据：

1. **上下文条目增长时主视图字节不变** —— side-pack 是独立产物；主视图 HTML 只内嵌
   展示字段白名单（见 render_html.py 的 DISPLAY_FIELDS），carrier 的 `context`
   字段永不进 GRAPH。主视图只有一个恒定的「上下文侧载」入口：不内嵌条目、
   不显示条目数，条目增长不改变本页一个字节。
2. **revision 不符时显式 stale 且不自动刷新** —— 刷新命令只作为字符串写出，
   本模块绝不调用任何执行原语；`auto_refresh` 恒 False。视图不会静默重绘，
   也不会反向改事实源。

anchor 信封 `zj-roadmap-anchor/v1` = view-kind + carrier-stem + node-uid + revision，
确定性编码、可复制、可解析；显示 id 从不作锚点（重排会漂移）。
"""
from __future__ import annotations

from .authority import AUTHORITY_ENVELOPE
from urllib.parse import quote, unquote

from . import doi
from .dependency import build_edge_meta, impact_closure
from .graph import RoadmapGraph

ANCHOR_PREFIX = "zj-roadmap-anchor/v1"
ANCHOR_FIELDS = ("view_kind", "carrier_stem", "node_uid", "carrier_revision")
VIEW_KIND = "zj-roadmap-visual-review/context-v1"


def encode_anchor(envelope: dict) -> str:
    """把信封编成单行、可复制、逐字节确定的 token。"""
    parts = [f"{k}={quote(str(envelope.get(k) or ''), safe='')}" for k in ANCHOR_FIELDS]
    return ANCHOR_PREFIX + "|" + "|".join(parts)


def decode_anchor(token: str) -> dict:
    """解析锚点；非法前缀 / 缺字段 / 未登记字段一律 fail-closed。"""
    if not isinstance(token, str) or not token.startswith(ANCHOR_PREFIX + "|"):
        raise ValueError(f"不是 {ANCHOR_PREFIX} 锚点: {token!r}")
    out = {}
    for part in token[len(ANCHOR_PREFIX) + 1 :].split("|"):
        if "=" not in part:
            raise ValueError(f"锚点字段格式错误: {part!r}")
        key, value = part.split("=", 1)
        if key not in ANCHOR_FIELDS:
            raise ValueError(f"锚点含未登记字段: {key!r}")
        out[key] = unquote(value)
    if set(out) != set(ANCHOR_FIELDS):
        raise ValueError("锚点字段不齐")
    return out


def unchecked_status(graph: RoadmapGraph) -> dict:
    """未携带期望 revision 时：明确标 unchecked，不假装「已核对、未过期」。"""
    return {
        "checked": False,
        "stale": False,
        "expected_revision": None,
        "carrier_revision": graph.revision,
        "refresh_command": None,
        "auto_refresh": False,
    }


def revision_status(
    graph: RoadmapGraph,
    expected_revision: str | None = None,
    anchor: str | None = None,
    roadmap_arg: str = "<roadmap.json>",
) -> dict:
    """比对 token / 期望 revision 与当前 carrier。

    只**写出**刷新命令，绝不执行：命令字符串是给 Human 的下一步，不是给 Agent
    的自动动作。carrier 只读，视图不静默重绘。
    """
    exp = expected_revision
    if anchor:
        exp = decode_anchor(anchor)["carrier_revision"]
    if exp is None:
        return unchecked_status(graph)
    stale = str(exp) != str(graph.revision)
    # 输出路径一律占位符：由 Human 显式给路径（ADR 0010），命令不默认落 cwd / 仓库根；
    # 这条字符串只被写出，永远不会被本模块执行。
    cmd = (
        f"python -m viz.cli {roadmap_arg} --out <X.html> "
        f"--dependency <X.dependency.json> --context <X.context.json> "
        f"--dependency-mermaid <X.dependency.mmd>"
    ) if stale else None
    return {
        "checked": True,
        "stale": stale,
        "expected_revision": str(exp),
        "carrier_revision": str(graph.revision),
        "refresh_command": cmd,
        "auto_refresh": False,
        "policy": "刷新命令只写出、不执行；不自动改事实源、不静默重绘",
    }


def build_context_pack(
    focus: str,
    graph: RoadmapGraph,
    radius: int = 2,
    view: dict | None = None,
    status: dict | None = None,
) -> dict:
    """构建单节点上下文侧载包（只读）。

    每条 entry 都有 `source`（carrier 内可追溯位置）与 `evidence_ref`（缺失显式
    unknown）。条目数增长只发生在 carrier.context[focus]，与主视图完全解耦。
    """
    if focus not in graph.nodes:
        raise KeyError(f"焦点不存在: {focus}")
    node = graph.nodes[focus]
    entries: list = []

    def add(kind: str, source: str, evidence_ref, payload) -> None:
        entries.append(
            {
                "entry_id": f"CTX::{focus}::{len(entries):03d}",
                "kind": kind,
                "source": source,
                "evidence_ref": evidence_ref or "unknown",
                "payload": payload,
            }
        )

    # 1. carrier 侧载条目 —— 上下文条目增长只发生在这里，永不进主视图
    for i, raw in enumerate(graph.context.get(focus) or []):
        ref = raw.get("evidence_ref") if isinstance(raw, dict) else None
        kind = str(raw.get("kind", "context")) if isinstance(raw, dict) else "context"
        add(kind, f"context.{focus}[{i}]", ref, raw)
    # 节点内侧载形式同样只被 side-pack 消费；render_html 的 DISPLAY_FIELDS 白名单挡住它们
    for j, raw in enumerate(node.get("context") or []):
        ref = raw.get("evidence_ref") if isinstance(raw, dict) else None
        kind = str(raw.get("kind", "context")) if isinstance(raw, dict) else "context"
        add(kind, f"nodes.{focus}.context[{j}]", ref, raw)

    # 2. 节点自身的决策 / 笔记 / 验收 / 预算
    for i, decision in enumerate(node.get("decisions") or []):
        ref = decision.get("evidence_ref") if isinstance(decision, dict) else None
        add("decision", f"nodes.{focus}.decisions[{i}]", ref, decision)
    if node.get("notes"):
        add("note", f"nodes.{focus}.notes", node.get("evidence_ref"), node["notes"])
    if node.get("exit_criteria"):
        add("exit_criteria", f"nodes.{focus}.exit_criteria", node.get("evidence_ref"), node["exit_criteria"])
    if node.get("budget"):
        add("budget", f"nodes.{focus}.budget", node.get("evidence_ref"), node["budget"])

    # 3. 债务（一等 schema，不自动晋升为节点）
    debt = graph.debt.get(focus) or {}
    if debt.get("level") != "none":
        add("debt", f"nodes.{focus}.notes/decisions(derived)", debt.get("evidence_ref"), debt)

    # 4. 入射 / 出射 blocks 边（带 edge_id 与 carrier 来源）
    for meta in build_edge_meta(graph):
        if meta["from"] == focus or meta["to"] == focus:
            add("block_edge", f"edges[{meta['source']['index']}]", meta["source"]["evidence_ref"], meta)

    # 5. 影响闭包 / 祖先链 / 半径内邻域；给定 S1 IR 时登记同源阻塞链
    if view is not None:
        add(
            "blocked_chain",
            "view-ir.selection.pdepth",
            "carrier-internal",
            sorted(view["selection"]["pdepth"]),
        )
    add(
        "impact",
        f"edges(blocks downstream of {focus})",
        "carrier-internal",
        impact_closure(focus, graph),
    )
    chain: list = []
    cur = graph.parent.get(focus)
    while cur and cur in graph.nodes and cur not in chain:
        chain.append(cur)
        cur = graph.parent.get(cur)
    add("ancestors", f"nodes.{focus}.parent(chain)", "carrier-internal", chain)
    hop = doi.bfs_hop(focus, graph.adj)
    add(
        "neighborhood",
        f"edges(blocks BFS r={radius})",
        "carrier-internal",
        sorted(nid for nid, dist in hop.items() if dist <= radius),
    )

    # 6. trace：carrier 未登记时显式 unknown，绝不编造
    traces = node.get("traces") or (graph.context.get("__traces__") or {}).get(focus)
    if traces:
        source = f"nodes.{focus}.traces" if node.get("traces") else f"context.__traces__.{focus}"
        add("trace", source, node.get("evidence_ref") or "carrier-internal", traces)
    else:
        add("trace", "carrier.traces", "unknown", None)

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
        "anchor": encode_anchor(envelope),
        "bfs_radius": radius,
        "scope_badge": f"focus-neighborhood/r{radius}",
        "entry_count": len(entries),
        "entries": entries,
        "revision_status": status if status is not None else unchecked_status(graph),
        "boundary": "side-loaded-only; not in Human main view; not in summary denominator",
    }
