"""Read-only storage recommendations for roadmap artifacts.

The advisor deliberately does not call bundle repair/rebuild paths and never
changes the roadmap carrier.  It reports structural signals first; an
optional ``measure`` pass adds local timing observations for comparison.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from roadmap import Roadmap, node_depth
from roadmap_bundle import BundleError, RoadmapBundle


ADVISOR_SCHEMA = "zj-roadmap-storage-recommendation/v1"

# These are advisory starting points, anchored by the small/medium/large
# benchmark fixtures.  They are deliberately not migration gates.
THRESHOLDS: dict[str, dict[str, int | float]] = {
    "consider_bundle": {
        "total_nodes": 1_000,
        "total_decisions": 500,
        "canonical_bytes": 256 * 1024,
        "full_section_ms": 100.0,
    },
    "recommend_bundle": {
        "total_nodes": 5_000,
        "total_decisions": 2_000,
        "canonical_bytes": 1024 * 1024,
        "full_section_ms": 300.0,
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


def _load_read_only(path: Path, storage: str) -> Roadmap | RoadmapBundle:
    roadmap: Roadmap | RoadmapBundle = RoadmapBundle(path) if storage == "bundle" else Roadmap(path)
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


def _signals(metrics: dict[str, Any], measurements: dict[str, float]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    values = {**metrics, **measurements}
    consider: list[dict[str, Any]] = []
    recommend: list[dict[str, Any]] = []
    for metric, threshold in THRESHOLDS["consider_bundle"].items():
        value = values.get(metric)
        if value is None or value < threshold:
            continue
        signal = {
            "metric": metric,
            "value": value,
            "threshold": threshold,
        }
        consider.append(signal)
        recommend_threshold = THRESHOLDS["recommend_bundle"][metric]
        if value >= recommend_threshold:
            recommend.append({**signal, "threshold": recommend_threshold})
    return consider, recommend


def _recommendation(
    storage: str,
    consider: list[dict[str, Any]],
    recommend: list[dict[str, Any]],
) -> dict[str, Any]:
    if storage == "bundle":
        return {
            "action": "keep-bundle",
            "level": "already-selected",
            "target_storage": "bundle",
            "reasons": ["roadmap bundle is already explicitly selected; no migration is needed."],
        }

    if recommend:
        reasons = [f"{item['metric']} reached {item['value']} (recommend threshold {item['threshold']})" for item in recommend]
        return {
            "action": "recommend-bundle",
            "level": "recommend",
            "target_storage": "bundle",
            "reasons": reasons,
        }

    if consider:
        return {
            "action": "consider-bundle",
            "level": "consider",
            "target_storage": "bundle",
            "reasons": [f"{item['metric']} reached {item['value']} (consider threshold {item['threshold']})" for item in consider],
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
        roadmap = RoadmapBundle(path)
        roadmap.load()
        storage = "bundle"
        metrics = _bundle_metrics(path)
    else:
        roadmap = Roadmap(path)
        roadmap.load()
        storage = "single"
        metrics = _single_metrics(path, roadmap)

    measurements = _measure(path, storage) if measure else {}
    consider, recommend = _signals(metrics, measurements)
    return {
        "schema": ADVISOR_SCHEMA,
        "path": str(path),
        "storage": storage,
        "read_only": True,
        "metrics": metrics,
        "measurements_ms": measurements,
        "signals": {
            "consider_bundle": consider,
            "recommend_bundle": recommend,
        },
        "thresholds": THRESHOLDS,
        "recommendation": _recommendation(storage, consider, recommend),
    }
