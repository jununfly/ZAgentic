#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S1 exit criteria: frozen view-ir, two-carrier byte identity, delta re-entry.

All assertions go through published seams (RoadmapGraph.load, build_view, the
renderers, receipt API, viz.cli main). No private helper is imported.
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
from viz import ir_schema, receipt  # noqa: E402
from viz.cli import main  # noqa: E402
from viz.graph import RoadmapGraph  # noqa: E402
from viz.ir import build_view  # noqa: E402
from viz.render_html import render_html  # noqa: E402
from viz.render_mermaid import render_mermaid  # noqa: E402

SAMPLE = SKILL / "demos" / "roadmap_viz_sample.json"
CLI = SKILL / "scripts" / "roadmap_cli.py"
AUTHORITY = "zj-roadmap-authority/v1"
FOCUS = "1"
THETA = 0.45


def _sample_data() -> dict:
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


def _project(path: Path) -> dict[str, str]:
    """Produce every public view from one carrier, with one fixed anchor."""
    graph = RoadmapGraph.load(path)
    view = build_view(FOCUS, graph, theta=THETA)
    envelope = {
        "view_kind": "zj-roadmap-visual-review/v1",
        "carrier_stem": graph.carrier_stem,
        "node_uid": graph.uid.get(FOCUS),
        "carrier_revision": graph.revision,
    }
    anchor = ctx.encode_anchor(envelope)
    status = ctx.revision_status(graph, anchor=anchor, roadmap_arg="<roadmap.json>")
    return {
        "html": render_html(graph, FOCUS, theta=THETA,
                            edge_meta=dep.build_edge_meta(graph),
                            revision_status=status),
        "mermaid": render_mermaid(FOCUS, graph, theta=THETA),
        "dependency": json.dumps(
            dep.build_dependency(FOCUS, graph, view=view),
            ensure_ascii=False, sort_keys=True),
        "dependency_mermaid": dep.to_dependency_mermaid(
            dep.build_dependency(FOCUS, graph, view=view)),
        "context": json.dumps(
            ctx.build_context_pack(FOCUS, graph, view=view, status=status),
            ensure_ascii=False, sort_keys=True),
        "ir": json.dumps(view, ensure_ascii=False, sort_keys=True),
    }


class FrozenIrSchema(unittest.TestCase):
    def test_schema_is_frozen_across_focus_theta_and_expand(self):
        graph = RoadmapGraph.from_data(_sample_data(), carrier_stem="s")
        count = 0
        for focus in sorted(graph.nodes)[:5]:
            for theta in (0.20, 0.45, 0.75):
                for expand in (False, True):
                    view = build_view(focus, graph, theta=theta, expand=expand)
                    self.assertEqual([], ir_schema.validate_view(view),
                                     f"schema drift at focus={focus} theta={theta}")
                    self.assertEqual(ir_schema.VIEW_IR_SCHEMA_VERSION,
                                     view["envelope"]["schema"])
                    count += 1
        self.assertEqual(30, count)

    def test_drifting_view_is_rejected(self):
        graph = RoadmapGraph.from_data(_sample_data(), carrier_stem="s")
        view = build_view(FOCUS, graph, theta=THETA)
        view["envelope"]["surprise_field"] = True
        self.assertTrue(ir_schema.validate_view(view))
        with self.assertRaises(ValueError):
            ir_schema.assert_frozen(view)


class TwoCarrierByteIdentity(unittest.TestCase):
    def _make_pair(self, tmp: Path) -> tuple[Path, Path]:
        json_path = tmp / "roadmap.json"
        json_path.write_text(SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        sqlite_path = tmp / "roadmap.sqlite"
        result = subprocess.run(
            [sys.executable, str(CLI), "migrate", str(json_path),
             "--to", "sqlite", "--output", str(sqlite_path)],
            capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertTrue(sqlite_path.is_file())
        return json_path, sqlite_path

    def test_same_anchor_same_bytes_across_carriers(self):
        with tempfile.TemporaryDirectory() as tmp:
            json_path, sqlite_path = self._make_pair(Path(tmp))
            before = sqlite_path.read_bytes()
            left, right = _project(json_path), _project(sqlite_path)
            self.assertEqual(set(left), set(right))
            for kind in sorted(left):
                with self.subTest(view=kind):
                    self.assertEqual(left[kind], right[kind],
                                     f"{kind} differs between carriers")
            self.assertEqual(before, sqlite_path.read_bytes(),
                             "projection mutated the carrier")

    def test_authority_envelope_in_every_public_view(self):
        with tempfile.TemporaryDirectory() as tmp:
            json_path, _ = self._make_pair(Path(tmp))
            for kind, text in _project(json_path).items():
                with self.subTest(view=kind):
                    self.assertIn(AUTHORITY, text)

    def test_baseline_none_full_view_is_identical_across_carriers(self):
        with tempfile.TemporaryDirectory() as tmp:
            json_path, sqlite_path = self._make_pair(Path(tmp))
            left, right = _project(json_path), _project(sqlite_path)
            self.assertEqual(left["html"], right["html"])
            delta = receipt.full_fallback(["1"], "baseline=None")
            self.assertEqual("full-fallback", delta["mode"])


class DeltaReentry(unittest.TestCase):
    def _graph(self, data: dict) -> RoadmapGraph:
        return RoadmapGraph.from_data(copy.deepcopy(data), carrier_stem="s")

    def test_added_changed_removed_and_stable_folded(self):
        data = _sample_data()
        g = self._graph(data)
        ids = ["1", "1-1", "1-2", "2"]
        before = receipt.item_hashes(g, ids)
        data["nodes"]["1-1"]["notes"] = "changed note"
        data["nodes"]["new"] = {"id": "new", "uid": "u-new", "label": "new",
                               "status": "pending", "parent": "1", "children": []}
        del data["nodes"]["2"]
        after = receipt.item_hashes(self._graph(data), ["1", "1-1", "1-2", "new"])
        delta = receipt.compute_delta(after, {"seen_item_hashes": before}, None)
        self.assertEqual("delta", delta["mode"])
        self.assertEqual(["1-1"], delta["changed"])
        self.assertEqual(["new"], delta["added"])
        self.assertEqual(["2"], delta["removed"])
        self.assertEqual(2, delta["stable-folded"])

    def test_missing_or_corrupt_receipt_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            got, warning = receipt.load_receipt(path)
            self.assertIsNone(got)
            self.assertIn("fail-closed", warning)
            delta = receipt.compute_delta({"1": "h"}, got, warning)
            self.assertEqual("full-fallback", delta["mode"])
            self.assertEqual(["1"], delta["added"])
            self.assertIn("fail-closed", delta["warning"])
            path.write_text("{not json", encoding="utf-8")
            got, warning = receipt.load_receipt(path)
            self.assertIsNone(got)
            self.assertIn("fail-closed", warning)

    def test_receipt_never_enters_carrier_or_view_ir(self):
        data = _sample_data()
        g = self._graph(data)
        view = build_view(FOCUS, g, theta=THETA)
        hashes = receipt.item_hashes(g, list(view["selection"]["shown"]))
        with tempfile.TemporaryDirectory() as tmp:
            carrier = Path(tmp) / "roadmap.json"
            carrier.write_text(json.dumps(data), encoding="utf-8")
            before = carrier.read_bytes()
            receipt_path = Path(tmp) / "isolated" / "receipt.json"
            receipt.write_receipt(receipt_path, anchor="a", carrier_revision=g.revision,
                                  theta=THETA, hashes=hashes)
            self.assertEqual(before, carrier.read_bytes())
            self.assertTrue(receipt_path.is_file())
            for forbidden in ("receipt", "seen_item_hashes", "delta"):
                self.assertNotIn(forbidden, json.dumps(view))
        self.assertEqual(data, _sample_data(), "carrier dict was mutated")

    def test_explicit_receipt_path_is_required_by_the_cli(self):
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
            self.assertEqual([], list(cwd.iterdir()),
                             "CLI wrote a default artifact (ADR 0010)")


if __name__ == "__main__":
    unittest.main()
