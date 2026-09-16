"""Read-only storage recommendations for roadmap artifacts.

The advisor deliberately does not call bundle repair/rebuild paths and never
changes the roadmap carrier.  It reports structural signals first; an
optional ``measure`` pass adds local timing observations for comparison.

Issue #117 (P3): it speaks about single / sqlite; bundle is deprecated (#140)
and any bundle artifact on disk is only advised to migrate off. Recognition
follows the same rule the CLI uses to pick a carrier, so a `.sqlite` artifact
can never again be handed to the JSON reader.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from roadmap import Roadmap, node_depth
from roadmap_bundle import BundleError, RoadmapBundle
from roadmap_sqlite import RoadmapSqlite, is_sqlite_path


ADVISOR_SCHEMA = "zj-roadmap-storage-recommendation/v1"

# 只有两档（#140 弃用 bundle 后）：single 是默认，sqlite 是 scale 档。
# 这些是建议起点，锚在 benchmark 夹具上，绝非迁移闸门。
THRESHOLDS: dict[str, dict[str, int | float]] = {
    # 外推档：benchmark 最大夹具 5000 节点，再往上无实测数据；按 §5 第 3 条
    # （整图读放大）上一个数量级估，只作建议起点——advisor 从不替人迁移。
    "consider_sqlite": {
        "total_nodes": 20_000,
        "total_decisions": 8_000,
        "canonical_bytes": 8 * 1024 * 1024,
        "full_section_ms": 1_500.0,
    },
}


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise BundleError(f"roadmap artifact is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise BundleError(f"roadmap artifact is not valid JSON: {path}") from error


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except FileNotFoundError:
        return 0


def _sum_files(paths: list[Path]) -> int:
    return sum(_file_size(path) for path in paths if path.is_file())


def _linked_view_size(path: Path) -> int:
    return _file_size(path) if path.is_file() else 0


def _single_metrics(path: Path, roadmap: Roadmap) -> dict[str, Any]:
    validation_errors = roadmap.validate()
    if validation_errors:
        raise BundleError("not a valid execution roadmap: " + "; ".join(validation_errors))
    stats = roadmap.stats()
    metadata = roadmap.data.get("metadata", {})
    linked_view = Path(str(metadata.get("md_file", ""))).expanduser() if metadata.get("md_file") else None
    canonical_bytes = _file_size(path)
    return {
        "total_nodes": stats["total_nodes"],
        "total_decisions": stats["total_decisions"],
        "max_depth": stats["max_depth"],
        "canonical_bytes": canonical_bytes,
        "artifact_bytes": canonical_bytes,
        "view_bytes": _linked_view_size(linked_view) if linked_view else 0,
        "node_shards": 0,
        "decision_shards": 0,
        "history_bytes": 0,
    }


def _bundle_metrics(path: Path) -> dict[str, Any]:
    nodes_dir = path / "nodes"
    decisions_dir = path / "decisions"
    node_paths = sorted(nodes_dir.glob("*.json"))
    decision_paths = sorted(decisions_dir.glob("*.json"))
    nodes = [_read_json(node_path) for node_path in node_paths]
    if not any(isinstance(node, dict) and node.get("id") == "1" for node in nodes):
        raise BundleError("not a valid execution roadmap bundle: missing root node '1'")

    total_decisions = 0
    for decision_path in decision_paths:
        shard = _read_json(decision_path)
        if (
            not isinstance(shard, dict)
            or shard.get("node_id") != decision_path.stem
            or not isinstance(shard.get("decisions"), list)
        ):
            raise BundleError(f"invalid decisions shard: {decision_path}")
        total_decisions += len(shard["decisions"])

    canonical_paths = [path / "manifest.json", path / "current.json"]
    canonical_paths.extend(node_paths)
    canonical_paths.extend(decision_paths)
    history_path = path / "history/events.jsonl"
    canonical_paths.append(history_path)

    all_files = [candidate for candidate in path.rglob("*") if candidate.is_file()]
    view_files = [candidate for candidate in all_files if "views" in candidate.relative_to(path).parts]
    metadata = _read_json(path / "manifest.json").get("metadata", {})
    linked_view = Path(str(metadata.get("md_file", ""))).expanduser() if metadata.get("md_file") else None

    return {
        "total_nodes": len(nodes),
        "total_decisions": total_decisions,
        "max_depth": max((node_depth(str(node["id"])) for node in nodes), default=0),
        "canonical_bytes": _sum_files(canonical_paths),
        "artifact_bytes": _sum_files(all_files),
        "view_bytes": _sum_files(view_files) + (_linked_view_size(linked_view) if linked_view else 0),
        "node_shards": len(node_paths),
        "decision_shards": len(decision_paths),
        "history_bytes": _file_size(history_path),
    }


def _sqlite_metrics(path: Path, roadmap: RoadmapSqlite) -> dict[str, Any]:
    """Sqlite metrics over the same keys the other two carriers report.

    `node_shards` / `decision_shards` / `history_bytes` are bundle-only layout
    facts; sqlite normalizes everything into one file, so they stay 0 rather
    than being invented.
    """
    validation_errors = roadmap.validate()
    if validation_errors:
        raise BundleError("not a valid execution roadmap: " + "; ".join(validation_errors))
    if "1" not in roadmap.data.get("nodes", {}):
        raise BundleError("not a valid execution roadmap sqlite: missing root node '1'")
    stats = roadmap.stats()
    metadata = roadmap.data.get("metadata", {})
    linked_view = Path(str(metadata.get("md_file", ""))).expanduser() if metadata.get("md_file") else None
    canonical_bytes = _file_size(path)
    return {
        "total_nodes": stats["total_nodes"],
        "total_decisions": stats["total_decisions"],
        "max_depth": stats["max_depth"],
        "canonical_bytes": canonical_bytes,
        "artifact_bytes": canonical_bytes,
        "view_bytes": _linked_view_size(linked_view) if linked_view else 0,
        "node_shards": 0,
        "decision_shards": 0,
        "history_bytes": 0,
    }


def _load_read_only(path: Path, storage: str) -> Roadmap | RoadmapBundle | RoadmapSqlite:
    roadmap: Roadmap | RoadmapBundle | RoadmapSqlite
    if storage == "bundle":
        roadmap = RoadmapBundle(path)
    elif storage == "sqlite":
        roadmap = RoadmapSqlite(path)
    else:
        roadmap = Roadmap(path)
    roadmap.load()
    return roadmap


def _measure(path: Path, storage: str) -> dict[str, float]:
    started = time.perf_counter()
    _load_read_only(path, storage).get_tree(max_depth=2)
    bounded_tree_ms = (time.perf_counter() - started) * 1000

    started = time.perf_counter()
    _load_read_only(path, storage).render_full_section(all_nodes=True)
    full_section_ms = (time.perf_counter() - started) * 1000
    return {
        "bounded_tree_ms": round(bounded_tree_ms, 3),
        "full_section_ms": round(full_section_ms, 3),
    }


def _signals(
    metrics: dict[str, Any],
    measurements: dict[str, float],
) -> list[dict[str, Any]]:
    """Return the metrics that justify suggesting sqlite, if any.

    After the bundle carrier was deprecated (#140) there is only one advisory
    tier above single: `consider_sqlite`.  No `consider`/`recommend` bundle
    tiers remain.
    """
    values = {**metrics, **measurements}
    sqlite: list[dict[str, Any]] = []
    for metric, threshold in THRESHOLDS["consider_sqlite"].items():
        value = values.get(metric)
        if value is None or value < threshold:
            continue
        sqlite.append({"metric": metric, "value": value, "threshold": threshold})
    return sqlite


def _reasons(signals: list[dict[str, Any]], level: str) -> list[str]:
    return [f"{item['metric']} reached {item['value']} ({level} threshold {item['threshold']})"
            for item in signals]


def _recommendation(
    storage: str,
    sqlite: list[dict[str, Any]],
    path: str = "",
) -> dict[str, Any]:
    """Pick the tier the metrics justify, with the explicit command to act on it.

    Tier order after the bundle carrier was deprecated (#140): keep-single <
    consider-sqlite.  A bundle artifact still on disk is advised to migrate off
    (sqlite outranks it), but **nothing here migrates anything** — the
    advisor's job ends at naming the command (Story 39/40).  The `command`
    value is that name, not an action taken.
    """
    if storage == "sqlite":
        return {
            "action": "keep-sqlite",
            "level": "already-selected",
            "target_storage": "sqlite",
            "reasons": ["sqlite roadmap is already explicitly selected; no migration is needed."],
        }

    if storage == "bundle":
        return {
            "action": "deprecate-bundle",
            "level": "deprecated",
            "target_storage": "sqlite",
            "reasons": [
                "bundle carrier is deprecated (#140); migrate to sqlite (or single) "
                "via an explicit command.",
            ],
            "command": f"migrate {path} --to sqlite",
        }

    if sqlite:
        return {
            "action": "consider-sqlite",
            "level": "consider",
            "target_storage": "sqlite",
            "reasons": _reasons(sqlite, "consider"),
            "command": f"migrate {path} --to sqlite",
        }

    return {
        "action": "keep-single",
        "level": "keep",
        "target_storage": "single",
        "reasons": ["no advisory storage threshold was reached."],
    }


def recommend_storage(path_value: str | Path, measure: bool = False) -> dict[str, Any]:
    """Return a read-only storage recommendation for one roadmap artifact."""
    path = Path(path_value).expanduser().resolve()
    if path.is_dir():
        roadmap: Roadmap | RoadmapBundle | RoadmapSqlite = RoadmapBundle(path)
        roadmap.load()
        storage = "bundle"
        metrics = _bundle_metrics(path)
    elif is_sqlite_path(path):
        roadmap = RoadmapSqlite(path)
        roadmap.load()
        storage = "sqlite"
        metrics = _sqlite_metrics(path, roadmap)
    else:
        roadmap = Roadmap(path)
        roadmap.load()
        storage = "single"
        metrics = _single_metrics(path, roadmap)

    measurements = _measure(path, storage) if measure else {}
    sqlite = _signals(metrics, measurements)
    return {
        "schema": ADVISOR_SCHEMA,
        "path": str(path),
        "storage": storage,
        "read_only": True,
        "metrics": metrics,
        "measurements_ms": measurements,
        "signals": {
            "consider_sqlite": sqlite,
        },
        "thresholds": THRESHOLDS,
        "recommendation": _recommendation(storage, sqlite, str(path)),
    }
