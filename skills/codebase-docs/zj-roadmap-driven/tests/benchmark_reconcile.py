#!/usr/bin/env python3
"""Measure deterministic reconciliation latency for both roadmap carriers."""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from roadmap import Roadmap  # noqa: E402
from roadmap_sqlite import RoadmapSqlite  # noqa: E402


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = (len(ordered) - 1) * p
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = index - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def build(path: Path, carrier: str, nodes: int):
    roadmap = RoadmapSqlite(path) if carrier == "sqlite" else Roadmap(path)
    roadmap.init("Reconciliation benchmark", md_file="")
    for index in range(nodes):
        roadmap.add_node("1", f"Work {index}", obligation_key=f"bench:{index}")
    trace = roadmap.add_trace(
        "finding", "benchmark finding", obligation_key=f"bench:{nodes // 2}",
    )
    roadmap.save()
    roadmap.load()
    return roadmap, trace["uid"]


def run(nodes: int = 5000, runs: int = 30) -> dict:
    results = {}
    with tempfile.TemporaryDirectory(prefix="zj-reconcile-benchmark-") as temporary:
        root = Path(temporary)
        for carrier, suffix in (("single", ".json"), ("sqlite", ".sqlite")):
            roadmap, trace_uid = build(root / f"benchmark{suffix}", carrier, nodes)
            timings = []
            for _ in range(runs):
                start = time.perf_counter()
                proposal = roadmap.reconcile(trace_uid)
                elapsed = (time.perf_counter() - start) * 1000
                if proposal["disposition"] != "covered":
                    raise AssertionError(f"unexpected benchmark disposition: {proposal['disposition']}")
                timings.append(elapsed)
            results[carrier] = {
                "nodes": nodes,
                "runs": runs,
                "min_ms": min(timings),
                "p50_ms": percentile(timings, 0.50),
                "p95_ms": percentile(timings, 0.95),
                "max_ms": max(timings),
                "samples_ms": timings,
            }
    threshold_ms = 1000.0
    return {
        "schema": "zj-reconciliation-benchmark/v1",
        "threshold_ms": threshold_ms,
        "results": results,
        "passed": all(result["p95_ms"] <= threshold_ms for result in results.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes", type=int, default=5000)
    parser.add_argument("--runs", type=int, default=30)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run(args.nodes, args.runs)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
