"""Explicit migration of legacy plan nodes to typed ``group``/``work`` nodes."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from carrier_migration import export_lease_store, export_roadmap_data, load_carrier, write_carrier
from roadmap import LAYER_PLAN, ensure_layer
from roadmap_sqlite import is_sqlite_path


NODE_TYPE_GROUP = "group"
NODE_TYPE_WORK = "work"
NODE_TYPES = frozenset({NODE_TYPE_GROUP, NODE_TYPE_WORK})


def migrate_types(source: str | Path, output: str | Path) -> dict[str, Any]:
    """Copy a roadmap to a new artifact and classify every plan node.

    A node with children is a ``group``; a leaf is a ``work``.  The root is
    always a group.  Trace nodes are left untouched and all existing UIDs,
    edges, decisions, statuses and placements are copied as-is.
    """
    source_path = Path(source).expanduser().resolve()
    target_path = Path(output).expanduser().resolve()
    if source_path == target_path:
        raise ValueError("type migration source and output must be different artifacts")
    if target_path.exists():
        raise ValueError(f"migration target already exists: {target_path}")

    original = load_carrier(source_path)
    data = copy.deepcopy(export_roadmap_data(original))
    ensure_layer(data.get("nodes", {}))
    typed = 0
    for node_id, node in data.get("nodes", {}).items():
        if node.get("layer", LAYER_PLAN) != LAYER_PLAN:
            continue
        node["node_type"] = (
            NODE_TYPE_GROUP
            if node_id == "1" or node.get("children")
            else NODE_TYPE_WORK
        )
        typed += 1

    target_storage = "sqlite" if is_sqlite_path(str(target_path)) else "single"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    write_carrier(target_path, target_storage, data, export_lease_store(original))
    return {
        "schema": "zj-node-type-migration/v1",
        "source": str(source_path),
        "target": str(target_path),
        "source_unchanged": True,
        "typed_plan_nodes": typed,
        "node_types": {
            NODE_TYPE_GROUP: sum(
                1 for node in data.get("nodes", {}).values()
                if node.get("node_type") == NODE_TYPE_GROUP
            ),
            NODE_TYPE_WORK: sum(
                1 for node in data.get("nodes", {}).values()
                if node.get("node_type") == NODE_TYPE_WORK
            ),
        },
    }
