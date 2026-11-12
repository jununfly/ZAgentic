#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression guards for the 2026-11-12 two-axis review findings.

Seams: the published CLI behaviour (no implicit cwd writes), the authority
envelope carried by every public view, budget-overflow reporting, and Python/JS
selection parity. No internal helper is asserted directly.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2]
for entry in (str(SKILL), str(SKILL / "scripts")):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from viz import context as ctx  # noqa: E402
from viz import dependency as dep  # noqa: E402
from viz import doi  # noqa: E402
from viz.cli import main  # noqa: E402
from viz.graph import RoadmapGraph  # noqa: E402
from viz.ir import build_view  # noqa: E402
from viz.render_html import render_html  # noqa: E402
from viz.render_mermaid import render_mermaid  # noqa: E402

SAMPLE = SKILL / "demos" / "roadmap_viz_sample.json"
VERIFY_SELECTION = SKILL / "viz" / "verify_selection.mjs"
AUTHORITY = "zj-roadmap-authority/v1"


def _graph() -> RoadmapGraph:
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    return RoadmapGraph.from_data(data, carrier_stem="roadmap_viz_sample")


def _big_graph() -> RoadmapGraph:
    """31 mandatory items: focus + 30 blocks successors → used must exceed 40."""
    nodes = {"1": {"id": "1", "uid": "u-1", "label": "focus", "status": "in_progress",
                   "parent": None, "children": []}}
    edges = []
    for i in range(2, 32):
        nid = f"n{i}"
        nodes[nid] = {"id": nid, "uid": f"u-{i}", "label": nid,
                      "status": "pending", "parent": "1", "children": []}
        edges.append({"from": "1", "to": nid, "type": "blocks", "uid": f"e-{i}"})
    data = {"nodes": nodes, "edges": edges, "metadata": {}, "debts": []}
    return RoadmapGraph.from_data(copy.deepcopy(data), carrier_stem="big")


class OutPathContract(unittest.TestCase):
    def test_without_out_no_file_is_written_into_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            previous = Path.cwd()
            os.chdir(cwd)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    rc = main([str(SAMPLE)])
            finally:
                os.chdir(previous)
            self.assertEqual(0, rc)
            self.assertEqual([], list(cwd.iterdir()), "implicit cwd write (ADR 0010)")

    def test_explicit_out_still_writes_the_view(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "view.html"
            with contextlib.redirect_stdout(io.StringIO()):
                rc = main([str(SAMPLE), "--out", str(out)])
            self.assertEqual(0, rc)
            self.assertTrue(out.is_file() and out.stat().st_size > 0)


class AuthorityEnvelopeContract(unittest.TestCase):
    def setUp(self):
        self.g = _graph()
        self.focus = "1"
        self.view = build_view(self.focus, self.g)
        self.status = ctx.revision_status(self.g, roadmap_arg=str(SAMPLE))

    def test_html_view(self):
        html = render_html(self.g, self.focus, edge_meta=dep.build_edge_meta(self.g),
                           revision_status=self.status)
        self.assertIn(AUTHORITY, html)

    def test_mermaid_text(self):
        self.assertIn(AUTHORITY, render_mermaid(self.focus, self.g))

    def test_dependency_json_and_mermaid(self):
        d = dep.build_dependency(self.focus, self.g, view=self.view)
        self.assertIn(AUTHORITY, json.dumps(d, ensure_ascii=False))
        self.assertIn(AUTHORITY, dep.to_dependency_mermaid(d))

    def test_context_side_pack(self):
        pack = ctx.build_context_pack(self.focus, self.g, view=self.view, status=self.status)
        self.assertIn(AUTHORITY, json.dumps(pack, ensure_ascii=False))

    def test_view_ir_envelope(self):
        self.assertIn(AUTHORITY, json.dumps(self.view["envelope"], ensure_ascii=False))


class BudgetOverflowContract(unittest.TestCase):
    def test_mandatory_overflow_is_reported_not_silent(self):
        g = _big_graph()
        self.assertGreater(len(doi.mandatory_set("1", doi.rev_bfs("1", g.pred), g)), 20)
        res = doi.select("1", 0.45, g)
        self.assertGreater(res["used"], doi.BUDGET, "fixture no longer overflows")
        self.assertGreater(
            res["budget_overflow"], 0,
            "overflow is silently swallowed; INV::09 requires an explicit count",
        )

    def test_cli_summary_reports_overflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            carrier = Path(tmp) / "big.json"
            nodes = {"1": {"id": "1", "uid": "u-1", "label": "focus", "status": "in_progress",
                           "parent": None, "children": []}}
            edges = []
            for i in range(2, 32):
                nid = f"n{i}"
                nodes[nid] = {"id": nid, "uid": f"u-{i}", "label": nid,
                              "status": "pending", "parent": "1", "children": []}
                edges.append({"from": "1", "to": nid, "type": "blocks", "uid": f"e-{i}"})
            carrier.write_text(json.dumps({"nodes": nodes, "edges": edges, "metadata": {}}),
                               encoding="utf-8")
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                rc = main([str(carrier), "--focus", "1"])
            self.assertEqual(0, rc)
            self.assertIn("溢出", captured.getvalue())


class SelectionParityContract(unittest.TestCase):
    def test_html_runtime_select_matches_python_doi_select(self):
        self.assertTrue(VERIFY_SELECTION.is_file(), "verify_selection.mjs is missing")
        # Two fixtures: the sample exercises normal budgets; the 31-mandatory
        # graph exercises the tight-budget path where the two algorithms diverge.
        for graph, label in ((_graph(), "sample"), (_big_graph(), "big")):
            with self.subTest(fixture=label):
                cases = []
                for focus in sorted(graph.nodes):
                    for theta in (0.20, 0.45, 0.75):
                        cases.append({"focus": focus, "theta": theta,
                                      "lod": doi.select(focus, theta, graph)["lod"]})
                status = ctx.revision_status(graph, roadmap_arg=str(SAMPLE))
                html = render_html(
                    graph, sorted(graph.nodes)[0],
                    edge_meta=dep.build_edge_meta(graph), revision_status=status,
                )
                with tempfile.TemporaryDirectory() as tmp:
                    html_path = Path(tmp) / "view.html"
                    expected_path = Path(tmp) / "expected.json"
                    html_path.write_text(html, encoding="utf-8")
                    expected_path.write_text(json.dumps({"cases": cases}), encoding="utf-8")
                    result = subprocess.run(
                        ["node", str(VERIFY_SELECTION), str(html_path), str(expected_path)],
                        capture_output=True, text=True, timeout=120,
                    )
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)


class ViewDeterminismContract(unittest.TestCase):
    """INV::08: same carrier + anchor + revision => byte-identical views."""

    def _public_views(self) -> dict[str, str]:
        graph = _graph()
        view = build_view("1", graph, theta=0.45)
        status = ctx.revision_status(graph, roadmap_arg=str(SAMPLE))
        return {
            "html": render_html(graph, "1", theta=0.45,
                                edge_meta=dep.build_edge_meta(graph),
                                revision_status=status),
            "mermaid": render_mermaid("1", graph, theta=0.45),
            "dependency": json.dumps(
                dep.build_dependency("1", graph, view=view),
                ensure_ascii=False, sort_keys=True,
            ),
            "context": json.dumps(
                ctx.build_context_pack("1", graph, view=view, status=status),
                ensure_ascii=False, sort_keys=True,
            ),
            "view-ir": json.dumps(view, ensure_ascii=False, sort_keys=True),
        }

    def test_same_carrier_anchor_revision_renders_identical_public_views(self):
        first = self._public_views()
        second = self._public_views()
        self.assertEqual(first, second)
        self.assertEqual(first["html"], second["html"])

    def test_revision_is_content_derived_not_a_wall_clock(self):
        first, second = _graph(), _graph()
        self.assertEqual(first.revision, second.revision)
        self.assertNotRegex(first.revision, r"20\d\d-\d\d-\d\d")


if __name__ == "__main__":
    unittest.main()
