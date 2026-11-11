#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""zj-roadmap-driven 只读可视化 CLI（S0/S2 + S3/S4 落地入口）。

读取 roadmap carrier（绝不回写），生成自包含 HTML + 可选 Mermaid 文本等价物，
以及 S3 dependency 投影 / S4 context 侧载包。用法：
  python -m viz.cli <roadmap.json> [--out X.html] [--mermaid X.mmd]
                     [--dependency X.json] [--dependency-mermaid X.mmd] [--context X.json]
                     [--focus ID] [--theta 0.45] [--expand] [--json]
                     [--anchor TOKEN] [--expect-revision REV] [--context-radius N]

新增产物一律要求 Human 显式给路径（ADR 0010）：--dependency / --context 无默认值。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import context as ctx
from . import dependency as dep
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
        prog="viz", description="zj-roadmap-driven 只读可视化投影（卡片 + 局部 DAG + 边回溯 + 侧载上下文）"
    )
    p.add_argument("roadmap", help="roadmap carrier JSON 路径")
    p.add_argument("--out", help="输出 HTML 路径（默认 <stem>.viz.html）")
    p.add_argument("--mermaid", help="可选：输出 Mermaid .mmd 路径")
    p.add_argument("--dependency", help="S3：输出 dependency 投影 JSON（必须显式给路径）")
    p.add_argument("--dependency-mermaid", help="S3：输出 dependency 投影的 Mermaid 文本等价物")
    p.add_argument("--context", help="S4：输出 context side-pack JSON（必须显式给路径）")
    p.add_argument("--focus", help="焦点节点 id（默认：阻塞前驱最多且 in_progress 优先）")
    p.add_argument("--theta", type=float, help="固定 θ（0..1）；缺省由焦点百分位校准中档")
    p.add_argument("--expand", action="store_true", help="展开全部折叠项")
    p.add_argument("--json", action="store_true", help="额外把 view-ir JSON 打到 stdout（不改 carrier）")
    p.add_argument("--anchor", help="S4 锚点 token；用于 stale 比对，并可反查焦点（node-uid）")
    p.add_argument("--expect-revision", help="S4：期望 carrier revision，与当前比对")
    p.add_argument("--context-radius", type=int, default=2, help="S4：上下文 BFS 半径（默认 2）")
    args = p.parse_args(argv)

    anchor_env = None
    if args.anchor:
        try:
            anchor_env = ctx.decode_anchor(args.anchor)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

    graph = RoadmapGraph.load(args.roadmap)
    focus = args.focus
    if not focus and anchor_env:
        uid = anchor_env.get("node_uid")
        focus = {v: k for k, v in graph.uid.items()}.get(uid)
    focus = focus or default_focus(graph)
    if not focus or focus not in graph.nodes:
        print(f"ERROR: 无效或缺失焦点：{focus!r}", file=sys.stderr)
        return 2

    out = args.out or (Path(args.roadmap).stem + ".viz.html")
    status = ctx.revision_status(
        graph,
        expected_revision=args.expect_revision,
        anchor=args.anchor,
        roadmap_arg=args.roadmap,
    )
    view = build_view(focus, graph, theta=args.theta, expand=args.expand)
    edge_meta = dep.build_edge_meta(graph)
    html = render_html(
        graph, focus, theta=args.theta,
        edge_meta=edge_meta, revision_status=status,
    )

    Path(out).write_text(html, encoding="utf-8")
    print(f"OK: HTML -> {out} ({len(html)} bytes)")

    if args.mermaid:
        Path(args.mermaid).write_text(
            render_mermaid(focus, graph, theta=args.theta, expand=args.expand), encoding="utf-8"
        )
        print(f"OK: Mermaid -> {args.mermaid}")

    if args.dependency or args.dependency_mermaid:
        d = dep.build_dependency(focus, graph, view=view)
        d["revision_status"] = status
        if args.dependency:
            Path(args.dependency).write_text(
                json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            print(
                f"OK: dependency -> {args.dependency} "
                f"(edges={d['edge_count']} blocked={len(d['blocked_by'])} "
                f"impact={len(d['impact'])} critical-path={len(d['critical_path'])})"
            )
        if args.dependency_mermaid:
            Path(args.dependency_mermaid).write_text(
                dep.to_dependency_mermaid(d), encoding="utf-8"
            )
            print(f"OK: dependency Mermaid -> {args.dependency_mermaid}")

    if args.context:
        pack = ctx.build_context_pack(
            focus, graph, radius=args.context_radius, view=view, status=status
        )
        Path(args.context).write_text(
            json.dumps(pack, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(
            f"OK: context -> {args.context} "
            f"(entries={pack['entry_count']} radius={pack['bfs_radius']})"
        )

    sel = view["selection"]
    print(
        f"焦点={focus} θ={sel['theta']:.2f} 可见={len(sel['shown'])} 压缩={len(sel['compressed'])} "
        f"(θ截{sel['theta_folded']}·预算截{sel['budget_folded']}) 预算={sel['used']}/{sel['budget']} 行"
    )
    print(
        "anchor: "
        + ctx.encode_anchor(
            {
                "view_kind": "zj-roadmap-visual-review/v1",
                "carrier_stem": graph.carrier_stem,
                "node_uid": graph.uid.get(focus),
                "carrier_revision": graph.revision,
            }
        )
    )
    if status["stale"]:
        print(
            f"STALE: 期望 revision={status['expected_revision']} "
            f"≠ carrier={status['carrier_revision']}",
            file=sys.stderr,
        )
        print(f"刷新命令（只写出，不执行）：{status['refresh_command']}", file=sys.stderr)
    if args.json:
        print(json.dumps(view, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
