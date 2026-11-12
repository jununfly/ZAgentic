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
import re
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
from viz.render_mermaid import render_mermaid, to_mermaid  # noqa: E402

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


def _spec_entry(node, wanted):
    """Find a spec entry by authority id without depending on its nesting."""
    if isinstance(node, dict):
        if node.get("id") == wanted:
            return node
        for value in node.values():
            found = _spec_entry(value, wanted)
            if found is not None:
                return found
    elif isinstance(node, list):
        for value in node:
            found = _spec_entry(value, wanted)
            if found is not None:
                return found
    return None


class DagLayoutDeterminismContract(unittest.TestCase):
    """INV::13: deterministic layered layout + a text equivalent from one view."""

    RENDER_HTML = SKILL / "viz" / "render_html.py"
    SPEC = (SKILL.parents[2] / "docs" / "designs"
            / "zj-roadmap-visual-review.spec.json")

    def _html(self, graph):
        return render_html(
            graph, "1", theta=0.45, edge_meta=dep.build_edge_meta(graph),
            revision_status=ctx.revision_status(graph, roadmap_arg=str(SAMPLE)),
        )

    def test_two_renders_are_byte_identical(self):
        graph = _graph()
        self.assertEqual(self._html(graph), self._html(graph))
        self.assertEqual(render_mermaid("1", graph, theta=0.45),
                         render_mermaid("1", graph, theta=0.45))

    @unittest.skipUnless(SPEC.exists(),
                         "external review spec (docs/designs) absent outside repo tree")
    def test_runtime_has_no_random_or_clock_driven_layout(self):
        source = self.RENDER_HTML.read_text(encoding="utf-8")
        for forbidden in ("Math.random", "Date(", "performance.now",
                          "force-directed"):
            self.assertNotIn(forbidden, source,
                             f"non-deterministic layout primitive: {forbidden}")
        self.assertIn("dagre.layout(g)", source)
        spec = json.loads(self.SPEC.read_text(encoding="utf-8"))
        dag = _spec_entry(spec["presentation"], "PRES::DAG")
        self.assertIsNotNone(dag)
        self.assertIn("确定性", dag["layout"])
        self.assertIn("禁止", dag["layout"])
        self.assertIn("Mermaid", dag["text-equivalent"])

    def test_mermaid_text_equivalent_is_sourced_from_the_same_view(self):
        graph = _graph()
        view = build_view("1", graph, theta=0.45)
        mermaid = to_mermaid(view, graph)
        self.assertEqual(mermaid, render_mermaid("1", graph, theta=0.45))
        node_ids = set(re.findall(r'^([^\s\[]+)\["', mermaid, re.M))
        expected = set(view["selection"]["shown"])
        if view["rest"]:
            expected.add("COMPOSITE")
        self.assertEqual(expected, node_ids,
                         "text equivalent and visual projection diverged")
        html = self._html(graph)
        for nid in view["selection"]["shown"]:
            self.assertIn(nid, html)


def _route_errors(contracts, routes) -> list[str]:
    """Independent checker shared by the live contract and its probes."""
    errors: list[str] = []
    expected = {
        item["id"]: (item["kind"], item["format"]) for item in contracts
    }
    actual = {key: (value[0], value[1]) for key, value in routes.items()}
    if expected != actual:
        errors.append("E_ROUTE_SET")
    pairs = list(actual.values())
    if len(set(pairs)) != len(pairs):
        errors.append("E_AMBIGUOUS_ROUTE")
    return errors


class ViewKindRoutingContract(unittest.TestCase):
    """C::05: view-kind -> output shape is a one-to-one, enumerable mapping."""

    CLI = SKILL / "viz" / "cli.py"
    SPEC = (SKILL.parents[2] / "docs" / "designs"
            / "zj-roadmap-visual-review.spec.json")

    def _routes(self):
        from viz.view_kinds import VIEW_CONTRACT_ROUTES
        return VIEW_CONTRACT_ROUTES

    @unittest.skipUnless(SPEC.exists(),
                         "external review spec (docs/designs) absent outside repo tree")
    def test_spec_view_contracts_match_the_independent_route_table(self):
        spec = json.loads(self.SPEC.read_text(encoding="utf-8"))
        errors = _route_errors(spec["view-contracts"], self._routes())
        self.assertEqual([], errors)

    def test_every_route_names_a_real_cli_flag(self):
        source = self.CLI.read_text(encoding="utf-8")
        for vc_id, (_, _, flags) in self._routes().items():
            self.assertTrue(flags, f"{vc_id} has no producing flag")
            for flag in flags:
                with self.subTest(vc=vc_id, flag=flag):
                    self.assertIn(f'add_argument("{flag}"', source,
                                  f"{vc_id} claims an unpublished flag")

    def test_route_pairs_are_unique(self):
        pairs = [(kind, fmt) for kind, fmt, _ in self._routes().values()]
        self.assertEqual(len(set(pairs)), len(pairs))

    @unittest.skipUnless(SPEC.exists(),
                         "external review spec (docs/designs) absent outside repo tree")
    def test_a_changed_or_dropped_contract_is_detected(self):
        spec = json.loads(self.SPEC.read_text(encoding="utf-8"))
        contracts = spec["view-contracts"]
        dropped = [item for item in contracts if item["id"] != "VC::04"]
        self.assertIn("E_ROUTE_SET", _route_errors(dropped, self._routes()))
        changed = [dict(item) for item in contracts]
        changed[0]["format"] = "pdf"
        self.assertIn("E_ROUTE_SET", _route_errors(changed, self._routes()))


class DoiOrderingContract(unittest.TestCase):
    """C::10: one comparator drives both the DAG insertion order and cards."""

    RENDER_HTML = SKILL / "viz" / "render_html.py"
    VERIFY_ORDERING = SKILL / "viz" / "verify_ordering.mjs"

    def _html(self):
        graph = _graph()
        return render_html(
            graph, "1", theta=0.45, edge_meta=dep.build_edge_meta(graph),
            revision_status=ctx.revision_status(graph, roadmap_arg=str(SAMPLE)),
        )

    def test_dag_and_cards_share_one_doi_ordering(self):
        graph = _graph()
        cases = [{"focus": focus, "theta": theta}
                 for focus in sorted(graph.nodes)
                 for theta in (0.20, 0.45, 0.75)]
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            html_path = tmp / "view.html"
            cases_path = tmp / "cases.json"
            html_path.write_text(self._html(), encoding="utf-8")
            cases_path.write_text(json.dumps({"cases": cases}), encoding="utf-8")
            result = subprocess.run(
                ["node", str(self.VERIFY_ORDERING), str(html_path), str(cases_path)],
                capture_output=True, text=True, timeout=180,
            )
        self.assertEqual(0, result.returncode,
                         result.stdout + result.stderr)

    def test_only_one_ordering_comparator_exists(self):
        source = self.RENDER_HTML.read_text(encoding="utf-8")
        self.assertEqual(1, source.count("function rankByDoi("),
                         "INV::03: exactly one ordering comparator")
        self.assertGreaterEqual(source.count("rankByDoi("), 4,
                                "cards and DAG must both call the shared comparator")
        self.assertNotIn("res.shown].sort((a,b)=>", source,
                         "a second inline comparator would fork the ordering")


class AncestorChainContract(unittest.TestCase):
    """C::01: the tree ancestor chain is visible at every focus and theta."""

    @staticmethod
    def _tree_ancestors(graph, focus):
        chain, seen = [], set()
        parent = graph.parent.get(focus)
        while parent and parent in graph.nodes and parent not in seen:
            chain.append(parent)
            seen.add(parent)
            parent = graph.parent.get(parent)
        return chain

    def test_tree_ancestors_are_always_visible(self):
        graph = _graph()
        checked = 0
        for focus in sorted(graph.nodes):
            chain = self._tree_ancestors(graph, focus)
            if not chain:
                continue
            for theta in (0.20, 0.45, 0.75):
                with self.subTest(focus=focus, theta=theta):
                    selection = doi.select(focus, theta, graph)
                    for ancestor in chain:
                        self.assertIn(ancestor, selection["mandatory"],
                                      f"{ancestor} is not mandatory for {focus}")
                        self.assertIn(ancestor, selection["shown"],
                                      f"ancestor {ancestor} vanished for {focus}")
                    self.assertIn(focus, selection["shown"])
                    checked += 1
        self.assertGreater(checked, 10, "no non-root focus was exercised")


class SiblingPartitionContract(unittest.TestCase):
    """C::01 second half: folded items are counted per sibling partition."""

    RENDER_HTML = SKILL / "viz" / "render_html.py"

    def test_mermaid_partition_counts_sum_to_rest(self):
        graph = _graph()
        view = build_view("1", graph, theta=0.45)
        mermaid = to_mermaid(view, graph)
        composite = [line for line in mermaid.splitlines()
                     if line.startswith("COMPOSITE[")]
        self.assertEqual(1, len(composite))
        self.assertIn("分区", composite[0])
        found = re.findall(r"分区 (\S+) (\d+) 项", composite[0])
        self.assertTrue(found, f"no partition counts in {composite[0]}")
        self.assertEqual(len(view["rest"]), sum(int(n) for _, n in found),
                         "partition counts must account for every folded item")

    def test_html_uses_one_partition_helper(self):
        source = self.RENDER_HTML.read_text(encoding="utf-8")
        self.assertEqual(1, source.count("function partitionRest("),
                         "INV::03: exactly one partition helper")
        self.assertGreaterEqual(source.count("partitionRest("), 2)
        self.assertIn("分区 ", source)


if __name__ == "__main__":
    unittest.main()
