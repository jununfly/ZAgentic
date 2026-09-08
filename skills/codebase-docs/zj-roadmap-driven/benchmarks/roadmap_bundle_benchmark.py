#!/usr/bin/env python3
"""Generate reproducible roadmap bundles and measure bounded operations.

This is intentionally a generator rather than a checked-in giant fixture. Run:

    python roadmap_bundle_benchmark.py --size small
    python roadmap_bundle_benchmark.py --size large --output /tmp/roadmap-bench.json

The reported timings are diagnostic, not machine-independent pass/fail limits.
"""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

import sys

SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR))

from roadmap_bundle import RoadmapBundle  # noqa: E402


SIZES = {"small": 100, "medium": 1000, "large": 5000}


def make_data(node_count: int) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {
        "1": {
            "id": "1",
            "label": "Benchmark roadmap",
            "status": "in_progress",
            "mode": "explore",
            "parent": None,
            "children": [],
            "decisions": [],
            "notes": "",
        }
    }
    frontier = ["1"]
    next_number = 0
    while next_number < node_count - 1:
        parent_id = frontier.pop(0)
        parent = nodes[parent_id]
        for _ in range(10):
            if next_number >= node_count - 1:
                break
            next_number += 1
            node_id = f"{parent_id}-{len(parent['children']) + 1}"
            node = {
                "id": node_id,
                "label": f"Benchmark node {next_number}",
                "status": "pending",
                "mode": "explore" if next_number % 2 else "exploit",
                "parent": parent_id,
                "children": [],
                "decisions": [],
                "notes": "",
            }
            if next_number % 50 == 0:
                node["decisions"].append({"q": f"Question {next_number}", "answer": "Recorded", "note": "benchmark"})
            nodes[node_id] = node
            parent["children"].append(node_id)
            frontier.append(node_id)
    # Keep one deep leaf as the current focus so focus and light-render reads
    # exercise their normal path without making every node in progress.
    focus_id = max((node_id for node_id, node in nodes.items() if not node["children"]), key=lambda value: value.count("-"))
    nodes[focus_id]["status"] = "in_progress"
    parent_id = nodes[focus_id]["parent"]
    while parent_id:
        nodes[parent_id]["status"] = "in_progress"
        parent_id = nodes[parent_id]["parent"]
    return {"title": "Benchmark roadmap", "description": "generated", "version": 1, "nodes": nodes, "metadata": {"md_file": ""}}


def measure(name: str, operation: Callable[[], Any]) -> float:
    started = time.perf_counter()
    operation()
    return round((time.perf_counter() - started) * 1000, 3)


def run(size: str) -> dict[str, Any]:
    node_count = SIZES[size]
    with tempfile.TemporaryDirectory(prefix=f"zj-roadmap-{size}-") as temporary:
        bundle_path = Path(temporary) / "roadmap.bundle"
        bundle = RoadmapBundle.create_from_data(bundle_path, make_data(node_count))
        node_ids = sorted((bundle.path / "nodes").glob("*.json"), key=lambda path: (path.stem.count("-"), path.stem))
        target = node_ids[len(node_ids) // 2].stem

        def fresh(operation: Callable[[RoadmapBundle], Any]) -> Any:
            reader = RoadmapBundle(bundle_path)
            reader.load()
            return operation(reader)

        timings = {
            "cold_get_ms": measure("cold_get", lambda: fresh(lambda reader: reader.get_node(target))),
            "bounded_tree_ms": measure("bounded_tree", lambda: fresh(lambda reader: reader.get_tree(max_depth=2))),
            "focus_ms": measure("focus", lambda: fresh(lambda reader: reader.get_current_focus())),
            "node_decisions_ms": measure("node_decisions", lambda: fresh(lambda reader: reader.get_decisions(target))),
            "light_render_ms": measure("light_render", lambda: fresh(lambda reader: reader.render_light_section())),
            "full_section_ms": measure("full_section", lambda: fresh(lambda reader: reader.render_full_section(all_nodes=True, max_bytes=2_000_000))),
        }
        mutation_bundle = RoadmapBundle(bundle_path)
        mutation_bundle.load()
        timings["add_node_ms"] = measure("add_node", lambda: mutation_bundle.add_node(target, "benchmark write"))
        timings["update_node_ms"] = measure("update_node", lambda: mutation_bundle.update_node(target, notes="benchmark update"))
        bundle_bytes = sum(path.stat().st_size for path in bundle_path.rglob("*") if path.is_file())
        return {"size": size, "nodes": node_count, "bundle_bytes": bundle_bytes, "timings_ms": timings}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", choices=sorted(SIZES), default="small")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.size)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
