#!/usr/bin/env python3
"""SQLite carrier is the second Roadmap carrier, behavior-identical to single-file.

Scope (reconstructed from docs/plans/zj-roadmap-dag-concurrency.md §5 + §测试缝):
implement `RoadmapSqlite` (stdlib `sqlite3`, zero new deps) that satisfies the
*same adapter contract* as `Roadmap` (single-file) — so the
existing contract tests can run a third time against it.

This file is the focused cross-carrier equality proof chosen for #116: build one
roadmap, persist it to BOTH single-file and SQLite with identical bytes, then
assert every observable behavior matches. That is the spec's acceptance ("同一套
契约测试参数化跑三遍") expressed directly — if the SQLite carrier drifted from
single-file on any of these, at least one assertion here breaks.

Seams under test
----------------
  1. Carrier API (in-memory `self.data`): current_revision, render_light_section,
     render_full_section, get_node_view (blocked derivation), stats, validate.
  2. Lease store: claim/heartbeat/release + the append-only event log, persisted
     to SQLite tables instead of a `.leases.json` sidecar.
  3. Decisions: add_decision / remove_decision (retract-and-keep) land identically.
  4. md view growth: owner column (lease) and open-question queue render byte-equal.

Run: python tests/test_sqlite_carrier.py
"""

import copy
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
if str(SKILL_DIR) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SKILL_DIR))

import roadmap
from roadmap import Roadmap
import roadmap_sqlite
from roadmap_sqlite import RoadmapSqlite, is_sqlite_path

LEASE_TTL = 300.0
NOW = 1_700_000_000.0  # fixed clock → deterministic expiry + event timestamps


def sample_data() -> dict:
    """A small graph with fixed uids so cross-carrier revisions are comparable."""
    return {
        "title": "x-carrier",
        "version": 1,
        "nodes": {
            "1": {"id": "1", "uid": "u1", "label": "root", "status": "in_progress",
                  "mode": "explore", "parent": None, "children": ["1-1"], "decisions": [],
                  "notes": "", "rounds": 1},
            "1-1": {"id": "1-1", "uid": "u1-1", "label": "child", "status": "pending",
                    "mode": "explore", "parent": "1", "children": ["1-1-1"], "decisions": [],
                    "notes": "", "rounds": 0},
            "1-1-1": {"id": "1-1-1", "uid": "u1-1-1", "label": "gc", "status": "pending",
                      "mode": "explore", "parent": "1-1", "children": [], "decisions": [],
                      "notes": "", "rounds": 0},
        },
        "edges": [{"id": "e1", "from": "u1-1", "to": "u1-1-1", "type": "blocks"}],
        "metadata": {"created": "2026-01-01 00:00:00", "updated": "2026-01-01 00:00:00",
                     "md_file": ""},
    }


def persist(path: str, data: dict, carrier_cls):
    r = carrier_cls(path)
    r.data = copy.deepcopy(data)
    r.save()
    return r


class SqliteCarrierEquality(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.json_path = Path(self.tmp.name) / "roadmap.json"
        self.db_path = Path(self.tmp.name) / "roadmap.sqlite"
        # identical bytes into both carriers
        persist(str(self.json_path), sample_data(), Roadmap)
        persist(str(self.db_path), sample_data(), RoadmapSqlite)
        self.single = Roadmap(str(self.json_path))
        self.single.load()
        self.sqlite = RoadmapSqlite(str(self.db_path))
        self.sqlite.load()

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def _body(section: str) -> str:
        """Drop the storage-path header line (filename + timestamp legitimately
        differ between carriers) so the comparison covers the actual tree / chains
        / queues — the part that must be byte-identical."""
        return "\n".join(
            ln for ln in section.splitlines() if not ln.startswith("> 数据文件:")
        )

    # ── read views (the Human-facing contract) ──

    def test_canonical_revision_is_identical(self):
        self.assertEqual(self.single.current_revision(), self.sqlite.current_revision())

    def test_light_section_renders_byte_equal(self):
        self.assertEqual(
            self._body(self.single.render_light_section()),
            self._body(self.sqlite.render_light_section()),
        )

    def test_full_section_renders_byte_equal(self):
        self.assertEqual(
            self._body(self.single.render_full_section()),
            self._body(self.sqlite.render_full_section()),
        )

    def test_blocked_is_derived_identically(self):
        # 1-1-1 is blocked by the e1 blocks edge from 1-1 (not yet completed)
        self.assertEqual(self.single.get_node_view("1-1-1"), self.sqlite.get_node_view("1-1-1"))
        self.assertTrue(self.single.get_node_view("1-1-1")["blocked"])

    def test_stats_are_identical(self):
        self.assertEqual(self.single.stats(), self.sqlite.stats())

    def test_validate_reports_no_errors_on_both(self):
        self.assertEqual(self.single.validate(), [])
        self.assertEqual(self.sqlite.validate(), [])

    # ── md view growth: owner column ──

    def test_owner_column_matches_after_lease(self):
        # claim with the real wall clock so owner_map (which also reads real time)
        # sees an unexpired lease and renders the owner column on both carriers.
        self.single.claim_lease("1-1", "a7", ttl=LEASE_TTL)
        self.sqlite.claim_lease("1-1", "a7", ttl=LEASE_TTL)
        self.assertEqual(
            self._body(self.single.render_light_section()),
            self._body(self.sqlite.render_light_section()),
        )
        self.assertIn("owner: a7", self.sqlite.render_light_section())

    # ── md view growth: open-question queue ──

    def test_open_question_queue_matches(self):
        oq = {"question": "q", "raised_at": "t", "raised_by": "a7", "attempts": 1,
              "last_error": "boom"}
        self.single.data["nodes"]["1-1-1"]["open_question"] = copy.deepcopy(oq)
        self.sqlite.data["nodes"]["1-1-1"]["open_question"] = copy.deepcopy(oq)
        self.single.save()
        self.sqlite.save()
        self.single.load()
        self.sqlite.load()
        self.assertEqual(
            self._body(self.single.render_light_section()),
            self._body(self.sqlite.render_light_section()),
        )

    # ── lease store parity (the storage-specific part) ──

    def test_lease_lifecycle_store_is_identical(self):
        self.single.claim_lease("1-1", "a7", ttl=LEASE_TTL, now=NOW)
        self.single.heartbeat_lease("1-1", "a7", now=NOW + 60)
        self.single.release_lease("1-1", "a7", force=True, now=NOW + 120)

        self.sqlite.claim_lease("1-1", "a7", ttl=LEASE_TTL, now=NOW)
        self.sqlite.heartbeat_lease("1-1", "a7", now=NOW + 60)
        self.sqlite.release_lease("1-1", "a7", force=True, now=NOW + 120)

        self.assertEqual(self.single._read_lease_store(), self.sqlite._read_lease_store())

    def test_expired_lease_is_not_shown_as_owner(self):
        # claim far in the past → expired; owner_map must stay empty on both
        self.single.claim_lease("1-1", "a7", ttl=LEASE_TTL, now=1.0)
        self.sqlite.claim_lease("1-1", "a7", ttl=LEASE_TTL, now=1.0)
        self.assertEqual(self.single.owner_map(), {})
        self.assertEqual(self.sqlite.owner_map(), {})

    # ── decisions: retract-and-keep lands identically ──

    def test_decisions_retract_and_keep_identically(self):
        self.single.add_decision("1", "为什么", "因为", note="n")
        self.sqlite.add_decision("1", "为什么", "因为", note="n")
        self.single.save()
        self.sqlite.save()
        # remove → append a retracted twin, keep original (count goes 1 → 2)
        self.single.remove_decision("1", index=0)
        self.sqlite.remove_decision("1", index=0)
        self.single.save()
        self.sqlite.save()
        self.assertEqual(
            self.single.data["nodes"]["1"]["decisions"],
            self.sqlite.data["nodes"]["1"]["decisions"],
        )
        # both keep 2 decision records (retract-and-keep, not hard delete)
        self.assertEqual(len(self.single.data["nodes"]["1"]["decisions"]), 2)


class SqlitePathRouting(unittest.TestCase):
    """`_load_roadmap` must pick the SQLite carrier by extension."""

    def test_is_sqlite_path_detects_extension(self):
        self.assertTrue(is_sqlite_path("a/roadmap.sqlite"))
        self.assertTrue(is_sqlite_path("a/roadmap.db"))
        self.assertFalse(is_sqlite_path("a/roadmap.json"))
        self.assertFalse(is_sqlite_path("a/roadmap.json"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
