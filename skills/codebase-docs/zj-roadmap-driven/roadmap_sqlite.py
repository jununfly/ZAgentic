"""Roadmap carrier backed by SQLite (stdlib `sqlite3`, zero new deps).

Design
------
`RoadmapSqlite` **inherits `Roadmap`** and overrides only the storage primitives:
  - `load()`   : SQLite → in-memory `self.data` (the same shape single-file uses)
  - `save()`   : `self.data` → normalized tables, wrapped in one transaction
  - `_read_lease_store` / `_write_lease_store` : leases + events in their own tables

Every other method (DAG queries, decisions, lease TTL/fencing/steal, md render,
`current_revision`, `validate`, `stats`, ...) is inherited unchanged. That is
deliberate: the spec's hard rule is "判定只写一处，两个 carrier 只 differ 在字节
落哪儿" — a subclass keeps the two carriers' semantics in one source of truth and
can never drift the way two independently-written classes would.

Storage layout (history / decisions / edges / leases 各归一表)
  meta         key/value  — title, description, version, edge_seq, metadata(JSON)
  nodes        uid PK, display_id, body(JSON)  — one row per node (decisions live
              inside the node body, exactly as in `self.data`)
  edges        id PK, type, from_uid, to_uid, body(JSON)
  leases       node_uid PK, body(JSON)
  lease_events  seq, node_uid, body(JSON)         — append-only audit log

`load()` reconstructs `self.data` to mirror what single-file produces in memory
(missing `edges`/`edge_seq` keys stay absent when empty, so behavior- and
revision-equality with the other carriers hold). Persisting the whole `self.data`
via DELETE+INSERT inside a transaction is the atomic multi-row write that the normalized layout
lists as SQLite's first justification.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from roadmap import Roadmap, ensure_uids, ensure_layer

SQLITE_SUFFIXES = (".sqlite", ".sqlite3", ".db")


def is_sqlite_path(path: str) -> bool:
    """Route a path to the SQLite carrier by its extension."""
    return Path(path).suffix.lower() in SQLITE_SUFFIXES


_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS nodes (
    uid        TEXT PRIMARY KEY,
    display_id TEXT NOT NULL,
    body       TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS edges (
    id       TEXT PRIMARY KEY,
    type     TEXT NOT NULL,
    from_uid TEXT NOT NULL,
    to_uid   TEXT NOT NULL,
    body     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS leases (
    node_uid TEXT PRIMARY KEY,
    body     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lease_events (
    seq      INTEGER PRIMARY KEY AUTOINCREMENT,
    node_uid TEXT NOT NULL,
    body     TEXT NOT NULL
);
"""


class RoadmapSqlite(Roadmap):
    """Roadmap persisted in a SQLite database file (third carrier)."""

    def __init__(self, db_path: str):
        # self.json_path becomes the sqlite file path (abspath); reused as the
        # db location by every storage primitive below.
        super().__init__(db_path)

    # ── connection / schema ────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.json_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(_SCHEMA)

    # ── file I/O (overrides) ──────────────────────────

    def load(self) -> dict:
        if not os.path.exists(self.json_path):
            raise FileNotFoundError(f"路线图文件不存在: {self.json_path}")
        conn = self._connect()
        try:
            self._ensure_schema(conn)
            meta_rows = {row[0]: row[1] for row in conn.execute("SELECT key, value FROM meta")}

            data: dict = {
                "title": meta_rows.get("title", ""),
                "description": meta_rows.get("description", ""),
                "version": int(meta_rows.get("version", "1")),
                "nodes": {},
                "metadata": json.loads(meta_rows["metadata"]) if meta_rows.get("metadata") else {},
            }
            if "edge_seq" in meta_rows:
                data["edge_seq"] = int(meta_rows["edge_seq"])

            for _uid, display_id, body in conn.execute("SELECT uid, display_id, body FROM nodes"):
                data["nodes"][display_id] = json.loads(body)

            edges = [json.loads(b) for (_id, _t, _f, _to, b)
                     in conn.execute("SELECT id, type, from_uid, to_uid, body FROM edges ORDER BY id")]
            if edges:
                data["edges"] = edges
        finally:
            conn.close()

        self.data = data
        return self.data

    def save(self) -> str:
        self.data.setdefault("metadata", {})
        self.data["metadata"]["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ensure_uids(self.data.get("nodes", {}))
        ensure_layer(self.data.get("nodes", {}))

        conn = self._connect()
        try:
            self._ensure_schema(conn)
            conn.execute("BEGIN")
            meta = {
                "title": self.data.get("title", ""),
                "description": self.data.get("description", ""),
                "version": self.data.get("version", 1),
                "metadata": json.dumps(self.data.get("metadata", {}), ensure_ascii=False),
            }
            if "edge_seq" in self.data:
                meta["edge_seq"] = self.data["edge_seq"]
            conn.executemany(
                "INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)", list(meta.items())
            )

            conn.execute("DELETE FROM nodes")
            node_rows = [
                (n.get("uid"), nid, json.dumps(n, ensure_ascii=False))
                for nid, n in self.data.get("nodes", {}).items()
            ]
            conn.executemany(
                "INSERT OR REPLACE INTO nodes(uid, display_id, body) VALUES(?, ?, ?)", node_rows
            )

            conn.execute("DELETE FROM edges")
            edge_rows = [
                (e.get("id"), e.get("type"), e.get("from"), e.get("to"),
                 json.dumps(e, ensure_ascii=False))
                for e in self.data.get("edges", [])
            ]
            conn.executemany(
                "INSERT OR REPLACE INTO edges(id, type, from_uid, to_uid, body) VALUES(?, ?, ?, ?, ?)",
                edge_rows,
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()
        return self.json_path

    # ── lease store (overrides) ───────────────────────
    # Kept in its own tables so a lease write never touches the roadmap data and
    # vice-versa — mirroring the single-file `.leases.json` sidecar exactly.

    def _read_lease_store(self) -> dict:
        if not os.path.exists(self.json_path):
            return {"leases": {}, "events": []}
        conn = self._connect()
        try:
            self._ensure_schema(conn)
            leases = {uid: json.loads(body)
                      for uid, body in conn.execute("SELECT node_uid, body FROM leases")}
            events = [json.loads(body)
                      for (_seq, _uid, body)
                      in conn.execute("SELECT seq, node_uid, body FROM lease_events ORDER BY seq")]
        finally:
            conn.close()
        return {"leases": leases, "events": events}

    def _write_lease_store(self, store: dict) -> None:
        conn = self._connect()
        try:
            self._ensure_schema(conn)
            conn.execute("BEGIN")
            conn.execute("DELETE FROM leases")
            conn.execute("DELETE FROM lease_events")
            lease_rows = [
                (uid, json.dumps(lease, ensure_ascii=False))
                for uid, lease in store.get("leases", {}).items()
            ]
            conn.executemany(
                "INSERT OR REPLACE INTO leases(node_uid, body) VALUES(?, ?)", lease_rows
            )
            event_rows = [
                (e.get("node_uid", ""), json.dumps(e, ensure_ascii=False))
                for e in store.get("events", [])
            ]
            conn.executemany(
                "INSERT INTO lease_events(node_uid, body) VALUES(?, ?)", event_rows
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()
