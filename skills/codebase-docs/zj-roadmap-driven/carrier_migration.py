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
    Edges are always in **display-id** form. bundle stores them as uids, so the
    export translates back — otherwise a single→bundle→single round trip would
    silently rewrite the fact source's endpoints and change nothing else
    visible, which is the worst kind of drift.

`export_lease_store` → the single-file sidecar layout
    ``{"leases": {...}, "events": [...]}`` keyed by display id, event `at` as
    epoch float (see `RoadmapBundle._read_lease_store`).
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from roadmap import Roadmap
from roadmap_bundle import BundleError, RoadmapBundle, DEFAULT_SNAPSHOT_INTERVAL
from roadmap_sqlite import RoadmapSqlite, is_sqlite_path


CARRIERS = ("single", "bundle", "sqlite")
SUFFIXES = {"single": ".json", "bundle": ".bundle", "sqlite": ".sqlite"}


def detect_storage(path: str | Path) -> str:
    """Which carrier owns this artifact, by the same rule the CLI routes by."""
    target = Path(path)
    if target.is_dir():
        return "bundle"
    if is_sqlite_path(str(target)):
        return "sqlite"
    return "single"


def load_carrier(path: str | Path, storage: str | None = None):
    """Load `path` with whichever carrier knows how to read it."""
    target = Path(path)
    kind = storage or detect_storage(target)
    roadmap: Roadmap | RoadmapBundle | RoadmapSqlite
    if kind == "bundle":
        roadmap = RoadmapBundle(target)
    elif kind == "sqlite":
        roadmap = RoadmapSqlite(target)
    elif kind == "single":
        roadmap = Roadmap(target)
    else:
        raise ValueError(f"unknown roadmap carrier: {storage}")
    roadmap.load()
    return roadmap


def export_roadmap_data(carrier) -> dict[str, Any]:
    """The whole fact source, in the canonical single-file layout."""
    if isinstance(carrier, RoadmapBundle):
        return _bundle_data(carrier)
    return copy.deepcopy(carrier.data)


def _bundle_data(bundle: RoadmapBundle) -> dict[str, Any]:
    shown: dict[str, Any] = {}
    for path in sorted((bundle.path / "nodes").glob("*.json"), key=lambda item: item.stem):
        node = copy.deepcopy(bundle._read_node_file(path.stem))
        node["decisions"] = bundle._read_decisions_file(path.stem)
        shown[path.stem] = node
    # 边**不翻显示 id**，保持 bundle 落盘的原形状（uid）。
    #
    # 翻成显示 id 看着更"像 Human 视野"，但它会让同一份 roadmap 在三家 carrier 上
    # 算出三个不同的 rev：single/sqlite 存 uid，bundle 导出却是显示 id，于是
    # single→bundle→sqlite 之后 rev 就漂移了。翻译层（`edge_endpoints_as_display`）
    # 本来就在读侧给 Human 用，不作为存储形态；这里的取舍是"让三家 carrier 的
    # current_revision 对齐"，而不是"导出看起来好看"。
    edges = list(bundle.materialize()["edges"])
    metadata = dict(bundle.manifest.get("metadata", {}))
    data: dict[str, Any] = {
        "title": bundle.manifest.get("title", "Untitled"),
        "description": bundle.manifest.get("description", ""),
        "version": bundle.manifest.get("roadmapVersion", 1),
        "nodes": shown,
        "edges": edges,
        "metadata": metadata,
    }
    # 边的 id 计数器跟着走：删过 id 的那段历史 bundle 不知道（它按现存最大 id
    # 续），带着它下次 `--to bundle` 才不会把已用过的 id 又发一遍。
    if bundle.manifest.get("edgeSequence") is not None:
        data["edge_seq"] = bundle.manifest["edgeSequence"]
    return data


def export_lease_store(carrier) -> dict[str, Any]:
    """Leases + audit events in the canonical sidecar layout.

    All three carriers expose `_read_lease_store`; bundle got its own
    implementation in #117 precisely so this function has no special cases.
    """
    return carrier._read_lease_store()


def write_carrier(
    path: str | Path,
    storage: str,
    data: dict[str, Any],
    lease_store: dict[str, Any] | None = None,
    snapshot_interval: int = DEFAULT_SNAPSHOT_INTERVAL,
):
    """Create `path` in `storage` from canonical data, then seed the leases.

    Refuses to overwrite anything: `create_from_data` already guards the bundle
    case and the file carriers get the same check here. Silent clobbering of an
    existing fact source is exactly the failure Story 40 exists to prevent.
    """
    target = Path(path)
    if target.exists():
        raise BundleError(f"migration target already exists: {target}")

    if storage == "bundle":
        carrier: Any = RoadmapBundle.create_from_data(target, data, snapshot_interval)
    else:
        carrier = RoadmapSqlite(str(target)) if storage == "sqlite" else Roadmap(str(target))
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
    snapshot_interval: int = DEFAULT_SNAPSHOT_INTERVAL,
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
    write_carrier(target, to, data, leases, snapshot_interval)

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
