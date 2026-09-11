"""Sharded, lazy roadmap storage for large roadmaps.

The public command surface is implemented by ``roadmap_cli.py``. This module
is the bundle adapter behind that interface: current node and decision state is
stored in small shards, history is append-only, and indexes/current pointers are
derived control data that can be rebuilt by validation.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

# 预算与开工计数是 carrier 无关的语义，复用 roadmap.py 的实现，
# 避免两个 carrier 对同一个 budget 各算一套（remove-decision 那类漂移）。
from roadmap import (
    EDGE_BLOCKS,
    EDGE_SUPERSEDES,
    EDGE_TYPES,
    STATUS_COMPLETED,
    SETTABLE_STATUSES,
    CycleError,
    InvalidStatus,
    NodeNotFound,
    build_budget,
    check_child_budget,
    count_round_start,
)


BUNDLE_SCHEMA = "zj-roadmap-bundle-manifest/v1"
CURRENT_SCHEMA = "zj-roadmap-bundle-current/v1"
SNAPSHOT_SCHEMA = "zj-roadmap-bundle-snapshot/v1"
HISTORY_SCHEMA = "zj-roadmap-bundle-history/v1"
EDGE_SCHEMA = "zj-roadmap-bundle-edge/v1"
EDGE_INDEX_SCHEMA = "zj-roadmap-bundle-edge-index/v1"
STATUS_VALUES = {"pending", "in_progress", "completed", "blocked"}
MODE_VALUES = {"explore", "exploit"}
NODE_ID_PATTERN = re.compile(r"^[1-9][0-9]*(?:-[1-9][0-9]*)*$")
DEFAULT_SNAPSHOT_INTERVAL = 100


class BundleError(RuntimeError):
    """A user-actionable roadmap bundle failure."""


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def atomic_json(path: Path, value: Any) -> None:
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as output:
        output.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
        output.flush()
        os.fsync(output.fileno())


def safe_node_id(node_id: str) -> str:
    if not isinstance(node_id, str) or not NODE_ID_PATTERN.fullmatch(node_id):
        raise BundleError(f"invalid roadmap node id: {node_id}")
    return node_id


def node_depth(node_id: str) -> int:
    return node_id.count("-") + 1


def parent_id_of(node_id: str) -> Optional[str]:
    return node_id.rsplit("-", 1)[0] if "-" in node_id else None


def status_file(status: str, node_id: str) -> str:
    return f"indexes/status/{status}/{safe_node_id(node_id)}"


class RoadmapBundle:
    """A lazy adapter with the same command-facing interface as ``Roadmap``."""

    is_bundle = True

    def __init__(self, bundle_path: str | Path):
        self.path = Path(bundle_path).expanduser().resolve()
        self.manifest: dict[str, Any] = {}
        self.last_edge_cascade: dict = {"total": 0, "by_type": {}}

    # ---- creation and loading -------------------------------------------------

    @classmethod
    def create_from_data(cls, bundle_path: str | Path, data: dict[str, Any], snapshot_interval: int = DEFAULT_SNAPSHOT_INTERVAL) -> "RoadmapBundle":
        bundle = cls(bundle_path)
        if bundle.path.exists():
            raise BundleError(f"roadmap bundle already exists: {bundle.path}")
        if snapshot_interval < 1:
            raise BundleError("snapshot interval must be positive")
        cls._validate_legacy_data(data)
        parent = bundle.path.parent
        parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=f".{bundle.path.name}.", dir=parent))
        try:
            target = cls(temporary)
            target._initialize_layout(data, snapshot_interval)
            target.validate_or_raise()
            if bundle.path.exists():
                raise BundleError(f"roadmap bundle appeared during migration: {bundle.path}")
            os.replace(temporary, bundle.path)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
        bundle.load()
        return bundle

    @classmethod
    def migrate_from_legacy(cls, source_path: str | Path, bundle_path: str | Path, snapshot_interval: int = DEFAULT_SNAPSHOT_INTERVAL) -> "RoadmapBundle":
        source = Path(source_path).expanduser().resolve()
        if not source.is_file():
            raise BundleError(f"legacy roadmap does not exist: {source}")
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise BundleError(f"could not read legacy roadmap {source}: {error}") from error
        if not isinstance(data, dict):
            raise BundleError("legacy roadmap must contain one JSON object")
        cls._validate_legacy_data(data)
        return cls.create_from_data(bundle_path, data, snapshot_interval)

    @staticmethod
    def _validate_legacy_data(data: dict[str, Any]) -> None:
        """Reject an invalid source before any bundle directory is created."""
        nodes = data.get("nodes")
        if not isinstance(nodes, dict) or "1" not in nodes:
            raise BundleError("legacy roadmap must contain a nodes object with root node '1'")
        for node_id, node in nodes.items():
            if not isinstance(node, dict) or node.get("id") != node_id:
                raise BundleError(f"legacy roadmap node {node_id} has an invalid shape or id")
            if not NODE_ID_PATTERN.fullmatch(str(node_id)):
                raise BundleError(f"legacy roadmap has invalid node id: {node_id}")
            if node.get("status") not in STATUS_VALUES or node.get("mode") not in MODE_VALUES:
                raise BundleError(f"legacy roadmap node {node_id} has invalid status or mode")
            if not isinstance(node.get("children", []), list) or not isinstance(node.get("decisions", []), list):
                raise BundleError(f"legacy roadmap node {node_id} has invalid children or decisions")
            parent = node.get("parent")
            if parent is not None and parent not in nodes:
                raise BundleError(f"legacy roadmap node {node_id} has missing parent {parent}")
            for child_id in node.get("children", []):
                if child_id not in nodes or nodes[child_id].get("parent") != node_id:
                    raise BundleError(f"legacy roadmap node {node_id} has invalid child reference {child_id}")
        if nodes["1"].get("parent") is not None:
            raise BundleError("legacy roadmap root node '1' must not have a parent")
        for edge in data.get("edges") or []:
            if not isinstance(edge, dict) or edge.get("from") not in nodes or edge.get("to") not in nodes:
                raise BundleError(f"legacy roadmap has an edge with a missing endpoint: {edge}")
            if edge.get("type") not in EDGE_TYPES:
                raise BundleError(f"legacy roadmap has an edge of unknown type: {edge}")

    def _initialize_layout(self, data: dict[str, Any], snapshot_interval: int) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        for directory in ("nodes", "decisions", "history", "snapshots", "views", "indexes/status/pending", "indexes/status/in_progress", "indexes/status/completed", "indexes/status/blocked"):
            (self.path / directory).mkdir(parents=True, exist_ok=True)
        metadata = data.get("metadata", {})
        self.manifest = {
            "schema": BUNDLE_SCHEMA,
            "kind": "roadmap-bundle",
            "version": 1,
            "title": data.get("title", "Untitled"),
            "description": data.get("description", ""),
            "roadmapVersion": data.get("version", 1),
            "metadata": {"md_file": metadata.get("md_file", "")},
            "snapshotInterval": snapshot_interval,
            "historySequence": 0,
            "currentPointer": "current.json",
            "currentSnapshot": "snapshots/snapshot-000000.json",
            "created": now_text(),
            "updated": now_text(),
        }
        nodes = data["nodes"]
        for node_id, node in nodes.items():
            self._write_node_file(node_id, node)
            self._write_decisions_file(node_id, node.get("decisions", []))
            self._set_status_marker(node_id, node["status"], True)
        # 边跟着一起迁：漏掉它就是静默丢数据，而命令层看起来一切正常。
        # 没有边时一个目录都不要建——布局必须和没有边的 bundle 完全一致。
        edges = data.get("edges") or []
        if edges:
            self._edges_dir().mkdir(parents=True, exist_ok=True)
            for edge in edges:
                self._write_edge_file({key: edge[key] for key in ("id", "from", "to", "type")})
            self._rebuild_edge_index()
            # 计数器按现存最大 id 续，不是按条数：删过的 id 不该在迁移后被复用。
            self.manifest["edgeSequence"] = max(int(str(edge["id"])[1:]) for edge in edges)
        stats = self._calculate_stats(nodes.values())
        atomic_json(self.path / "indexes/stats.json", stats)
        atomic_json(self.path / "indexes/focus.json", {"focus": self._focus_from_nodes(nodes.values())})
        atomic_json(self.path / "current.json", self._current_document(0, stats))
        atomic_json(self.path / "snapshots/snapshot-000000.json", self._snapshot_document(0, stats))
        atomic_write(self.path / "history/events.jsonl", "")
        atomic_json(self.path / "manifest.json", self.manifest)

    def load(self) -> dict[str, Any]:
        manifest_path = self.path / "manifest.json"
        if not manifest_path.is_file():
            raise BundleError(f"roadmap bundle manifest does not exist: {manifest_path}")
        try:
            self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise BundleError(f"could not read roadmap bundle manifest: {error}") from error
        if self.manifest.get("schema") != BUNDLE_SCHEMA or self.manifest.get("kind") != "roadmap-bundle":
            raise BundleError(f"unsupported roadmap bundle: {manifest_path}")
        return self.manifest

    def save(self) -> str:
        """Mutations are committed shard-by-shard; retain CLI's save seam."""
        if not self.manifest:
            self.load()
        return str(self.path)

    def _write_node_file(self, node_id: str, node: dict[str, Any]) -> None:
        stored = {key: value for key, value in node.items() if key != "decisions"}
        atomic_json(self.path / "nodes" / f"{safe_node_id(node_id)}.json", stored)

    def _write_decisions_file(self, node_id: str, decisions: list[dict[str, Any]]) -> None:
        atomic_json(self.path / "decisions" / f"{safe_node_id(node_id)}.json", {"node_id": node_id, "decisions": decisions})

    def _read_node_file(self, node_id: str) -> dict[str, Any]:
        safe_node_id(node_id)
        path = self.path / "nodes" / f"{node_id}.json"
        if not path.is_file():
            raise KeyError(f"节点不存在: {node_id}")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise BundleError(f"could not read node shard {path}: {error}") from error
        if not isinstance(value, dict):
            raise BundleError(f"node shard is not an object: {path}")
        return value

    def _read_decisions_file(self, node_id: str) -> list[dict[str, Any]]:
        safe_node_id(node_id)
        path = self.path / "decisions" / f"{node_id}.json"
        if not path.is_file():
            return []
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or value.get("node_id") != node_id or not isinstance(value.get("decisions"), list):
            raise BundleError(f"invalid decisions shard: {path}")
        return value["decisions"]

    def _current_document(self, sequence: int, stats: dict[str, Any], snapshot: Optional[str] = None) -> dict[str, Any]:
        snapshot = snapshot or str(self.manifest.get("currentSnapshot", "snapshots/snapshot-000000.json"))
        return {"schema": CURRENT_SCHEMA, "sequence": sequence, "snapshot": snapshot, "stats": stats, "updated": now_text()}

    def _snapshot_document(self, sequence: int, stats: dict[str, Any]) -> dict[str, Any]:
        return {"schema": SNAPSHOT_SCHEMA, "snapshotId": f"snapshot-{sequence:06d}", "sequence": sequence, "nodeCount": stats["total_nodes"], "stats": stats, "materialized": True, "created": now_text()}

    def _commit(self, operation: str, payload: dict[str, Any], stats: dict[str, Any]) -> None:
        sequence = int(self.manifest.get("historySequence", 0)) + 1
        event = {"schema": HISTORY_SCHEMA, "sequence": sequence, "operation": operation, "payload": payload, "at": now_text()}
        append_jsonl(self.path / "history/events.jsonl", event)
        atomic_json(self.path / "indexes/stats.json", stats)
        snapshot = str(self.manifest.get("currentSnapshot", "snapshots/snapshot-000000.json"))
        interval = int(self.manifest.get("snapshotInterval", DEFAULT_SNAPSHOT_INTERVAL))
        if sequence % interval == 0:
            snapshot = f"snapshots/snapshot-{sequence:06d}.json"
            atomic_json(self.path / snapshot, self._snapshot_document(sequence, stats))
        atomic_json(self.path / "current.json", self._current_document(sequence, stats, snapshot))
        self.manifest["historySequence"] = sequence
        self.manifest["currentSnapshot"] = snapshot
        self.manifest["updated"] = now_text()
        atomic_json(self.path / "manifest.json", self.manifest)

    # ---- indexes and current state -------------------------------------------

    @staticmethod
    def _calculate_stats(nodes: Iterable[dict[str, Any]]) -> dict[str, Any]:
        values = list(nodes)
        status_counts = {status: 0 for status in STATUS_VALUES}
        total_decisions = 0
        for node in values:
            status = node.get("status")
            if status in status_counts:
                status_counts[status] += 1
            total_decisions += len(node.get("decisions", []))
        return {"total_nodes": len(values), "status_counts": status_counts, "total_decisions": total_decisions, "max_depth": max((node_depth(node["id"]) for node in values), default=0)}

    @staticmethod
    def _focus_from_nodes(nodes: Iterable[dict[str, Any]]) -> Optional[str]:
        values = list(nodes)
        candidates = [node for node in values if node.get("status") == "in_progress" and not node.get("children")]
        return max((node["id"] for node in candidates), key=node_depth, default=None)

    def _read_stats(self) -> dict[str, Any]:
        path = self.path / "indexes/stats.json"
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
        self.rebuild_indexes()
        return json.loads(path.read_text(encoding="utf-8"))

    def _read_focus(self) -> Optional[str]:
        path = self.path / "indexes/focus.json"
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8")).get("focus")
        self.rebuild_indexes()
        return json.loads(path.read_text(encoding="utf-8")).get("focus")

    def _set_status_marker(self, node_id: str, status: str, present: bool) -> None:
        if status not in STATUS_VALUES:
            raise BundleError(f"invalid status: {status}")
        marker = self.path / status_file(status, node_id)
        if present:
            marker.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(marker, "")
        else:
            try:
                marker.unlink()
            except FileNotFoundError:
                pass

    def _update_status_marker(self, node_id: str, old: str, new: str) -> None:
        if old != new:
            self._set_status_marker(node_id, old, False)
            self._set_status_marker(node_id, new, True)

    def _refresh_focus(self) -> Optional[str]:
        candidates: list[dict[str, Any]] = []
        status_dir = self.path / "indexes/status/in_progress"
        for marker in sorted(status_dir.iterdir()) if status_dir.is_dir() else []:
            if marker.is_file():
                node_id = marker.name
                try:
                    node = self._read_node_file(node_id)
                except (KeyError, BundleError):
                    continue
                if not node.get("children"):
                    candidates.append(node)
        focus = self._focus_from_nodes(candidates)
        atomic_json(self.path / "indexes/focus.json", {"focus": focus})
        return focus

    def rebuild_indexes(self) -> dict[str, Any]:
        nodes = [self._read_node_file(path.stem) for path in sorted((self.path / "nodes").glob("*.json"))]
        for status in STATUS_VALUES:
            directory = self.path / "indexes/status" / status
            if directory.exists():
                shutil.rmtree(directory)
            directory.mkdir(parents=True, exist_ok=True)
        for node in nodes:
            self._set_status_marker(node["id"], node["status"], True)
        stats = self._calculate_stats(nodes)
        stats["total_decisions"] = sum(len(self._read_decisions_file(node["id"])) for node in nodes)
        atomic_json(self.path / "indexes/stats.json", stats)
        atomic_json(self.path / "indexes/focus.json", {"focus": self._focus_from_nodes(nodes)})
        return stats

    # ---- node and decision operations ----------------------------------------

    def get_node(self, node_id: str) -> dict[str, Any]:
        node = self._read_node_file(node_id)
        node["decisions"] = self._read_decisions_file(node_id)
        return node

    # ── 派生阻塞（#80）─────────────────────────────────
    # 与 single-file 同一套语义：读视图里算，carrier 的 status 不写 blocked。

    def blocking_edges(self, node_id: str) -> list[str]:
        index = self._read_edge_index()
        blockers: list[str] = []
        for edge_id in index.get("to", {}).get(node_id, []):
            edge = self._read_edge_file(edge_id)
            if edge["type"] != EDGE_BLOCKS:
                continue
            try:
                predecessor = self._read_node_file(edge["from"])
            except KeyError:
                # 悬空边按未完成算：它永远等不到"完成"那天。
                blockers.append(edge_id)
                continue
            if predecessor.get("status") != STATUS_COMPLETED:
                blockers.append(edge_id)
        return sorted(blockers, key=lambda edge_id: int(edge_id[1:]))

    def blocked_node_ids(self) -> set[str]:
        """一次算出整张图里被阻塞的节点 id（渲染按整棵树取图标）。"""
        blocked: set[str] = set()
        for edge_id in self._edge_ids():
            edge = self._read_edge_file(edge_id)
            if edge["type"] != EDGE_BLOCKS:
                continue
            try:
                predecessor = self._read_node_file(edge["from"])
            except KeyError:
                blocked.add(edge["to"])
                continue
            if predecessor.get("status") != STATUS_COMPLETED:
                blocked.add(edge["to"])
        return blocked

    def get_node_view(self, node_id: str) -> dict[str, Any]:
        node = self.get_node(node_id)
        blockers = self.blocking_edges(node_id)
        if not blockers:
            return node
        return {**node, "blocked": True, "blocked_reason": blockers}

    def add_node(
        self,
        parent_id: str,
        label: str,
        status: str = "pending",
        mode: str = "explore",
        max_children: Any = None,
        max_rounds: Any = None,
        exit_criteria: Optional[list] = None,
    ) -> dict[str, Any]:
        parent = self._read_node_file(parent_id)
        if status not in SETTABLE_STATUSES:
            raise InvalidStatus(f"不可设置的状态: {status}（blocked 由 blocks 边派生）")
        if mode not in MODE_VALUES:
            raise BundleError("invalid node mode")
        check_child_budget(parent)
        children = parent.setdefault("children", [])
        next_index = int(children[-1].split("-")[-1]) + 1 if children else 1
        node_id = f"{parent_id}-{next_index}"
        node = {"id": node_id, "label": label, "status": "pending", "mode": mode, "parent": parent_id, "children": [], "decisions": [], "notes": ""}
        budget = build_budget(max_children, max_rounds)
        if budget:
            node["budget"] = budget
        if exit_criteria:
            node["exit_criteria"] = list(exit_criteria)
        count_round_start(node, status)
        node["status"] = status
        children.append(node_id)
        self._write_node_file(node_id, node)
        self._write_decisions_file(node_id, [])
        self._set_status_marker(node_id, status, True)
        self._write_node_file(parent_id, parent)
        stats = self._read_stats()
        stats["total_nodes"] += 1
        stats["status_counts"][status] += 1
        stats["max_depth"] = max(stats["max_depth"], node_depth(node_id))
        self._sync_parent_status(node_id, stats)
        self._refresh_focus()
        self._commit("node-added", {"nodeId": node_id, "parentId": parent_id}, stats)
        return node

    def update_node(
        self,
        node_id: str,
        label: Optional[str] = None,
        status: Optional[str] = None,
        mode: Optional[str] = None,
        notes: Optional[str] = None,
        max_children: Any = None,
        max_rounds: Any = None,
        exit_criteria: Optional[list] = None,
        clear_budget: bool = False,
        clear_exit_criteria: bool = False,
    ) -> dict[str, Any]:
        node = self._read_node_file(node_id)
        old_status = node["status"]
        if label is not None:
            node["label"] = label
        if status is not None:
            if status not in SETTABLE_STATUSES:
                raise InvalidStatus(f"不可设置的状态: {status}（blocked 由 blocks 边派生）")
            count_round_start(node, status)
            node["status"] = status
        if mode is not None:
            if mode not in MODE_VALUES:
                raise BundleError(f"invalid mode: {mode}")
            node["mode"] = mode
        if notes is not None:
            node["notes"] = notes

        if clear_budget:
            node.pop("budget", None)
        budget = build_budget(max_children, max_rounds)
        if budget:
            node.setdefault("budget", {}).update(budget)
        elif max_children is not None or max_rounds is not None:
            raise BundleError("budget values must be non-negative integers")

        if clear_exit_criteria:
            node["exit_criteria"] = []
        if exit_criteria:
            node.setdefault("exit_criteria", []).extend(exit_criteria)
        self._write_node_file(node_id, node)
        stats = self._read_stats()
        if old_status != node["status"]:
            self._update_status_marker(node_id, old_status, node["status"])
            stats["status_counts"][old_status] -= 1
            stats["status_counts"][node["status"]] += 1
        self._sync_parent_status(node_id, stats)
        self._refresh_focus()
        fields = [key for key, value in (("label", label), ("status", status), ("mode", mode), ("notes", notes)) if value is not None]
        fields += [key for key, value in (("max_children", max_children), ("max_rounds", max_rounds)) if value is not None]
        if exit_criteria:
            fields.append("exit_criteria")
        if clear_budget:
            fields.append("clear_budget")
        if clear_exit_criteria:
            fields.append("clear_exit_criteria")
        self._commit("node-updated", {"nodeId": node_id, "fields": fields}, stats)
        return node

    def _collect_subtree(self, node_id: str) -> list[dict[str, Any]]:
        node = self._read_node_file(node_id)
        result = [node]
        for child_id in node.get("children", []):
            result.extend(self._collect_subtree(child_id))
        return result

    # ── 依赖边（P1 依赖层）──────────────────────────────
    # 边只存一处：`edges/<id>.json`。节点分片里禁止反向存 edge id——
    # 那会造出"节点说有这条边、edges/ 里没有"的双写不一致，而事务对它免疫
    # （你忘了写哪个位置，事务照样提交）。`edges/index.json` 是纯冗余，能从
    # 目录重扫重建，坏了不丢信息；节点里的 edge id 坏了则无法判断谁对。

    def _edges_dir(self) -> Path:
        return self.path / "edges"

    def _edge_ids(self) -> list[str]:
        """按 id 的数字序返回——与 single-file 的插入序一致，两个 carrier 可比对。"""
        directory = self._edges_dir()
        if not directory.is_dir():
            return []
        return sorted((path.stem for path in directory.glob("e*.json")), key=lambda name: int(name[1:]))

    def _read_edge_file(self, edge_id: str) -> dict[str, Any]:
        path = self._edges_dir() / f"{edge_id}.json"
        if not path.is_file():
            raise KeyError(f"边不存在: {edge_id}")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise BundleError(f"could not read edge shard {path}: {error}") from error
        if not isinstance(value, dict):
            raise BundleError(f"edge shard is not an object: {path}")
        value = dict(value)
        value.pop("schema", None)
        return value

    def _write_edge_file(self, edge: dict[str, Any]) -> None:
        atomic_json(self._edges_dir() / f"{edge['id']}.json", {"schema": EDGE_SCHEMA, **edge})

    def _rebuild_edge_index(self) -> dict[str, Any]:
        """从 edges/ 目录重扫索引。目录不存在时不要创建——那会污染布局。"""
        index: dict[str, Any] = {"schema": EDGE_INDEX_SCHEMA, "from": {}, "to": {}}
        for edge_id in self._edge_ids():
            edge = self._read_edge_file(edge_id)
            index["from"].setdefault(edge["from"], []).append(edge_id)
            index["to"].setdefault(edge["to"], []).append(edge_id)
        if self._edges_dir().is_dir():
            atomic_json(self._edges_dir() / "index.json", index)
        return index

    def _read_edge_index(self) -> dict[str, Any]:
        path = self._edges_dir() / "index.json"
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
        return self._rebuild_edge_index()

    def _write_edge_index(self, index: dict[str, Any]) -> None:
        atomic_json(self._edges_dir() / "index.json", index)

    def add_edge(self, from_id: str, to_id: str, edge_type: str) -> dict[str, Any]:
        """在两个节点之间记一条边。返回写入的边。"""
        for endpoint in (from_id, to_id):
            try:
                self._read_node_file(endpoint)
            except KeyError:
                raise NodeNotFound(f"节点不存在: {endpoint}") from None
        if edge_type not in EDGE_TYPES:
            raise ValueError(f"无效的边类型: {edge_type}")
        if edge_type == EDGE_BLOCKS and self._blocks_reachable(to_id, from_id):
            raise CycleError(
                f"{from_id} -blocks-> {to_id} 会让依赖图成环"
                f"（{to_id} 已经直接或间接阻塞 {from_id}）"
            )
        self._edges_dir().mkdir(parents=True, exist_ok=True)
        sequence = int(self.manifest.get("edgeSequence", 0)) + 1
        self.manifest["edgeSequence"] = sequence
        edge = {"id": f"e{sequence}", "from": from_id, "to": to_id, "type": edge_type}
        self._write_edge_file(edge)
        # 整表重建，不追加：追加会重复登记刚写进去的这条边——读索引时若索引
        # 不存在会按目录重建，那份重建结果已经含它了。`list_edges` 用 set 去重
        # 所以看不见，派生字段（#80 的 blocked_reason）直接照抄索引就会报两遍。
        # 索引是纯冗余，重建的成本换"索引与目录不可能不一致"是划算的。
        self._rebuild_edge_index()
        if edge_type == EDGE_SUPERSEDES:
            # 被取代的节点转 archived 但不删除：它的决策与历史仍然可读。
            # 用标记而不是 status，因为"completed 且 archived"（做完了但被取代）
            # 是合理组合，塞进 status 会丢掉"完成过"这个信息。
            node = self._read_node_file(to_id)
            node["archived"] = True
            self._write_node_file(to_id, node)
        self._commit("edge-added", {"edgeId": edge["id"], "from": from_id, "to": to_id, "type": edge_type}, self._read_stats())
        return edge

    def list_edges(self, node_id: Optional[str] = None) -> list[dict[str, Any]]:
        """列出全部边；给了 node_id 就只列与它相连的（入边 + 出边）。"""
        if node_id is None:
            return [self._read_edge_file(edge_id) for edge_id in self._edge_ids()]
        index = self._read_edge_index()
        selected = set(index.get("from", {}).get(node_id, [])) | set(index.get("to", {}).get(node_id, []))
        return [self._read_edge_file(edge_id) for edge_id in self._edge_ids() if edge_id in selected]

    def remove_edges_touching(self, node_ids: set) -> dict:
        """删掉所有端点落在 node_ids 里的边。返回 {"total": n, "by_type": {...}}。

        边不能独立于节点存在——节点没了，它的边就没有信息量，留着只会变成
        悬空边。所以 delete 默认级联，不设 --cascade 之类的开关。

        不写 history：调用方（delete_node）会在自己的 event 里带上条数，
        一次删除不该产生两条 event。
        """
        directory = self._edges_dir()
        if not directory.is_dir():
            # 一条边都没有时别碰磁盘：否则会给从未用过边的 bundle 造出
            # edges/ 目录与空 index，违反"没有边时布局与 P1 之前一致"。
            return {"total": 0, "by_type": {}}
        by_type: dict = {}
        doomed = []
        for edge_id in self._edge_ids():
            edge = self._read_edge_file(edge_id)
            if edge["from"] in node_ids or edge["to"] in node_ids:
                by_type[edge["type"]] = by_type.get(edge["type"], 0) + 1
                doomed.append(edge_id)
        for edge_id in doomed:
            (directory / f"{edge_id}.json").unlink()
        if doomed:
            self._rebuild_edge_index()
        return {"total": sum(by_type.values()), "by_type": by_type}

    def remove_edge(self, edge_id: str) -> dict[str, Any]:
        """删掉一条边。返回被删掉的边。"""
        edge = self._read_edge_file(edge_id)
        (self._edges_dir() / f"{edge_id}.json").unlink()
        self._rebuild_edge_index()
        self._commit("edge-removed", {"edgeId": edge_id}, self._read_stats())
        return edge

    def _blocks_reachable(self, start: str, target: str) -> bool:
        """沿 blocks 边从 start 出发能否走到 target。自环也算（start == target）。"""
        adjacency: dict[str, list[str]] = {}
        for edge_id in self._edge_ids():
            edge = self._read_edge_file(edge_id)
            if edge["type"] == EDGE_BLOCKS:
                adjacency.setdefault(edge["from"], []).append(edge["to"])
        seen: set[str] = set()
        stack = [start]
        while stack:
            current = stack.pop()
            if current == target:
                return True
            if current in seen:
                continue
            seen.add(current)
            stack.extend(adjacency.get(current, []))
        return False

    def delete_node(self, node_id: str) -> list[str]:
        if node_id == "1":
            raise BundleError("不能删除根节点")
        node = self._read_node_file(node_id)
        parent = self._read_node_file(node["parent"])
        deleted_nodes = self._collect_subtree(node_id)
        # 先删边、后删节点：万一中间被打断，剩下的是"边没了、节点还在"这种
        # 能重做的半态，而不是悬空边。穷人的事务——零成本，且两个 carrier 一致。
        self.last_edge_cascade = self.remove_edges_touching({item["id"] for item in deleted_nodes})
        parent["children"].remove(node_id)
        self._write_node_file(parent["id"], parent)
        stats = self._read_stats()
        for deleted in deleted_nodes:
            deleted_id = deleted["id"]
            decision_count = len(self._read_decisions_file(deleted_id))
            try:
                (self.path / "nodes" / f"{deleted_id}.json").unlink()
                (self.path / "decisions" / f"{deleted_id}.json").unlink()
            except FileNotFoundError:
                pass
            self._set_status_marker(deleted_id, deleted["status"], False)
            stats["total_nodes"] -= 1
            stats["status_counts"][deleted["status"]] -= 1
            stats["total_decisions"] -= decision_count
        stats["max_depth"] = max((node_depth(path.stem) for path in (self.path / "nodes").glob("*.json")), default=0)
        self._sync_parent_status(parent["id"], stats, include_self=True)
        self._refresh_focus()
        payload = {"nodeIds": [item["id"] for item in deleted_nodes]}
        if self.last_edge_cascade["total"]:
            # 只在真删了边时带：没有边的 bundle 的 history 必须与 P1 之前逐字节一致。
            payload["removedEdges"] = self.last_edge_cascade
        self._commit("nodes-deleted", payload, stats)
        return [item["id"] for item in deleted_nodes]

    def add_decision(self, node_id: str, question: str, answer: str, note: str = "") -> dict[str, Any]:
        self._read_node_file(node_id)
        decisions = self._read_decisions_file(node_id)
        decision = {"q": question, "answer": answer, "note": note}
        decisions.append(decision)
        self._write_decisions_file(node_id, decisions)
        stats = self._read_stats()
        stats["total_decisions"] += 1
        self._commit("decision-added", {"nodeId": node_id}, stats)
        return decision

    def remove_decision(self, node_id: str, index: Optional[int] = None, question: Optional[str] = None) -> int:
        self._read_node_file(node_id)
        decisions = self._read_decisions_file(node_id)
        selected: list[dict[str, Any]] = []
        if index is not None:
            if not 0 <= index < len(decisions):
                raise IndexError(f"决策索引越界: {index} (共 {len(decisions)} 条)")
            selected = [decisions[index]] if not decisions[index].get("retracted") else []
        elif question is not None:
            selected = [decision for decision in decisions if decision.get("q") == question and not decision.get("retracted")]
        else:
            raise BundleError("remove_decision 需提供 index 或 question 之一")
        if not selected:
            return 0
        for decision in selected:
            decisions.append({"q": decision.get("q", ""), "answer": "", "note": f"retracted: {decision.get('note', '')}".rstrip(), "retracted": True, "retracts": sha256(canonical_json(decision))})
        self._write_decisions_file(node_id, decisions)
        stats = self._read_stats()
        stats["total_decisions"] += len(selected)
        self._commit("decision-retracted", {"nodeId": node_id, "count": len(selected)}, stats)
        return len(selected)

    def get_decisions(self, node_id: Optional[str] = None) -> list[dict[str, Any]]:
        if node_id:
            return self._read_decisions_file(node_id)
        result = []
        for path in sorted((self.path / "nodes").glob("*.json"), key=lambda item: node_depth(item.stem)):
            current_id = path.stem
            node = self._read_node_file(current_id)
            result.extend({"node_id": current_id, "node_label": node["label"], **decision} for decision in self._read_decisions_file(current_id))
        return result

    def _sync_parent_status(self, node_id: str, stats: dict[str, Any], include_self: bool = False) -> None:
        current = self._read_node_file(node_id)
        parent_id = node_id if include_self else current.get("parent")
        while parent_id:
            parent = self._read_node_file(parent_id)
            children = [self._read_node_file(child_id) for child_id in parent.get("children", [])]
            old_status = parent["status"]
            all_done = bool(children) and all(child["status"] == "completed" for child in children)
            new_status = "completed" if all_done else ("in_progress" if old_status == "completed" else old_status)
            if new_status != old_status:
                parent["status"] = new_status
                self._write_node_file(parent_id, parent)
                self._update_status_marker(parent_id, old_status, new_status)
                stats["status_counts"][old_status] -= 1
                stats["status_counts"][new_status] += 1
            parent_id = parent.get("parent")

    # ---- bounded navigation and views ---------------------------------------

    def get_tree(self, root_id: str = "1", max_depth: int = 2) -> str:
        root = self._read_node_file(root_id)
        blocked = self.blocked_node_ids()
        lines = [self._tree_line(root, "", True, 0, blocked)]

        def walk(node: dict[str, Any], prefix: str, last: bool, depth: int) -> None:
            if depth > max_depth:
                return
            lines.append(self._tree_line(node, prefix, last, depth, blocked))
            if depth >= max_depth:
                return
            children = node.get("children", [])
            child_prefix = prefix + ("    " if last else "│   ")
            for index, child_id in enumerate(children):
                walk(self._read_node_file(child_id), child_prefix, index == len(children) - 1, depth + 1)

        for index, child_id in enumerate(root.get("children", [])):
            child = self._read_node_file(child_id)
            child_last = index == len(root.get("children", [])) - 1
            walk(child, "", child_last, 1)
        return "\n".join(lines)

    @staticmethod
    def _tree_line(
        node: dict[str, Any],
        prefix: str,
        last: bool,
        depth: int,
        blocked: Optional[set[str]] = None,
    ) -> str:
        icons = {"pending": "[ ]", "in_progress": "[~]", "completed": "[x]", "blocked": "[!]"}
        modes = {"explore": "[X+]", "exploit": "[Y+]"}
        connector = "" if depth == 0 else ("└── " if last else "├── ")
        # blocked 派生自边，不读 status——status 里永远不该有它（#80）。
        icon = "[!]" if node["id"] in (blocked or frozenset()) else icons.get(node.get("status"), "[?]")
        return f"{prefix}{connector}{icon}{modes.get(node.get('mode'), '')} {node['id']}. {node['label']}"

    def get_path(self, node_id: str) -> list[str]:
        path: list[str] = []
        current = node_id
        while current:
            path.insert(0, current)
            current = self._read_node_file(current).get("parent")
        return path

    def get_siblings(self, node_id: str) -> list[str]:
        node = self._read_node_file(node_id)
        parent_id = node.get("parent")
        if not parent_id:
            return []
        return [child_id for child_id in self._read_node_file(parent_id).get("children", []) if child_id != node_id]

    def get_current_focus(self) -> Optional[str]:
        return self._read_focus()

    def get_focus_subtree(self, root_id: str, max_depth: int = 1) -> str:
        root = self._read_node_file(root_id)
        lines: list[str] = []
        blocked = self.blocked_node_ids()

        def walk(node: dict[str, Any], prefix: str, last: bool, depth: int) -> None:
            connector = "└── " if last else "├── "
            lines.append(self._tree_line(node, prefix, last, depth, blocked))
            children = node.get("children", [])
            child_prefix = prefix + ("    " if last else "│   ")
            if depth >= max_depth:
                if children:
                    lines.append(f"{child_prefix}... {len(children)} more child nodes; run tree {node['id']} --depth 2 for full view")
                return
            for index, child_id in enumerate(children):
                walk(self._read_node_file(child_id), child_prefix, index == len(children) - 1, depth + 1)

        for index, child_id in enumerate(root.get("children", [])):
            walk(self._read_node_file(child_id), "", index == len(root.get("children", [])) - 1, 1)
        return "\n".join(lines)

    def render_light_section(self) -> str:
        focus_id = self.get_current_focus()
        section = f"<!-- ROADMAP_SECTION_START -->\n## ZJ Roadmap\n\n> 数据文件: `{self.path.name}` | 最后更新: {self.manifest.get('updated', now_text())}\n\n{self.get_tree(max_depth=2)}\n"
        if focus_id:
            focus = self._read_node_file(focus_id)
            section += f"\n### 当前施工：{focus_id}. {focus['label']}\n"
            if focus.get("notes"):
                section += f"\n{focus['notes']}\n"
            decisions = self._read_decisions_file(focus_id)
            if decisions:
                section += "\n**决策：**\n" + "\n".join(f"- Q: {item['q']} → {item['answer']}" for item in decisions) + "\n"
            subtree = self.get_focus_subtree(focus_id, max_depth=1)
            if subtree:
                section += f"\n**当前子树：**\n{subtree}\n"
        return section + "<!-- ROADMAP_SECTION_END -->\n"

    def render_full_section(self, all_nodes: bool = False, max_depth: int = 2, max_bytes: Optional[int] = None) -> str:
        depth = 100000 if all_nodes else max_depth
        section = f"## ZJ Roadmap\n\n> 数据文件: `{self.path.name}` | 最后更新: {self.manifest.get('updated', now_text())}\n\n{self.get_tree(max_depth=depth)}\n"
        if all_nodes:
            decisions = self.get_decisions()
            if decisions:
                section += "\n### 决策历史\n\n| 节点 | 问题 | 答案 | 备注 |\n|------|------|------|------|\n"
                section += "\n".join(f"| {item['node_id']} | {item['q']} | {item['answer']} | {item.get('note', '')} |" for item in decisions) + "\n"
        if max_bytes is not None and len(section.encode("utf-8")) > max_bytes:
            encoded = section.encode("utf-8")[:max_bytes]
            section = encoded.decode("utf-8", errors="ignore") + "\n> View truncated at --max-bytes. Use section --all with a larger limit for export.\n"
        return section

    def write_markdown_section(self) -> Optional[str]:
        internal = self.path / "views/roadmap.md"
        atomic_write(internal, self.render_light_section())
        md_file = self.manifest.get("metadata", {}).get("md_file", "")
        if not md_file:
            return str(internal)
        destination = Path(md_file)
        content = destination.read_text(encoding="utf-8") if destination.exists() else ""
        section = self.render_light_section().rstrip()
        start_marker = "<!-- ROADMAP_SECTION_START -->"
        end_marker = "<!-- ROADMAP_SECTION_END -->"
        start = content.find(start_marker)
        end = content.find(end_marker, start + len(start_marker)) if start >= 0 else -1
        if start >= 0 and end >= 0:
            content = content[:start] + section + content[end + len(end_marker):]
        elif start >= 0:
            content = content[:start] + section
        else:
            content = content.rstrip() + ("\n\n" if content.strip() else "") + section + "\n"
        atomic_write(destination, content)
        return str(destination)

    def link_md_file(self, md_file: str) -> None:
        self.manifest.setdefault("metadata", {})["md_file"] = str(Path(md_file).expanduser().resolve())
        self.manifest["updated"] = now_text()
        atomic_json(self.path / "manifest.json", self.manifest)

    # ---- validation and statistics ------------------------------------------

    def validate(self) -> list[str]:
        errors: list[str] = []
        try:
            self.load()
        except BundleError as error:
            return [str(error)]
        if self.manifest.get("currentPointer") != "current.json":
            errors.append("manifest currentPointer must be current.json")
        if not (self.path / "current.json").is_file() or not (self.path / "indexes/stats.json").is_file():
            errors.append("bundle control files are missing")
            return errors
        try:
            current = json.loads((self.path / "current.json").read_text(encoding="utf-8"))
            if current.get("schema") != CURRENT_SCHEMA:
                errors.append("current pointer has an invalid schema")
            if current.get("snapshot") != self.manifest.get("currentSnapshot"):
                errors.append("current pointer snapshot does not match manifest")
            snapshot_path = self.path / str(current.get("snapshot", ""))
            if not snapshot_path.is_file():
                errors.append("current materialized snapshot is missing")
            else:
                snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
                if snapshot.get("schema") != SNAPSHOT_SCHEMA:
                    errors.append("current materialized snapshot has an invalid schema")
                if snapshot.get("sequence", -1) > current.get("sequence", -1):
                    errors.append("current materialized snapshot is ahead of current history")
            stats = self._read_stats()
            nodes = [self._read_node_file(path.stem) for path in sorted((self.path / "nodes").glob("*.json"))]
            node_ids = {node.get("id") for node in nodes}
            if "1" not in node_ids:
                errors.append("bundle is missing root node 1")
            if len(node_ids) != len(nodes):
                errors.append("node IDs are not unique")
            for node in nodes:
                node_id = node.get("id")
                shard_path = self.path / "nodes" / f"{node_id}.json"
                if node_id not in node_ids or not NODE_ID_PATTERN.fullmatch(str(node_id)):
                    errors.append(f"invalid node id: {node_id}")
                if shard_path.stem != str(node_id):
                    errors.append(f"node shard filename does not match node id: {shard_path.name}")
                if node.get("status") not in STATUS_VALUES or node.get("mode") not in MODE_VALUES:
                    errors.append(f"node {node_id} has invalid status or mode")
                if node.get("parent") is not None and node.get("parent") not in node_ids:
                    errors.append(f"node {node_id} has a missing parent")
                if node_id == "1" and node.get("parent") is not None:
                    errors.append("root node 1 must not have a parent")
                for child_id in node.get("children", []):
                    if child_id not in node_ids:
                        errors.append(f"node {node_id} has a missing child {child_id}")
                    elif self._read_node_file(child_id).get("parent") != node_id:
                        errors.append(f"node {node_id} child {child_id} has a mismatched parent")
                decisions = self._read_decisions_file(node_id)
                if not isinstance(decisions, list):
                    errors.append(f"node {node_id} decisions are not a list")
            for edge_id in self._edge_ids():
                try:
                    edge = self._read_edge_file(edge_id)
                except (KeyError, BundleError) as error:
                    errors.append(str(error))
                    continue
                for endpoint in ("from", "to"):
                    if edge.get(endpoint) not in node_ids:
                        errors.append(f"edge {edge_id} points at missing node {edge.get(endpoint)}")
            expected = self._calculate_stats(nodes)
            expected["total_decisions"] = sum(len(self._read_decisions_file(node["id"])) for node in nodes)
            if stats != expected:
                errors.append("materialized stats do not match node shards")
            if current.get("sequence") != self.manifest.get("historySequence"):
                errors.append("current pointer sequence does not match manifest")
            history_path = self.path / "history/events.jsonl"
            if not history_path.is_file():
                errors.append("history log is missing")
            else:
                expected_sequence = 0
                for line in history_path.read_text(encoding="utf-8").splitlines():
                    event = json.loads(line)
                    expected_sequence += 1
                    if event.get("schema") != HISTORY_SCHEMA or event.get("sequence") != expected_sequence:
                        errors.append("history log has a broken sequence")
                        break
                if expected_sequence != self.manifest.get("historySequence"):
                    errors.append("history log sequence does not match manifest")
        except (OSError, KeyError, json.JSONDecodeError, BundleError) as error:
            errors.append(str(error))
        return errors

    def validate_or_raise(self) -> None:
        errors = self.validate()
        if errors:
            raise BundleError("roadmap bundle validation failed: " + "; ".join(errors))

    def stats(self) -> dict[str, Any]:
        return self._read_stats()
