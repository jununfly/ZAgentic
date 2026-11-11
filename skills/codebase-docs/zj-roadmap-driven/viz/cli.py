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
from . import receipt
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


def _emit(path: str, content: str, label: str, detail: str = "") -> None:
    """Write one Human-requested artifact; the path is always explicit."""
    Path(path).write_text(content, encoding="utf-8")
    suffix = f" {detail}" if detail else ""
    print(f"OK: {label} -> {path}{suffix}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="viz", description="zj-roadmap-driven 只读可视化投影（卡片 + 局部 DAG + 边回溯 + 侧载上下文）"
    )
    p.add_argument("roadmap", help="roadmap carrier JSON 路径")
    p.add_argument("--out", help="输出 HTML 路径；不传则不写文件（ADR 0010）")
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
    p.add_argument("--ir", help="S1：输出冻结 view-ir JSON（必须显式给路径）")
    p.add_argument("--receipt", help="S1：Δ 重入 receipt 路径（读 baseline 并写回，必须显式给路径）")
    p.add_argument("--delta", help="S1：输出增量 JSON（必须显式给路径）")
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

    out = args.out  # ADR 0010: never default an artifact into cwd
    status = ctx.revision_status(
        graph,
        expected_revision=args.expect_revision,
        anchor=args.anchor,
        roadmap_arg=args.roadmap,
    )
    view = build_view(focus, graph, theta=args.theta, expand=args.expand)
    hashes = receipt.item_hashes(graph, list(view["selection"]["shown"]))
    baseline, baseline_warning = (None, None)
    if args.receipt:
        baseline, baseline_warning = receipt.load_receipt(args.receipt)
    delta = receipt.compute_delta(hashes, baseline, baseline_warning)
    edge_meta = dep.build_edge_meta(graph)
    html = render_html(
        graph, focus, theta=args.theta,
        edge_meta=edge_meta, revision_status=status, delta=delta,
    )

    if out:
        _emit(out, html, "HTML", f"({len(html)} bytes)")

    if args.mermaid:
        _emit(args.mermaid,
              render_mermaid(focus, graph, theta=args.theta, expand=args.expand),
              "Mermaid")

    if args.dependency or args.dependency_mermaid:
        d = dep.build_dependency(focus, graph, view=view)
        d["revision_status"] = status
        if args.dependency:
            _emit(
                args.dependency,
                json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                "dependency",
                f"(edges={d['edge_count']} blocked={len(d['blocked_by'])} "
                f"impact={len(d['impact'])} critical-path={len(d['critical_path'])})",
            )
        if args.dependency_mermaid:
            _emit(args.dependency_mermaid, dep.to_dependency_mermaid(d),
                  "dependency Mermaid")

    if args.context:
        pack = ctx.build_context_pack(
            focus, graph, radius=args.context_radius, view=view, status=status
        )
        _emit(
            args.context,
            json.dumps(pack, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            "context",
            f"(entries={pack['entry_count']} radius={pack['bfs_radius']})",
        )

    sel = view["selection"]
    print(
        f"焦点={focus} θ={sel['theta']:.2f} 可见={len(sel['shown'])} 压缩={len(sel['compressed'])} "
        f"(θ截{sel['theta_folded']}·预算截{sel['budget_folded']}) "
        f"预算={sel['used']}/{sel['budget']} 行"
        + (f" 溢出={sel['budget_overflow']} 行（必备项超限，已显式报数）"
           if sel["budget_overflow"] else "")
        + f" Δ={delta['mode']} (+{len(delta['added'])} ~{len(delta['changed'])} "
          f"-{len(delta['removed'])} 稳{delta['stable-folded']})"
    )
    anchor_token = ctx.encode_anchor(
        {
            "view_kind": "zj-roadmap-visual-review/v1",
            "carrier_stem": graph.carrier_stem,
            "node_uid": graph.uid.get(focus),
            "carrier_revision": graph.revision,
        }
    )
    print("anchor: " + anchor_token)
    if args.ir:
        _emit(args.ir, json.dumps(view, ensure_ascii=False, sort_keys=True) + "\n", "view-ir")
    if args.delta:
        _emit(args.delta, json.dumps(delta, ensure_ascii=False, sort_keys=True) + "\n", "delta")
    if args.receipt:
        receipt.write_receipt(
            args.receipt, anchor=anchor_token, carrier_revision=graph.revision,
            theta=view["selection"]["theta"], hashes=hashes,
        )
        print(f"receipt: {args.receipt} (mode={delta['mode']}, 条目 hash={len(hashes)})")
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
