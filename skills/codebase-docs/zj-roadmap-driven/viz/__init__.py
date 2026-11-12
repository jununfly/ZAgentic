#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""zj-roadmap-driven / viz —— 路线图只读可视化投影（S0/S2 + S3/S4 落地包）。

只读取 roadmap carrier，派生 view-ir，再由确定性模板投影成：
  - 自包含 HTML（局部 DAG + 信息卡片 + 交互 + 边回溯 + stale 横幅）
  - Mermaid 文本等价物（可 diff、可逐字节回归）
  - dependency 投影（S3）：阻塞链 / critical-path / impact + 每条边的 id 与来源
  - context side-pack（S4）：侧载 JSON，主视图字节不随上下文条目增长变化

绝不回写 carrier。S1 已落地：view-ir schema 冻结、两 carrier 同 anchor 输出
逐字节相同、权威信封必现、Δ reentry receipt（fail-closed、gitignored、路径显式）。
S1b 已落地：v2 收据带设备标识与 TTL、跨设备合并取并集、冲突/过期一律
fail-closed 全量回退；同步介质由 Human 显式给路径，不含网络协议。
"""
from __future__ import annotations

from . import context, dependency, doi
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
    "dependency",
    "context",
]

# DOI / 预算常量（与 spec information-selection 一致）
WEIGHTS = doi.WEIGHTS
BUDGET = doi.BUDGET
COST = doi.COST
THRESHOLDS = doi.THRESHOLDS
