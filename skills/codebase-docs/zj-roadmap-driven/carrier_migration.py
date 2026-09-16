"""Explicit, no-loss conversion between the three roadmap carriers (#117, P3).

Spec: ``docs/plans/zj-roadmap-dag-concurrency.md`` §5 + Stories 39/40.

Two rules shape this module:

**Explicit (Story 40).** Nothing here is reachable implicitly. No command
auto-upgrades a carrier, and this module never deletes or rewrites the source
artifact — carrying the fact source across is a decision a Human makes once,
out loud, with `migrate <source> --to <carrier>`.

**One adapter contract.** All three carriers already satisfy one shared
contract (that was #116's hard rule). So this module does *not* write three
converters; it exports one canonical shape out of whatever carrier it is given
and feeds that same shape into whichever carrier it is asked for. Adding a
fourth carrier later means adding one case to each of two functions, not six
pairwise converters.

Canonical shapes
----------------
`export_roadmap_data` → the single-file JSON layout
    ``{title, description, version, nodes, edges, metadata, edge_seq?}``
    Edges are always in **display-id** form, and both carriers store them the
    same way — so a migration round trip can never silently rewrite the fact
    source's endpoints while changing nothing else visible, which is the worst
    kind of drift.

`export_lease_store` → the single-file sidecar layout
    ``{"leases": {...}, "events": [...]}`` keyed by display id, event `at` as
    epoch float (see `Roadmap._read_lease_store`).
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from roadmap import Roadmap
from roadmap_sqlite import RoadmapSqlite, is_sqlite_path


CARRIERS = ("single", "sqlite")
SUFFIXES = {"single": ".json", "sqlite": ".sqlite"}


def detect_storage(path: str | Path) -> str:
    """Which carrier owns this artifact, by the same rule the CLI routes by.

    A directory is not an artifact: the only carriers are a single JSON file
    and a sqlite file, so refusing here keeps migration from guessing.
    """
    target = Path(path)
    if target.is_dir():
        raise ValueError(f"not a roadmap artifact (directory): {target}")
    if is_sqlite_path(str(target)):
        return "sqlite"
    return "single"


def load_carrier(path: str | Path, storage: str | None = None):
    """Load `path` with whichever carrier knows how to read it."""
    target = Path(path)
    kind = storage or detect_storage(target)
    roadmap: Roadmap | RoadmapSqlite
    if kind == "sqlite":
        roadmap = RoadmapSqlite(target)
    elif kind == "single":
        roadmap = Roadmap(target)
    else:
        raise ValueError(f"unknown roadmap carrier: {storage}")
    roadmap.load()
    return roadmap


def export_roadmap_data(carrier) -> dict[str, Any]:
    """The whole fact source, in the canonical single-file layout."""
    return copy.deepcopy(carrier.data)


def export_lease_store(carrier) -> dict[str, Any]:
    """Leases + audit events in the canonical sidecar layout.

    Both carriers expose `_read_lease_store`, so this function has no
    special cases.
    """
    return carrier._read_lease_store()


def write_carrier(
    path: str | Path,
    storage: str,
    data: dict[str, Any],
    lease_store: dict[str, Any] | None = None,
):
    """Create `path` in `storage` from canonical data, then seed the leases.

    Refuses to overwrite anything: silent clobbering of an existing fact source
    is exactly the failure Story 40 exists to prevent.
    """
    target = Path(path)
    if target.exists():
        raise ValueError(f"migration target already exists: {target}")

    carrier: Any = RoadmapSqlite(str(target)) if storage == "sqlite" else Roadmap(str(target))
    carrier.data = copy.deepcopy(data)
    target.parent.mkdir(parents=True, exist_ok=True)
    carrier.save()

    if lease_store:
        carrier._write_lease_store(copy.deepcopy(lease_store))
    return carrier


def default_output(source: Path, to: str) -> Path:
    """Where the migrated artifact goes when `--output` is not given.

    Never equal to `source`: a default that silently points back at the input
    would turn the explicit guard into an overwrite.
    """
    candidate = source.with_suffix(SUFFIXES[to])
    if candidate.resolve() == source.resolve():
        candidate = Path(f"{source}{SUFFIXES[to]}")
    return candidate


def migrate(
    source: str | Path,
    to: str,
    output: str | Path | None = None,
) -> dict[str, Any]:
    """Copy one roadmap into another carrier. Returns a report dict.

    The source is read and left untouched — a migration that rewrites its input
    leaves you unable to answer "which artifact was the fact source a minute
    ago", which is the question Story 40 is about.
    """
    if to not in CARRIERS:
        raise ValueError(f"--to must be one of {', '.join(CARRIERS)}, got: {to}")
    source_path = Path(source).expanduser().resolve()
    source_storage = detect_storage(source_path)
    if to == source_storage:
        raise ValueError(f"{source_path} is already {to}; migrating to the same carrier is a no-op")

    target = Path(output).expanduser().resolve() if output else default_output(source_path, to)
    original = load_carrier(source_path, source_storage)
    data = export_roadmap_data(original)
    leases = export_lease_store(original)
    target.parent.mkdir(parents=True, exist_ok=True)
    write_carrier(target, to, data, leases)

    return {
        "source": str(source_path),
        "source_storage": source_storage,
        "target": str(target),
        "target_storage": to,
        "total_nodes": len(data.get("nodes", {})),
        "total_edges": len(data.get("edges", [])),
        "total_decisions": sum(len(node.get("decisions", [])) for node in data.get("nodes", {}).values()),
        "total_leases": len(leases.get("leases", {})),
        "lease_events": len(leases.get("events", [])),
    }
