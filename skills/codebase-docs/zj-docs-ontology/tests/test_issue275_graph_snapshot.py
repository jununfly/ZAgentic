#!/usr/bin/env python3
"""Issue #275 Fix 7: map relations layer + graph_snapshot.

Bidirectional per repo discipline: defect-shaped fixtures must produce the
named diagnostics (red before implementation), and the valid fixture must
stay green (zero ERROR) with the snapshot derived from the map alone.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = SKILL_ROOT / "tests" / "fixtures"
SPEC = importlib.util.spec_from_file_location("docs_governance", SKILL_ROOT / "scripts" / "docs_governance.py")
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


def codes(payload: dict) -> list[str]:
    return [d["code"] for d in payload["diagnostics"]]


class GraphSnapshotValidFixtureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = TOOL.report(FIXTURES / "graph-snapshot", validate_links=True)

    def test_snapshot_present_with_pinned_schema_version(self) -> None:
        snap = self.payload["graph_snapshot"]
        self.assertEqual(snap["schema_version"], "graph-snapshot/v1")

    def test_nodes_are_map_entries_with_declared_attributes(self) -> None:
        nodes = {n["path"]: n for n in self.payload["graph_snapshot"]["nodes"]}
        self.assertEqual(nodes["docs/designs/overview.md"]["role"], "primary")
        self.assertEqual(nodes["docs/designs/overview.md"]["authority-id"], "graph.overview")
        self.assertEqual(nodes["docs/designs/detail.md"]["role"], "supporting")
        self.assertIsNone(nodes["docs/prds/plain.md"]["role"])
        self.assertEqual(len(nodes), 4)

    def test_edges_resolve_id_and_path_targets(self) -> None:
        edges = self.payload["graph_snapshot"]["edges"]
        self.assertEqual(len(edges), 2)
        self.assertEqual({e["to"] for e in edges}, {"docs/designs/detail.md"})
        self.assertEqual({e["type"] for e in edges}, {"supports", "derived-from"})
        self.assertEqual({e["from"] for e in edges}, {"docs/designs/overview.md"})
        self.assertEqual({e["via"] for e in edges}, {"authority-id", "path"})

    def test_constraints_are_a_separate_block_not_edges(self) -> None:
        snap = self.payload["graph_snapshot"]
        self.assertIsInstance(snap["constraints"], list)
        for item in snap["constraints"]:
            self.assertIsInstance(item, str)
        for edge in snap["edges"]:
            self.assertNotIn("constraint", edge)

    def test_valid_fixture_has_zero_errors(self) -> None:
        self.assertFalse(TOOL.has_error(self.payload))

    def test_orphan_signal_only_for_declared_non_primary_without_inbound(self) -> None:
        orphans = [d for d in self.payload["diagnostics"] if d["code"] == "ORPHAN_PAGE"]
        self.assertEqual([d["path"] for d in orphans], ["docs/prds/orphan.md"])

    def test_primary_inbound_and_undeclared_are_not_orphans(self) -> None:
        orphans = [d["path"] for d in self.payload["diagnostics"] if d["code"] == "ORPHAN_PAGE"]
        self.assertNotIn("docs/designs/overview.md", orphans)
        self.assertNotIn("docs/designs/detail.md", orphans)
        self.assertNotIn("docs/prds/plain.md", orphans)


class GraphDanglingFixtureTest(unittest.TestCase):
    def test_dangling_target_is_map_error(self) -> None:
        payload = TOOL.report(FIXTURES / "graph-dangling", validate_links=True)
        self.assertIn("MAP_RELATION_DANGLING", codes(payload))
        self.assertTrue(TOOL.has_error(payload))


class GraphInvalidTypeFixtureTest(unittest.TestCase):
    def test_unknown_relation_type_is_map_error(self) -> None:
        payload = TOOL.report(FIXTURES / "graph-invalid-type", validate_links=True)
        self.assertIn("MAP_RELATION_TYPE_INVALID", codes(payload))
        self.assertTrue(TOOL.has_error(payload))


class SnapshotDerivedOnlyFromMapTest(unittest.TestCase):
    def test_proposal_mode_also_carries_snapshot(self) -> None:
        payload = TOOL.report(FIXTURES / "graph-snapshot", validate_links=False)
        self.assertIn("graph_snapshot", payload)
        self.assertEqual(len(payload["graph_snapshot"]["edges"]), 2)

    def test_proposal_mode_stays_read_only_on_dangling(self) -> None:
        # Parse/resolve are derivation, not validation: the snapshot is present
        # and the report stays in proposal mode; the ERROR fires in validate.
        payload = TOOL.report(FIXTURES / "graph-dangling", validate_links=False)
        self.assertIn("graph_snapshot", payload)
        self.assertNotIn("MAP_RELATION_DANGLING", codes(payload))


class PreambleAndProseLinksAreNotEntriesTest(unittest.TestCase):
    """Q7 (2026-11-20) regression: only list blocks whose FIRST line carries
    the markdown link are map entries. A link in the preamble (blockquote /
    table) or in trailing prose after a linkless list item must not become a
    graph node — derived files and prose mentions are not pages."""

    def setUp(self) -> None:
        self.payload = TOOL.report(FIXTURES / "graph-snapshot", validate_links=True)

    def test_node_count_matches_real_entries(self) -> None:
        nodes = self.payload["graph_snapshot"]["nodes"]
        self.assertEqual(len(nodes), 4)

    def test_entry_link_must_sit_on_the_blocks_first_line(self) -> None:
        # Direct parse: entries come only from list blocks whose first line
        # carries the link. The linkless shorthand item plus trailing prose
        # (which mentions detail.md) must yield no entry — the linkless block
        # is exactly the negative case, and the prose mention is not a page.
        import re as _re
        map_text = (FIXTURES / "graph-snapshot" / "docs" / "README.md").read_text(encoding="utf-8")
        blocks = _re.split(r"(?m)^(?=-\s+)", map_text)
        linkless_block = next(b for b in blocks if b.lstrip().startswith("- `"))
        self.assertIsNone(TOOL.LINK_RE.search(linkless_block.splitlines()[0]))
        entries, _edges, _parse = TOOL.map_graph(
            FIXTURES / "graph-snapshot", FIXTURES / "graph-snapshot" / "docs" / "README.md", []
        )
        self.assertEqual(
            [str(e["path"]) for e in entries],
            ["docs/designs/overview.md", "docs/designs/detail.md", "docs/prds/orphan.md", "docs/prds/plain.md"],
        )


if __name__ == "__main__":
    unittest.main()
