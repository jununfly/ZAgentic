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


@dataclass
class RoadmapGraph:
    """归一化图：可视化只读消费的单一内部表示。"""

    nodes: dict  # id -> 原始 roadmap 节点（不在此处被改写）
    edges: list  # 仅 blocks 边（原始 edge dict）
    adj: dict = field(default_factory=dict)  # id -> [邻居 id]（blocks 无向）
    pred: dict = field(default_factory=dict)  # id -> set(阻塞前驱)
    succ: dict = field(default_factory=dict)  # id -> set(阻塞后继)
    parent: dict = field(default_factory=dict)  # id -> parent id | None
    uid: dict = field(default_factory=dict)  # id -> 不可变 uid
    layer: dict = field(default_factory=dict)  # id -> 层级
    debt: dict = field(default_factory=dict)  # id -> {score,level,hits,severity}
    revision: str = "unknown"
    carrier_stem: str = "roadmap"
    title: str = ""
    description: str = ""

    @classmethod
    def from_data(cls, data: dict, carrier_stem: str = "roadmap") -> "RoadmapGraph":
        nodes = data.get("nodes", {}) or {}
        edges_raw = data.get("edges", []) or []
        blocks = [
            e for e in edges_raw
            if (edge_endpoints(e)[2] or "").lower() == "blocks"
        ]
        adj, pred, succ = {}, {}, {}
        for nid in nodes:
            adj[nid] = []
            pred[nid] = set()
            succ[nid] = set()
        for e in blocks:
            s, d, _ = edge_endpoints(e)
            if s in nodes and d in nodes:
                adj[s].append(d)
                adj[d].append(s)
                pred[d].add(s)
                succ[s].add(d)
        parent = {nid: n.get("parent") for nid, n in nodes.items()}
        uid = {nid: n.get("uid") or nid for nid, n in nodes.items()}
        layer = {nid: layer_of(nid) for nid in nodes}
        debt = build_debt(nodes, data.get("debts"))
        meta = data.get("metadata", {}) or {}
        revision = meta.get("updated") or data.get("version") or "unknown"
        title = data.get("title", "") or ""
        description = data.get("description", "") or ""
        return cls(
            nodes=nodes, edges=blocks, adj=adj, pred=pred, succ=succ,
            parent=parent, uid=uid, layer=layer, debt=debt,
            revision=revision, carrier_stem=carrier_stem,
            title=title, description=description,
        )

    @classmethod
    def load(cls, path: str | Path, carrier_stem: str | None = None) -> "RoadmapGraph":
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        stem = carrier_stem or Path(path).stem
        return cls.from_data(data, carrier_stem=stem)
