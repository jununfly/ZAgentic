"""zj-dp-driven carrier — process state in SQLite (stdlib `sqlite3`, zero new deps).

Design baseline: docs/designs/zj-dp-driven-skill-design.md §2 / §3 / §5.3 / §7.

The carrier is the physical home of the DP table (§2 "存储 / carrier"). It holds
ONLY process state: the two-layer state graph (tasks / task-plans / tickets /
findings + their edges & memberships). It is deleted at closeout (§5.2) and must
never be referenced by a long-lived doc (§5.3).

Schema discipline locked by the design — this file is where the `[目标]`
"实现时定列/类型" lands:

  meta        key/value         — destination, version, timestamps
  task        id PK             — layer-1 node. NO status / NO completed_at:
                                  both are derived from the 1:1 task_plan (§3.1, §3.3).
                                  `derived_from_finding` records §3.5 form-③ origin
                                  (a new task spawned by a finding's disposition).
  task_plan   task_id PK(1:1)   — layer-2 region. `status` is the SINGLE source of
                                  the task↔plan lifecycle (§3.1); explicit three-state
                                  only — 被阻塞 is derived, never stored here (§3.2).
  finding     id PK             — memoized subproblem node. `status` explicit three-state;
                                  多归属 via finding_membership (§3.4); content lives in `md_path`.
                                  `derived_from_finding` records §3.5 form-② origin (a new
                                  finding split out of a parent finding); NULL for a root.
  finding_membership (fid,tid)  — many-to-many finding↔plan (§3.4, §3.6 F1).
  ticket      id PK             — atomic action node. `task_id` is the SINGLE-membership
                                  owner (§3.4) — NULL means "not yet in any plan" = in pool.
                                  `derived_from_finding` is the §7 Q1 物化 edge (int|null).
   edge        id PK             — `blocks` dependency among layer-2 nodes (any kind pair).
                                   The ONLY source of `blocked` (§3.2). Parent-child is a
                                   ticket column, not an edge, so it never blocks (§3.2).
   claim      (kind,ref_id) PK   — two-layer claim (§4.4). `last_seen_at`(epoch) +
                                   `lease_seconds` make `expired` a DERIVED read-time fact
                                   (the lease is the stored truth; `expired` is never stored —
                                   same anti-drift rule as §3.1/§3.2). `lease_seconds = NULL`
                                   ⇒ never expires (§8 opt-in `--no-lease`).

`load()` returns an in-memory dict mirroring what `DpDriven` operates on; `save()`
rewrites all rows inside a single transaction (the atomic multi-row write SQLite's
justification). NULL columns round-trip to Python `None`, which the model treats as
"field absent" so derived views never write a `false` / empty placeholder (§3.2).
"""

from __future__ import annotations

import json
import os
import sqlite3

DB_SUFFIXES = (".sqlite", ".sqlite3", ".db")


def is_db_path(path: str) -> bool:
    """Route a carrier path to the SQLite backend by its extension."""
    return os.path.splitext(path)[1].lower() in DB_SUFFIXES


_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS task (
    id                    INTEGER PRIMARY KEY,
    name                  TEXT NOT NULL,
    context_md            TEXT,
    memory_md             TEXT,
    derived_from_finding  INTEGER,
    created_at            TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS task_plan (
    task_id      INTEGER PRIMARY KEY,
    status       TEXT NOT NULL,
    summary      TEXT,
    created_at   TEXT NOT NULL,
    completed_at TEXT
);
CREATE TABLE IF NOT EXISTS finding (
    id                   INTEGER PRIMARY KEY,
    status               TEXT NOT NULL,
    md_path              TEXT,
    external_hold        TEXT,
    derived_from_finding INTEGER,
    created_at           TEXT NOT NULL,
    completed_at         TEXT
);
CREATE TABLE IF NOT EXISTS finding_membership (
    finding_id INTEGER NOT NULL,
    task_id    INTEGER NOT NULL,
    PRIMARY KEY (finding_id, task_id)
);
CREATE TABLE IF NOT EXISTS ticket (
    id                   INTEGER PRIMARY KEY,
    status               TEXT NOT NULL,
    task_id              INTEGER,
    derived_from_finding INTEGER,
    parent_id            INTEGER,
    ref                  TEXT,
    kv                   TEXT,
    md_path              TEXT,
    external_hold        TEXT,
    created_at           TEXT NOT NULL,
    completed_at         TEXT
);
CREATE TABLE IF NOT EXISTS edge (
    id        INTEGER PRIMARY KEY,
    type      TEXT NOT NULL,
    from_kind TEXT NOT NULL,
    from_id   INTEGER NOT NULL,
    to_kind   TEXT NOT NULL,
    to_id     INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS claim (
    kind          TEXT NOT NULL,   -- 'plan' | 'ticket' (§4.4 two-layer)
    ref_id        INTEGER NOT NULL,
    agent         TEXT NOT NULL,
    claimed_at    TEXT NOT NULL,
    last_seen_at  INTEGER,         -- epoch seconds; refreshed by claim/renew (§4.4 TTL)
    lease_seconds INTEGER,         -- lease length; NULL = never expires (§8 opt-in)
    PRIMARY KEY (kind, ref_id)
);
"""


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    # Single-writer carrier (§4.4 "carrier 单写者"): serialized writes are the
    # atomicity guarantee for finding disposition / hot-plug. WAL is fine but not
    # required for Phase 1; keep it for read-while-write.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)


def empty_data() -> dict:
    return {
        "meta": {},
        "tasks": {},        # str(id) -> task row
        "plans": {},        # str(task_id) -> task_plan row (1:1)
        "findings": {},     # str(id) -> finding row
        "memberships": [],  # [{"finding_id":int,"task_id":int}]
        "tickets": {},      # str(id) -> ticket row
        "edges": [],        # [{"id":int,"type":str,"from_kind":str,"from_id":int,...}]
        "claims": [],       # [{"kind":str,"ref_id":int,"agent":str,"claimed_at":str,"last_seen_at":int|None,"lease_seconds":int|None}]
    }


def load(db_path: str) -> dict:
    """Read the whole carrier into an in-memory dict. Raises FileNotFoundError
    when the carrier does not exist (caller decides whether to `init`)."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"carrier 文件不存在: {db_path}")
    conn = _connect(db_path)
    try:
        ensure_schema(conn)
        data = empty_data()
        data["meta"] = {r[0]: r[1] for r in conn.execute("SELECT key, value FROM meta")}

        for row in conn.execute(
            "SELECT id, name, context_md, memory_md, derived_from_finding, created_at FROM task ORDER BY id"
        ):
            tid = row[0]
            data["tasks"][str(tid)] = {
                "id": tid, "name": row[1], "context_md": row[2],
                "memory_md": row[3], "derived_from_finding": row[4], "created_at": row[5],
            }
        for row in conn.execute(
            "SELECT task_id, status, summary, created_at, completed_at FROM task_plan ORDER BY task_id"
        ):
            data["plans"][str(row[0])] = {
                "task_id": row[0], "status": row[1], "summary": row[2],
                "created_at": row[3], "completed_at": row[4],
            }
        for row in conn.execute(
            "SELECT id, status, md_path, external_hold, derived_from_finding, created_at, completed_at FROM finding ORDER BY id"
        ):
            fid = row[0]
            data["findings"][str(fid)] = {
                "id": fid, "status": row[1], "md_path": row[2],
                "external_hold": row[3], "derived_from_finding": row[4],
                "created_at": row[5], "completed_at": row[6],
            }
        for fid, tid in conn.execute(
            "SELECT finding_id, task_id FROM finding_membership ORDER BY finding_id, task_id"
        ):
            data["memberships"].append({"finding_id": fid, "task_id": tid})

        for row in conn.execute(
            "SELECT id, status, task_id, derived_from_finding, parent_id, ref, kv, "
            "md_path, external_hold, created_at, completed_at FROM ticket ORDER BY id"
        ):
            tkid = row[0]
            kv = json.loads(row[6]) if row[6] else None
            data["tickets"][str(tkid)] = {
                "id": tkid, "status": row[1], "task_id": row[2],
                "derived_from_finding": row[3], "parent_id": row[4], "ref": row[5],
                "kv": kv, "md_path": row[7], "external_hold": row[8],
                "created_at": row[9], "completed_at": row[10],
            }
        for row in conn.execute(
            "SELECT id, type, from_kind, from_id, to_kind, to_id FROM edge ORDER BY id"
        ):
            data["edges"].append({
                "id": row[0], "type": row[1], "from_kind": row[2],
                "from_id": row[3], "to_kind": row[4], "to_id": row[5],
            })
        for row in conn.execute(
            "SELECT kind, ref_id, agent, claimed_at, last_seen_at, lease_seconds FROM claim ORDER BY kind, ref_id"
        ):
            data["claims"].append({
                "kind": row[0], "ref_id": row[1], "agent": row[2], "claimed_at": row[3],
                "last_seen_at": row[4], "lease_seconds": row[5],
            })
    finally:
        conn.close()
    return data


def save(db_path: str, data: dict) -> str:
    """Persist the in-memory dict. All rows are rewritten inside one transaction so
    a half-written carrier can never be observed (§4.4 single-writer atomicity)."""
    conn = _connect(db_path)
    try:
        ensure_schema(conn)
        conn.execute("BEGIN")

        conn.execute("DELETE FROM meta")
        conn.executemany(
            "INSERT INTO meta(key, value) VALUES(?, ?)",
            [(k, _as_text(v)) for k, v in data.get("meta", {}).items()],
        )

        conn.execute("DELETE FROM task")
        conn.executemany(
            "INSERT INTO task(id, name, context_md, memory_md, derived_from_finding, created_at) VALUES(?,?,?,?,?,?)",
            [
                (t["id"], t["name"], t.get("context_md"), t.get("memory_md"),
                 t.get("derived_from_finding"), t["created_at"])
                for t in data.get("tasks", {}).values()
            ],
        )

        conn.execute("DELETE FROM task_plan")
        conn.executemany(
            "INSERT INTO task_plan(task_id, status, summary, created_at, completed_at) VALUES(?,?,?,?,?)",
            [
                (p["task_id"], p["status"], p.get("summary"), p["created_at"], p.get("completed_at"))
                for p in data.get("plans", {}).values()
            ],
        )

        conn.execute("DELETE FROM finding")
        conn.executemany(
            "INSERT INTO finding(id, status, md_path, external_hold, derived_from_finding, "
            "created_at, completed_at) VALUES(?,?,?,?,?,?,?)",
            [
                (f["id"], f["status"], f.get("md_path"), f.get("external_hold"),
                 f.get("derived_from_finding"), f["created_at"], f.get("completed_at"))
                for f in data.get("findings", {}).values()
            ],
        )

        conn.execute("DELETE FROM finding_membership")
        conn.executemany(
            "INSERT INTO finding_membership(finding_id, task_id) VALUES(?,?)",
            [(m["finding_id"], m["task_id"]) for m in data.get("memberships", [])],
        )

        conn.execute("DELETE FROM ticket")
        conn.executemany(
            "INSERT INTO ticket(id, status, task_id, derived_from_finding, parent_id, ref, kv, "
            "md_path, external_hold, created_at, completed_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            [
                (t["id"], t["status"], t.get("task_id"), t.get("derived_from_finding"),
                 t.get("parent_id"), t.get("ref"),
                 json.dumps(t["kv"], ensure_ascii=False) if t.get("kv") is not None else None,
                 t.get("md_path"), t.get("external_hold"), t["created_at"], t.get("completed_at"))
                for t in data.get("tickets", {}).values()
            ],
        )

        conn.execute("DELETE FROM edge")
        conn.executemany(
            "INSERT INTO edge(id, type, from_kind, from_id, to_kind, to_id) VALUES(?,?,?,?,?,?)",
            [
                (e["id"], e["type"], e["from_kind"], e["from_id"], e["to_kind"], e["to_id"])
                for e in data.get("edges", [])
            ],
        )

        conn.execute("DELETE FROM claim")
        conn.executemany(
            "INSERT INTO claim(kind, ref_id, agent, claimed_at, last_seen_at, lease_seconds) VALUES(?,?,?,?,?,?)",
            [
                (c["kind"], c["ref_id"], c["agent"], c["claimed_at"],
                 c.get("last_seen_at"), c.get("lease_seconds"))
                for c in data.get("claims", [])
            ],
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    return db_path


def _as_text(value) -> str:
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
