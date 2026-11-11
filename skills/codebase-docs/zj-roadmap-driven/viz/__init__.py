#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""zj-roadmap-driven / viz —— 路线图只读可视化投影（S0/S2 落地包）。

只读取 roadmap carrier，派生 view-ir，再由确定性模板投影成：
  - 自包含 HTML（局部 DAG + 信息卡片 + 交互；dagre 坐标来自 vendored @dagrejs/dagre）
  - Mermaid 文本等价物（可 diff、可逐字节回归）

绝不回写 carrier。S1 的只读命令 / anchor 信封 / reentry receipt 持久化与
S3（依赖回溯）/ S4（stale 标记）按路线图后续切片落地。
"""
from __future__ import annotations

from . import doi
from .graph import RoadmapGraph, edge_endpoints, layer_of, build_debt, debt_signal
from .ir import build_view
from .render_html import render_html
from .render_mermaid import render_mermaid, to_mermaid

__all__ = [
    "RoadmapGraph",
    "edge_endpoints",
    "layer_of",
    "build_debt",
    "debt_signal",
    "build_view",
    "render_html",
    "render_mermaid",
    "to_mermaid",
    "doi",
]

# DOI / 预算常量（与 spec information-selection 一致）
WEIGHTS = doi.WEIGHTS
BUDGET = doi.BUDGET
COST = doi.COST
THRESHOLDS = doi.THRESHOLDS
