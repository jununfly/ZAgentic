#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S0 之一：把真实 roadmap carrier 归一化为可视化图。

输入是 roadmap_cli.py 产出的单文件 JSON（或等价结构）：
  - nodes: {id: {id,label,status,mode,parent,children,decisions,notes,rounds,uid,node_type,...}}
  - edges: [{from,to,type,uid} | {from_uid,to_uid,type,uid}]  （blocks 边）
  - metadata.updated / version: carrier revision
  - debts（可选）: [{anchor,kind,severity,...}]

本模块**只读**——绝不修改传入的 data 字典（S0 出口判据：receipt 不进 carrier / 视图不污染源）。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEBT_HIGH = ["风险", "risk", "缺口", "gap", "缺失", "不一致", "返工", "错误"]
DEBT_MED = ["todo", "待", "sweep", "清理", "核对", "跟进", "补", "未覆盖", "隐患"]


def layer_of(node_id: str) -> int:
    """节点层级 = id 中 '-' 的个数（'1'=0, '1-2'=1, '1-2-3'=2）。"""
    return node_id.count("-")


def edge_endpoints(edge: dict) -> tuple[str | None, str | None, str | None]:
    src = edge.get("from_uid") or edge.get("from")
    dst = edge.get("to_uid") or edge.get("to")
    typ = edge.get("type")
    return src, dst, typ


def debt_signal(node: dict) -> dict:
    """文本启发债务信号（回退）：仅当 notes + decisions 命中债务关键词才计债务。

    与 spec debt-schema 对齐——只认 gap/todo/risk/sweep 一类信号；不把「有 notes」误判为债务。
    无命中 → level=none（score=0，不强制可见、不染色）。
    """
    txt = (node.get("notes") or "") + " " + json.dumps(node.get("decisions") or [], ensure_ascii=False)
    hi = [k for k in DEBT_HIGH if k in txt]
    if hi:
        return {"score": 1.0, "level": "high", "hits": hi, "severity": "high"}
    med = [k for k in DEBT_MED if k.lower() in txt.lower()]
    if med:
        return {"score": 0.6, "level": "medium", "hits": med, "severity": "medium"}
    return {"score": 0.0, "level": "none", "hits": [], "severity": "none"}


def build_debt(nodes: dict, explicit: list | None) -> dict:
    """债务合并：显式 debts 优先；缺省节点用文本启发。"""
    explicit_map: dict[str, dict] = {}
    if explicit:
        score_by_level = {"high": 1.0, "medium": 0.6, "low": 0.3}
        for d in explicit:
            a = d.get("anchor")
            sev = (d.get("severity") or "medium").lower()
            level = "high" if sev == "high" else ("medium" if sev == "medium" else "low")
            explicit_map[a] = {
                "score": score_by_level.get(level, 0.3),
                "level": level,
                "hits": [d.get("kind", ""), d.get("note", "")],
                "severity": sev,
            }
    debt: dict[str, dict] = {}
    for nid, n in nodes.items():
        if nid in explicit_map:
            debt[nid] = explicit_map[nid]
        else:
            debt[nid] = debt_signal(n)
    return debt


_REVISION_NODE_FIELDS = (
    "id", "label", "status", "mode", "parent", "children", "decisions",
    "notes", "rounds", "exit_criteria", "budget",
)


def _content_revision(title, description, nodes, blocks, debt) -> str:
    """Stable short hash of the projected content (S1 two-carrier identity).

    Deliberately excludes metadata.updated (a carrier write timestamp) and
    carrier-added fields such as uid/layer: two carriers holding the same
    roadmap must produce the same revision and therefore the same bytes.
    """
    canonical = {
        "title": title,
        "description": description,
        "nodes": {
            nid: {k: node.get(k) for k in _REVISION_NODE_FIELDS}
            for nid, node in nodes.items()
        },
        "edges": sorted(
            tuple(str(part) for part in edge_endpoints(edge)) for edge in blocks
        ),
        "debt": debt,
    }
    raw = json.dumps(canonical, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@dataclass
class RoadmapGraph:
    """归一化图：可视化只读消费的单一内部表示。"""

    nodes: dict  # id -> 原始 roadmap 节点（不在此处被改写）
    edges: list  # 仅 blocks 边（端点已归一化为节点 id）
    hierarchy: list = field(default_factory=list)  # 父子层级边 [{from: parent_id, to: child_id}]
    adj: dict = field(default_factory=dict)  # id -> [邻居 id]（blocks 无向）
    pred: dict = field(default_factory=dict)  # id -> set(阻塞前驱)
    succ: dict = field(default_factory=dict)  # id -> set(阻塞后继)
    parent: dict = field(default_factory=dict)  # id -> parent id | None
    uid: dict = field(default_factory=dict)  # id -> 不可变 uid
    layer: dict = field(default_factory=dict)  # id -> 层级
    debt: dict = field(default_factory=dict)  # id -> {score,level,hits,severity}
    context: dict = field(default_factory=dict)  # S4 侧载上下文条目（carrier.context），不进主视图
    revision: str = "unknown"
    carrier_stem: str = "roadmap"
    title: str = ""
    description: str = ""

    @classmethod
    def from_data(cls, data: dict, carrier_stem: str = "roadmap") -> "RoadmapGraph":
        """归一化 carrier → 内部图。

        端点键空间收敛：carrier 的 blocks 边可能以 **uid** 存储（`add_edge` 写入 uid），
        也可能以 **id** 存储（老数据 / 部分 fixture）。roadmap.py 的展示约定也是 id
        （`edge_endpoints_as_display` 把 uid 解析成 id），因此这里统一把边端点解析为节点
        id，使 `adj/pred/succ`、`graph.edges`、embed 与前端 JS 全部按 id 索引一致。
        归一化只读入参、不改写。
        """
        nodes = data.get("nodes", {}) or {}
        edges_raw = data.get("edges", []) or []
        uid = {nid: n.get("uid") or nid for nid, n in nodes.items()}
        id_by_uid = {v: k for k, v in uid.items()}

        def endpoint_to_id(ep):
            # ep 可能是 uid 或 id：uid→id，否则原样保留（幂等）。
            return id_by_uid.get(ep, ep)

        # 原始 blocks 边（保留 uid 端点）仅用于内容指纹，不参与图查询。
        blocks_raw = [
            e for e in edges_raw
            if (edge_endpoints(e)[2] or "").lower() == "blocks"
        ]
        # 归一化：端点统一为节点 id，供图查询与前端按 id 索引。
        blocks = []
        adj, pred, succ = {}, {}, {}
        for nid in nodes:
            adj[nid] = []
            pred[nid] = set()
            succ[nid] = set()
        for e in blocks_raw:
            s, d, _ = edge_endpoints(e)
            s_id, d_id = endpoint_to_id(s), endpoint_to_id(d)
            ne = dict(e)
            ne["from"] = s_id
            ne["to"] = d_id
            blocks.append(ne)
            if s_id in nodes and d_id in nodes:
                adj[s_id].append(d_id)
                adj[d_id].append(s_id)
                pred[d_id].add(s_id)
                succ[s_id].add(d_id)
        parent = {nid: n.get("parent") for nid, n in nodes.items()}
        layer = {nid: layer_of(nid) for nid in nodes}
        debt = build_debt(nodes, data.get("debts"))
        # 父子层级边（parent → child），供主图可见大纲拓扑；与 blocks 边用不同线型区分。
        hierarchy = []
        for nid, n in nodes.items():
            p = n.get("parent")
            if p and p in nodes:
                hierarchy.append({"from": p, "to": nid})
        side_context = data.get("context") or {}  # S4 侧载条目，只读引用，不进主视图
        title = data.get("title", "") or ""
        description = data.get("description", "") or ""
        # Content-derived, deliberately independent of metadata.updated.
        # 用原始 blocks_raw（uid 端点）保证同一 carrier 指纹不变（S1 Δ 可回归）。
        revision = _content_revision(title, description, nodes, blocks_raw, debt)
        return cls(
            nodes=nodes, edges=blocks, hierarchy=hierarchy, adj=adj, pred=pred, succ=succ,
            parent=parent, uid=uid, layer=layer, debt=debt, context=side_context,
            revision=revision, carrier_stem=carrier_stem,
            title=title, description=description,
        )

    @classmethod
    def load(cls, path: str | Path, carrier_stem: str | None = None) -> "RoadmapGraph":
        # S1: JSON and SQLite carriers must project to identical bytes.
        from .carrier import load_data

        data = load_data(path)
        stem = carrier_stem or Path(path).stem
        return cls.from_data(data, carrier_stem=stem)
