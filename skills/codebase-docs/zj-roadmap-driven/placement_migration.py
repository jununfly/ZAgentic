"""Placement projection and explicit migration helpers.

The legacy roadmap tree stores outline position on ``parent``/``children``.
This module makes that position an explicit, separately addressable fact while
leaving the source carrier untouched.  Work identity remains the node UID;
placement records only describe where a work item appears in the Human
outline.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from carrier_migration import export_lease_store, export_roadmap_data, load_carrier, write_carrier
from roadmap import LAYER_PLAN, ensure_layer, ensure_uids, resolve_node
from roadmap_sqlite import is_sqlite_path


def _plan_nodes(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    nodes = data.get("nodes", {})
    ensure_uids(nodes)
    ensure_layer(nodes)
    return {
        node_id: node
        for node_id, node in nodes.items()
        if node.get("layer", LAYER_PLAN) == LAYER_PLAN
    }


def build_primary_placements(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Project ordered tree membership into primary placements.

    The root is the outline container, not an executable work item, so it has
    no placement.  Every other plan node must occur exactly once in the
    ordered ``children`` relation.  Refusing an orphan is safer than silently
    inventing a display location during migration.
    """
    plan = _plan_nodes(data)
    root = plan.get("1")
    if root is None:
        raise ValueError("placement migration requires root plan node 1")

    placements: list[dict[str, Any]] = []
    visited: set[str] = set()

    def visit(parent_id: str) -> None:
        parent = plan[parent_id]
        for outline_rank, child_id in enumerate(parent.get("children", [])):
            child = plan.get(child_id)
            if child is None:
                raise ValueError(
                    f"placement migration found missing or non-plan child {child_id!r} under {parent_id}"
                )
            if child_id in visited:
                raise ValueError(f"placement migration found duplicate child placement: {child_id}")
            visited.add(child_id)
            placements.append(
                {
                    "id": f"p{len(placements) + 1}",
                    "kind": "primary",
                    "work_uid": child["uid"],
                    "parent_uid": parent["uid"],
                    "outline_rank": outline_rank,
                }
            )
            visit(child_id)

    visit("1")
    expected = set(plan) - {"1"}
    missing = sorted(expected - visited)
    if missing:
        raise ValueError(
            "placement migration cannot place plan nodes not reachable from ordered children: "
            + ", ".join(missing)
        )
    return placements


def placement_views(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return placements with display-id projections for Human-facing output."""
    nodes = data.get("nodes", {})
    by_uid = {node.get("uid"): node for node in nodes.values() if node.get("uid")}
    views = []
    for placement in data.get("placements", []):
        work = by_uid.get(placement.get("work_uid"))
        parent = by_uid.get(placement.get("parent_uid"))
        if work is None:
            raise ValueError(f"placement references missing work uid: {placement.get('work_uid')}")
        if parent is None:
            raise ValueError(f"placement references missing parent uid: {placement.get('parent_uid')}")
        views.append(
            {
                "id": placement["id"],
                "kind": placement["kind"],
                "work_uid": placement["work_uid"],
                "work_id": work["id"],
                "parent_uid": placement["parent_uid"],
                "parent_id": parent["id"],
                "outline_rank": placement["outline_rank"],
            }
        )
    return views


def _resolve_plan_node(data: dict[str, Any], ref: str) -> dict[str, Any]:
    node_id = resolve_node(str(ref), data.get("nodes", {}))
    node = data.get("nodes", {}).get(node_id)
    if node is None or node.get("layer", LAYER_PLAN) != LAYER_PLAN:
        raise ValueError(f"placement target is not a plan node: {ref}")
    return node


def _next_placement_id(placements: list[dict[str, Any]]) -> str:
    used = {str(item.get("id")) for item in placements}
    number = 1
    while f"p{number}" in used:
        number += 1
    return f"p{number}"


def add_reference_placement(
    data: dict[str, Any],
    work_ref: str,
    parent_ref: str,
    outline_rank: int | None = None,
) -> dict[str, Any]:
    """Add a second outline context without copying the WorkItem record."""
    nodes = data.get("nodes", {})
    ensure_uids(nodes)
    ensure_layer(nodes)
    if "placements" not in data:
        data["placements"] = build_primary_placements(data)
    work = _resolve_plan_node(data, work_ref)
    parent = _resolve_plan_node(data, parent_ref)
    if outline_rank is None:
        outline_rank = sum(
            1 for item in data.get("placements", [])
            if item.get("parent_uid") == parent["uid"]
        )
    if int(outline_rank) < 0:
        raise ValueError("outline rank must be non-negative")
    placement = {
        "id": _next_placement_id(data.setdefault("placements", [])),
        "kind": "reference",
        "work_uid": work["uid"],
        "parent_uid": parent["uid"],
        "outline_rank": int(outline_rank),
    }
    data["placements"].append(placement)
    return placement_views(data)[-1]


def move_placement(
    data: dict[str, Any],
    placement_id: str,
    parent_ref: str,
    outline_rank: int | None = None,
) -> dict[str, Any]:
    """Move a Placement while preserving its Work UID and kind."""
    parent = _resolve_plan_node(data, parent_ref)
    placement = next(
        (item for item in data.get("placements", []) if item.get("id") == placement_id),
        None,
    )
    if placement is None:
        raise ValueError(f"placement not found: {placement_id}")
    if outline_rank is None:
        outline_rank = sum(
            1 for item in data.get("placements", [])
            if item.get("parent_uid") == parent["uid"] and item.get("id") != placement_id
        )
    if int(outline_rank) < 0:
        raise ValueError("outline rank must be non-negative")
    placement["parent_uid"] = parent["uid"]
    placement["outline_rank"] = int(outline_rank)
    return next(view for view in placement_views(data) if view["id"] == placement_id)


def _target_storage(path: Path) -> str:
    return "sqlite" if is_sqlite_path(str(path)) else "single"


def migrate_placements(source: str | Path, output: str | Path) -> dict[str, Any]:
    """Copy a roadmap to a new carrier and add explicit primary placements."""
    source_path = Path(source).expanduser().resolve()
    target_path = Path(output).expanduser().resolve()
    if source_path == target_path:
        raise ValueError("placement migration source and output must be different artifacts")
    if target_path.exists():
        raise ValueError(f"migration target already exists: {target_path}")

    original = load_carrier(source_path)
    data = export_roadmap_data(original)
    if data.get("placements"):
        placements = copy.deepcopy(data["placements"])
    else:
        placements = build_primary_placements(data)
        data["placements"] = placements

    target_storage = _target_storage(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    write_carrier(
        target_path,
        target_storage,
        data,
        export_lease_store(original),
    )
    return {
        "schema": "zj-placement-migration/v1",
        "source": str(source_path),
        "source_storage": "sqlite" if is_sqlite_path(str(source_path)) else "single",
        "target": str(target_path),
        "target_storage": target_storage,
        "placements": len(placements),
        "source_unchanged": True,
    }
