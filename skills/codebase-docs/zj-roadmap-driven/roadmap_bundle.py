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
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

# 预算与开工计数是 carrier 无关的语义，复用 roadmap.py 的实现，
# 避免两个 carrier 对同一个 budget 各算一套（remove-decision 那类漂移）。
from roadmap import (
    # 租约策略（P2）与 single-file 共用，保证两个 carrier 对 claim/heartbeat/steal/
    # release/fencing 只有一份语义真相；这里只负责把租约落进 leases/ 分片。
    LEASE_TTL_SECONDS,
    is_expired,
    new_lease,
    apply_heartbeat,
    apply_steal,
    LeaseHeld,
    # 边 / 阻塞 / 序号 / uid / 引用解析 / 血缘 等 carrier 无关语义共用，避免漂移。
    EDGE_BLOCKS,
    EDGE_SUPERSEDES,
    EDGE_TYPES,
    # Markdown 模板（#117）：与 single-file 共用同一份，两个 carrier 只喂数据。
    ALL_NODES_TREE_DEPTH,
    compose_full_section,
    compose_light_section,
    focus_export_detail,
    focus_light_detail,
    focus_line,
    CycleError,
    NodeNotFound,
    InvalidKind,
    TraceNotFound,
    InvalidLayer,
    PromoteTargetInvalid,
    PruneNoEdge,
    ReferencedError,
    assert_settable_status,
    blocked_chain_lines,
    blocked_view,
    apply_failure,
    apply_promotion,
    build_budget,
    check_child_budget,
    count_round_start,
    edge_sort_key,
    is_blocking,
    next_child_index,
    note_child_removal,
    ensure_uid,
    ensure_uids,
    new_uid,
    LAYER_PLAN,
    LAYER_TRACE,
    PROMOTE_ACCEPTED,
    TRACE_KINDS,
    EDGE_MAINLINE,
    EDGE_REFERENCE,
    EDGE_DERIVES_FROM,
    ensure_layer,
    assert_plan_layer,
    resolve_node,
    endpoint_to_uid,
    edge_endpoints_as_display,
    migrate_edge_endpoints_to_uid,
    node_context,
    ready_node_list,
    critical_path,
    impact_node_ids,
    render_chain_collapsed,
    render_chain_plain,
    open_question_items,
    render_open_questions_collapsed,
    render_open_questions_plain,
    owner_label,
    tree_line,
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


# history / manifest 里的时间戳一律是这个形状（现在的 `now_text()` 产出，
# 也是所有既有产物里已落盘的形状）。
BUNDLE_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def now_text() -> str:
    return datetime.now().strftime(BUNDLE_TIME_FORMAT)


def bundle_timestamp_to_epoch(text: Any) -> float:
    """bundle history 的文本时间 → epoch float（租约跨 carrier 搬运用）。

    转成 float 是为了和 single / sqlite 侧车里 event 的 `at` 同型：搬过去又搬回来
    时类型不能变，否则同一个事件在两家 carrier 上长得不一样（漂移）。
    """
    try:
        return datetime.strptime(str(text), BUNDLE_TIME_FORMAT).timestamp()
    except (TypeError, ValueError):
        return 0.0


def epoch_to_bundle_timestamp(value: Any) -> str:
    try:
        return datetime.fromtimestamp(float(value)).strftime(BUNDLE_TIME_FORMAT)
    except (TypeError, ValueError, OSError, OverflowError):
        return now_text()


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
        # 边端点接受显示 id 或 uid（#106 S4 后存量边可能已是 uid）。
        node_ids = set(nodes.keys())
        uids = {n.get("uid") for n in nodes.values() if n.get("uid")}
        valid_endpoints = node_ids | uids
        for edge in data.get("edges") or []:
            if not isinstance(edge, dict) or edge.get("from") not in valid_endpoints or edge.get("to") not in valid_endpoints:
                raise BundleError(f"legacy roadmap has an edge with a missing endpoint: {edge}")
            if edge.get("type") not in EDGE_TYPES:
                raise BundleError(f"legacy roadmap has an edge of unknown type: {edge}")

    def _initialize_layout(self, data: dict[str, Any], snapshot_interval: int) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        for directory in ("nodes", "decisions", "history", "snapshots", "views", "traces", "indexes/status/pending", "indexes/status/in_progress", "indexes/status/completed", "indexes/status/blocked"):
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
            # 存量边可能是显示 id（pre-S4 legacy）或已是 uid（post-S4 legacy）：
            # endpoint_to_uid 两种形状都接，落盘一律翻成 uid（#106 S4）。
            for edge in edges:
                self._write_edge_file({
                    "id": edge["id"],
                    "from": endpoint_to_uid(edge["from"], nodes),
                    "to": endpoint_to_uid(edge["to"], nodes),
                    "type": edge["type"],
                })
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
        # 写入时补 uid / layer：老 bundle 的分片在这里被逐片升级。放在写侧
        # 而不是 `_read_node_file` 里，理由与 Roadmap.save 相同——读命令无锁，
        # 在读里写文件并发时可能给同一节点生成两个不同 uid / layer。
        ensure_uid(node)
        ensure_layer([node])
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

    def _read_trace_file(self, node_id: str) -> dict[str, Any]:
        """读一条 trace 分片（L3 隔离在 traces/）。与 _read_node_file 同纪律。"""
        safe_node_id(node_id)
        path = self.path / "traces" / f"{node_id}.json"
        if not path.is_file():
            raise KeyError(f"trace 节点不存在: {node_id}")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise BundleError(f"could not read trace shard {path}: {error}") from error
        if not isinstance(value, dict):
            raise BundleError(f"trace shard is not an object: {path}")
        return value

    def _write_trace_file(self, node_id: str, node: dict[str, Any]) -> None:
        """写一条 trace 分片到 traces/（L3 物理隔离，不进 nodes/、不进状态索引）。"""
        ensure_uid(node)
        ensure_layer([node])  # trace 已是 trace，幂等升级
        stored = {key: value for key, value in node.items() if key != "decisions"}
        atomic_json(self.path / "traces" / f"{safe_node_id(node_id)}.json", stored)

    def _all_trace_nodes(self) -> list[dict[str, Any]]:
        """traces/ 目录下的全部 trace 节点（L3）。目录不存在时返回空。

        直接读每个分片的内容，用分片里的权威 `id` 字段，而不拿文件名当 id——
        否则 `safe_node_id(文件名)` 会拒掉"文件名≠id"的存量/测试分片（如
        `traces/t1.json` 内部 id 是 9001），导致 `list_edges` 等读侧路径崩。
        """
        traces_dir = self.path / "traces"
        if not traces_dir.is_dir():
            return []
        out: list[dict[str, Any]] = []
        for p in sorted(traces_dir.glob("*.json")):
            try:
                value = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise BundleError(f"could not read trace shard {p}: {error}") from error
            if not isinstance(value, dict):
                raise BundleError(f"trace shard is not an object: {p}")
            out.append(value)
        return out

    def _read_any_node(self, node_id: str) -> dict[str, Any]:
        """点查：先 nodes/（plan），再 traces/（trace）。get_node / resolve_node /
        add_edge 都靠它，从而 trace↔trace 的边也能落地与翻译。"""
        try:
            return self._read_node_file(node_id)
        except KeyError:
            pass
        return self._read_trace_file(node_id)

    def _nodes_for_edge_translation(self) -> list[dict[str, Any]]:
        """边端点翻译用的整图节点表（plan + trace）。

        `_all_nodes()` 只含 plan（喂 render/tree/stats/validate），不能把 trace
        端点漏掉——否则 `edge_endpoints_as_display` 翻不出 trace 的显示 id。
        """
        return self._all_nodes() + self._all_trace_nodes()

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
        # 只重建 plan 层索引：trace 节点（S2 起，L3 在 traces/）没有 status，
        # 套用 plan 的状态索引会误建标记甚至崩。遍历经 `iter_nodes(layer='plan')`
        # ——即便某条 trace 分片误落进 nodes/，也只重建 plan 索引。
        nodes = self.iter_nodes()
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
        node = self._read_any_node(node_id)
        node["decisions"] = self._read_decisions_file(node_id)
        return node

    def resolve_node(self, ref: str) -> str:
        """把显示 id 或 uid 翻成显示 id（见模块级 resolve_node）。

        bundle 没有"整图 dict"，节点分散在分片里，所以传 `_all_nodes()` + `_all_trace_nodes()`
        的合并列表——trace 节点的 id / uid 也要能解析（provenance 边引用 trace）。
        """
        return resolve_node(ref, self._all_nodes() + self._all_trace_nodes())

    # ── 来龙去脉 / 就绪建议（#104 S5）─────────────────────

    def context(self, node_id: str, includes=()) -> dict:
        """节点来龙去脉：上游（依赖谁）/下游（谁依赖我）/阻塞链 + `--include`（P5-S4）。

        bundle 的 plan 节点在 `nodes/`、trace 在 `traces/`，故把两者一起喂给
        node_context，--include trace 的对端 trace 才可见（single-file 两份同处
        data["nodes"]，无需此处理）。端点已是显示 id（list_edges 已翻译）。

        注意：bundle 把 `decisions` 拆进独立分片，`_read_node_file` 返回的节点**不含**
        decisions 字段；--include decisions 要读 `by_id[node]["decisions"]`，所以这里
        从分片补回（single-file 的节点 dict 自带 decisions，天然免疫）。
        """
        self._read_any_node(node_id)  # 不存在抛 KeyError，与 single-file 一致
        nodes = self._all_nodes() + self._all_trace_nodes()
        for n in nodes:
            n["decisions"] = self._read_decisions_file(n["id"])
        return node_context(
            node_id,
            nodes,
            self.list_edges(),
            includes=includes,
        )

    def next_nodes(self) -> list:
        """就绪优先建议：关键路径上的就绪节点优先，其余按 id 排序。"""
        ready = self.ready_nodes()
        cp = set(self.critical_path())
        ready.sort(key=lambda n: (n["id"] not in cp, n["id"]))
        return ready

    # ── 派生阻塞（#80）─────────────────────────────────
    # 与 single-file 同一套语义：读视图里算，carrier 的 status 不写 blocked。

    def blocking_edges(self, node_id: str) -> list[str]:
        # 索引按 uid 建（端点落盘是 uid），不能用显示 id 直接查；逐边翻译后比对。
        # 翻译表须含 trace（_nodes_for_edge_translation），否则 derives-from 等边的
        # trace 端点留成 raw uid，下游 _read_node_file 会炸。
        nodes = self._nodes_for_edge_translation()
        blockers: list[str] = []
        for edge_id in self._edge_ids():
            de = edge_endpoints_as_display(self._read_edge_file(edge_id), nodes)
            if de["to"] != node_id:
                continue
            try:
                predecessor = self._read_node_file(de["from"])
            except KeyError:
                predecessor = None
            if is_blocking(de, predecessor):
                blockers.append(edge_id)
        return sorted(blockers, key=edge_sort_key)

    def blocked_node_ids(self) -> set[str]:
        """一次算出整张图里被阻塞的节点 id（显示 id 集合，渲染按整棵树取图标）。

        端点落盘是 uid：比较前每条边翻回显示 id。

        没有边就不可能有被阻塞节点——直接返回空集，不读任何节点分片，
        保证 tree --depth 的懒读契约（只读到请求深度）不被 `blocked_node_ids`
        拉成整图扫描。有边时再走全图计算，供 ready_nodes / critical_path /
        render_* 等需要整图 blocked 集的调用方使用。
        """
        edge_ids = self._edge_ids()
        if not edge_ids:
            return set()
        # 端点翻译必须含 trace 节点：derives-from / mainline / reference 边的端点可能是
        # trace 的 uid，plan 之外的 uid 不在 _all_nodes() 里，会被 edge_endpoints_as_display
        # 原样留成 raw uid，随后 _read_node_file(raw_uid) 触发 safe_node_id 抛 BundleError
        # （single-file 把 trace 与 plan 同存 data["nodes"]，天然免疫——这是 bundle 特有问题）。
        nodes = self._nodes_for_edge_translation()
        blocked: set[str] = set()
        for edge_id in edge_ids:
            de = edge_endpoints_as_display(self._read_edge_file(edge_id), nodes)
            try:
                predecessor = self._read_node_file(de["from"])
            except (KeyError, BundleError):
                predecessor = None
            if is_blocking(de, predecessor):
                blocked.add(de["to"])
        return blocked

    def _predecessor_or_none(self, node_id: str) -> Optional[dict[str, Any]]:
        """读前驱节点；悬空边（前驱不存在）或非法 id 返回 None —— 按未完成算。"""
        try:
            return self._read_node_file(node_id)
        except (KeyError, BundleError):
            return None

    def get_node_view(self, node_id: str) -> dict[str, Any]:
        return blocked_view(self.get_node(node_id), self.blocking_edges(node_id))

    def ready_nodes(self) -> list[dict[str, Any]]:
        """就绪集（#81）：与 single-file 同一份判定，见 `is_ready`。

        遍历经 `iter_nodes(layer='plan')`：trace 节点不进就绪集。
        """
        return ready_node_list(self.iter_nodes(), self.blocked_node_ids())

    def critical_path(self) -> list[str]:
        """关键路径（#81）：与 single-file 同一份判定。

        遍历经 `iter_nodes(layer='plan')`：trace 节点不进关键路径。
        """
        return critical_path(self.iter_nodes(), self.list_edges())

    def impact(self, node_id: str) -> list[str]:
        """影响集（#81）：与 single-file 同一份判定（不含自身）。

        遍历经 `iter_nodes(layer='plan')`：trace 节点不进影响集。
        """
        return impact_node_ids(node_id, self.iter_nodes(), self.list_edges())

    def _all_nodes(self) -> list[dict[str, Any]]:
        """整张图的节点：nodes/ 目录才是权威，状态索引可能失效。

        `nodes/` 只放 plan 节点（L3 物理隔离：trace 在 `traces/`），所以这里读
        到的本来就是 plan；`iter_nodes` 再叠一层字段过滤作逻辑兜底。
        """
        return [
            self._read_node_file(path.stem)
            for path in sorted((self.path / "nodes").glob("*.json"))
        ]

    # ── 遍历入口收敛（P5-S1，L1/L2 归口，§2.3）──────────────
    # 与 single-file 同一套语义契约：默认只看 plan，显式 `layer=LAYER_TRACE`
    # 才看 trace。bundle 的 trace 在独立 `traces/` 目录（L3），目录布局即过滤；
    # 这里再按 `layer` 字段过滤一次，作为逻辑兜底——即便某条 trace 分片误落
    # 进 `nodes/`，遍历也不会把它泄进调度与 md。

    def iter_nodes(self, layer: str = LAYER_PLAN) -> list[dict[str, Any]]:
        if layer == LAYER_TRACE:
            # L3 物理隔离的 trace（traces/）优先；同时保留 L2 字段过滤兜底：
            # 即便某条 trace 分片误落进 nodes/，也能按 layer 过滤出来（不泄进 plan）。
            selected = self._all_trace_nodes() + [
                n for n in self._all_nodes() if n.get("layer") == LAYER_TRACE
            ]
        else:
            # 默认只看 plan；_all_nodes 只读 nodes/，天然不含 traces。
            selected = [n for n in self._all_nodes() if n.get("layer", LAYER_PLAN) == layer]
        selected.sort(key=lambda n: n.get("id", ""))
        return selected

    def node_ids(self, layer: str = LAYER_PLAN) -> list[str]:
        return [n["id"] for n in self.iter_nodes(layer)]

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
        # §2.4 硬前提：trace 节点不设 parent。任何把 plan 节点挂到 trace 节点下的写入
        # 路径必须当场被拒，否则 trace 就会混进 children 数组，污染 tree / _sync_parent_status。
        assert_plan_layer(parent)
        assert_settable_status(status)
        if mode not in MODE_VALUES:
            raise BundleError("invalid node mode")
        check_child_budget(parent)
        children = parent.setdefault("children", [])
        next_index = next_child_index(parent)
        node_id = f"{parent_id}-{next_index}"
        node = {"id": node_id, "uid": new_uid(), "label": label, "status": "pending", "mode": mode, "parent": parent_id, "children": [], "decisions": [], "notes": "", "layer": LAYER_PLAN}
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

    # ── trace 节点（P5-S2，§3.3）────────────────────────
    # 覆写 single-file 的 add_trace：trace 物理落在 traces/（L3），不进 nodes/、
    # 不进状态索引；provenance 诞生即写（--under → prompted_by、--from → mainline 边）。

    def _new_trace_id(self) -> str:
        """生成不与 plan 节点冲突的 trace id（见 Roadmap._new_trace_id 的同名纪律）。"""
        seq = 1
        while (self.path / "traces" / f"9-{seq}.json").exists():
            seq += 1
        return f"9-{seq}"

    def add_trace(
        self,
        kind: str,
        body: str,
        under: Optional[str] = None,
        from_trace: Optional[str] = None,
        session_ref: Optional[str] = None,
        agent_id: Optional[str] = None,
        device_id: Optional[str] = None,
        compressed_from: Optional[list] = None,
    ) -> dict[str, Any]:
        if kind not in TRACE_KINDS:
            raise InvalidKind(kind)
        under_id: Optional[str] = None
        if under is not None:
            try:
                under_id = self.resolve_node(under)
                under_node = self.get_node(under_id)
            except (NodeNotFound, KeyError):
                raise PromoteTargetInvalid(f"--under 目标不存在: {under}")
            if under_node.get("layer", LAYER_PLAN) != LAYER_PLAN:
                raise PromoteTargetInvalid(f"--under 目标 {under_id} 不是 plan 节点")
        from_id: Optional[str] = None
        if from_trace is not None:
            try:
                from_id = self.resolve_node(from_trace)
                src = self.get_node(from_id)
            except (NodeNotFound, KeyError):
                raise TraceNotFound(from_trace)
            if src.get("layer") != LAYER_TRACE:
                raise TraceNotFound(from_trace)
        trace_id = self._new_trace_id()
        node = {
            "id": trace_id,
            "uid": new_uid(),
            "label": f"trace:{kind}",
            "layer": LAYER_TRACE,
            "kind": kind,
            "body": body,
            "parent": None,
            "children": [],
            "decisions": [],
            "notes": "",
            "prompted_by": under_id,
            "session_ref": session_ref or "",
            "agent_id": agent_id or "",
            "device_id": device_id or "",
            "compressed_from": [self.resolve_node(c) for c in compressed_from] if compressed_from else [],
        }
        self._write_trace_file(trace_id, node)
        if from_trace is not None:
            # 端点落盘一律 uid；mainline 不触发环检测。
            self.add_edge(trace_id, from_id, EDGE_MAINLINE)
        return node

    # ── promote 状态机 / prune（P5-S3/S4，§3.2/§3.3）────────
    # trace 节点在 bundle 里是 traces/ 分片，不在 data["nodes"]，所以覆写 single-file
    # 的 promote/prune：读/写走 _read_trace_file / _write_trace_file，状态机语义仍交
    # 给模块级 apply_promotion（单一事实源）。

    def promote(
        self,
        trace_id: str,
        action: str,
        target: Optional[str] = None,
        label: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> dict[str, Any]:
        trace_id = self.resolve_node(trace_id)
        # 先按"任意节点"解析并判 layer：plan 节点必须先在这里以 InvalidLayer 拒掉，
        # 不能等 _read_trace_file 抛 KeyError（那会变成"trace 节点不存在"的误报，§3.4）。
        node = self._read_any_node(trace_id)
        if node.get("layer", LAYER_PLAN) != LAYER_TRACE:
            raise InvalidLayer(f"promote 只作用于 trace 节点，{trace_id} 是 plan 节点")
        if action == "propose":
            target_id = self.resolve_node(target) if target is not None else None
            if target_id is not None:
                tnode = self._read_any_node(target_id)
                if tnode.get("layer", LAYER_PLAN) != LAYER_PLAN:
                    raise PromoteTargetInvalid(f"--under 目标 {target_id} 不是 plan 节点")
            result = apply_promotion(node, action, target=target_id, label=label, reason=reason)
        else:
            result = apply_promotion(node, action, target=target, label=label, reason=reason)
        if result.get("create_plan"):
            spec = result["create_plan"]
            new_node = self.add_node(spec["parent_id"], spec["label"])
            self.add_edge(trace_id, new_node["id"], EDGE_DERIVES_FROM)
            self._write_trace_file(trace_id, node)
            return new_node
        self._write_trace_file(trace_id, node)
        return node

    def prune(self, trace_id: str, edge_id: str = None) -> dict[str, Any]:
        trace_id = self.resolve_node(trace_id)
        # 先按"任意节点"解析并判 layer：plan 节点必须先以 InvalidLayer 拒掉，
        # 不能等 _read_trace_file 抛 KeyError（会变成"trace 节点不存在"的误报）。
        node = self._read_any_node(trace_id)
        if node.get("layer", LAYER_PLAN) != LAYER_TRACE:
            raise InvalidLayer(f"prune 只作用于 trace 节点，{trace_id} 是 plan 节点")
        if edge_id is not None:
            for e in self.list_edges(trace_id):
                if e["id"] == edge_id:
                    return self.remove_edge(edge_id)
            raise TraceNotFound(f"边 {edge_id} 不存在或不涉及 trace {trace_id}")
        mainline = [
            e for e in self.list_edges(trace_id)
            if e["type"] == EDGE_MAINLINE and e["to"] == trace_id
        ] or [
            e for e in self.list_edges(trace_id)
            if e["type"] == EDGE_MAINLINE and e["from"] == trace_id
        ]
        if not mainline:
            raise PruneNoEdge(f"trace {trace_id} 没有 mainline 边可 prune")
        return self.remove_edge(mainline[0]["id"])

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
            assert_settable_status(status)
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

    def record_failure(self, node_id: str, error: str, now=None,
                       raised_by: str = None, question: str = None,
                       max_attempts: int = None) -> dict:
        """记录一次节点执行失败（Story 33/34）。见 `roadmap.apply_failure`。

        分片 carrier：读节点 → 原地累积 → 写回节点分片（fail 不改 status，
        故状态索引 / stats 不动）。
        """
        node = self._read_node_file(node_id)
        apply_failure(node, error, now=now, raised_by=raised_by, question=question,
                      max_attempts=max_attempts)
        self._write_node_file(node_id, node)
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
        """在两个节点之间记一条边。返回写出的边（端点翻回显示 id，保持旧契约）。

        端点接受显示 id 或 uid（复用 resolve_node）；落盘一律存 uid（#106 S4）。
        """
        from_display = self.resolve_node(from_id)
        to_display = self.resolve_node(to_id)
        try:
            self._read_any_node(from_display)
        except KeyError:
            raise NodeNotFound(f"节点不存在: {from_id}") from None
        try:
            self._read_any_node(to_display)
        except KeyError:
            raise NodeNotFound(f"节点不存在: {to_id}") from None
        if edge_type not in EDGE_TYPES:
            raise ValueError(f"无效的边类型: {edge_type}")
        from_uid = self._read_any_node(from_display)["uid"]
        to_uid = self._read_any_node(to_display)["uid"]
        if edge_type == EDGE_BLOCKS and self._blocks_reachable(to_uid, from_uid):
            raise CycleError(
                f"{from_id} -blocks-> {to_id} 会让依赖图成环"
                f"（{to_id} 已经直接或间接阻塞 {from_id}）"
            )
        self._edges_dir().mkdir(parents=True, exist_ok=True)
        sequence = int(self.manifest.get("edgeSequence", 0)) + 1
        self.manifest["edgeSequence"] = sequence
        edge = {"id": f"e{sequence}", "from": from_uid, "to": to_uid, "type": edge_type}
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
            node = self._read_any_node(to_display)
            node["archived"] = True
            self._write_node_file(to_display, node)
        self._commit("edge-added", {"edgeId": edge["id"], "from": from_uid, "to": to_uid, "type": edge_type}, self._read_stats())
        # 返回显示 id 副本：控制例钉的是"返回给 Human 的是显示 id"，不钉落盘字节。
        return edge_endpoints_as_display(edge, self._nodes_for_edge_translation())

    def list_edges(self, node_id: Optional[str] = None) -> list[dict[str, Any]]:
        """列出全部边；给了 node_id 就只列与它相连的（入边 + 出边）。

        端点翻回显示 id：控制例钉的是"列给 Human 的是显示 id"，不钉落盘字节。
        """
        nodes = self._nodes_for_edge_translation()
        raw = [self._read_edge_file(edge_id) for edge_id in self._edge_ids()]
        disp = [edge_endpoints_as_display(e, nodes) for e in raw]
        if node_id is None:
            return disp
        return [d for d in disp if d["from"] == node_id or d["to"] == node_id]

    def remove_edges_touching(self, node_ids: set) -> dict:
        """删掉所有端点落在 node_ids 里的边。返回 {"total": n, "by_type": {...}}。

        边不能独立于节点存在——节点没了，它的边就没有信息量，留着只会变成
        悬空边。所以 delete 默认级联，不设 --cascade 之类的开关。

        不写 history：调用方（delete_node）会在自己的 event 里带上条数，
        一次删除不该产生两条 event。

        端点落盘是 uid：比较前把每条边翻回显示 id（node_ids 是显示 id 集合）。
        """
        directory = self._edges_dir()
        if not directory.is_dir():
            # 一条边都没有时别碰磁盘：否则会给从未用过边的 bundle 造出
            # edges/ 目录与空 index，违反"没有边时布局与 P1 之前一致"。
            return {"total": 0, "by_type": {}}
        nodes = self._nodes_for_edge_translation()
        by_type: dict = {}
        doomed = []
        for edge_id in self._edge_ids():
            raw = self._read_edge_file(edge_id)
            de = edge_endpoints_as_display(raw, nodes)
            if de["from"] in node_ids or de["to"] in node_ids:
                by_type[raw["type"]] = by_type.get(raw["type"], 0) + 1
                doomed.append(edge_id)
        for edge_id in doomed:
            (directory / f"{edge_id}.json").unlink()
        if doomed:
            self._rebuild_edge_index()
        return {"total": sum(by_type.values()), "by_type": by_type}

    def remove_edge(self, edge_id: str) -> dict[str, Any]:
        """删掉一条边。返回被删掉的边（端点翻回显示 id，保持旧契约）。"""
        edge = self._read_edge_file(edge_id)
        (self._edges_dir() / f"{edge_id}.json").unlink()
        self._rebuild_edge_index()
        self._commit("edge-removed", {"edgeId": edge_id}, self._read_stats())
        return edge_endpoints_as_display(edge, self._nodes_for_edge_translation())

    def migrate_edges(self) -> int:
        """把存量显示 id 边一次性转成 uid（#106 S4 的显式迁移命令）。

        逐边文件改端点并写回；改了几条提交一份 history event。已是 uid 的边不动，
        所以幂等——重跑不会制造写入噪声。
        """
        nodes = self._nodes_for_edge_translation()
        total = 0
        for edge_id in self._edge_ids():
            raw = self._read_edge_file(edge_id)
            new_f = endpoint_to_uid(raw["from"], nodes)
            new_t = endpoint_to_uid(raw["to"], nodes)
            if new_f != raw["from"] or new_t != raw["to"]:
                raw["from"] = new_f
                raw["to"] = new_t
                self._write_edge_file(raw)
                total += 1
        if total:
            self._rebuild_edge_index()
            self._commit("edges-migrated", {"count": total}, self._read_stats())
        return total

    def _blocks_reachable(self, start: str, target: str) -> bool:
        """沿 blocks 边从 start 出发能否走到 target。自环也算（start == target）。

        边端点统一翻成 uid 再建邻接表（与单文件 carrier 同语义）：存量显示 id 边
        （迁移前）与 uid 边在 uid 空间里一致，环检测才与存储形状无关、始终正确。
        """
        adjacency: dict[str, list[str]] = {}
        nodes = self._all_nodes()
        for edge_id in self._edge_ids():
            edge = self._read_edge_file(edge_id)
            if edge["type"] == EDGE_BLOCKS:
                try:
                    f = endpoint_to_uid(edge["from"], nodes)
                    t = endpoint_to_uid(edge["to"], nodes)
                except NodeNotFound:
                    continue
                adjacency.setdefault(f, []).append(t)
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
        # trace 节点在 traces/ 分片（L3），不在 nodes/——先识别它再走专门的删除路径。
        try:
            node = self._read_node_file(node_id)
        except KeyError:
            return self._delete_trace_node(node_id)
        parent = self._read_node_file(node["parent"])
        deleted_nodes = self._collect_subtree(node_id)
        # 先删边、后删节点：万一中间被打断，剩下的是"边没了、节点还在"这种
        # 能重做的半态，而不是悬空边。穷人的事务——零成本，且两个 carrier 一致。
        self.last_edge_cascade = self.remove_edges_touching({item["id"] for item in deleted_nodes})
        parent["children"].remove(node_id)
        # 抬高水位：被删掉的序号不再发第二次（Problem #5）。
        note_child_removal(parent, node_id)
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

    def _delete_trace_node(self, trace_id: str) -> list[str]:
        """删除一条 trace 节点（L3 在 traces/）。plan 节点的删除走上面的 delete_node。"""
        node = self._read_trace_file(trace_id)
        # S3 参照完整性：已被 promote --accept 落进地图的 trace 不允许删（派生自单纯
        # 文件的同一验收，避免两 carrier 漂移）。
        promo = node.get("promotion") or {}
        if promo.get("state") == PROMOTE_ACCEPTED:
            raise ReferencedError(
                f"trace {trace_id} 已被 promote --accept 引用，删除会让 derives-from 边悬空"
            )
        # 先删边、后删节点：与 plan 删除同纪律的穷人事务。
        self.last_edge_cascade = self.remove_edges_touching({trace_id})
        (self.path / "traces" / f"{trace_id}.json").unlink()
        self._commit("trace-deleted", {"nodeId": trace_id}, self._read_stats())
        return [trace_id]

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
        for node in self.iter_nodes():
            current_id = node["id"]
            result.extend({"node_id": current_id, "node_label": node["label"], **decision}
                          for decision in self._read_decisions_file(current_id))
        return result

    # ── 节点租约（P2 核心） ──────────────────────────────
    # 租约分片放在 leases/<node_uid>.json，与 nodes/decisions/ 平级。策略由
    # lease.py 统一提供；心跳频（60s）只改分片、进 history 会刷屏，故不记事件，
    # 其余动作（claim/steal/release）都落 history/events.jsonl（release --force
    # 必须可审计）。

    def _lease_path(self, node_uid: str) -> Path:
        return self.path / "leases" / f"{safe_node_id(node_uid)}.json"

    def _read_lease_file(self, node_uid: str) -> Optional[dict[str, Any]]:
        path = self._lease_path(node_uid)
        if not path.is_file():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise BundleError(f"could not read lease shard {path}: {error}") from error
        return value if isinstance(value, dict) else None

    def _write_lease_file(self, node_uid: str, lease: dict[str, Any]) -> None:
        atomic_json(self._lease_path(node_uid), lease)

    def _delete_lease_file(self, node_uid: str) -> None:
        try:
            self._lease_path(node_uid).unlink()
        except FileNotFoundError:
            pass

    def _commit_event(self, operation: str, payload: dict[str, Any], at: str | None = None) -> None:
        """轻量事件提交：只追加 history + 推进 current/manifest，不动 stats。

        租约动作的 stats 不变（租约不是节点/决策），无需重算 indexes/stats；
        claim/steal/release 仍要进 history 以满足 release --force 的可审计要求。

        `at` 只在**搬运既有事件**（#117 跨 carrier 迁移）时显式给：那时时间要跟着
        事件走，不能写成"现在"，否则审计时间线被改写。正常写路径不传，就用当前时间。
        """
        sequence = int(self.manifest.get("historySequence", 0)) + 1
        event = {"schema": HISTORY_SCHEMA, "sequence": sequence, "operation": operation,
                 "payload": payload, "at": at or now_text()}
        append_jsonl(self.path / "history/events.jsonl", event)
        current = self.manifest.get("currentSnapshot", "snapshots/snapshot-000000.json")
        atomic_json(self.path / "current.json", self._current_document(sequence, self._read_stats(), current))
        self.manifest["historySequence"] = sequence
        self.manifest["updated"] = now_text()
        atomic_json(self.path / "manifest.json", self.manifest)

    def get_lease(self, node_uid: str) -> Optional[dict[str, Any]]:
        return self._read_lease_file(node_uid)

    def claim_lease(self, node_uid: str, agent_id: str, ttl: float = LEASE_TTL_SECONDS,
                    device_id: str = "", now: Optional[float] = None) -> dict:
        self._read_node_file(node_uid)  # 节点必须存在，否则 BundleError
        now = time.time() if now is None else now
        existing = self._read_lease_file(node_uid)
        if existing is not None and not is_expired(existing, now):
            raise LeaseHeld(f"node {node_uid} already leased by {existing['agent_id']} "
                            f"(fencing {existing['fencing_token']}, expires {existing['expires_at']})")
        lease = new_lease(node_uid, agent_id, device_id, ttl, now)
        self._write_lease_file(node_uid, lease)
        self._commit_event("lease-claimed", {"nodeId": node_uid, "agentId": agent_id,
                                              "fencingToken": lease["fencing_token"]})
        return lease

    def heartbeat_lease(self, node_uid: str, agent_id: str, now: Optional[float] = None) -> dict:
        now = time.time() if now is None else now
        lease = self._read_lease_file(node_uid)
        if lease is None:
            raise LeaseHeld(f"node {node_uid} has no active lease to heartbeat")
        if is_expired(lease, now):
            raise LeaseHeld(f"node {node_uid} lease expired at {lease['expires_at']}; steal instead")
        if lease["agent_id"] != agent_id:
            raise LeaseHeld(f"node {node_uid} leased by {lease['agent_id']}, not {agent_id}")
        renewed = apply_heartbeat(lease, now)
        self._write_lease_file(node_uid, renewed)  # 心跳频密，不记 history 事件
        return renewed

    def steal_lease(self, node_uid: str, agent_id: str, device_id: str = "",
                   now: Optional[float] = None) -> dict:
        now = time.time() if now is None else now
        existing = self._read_lease_file(node_uid)
        if existing is not None and not is_expired(existing, now):
            raise LeaseHeld(f"node {node_uid} lease not expired (expires {existing['expires_at']}); "
                            f"cannot steal before TTL")
        lease = apply_steal(existing, node_uid, agent_id, device_id, now)
        self._write_lease_file(node_uid, lease)
        self._commit_event("lease-stolen", {"nodeId": node_uid, "agentId": agent_id,
                                             "fencingToken": lease["fencing_token"]})
        return lease

    def release_lease(self, node_uid: str, agent_id: str, force: bool = False,
                      now: Optional[float] = None) -> None:
        now = time.time() if now is None else now
        lease = self._read_lease_file(node_uid)
        if lease is None:
            return  # 幂等
        if not force:
            if is_expired(lease, now):
                raise LeaseHeld(f"node {node_uid} lease expired; use steal, not release")
            if lease["agent_id"] != agent_id:
                raise LeaseHeld(f"node {node_uid} leased by {lease['agent_id']}, not {agent_id}")
        self._delete_lease_file(node_uid)
        self._commit_event("lease-released", {"nodeId": node_uid, "agentId": agent_id, "force": force})

    # ── 跨 carrier 租约搬运（#117）──────────────────────────
    # bundle 自己一条租约一个文件、事件进共享 history；single / sqlite 则是整份
    # {"leases", "events"} 侧车。下面这一对把 bundle 的布局翻译成那个共用形状，
    # 于是"带着租约换 carrier"在三家 carrier 上是同一个调用，不需要各写一趟翻译。
    #
    # 形状要说清三点：
    #   - leases 的键与**显示 id**同形（`_lease_path` 走 `safe_node_id`，uid 那种
    #     带十六进制的字符串会被拒），和 single / sqlite 的侧车一致；
    #   - event 的 `at` 统一成 epoch float：bundle history 里它是文本时间戳，原样
    #     搬会让 round-trip 换一种类型，属于漂移；
    #   - payload 的 camelCase 与 flat 的 snake_case 逐键可逆映射，`force` 这类只
    #     在部分动作里出现的字段不会被丢。

    _LEASE_PAYLOAD_KEYS = {
        "node_uid": "nodeId",
        "agent_id": "agentId",
        "fencing_token": "fencingToken",
        "force": "force",
    }

    def _history_events(self) -> list[dict[str, Any]]:
        history = self.path / "history" / "events.jsonl"
        if not history.is_file():
            return []
        events = []
        for line in history.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return events

    def _read_lease_store(self) -> dict:
        store: dict[str, Any] = {"leases": {}, "events": []}
        leases_dir = self.path / "leases"
        if leases_dir.is_dir():
            for path in sorted(leases_dir.glob("*.json")):
                try:
                    lease = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as error:
                    raise BundleError(f"could not read lease shard {path}: {error}") from error
                if isinstance(lease, dict):
                    store["leases"][path.stem] = lease
        reverse = {v: k for k, v in self._LEASE_PAYLOAD_KEYS.items()}
        for event in self._history_events():
            operation = event.get("operation")
            if not operation or not operation.startswith("lease-"):
                continue
            flat = {"operation": operation}
            for camel, value in (event.get("payload") or {}).items():
                flat[reverse.get(camel, camel)] = value
            flat["at"] = bundle_timestamp_to_epoch(event.get("at"))
            store["events"].append(flat)
        return store

    def _write_lease_store(self, store: dict) -> None:
        leases = store.get("leases", {})
        leases_dir = self.path / "leases"
        for uid, lease in leases.items():
            self._write_lease_file(uid, lease)
        # 整份替换的语义与 single / sqlite 一致：store 里没有的那把锁必须消失，
        # 否则迁移会把源侧已释放的租约复活成"看起来还持有"。
        if leases_dir.is_dir():
            for path in sorted(leases_dir.glob("*.json")):
                if path.stem not in leases:
                    path.unlink()
        for event in store.get("events", []):
            payload = {
                camel: event[key]
                for key, camel in self._LEASE_PAYLOAD_KEYS.items()
                if key in event
            }
            self._commit_event(
                event["operation"],
                payload,
                at=epoch_to_bundle_timestamp(event.get("at")),
            )

    def materialize(self) -> dict[str, Any]:
        """重建与 single-file 同形的 canonical 数据，供 current_revision 哈希。

        不含 volatile 的 metadata.updated/created，心跳/租约都不进这份视图，
        所以 --if-rev 的 rev 只随 roadmap 语义变化。
        """
        nodes: dict[str, Any] = {}
        for path in sorted((self.path / "nodes").glob("*.json"), key=lambda item: item.stem):
            node = self._read_node_file(path.stem)
            stored = {key: value for key, value in node.items() if key != "decisions"}
            stored["decisions"] = self._read_decisions_file(path.stem)
            nodes[path.stem] = stored
        # 边从 **edges/ 里的边文件**读，不从 edges/index.json 读：那份索引只有
        # from/to 两张邻接表、从来没有 `edges` 列表（`_rebuild_edge_index` 不写它），
        # 于是这里的 `index.get("edges", [])` 恒为 []——bundle 的 rev 完全不含边。
        # 后果是 `--if-rev` 在 bundle 上探测不到别人并发加/删边，而且同一个 roadmap
        # 在 bundle 与另外两家 carrier 上算出不同 rev（#117 迁移验收时发现）。
        # 索引是纯冗余，真正的边事实在分片里，从这里读才能让三家 carrier 的
        # current_revision 对齐。
        edges: list[dict[str, Any]] = []
        if self._edges_dir().is_dir():
            edges = [self._read_edge_file(edge_id) for edge_id in self._edge_ids()]
        metadata = {k: v for k, v in self.manifest.get("metadata", {}).items()
                    if k not in ("updated", "created")}
        return {"nodes": nodes, "edges": edges, "metadata": metadata,
                "version": self.manifest.get("roadmapVersion", 1)}

    def current_revision(self) -> str:
        from roadmap import canonical_json, sha256
        return sha256(canonical_json(self.materialize()))

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

    # ── #115 md 视图数据（owner 列 / 待决问题队列） ──────

    def owner_map(self) -> dict[str, str]:
        """display id → `agent[/device]`：当前持有**未过期**租约的节点。

        租约分片在 `leases/<node_uid>.json`；uid 与显示 id 都可能被当作键传入
        （claim 不解析），所以两端都查。过期租约不算持有者——僵尸租约留着不自动删，
        但 md 不该显示。
        """
        result: dict[str, str] = {}
        lookup: dict[str, str] = {}
        for node in self._all_nodes():
            nid = node.get("id")
            if nid is None:
                continue
            lookup[nid] = nid
            if node.get("uid"):
                lookup[node["uid"]] = nid
        leases_dir = self.path / "leases"
        if not leases_dir.is_dir():
            return result
        now = time.time()
        for path in leases_dir.glob("*.json"):
            try:
                lease = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if is_expired(lease, now):
                continue
            nid = lookup.get(lease.get("node_uid") or path.stem)
            if nid is None:
                continue
            result[nid] = owner_label(lease)
        return result

    def open_question_items(self) -> list:
        """带 open_question 字段的节点，按 display id 排序——喂给 md 渲染。

        遍历经 `iter_nodes(layer='plan')`：trace 节点无 open_question、不进队列。
        """
        return open_question_items(((n["id"], n) for n in self.iter_nodes()))

    def get_tree(self, root_id: str = "1", max_depth: int = 2, owners: dict = None) -> str:
        root = self._read_node_file(root_id)
        blocked = self.blocked_node_ids()
        owners = owners or {}
        lines = [tree_line(root, "", True, 0, blocked, owners.get(root.get("id")))]

        def walk(node: dict[str, Any], prefix: str, last: bool, depth: int) -> None:
            if depth > max_depth:
                return
            lines.append(tree_line(node, prefix, last, depth, blocked, owners.get(node.get("id"))))
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

    def get_focus_subtree(self, root_id: str, max_depth: int = 1, owners: dict = None) -> str:
        root = self._read_node_file(root_id)
        lines: list[str] = []
        owners = owners or {}
        blocked = self.blocked_node_ids()

        def walk(node: dict[str, Any], prefix: str, last: bool, depth: int) -> None:
            lines.append(tree_line(node, prefix, last, depth, blocked, owners.get(node.get("id"))))
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

    def _blocked_chain_lines(self) -> list[str]:
        """本 carrier 的阻塞链条目：喂的是自己的边与节点，取舍规则共用。

        源喂的是 `edges/` 目录本身，不是它的索引——索引可以整份丢掉。逐个边文件
        读比读索引贵，但索引是另一份可失效的副本：挂在它上面就等于让派生值依赖
        派生值。端点落盘是 uid：喂给 blocked_chain_lines 前每条边翻回显示 id。
        翻译表须含 trace（_nodes_for_edge_translation），否则 derives-from 等边的
        trace 端点留成 raw uid，下游 _read_node_file 会炸（single-file 同存两张图免疫）。
        """
        nodes = self._nodes_for_edge_translation()
        return blocked_chain_lines(
            (edge_endpoints_as_display(self._read_edge_file(edge_id), nodes) for edge_id in self._edge_ids()),
            self._predecessor_or_none,
        )

    def render_light_section(self) -> str:
        focus_id = self.get_current_focus()
        owners = self.owner_map()
        focus = self._read_node_file(focus_id) if focus_id else None
        # 模板与 single-file 共用（#117）：这里只喂本 carrier 的数据。
        # 以前这里自己拼一份，于是焦点决策的备注被整段漏掉——同一个焦点节点在两个
        # carrier 的 md 里长相不同，而 diff 里看不出来。
        return compose_light_section(
            artifact_name=self.path.name,
            updated=self.manifest.get("updated", now_text()),
            tree_text=self.get_tree(max_depth=2, owners=owners),
            # 空链时这里得到空串：模板因此在无阻塞时与 #82 之前逐字节相同。
            chain=render_chain_collapsed(self._blocked_chain_lines()),
            # #115：待决问题队列，同样只在有状态时出现（无状态时空串，md 不变）。
            open_questions=render_open_questions_collapsed(self.open_question_items()),
            focus_detail=focus_light_detail(
                focus_id,
                focus["label"] if focus else "",
                focus.get("notes", "") if focus else "",
                self._read_decisions_file(focus_id) if focus_id else [],
                self.get_focus_subtree(focus_id, max_depth=1, owners=owners) if focus_id else "",
            ),
        )

    def render_full_section(self, all_nodes: bool = False, max_depth: int = 2, max_bytes: Optional[int] = None) -> str:
        focus_id = self.get_current_focus()
        focus = self._read_node_file(focus_id) if focus_id else None
        owners = self.owner_map()
        table = ""
        if all_nodes:
            decisions = self.get_decisions()
            if decisions:
                table = "| 节点 | 问题 | 答案 | 备注 |\n|------|------|------|------|\n"
                table += "\n".join(
                    f"| {item['node_id']} | {item['q']} | {item['answer']} | {item.get('note', '')} |"
                    for item in decisions
                ) + "\n"
        return compose_full_section(
            artifact_name=self.path.name,
            updated=self.manifest.get("updated", now_text()),
            # 以前这里连 `> 当前施工` 行、ROADMAP_TREE 标记与"当前施工点"块都没有：
            # Human 看到的 md 少一截，而 `section` 看起来一切正常。
            focus_head=focus_line(focus_id, focus["label"] if focus else ""),
            tree_text=self.get_tree(
                max_depth=ALL_NODES_TREE_DEPTH if all_nodes else max_depth, owners=owners
            ),
            chain=render_chain_plain(self._blocked_chain_lines()),
            # #115：待决问题队列，只在有状态时出现（无状态时空串，md 不变）。
            open_questions=render_open_questions_plain(self.open_question_items()),
            decision_table=table,
            focus_detail=focus_export_detail(
                focus_id,
                focus["label"] if focus else "",
                focus.get("notes", "") if focus else "",
            ),
            max_bytes=max_bytes,
        )

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
            uids = {node.get("uid") for node in nodes if node.get("uid")}
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
                    if edge.get(endpoint) not in uids and edge.get(endpoint) not in node_ids:
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
