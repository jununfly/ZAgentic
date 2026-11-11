#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""zj-roadmap-driven 只读可视化 CLI（S0/S2 落地入口）。

读取 roadmap carrier（绝不回写），生成自包含 HTML + 可选 Mermaid 文本等价物。
用法：
  python -m viz.cli <roadmap.json> [--out X.html] [--mermaid X.mmd]
                     [--focus ID] [--theta 0.45] [--expand] [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .graph import RoadmapGraph, edge_endpoints
from .ir import build_view
from .render_html import render_html
from .render_mermaid import render_mermaid


def default_focus(graph: RoadmapGraph) -> str | None:
    """默认焦点：阻塞前驱最多者优先，其次 in_progress，否则首个节点。"""
    pred_count: dict[str, int] = {}
    for e in graph.edges:
        s, d, _ = edge_endpoints(e)
        if d in graph.nodes:
            pred_count[d] = pred_count.get(d, 0) + 1
    if not graph.nodes:
        return None
    return max(
        graph.nodes.keys(),
        key=lambda i: (pred_count.get(i, 0), 1 if graph.nodes[i].get("status") == "in_progress" else 0),
    )


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="viz", description="zj-roadmap-driven 只读可视化投影（卡片 + 局部 DAG + Mermaid）"
    )
    p.add_argument("roadmap", help="roadmap carrier JSON 路径")
    p.add_argument("--out", help="输出 HTML 路径（默认 <stem>.viz.html）")
    p.add_argument("--mermaid", help="可选：输出 Mermaid .mmd 路径")
    p.add_argument("--focus", help="焦点节点 id（默认：阻塞前驱最多且 in_progress 优先）")
    p.add_argument("--theta", type=float, help="固定 θ（0..1）；缺省由焦点百分位校准中档")
    p.add_argument("--expand", action="store_true", help="展开全部折叠项")
    p.add_argument("--json", action="store_true", help="额外把 view-ir JSON 打到 stdout（不改 carrier）")
    args = p.parse_args(argv)

    graph = RoadmapGraph.load(args.roadmap)
    focus = args.focus or default_focus(graph)
    if not focus or focus not in graph.nodes:
        print(f"ERROR: 无效或缺失焦点：{focus!r}", file=sys.stderr)
        return 2

    view = build_view(focus, graph, theta=args.theta, expand=args.expand)
    html = render_html(graph, focus, theta=args.theta)

    out = args.out or (Path(args.roadmap).stem + ".viz.html")
    Path(out).write_text(html, encoding="utf-8")
    print(f"OK: HTML -> {out} ({len(html)} bytes)")

    if args.mermaid:
        Path(args.mermaid).write_text(
            render_mermaid(focus, graph, theta=args.theta, expand=args.expand), encoding="utf-8"
        )
        print(f"OK: Mermaid -> {args.mermaid}")

    sel = view["selection"]
    print(
        f"焦点={focus} θ={sel['theta']:.2f} 可见={len(sel['shown'])} 压缩={len(sel['compressed'])} "
        f"(θ截{sel['theta_folded']}·预算截{sel['budget_folded']}) 预算={sel['used']}/{sel['budget']} 行"
    )
    if args.json:
        print(json.dumps(view, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
