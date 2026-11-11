#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S2：Mermaid 文本等价物（flowchart TB）。

文字投影与 HTML 视图同源（同一 DOI 选择 + 同一 blocks 边），可 diff、可逐字节回归
（spec R16：DAG 文本等价物必须存在）。可见节点逐个列出，折叠项聚合为一个虚线复合节点。
"""
from __future__ import annotations

from .graph import RoadmapGraph
from .ir import build_view


def _escape(label: str) -> str:
    return label.replace('"', "'").replace("\n", " ").strip()


def to_mermaid(view: dict, graph: RoadmapGraph) -> str:
    sel = view["selection"]
    focus = view["envelope"]["focus"]
    shown = set(sel["shown"])
    lines = ["flowchart TB"]

    lines.append("classDef focus fill:#fff7ed,stroke:#ea580c,stroke-width:2px;")
    lines.append("classDef block fill:#fef2f2,stroke:#b91c1c;")
    lines.append("classDef sib fill:#eff6ff,stroke:#2563eb;")
    lines.append("classDef debt fill:#faf5ff,stroke:#7c3aed;")
    lines.append("classDef other fill:#f8fafc,stroke:#64748b;")
    lines.append("classDef comp fill:#f1f5f9,stroke:#94a3b8,stroke-dasharray:4 3;")

    style_for = lambda c: (
        "focus" if c["is_focus"]
        else "block" if c["is_block_pred"]
        else "sib" if c["is_sibling"]
        else "debt" if c["debt_level"] != "none"
        else "other"
    )
    for nid in sorted(shown):
        c = view["cards"][nid]
        label = _escape(f'{nid} {c["label"]}')
        lines.append(f'{nid}["{label}"]:::{style_for(c)}')

    rest = view["rest"]
    if rest:
        lines.append(f'COMPOSITE["其余 {len(rest)} 项（未展开）"]:::comp')
        # 文本等价：复合节点与焦点用虚线连，提示「还有远端子树被折起」
        lines.append(f"{focus} -.-> COMPOSITE")

    seen = set()
    for e in graph.edges:
        s, d, _ = (e.get("from_uid") or e.get("from"), e.get("to_uid") or e.get("to"), e.get("type"))
        if s in shown and d in shown and (s, d) not in seen:
            seen.add((s, d))
            lines.append(f"{s} --> {d}")

    return "\n".join(lines) + "\n"


def render_mermaid(focus: str, graph: RoadmapGraph, theta: float | None = None, expand: bool = False) -> str:
    """便捷封装：直接由焦点 + 图生成 Mermaid 文本。"""
    return to_mermaid(build_view(focus, graph, theta=theta, expand=expand), graph)
