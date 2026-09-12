"""
zj-roadmap-driven — 路线图核心数据模型

确定性操作：所有方法都是纯函数，输入确定则输出确定。
普通模式以单 JSON 为事实源；大型模式由 roadmap bundle 的 canonical shards
组成事实源，Markdown 只是渲染视图。
"""

import errno
import json
import os
import shutil
import tempfile
import time
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, Any

# ── 状态常量 ──────────────────────────────────────────────
STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_BLOCKED = "blocked"

# 可人工设置的 status。`blocked` 不在其中——它只能由 blocks 边派生（#80）：
# 允许人写，就等于让"人设的 blocked"和"边推导的 blocked"并存，那又是一个真相源。
SETTABLE_STATUSES = (STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_COMPLETED)

STATUS_ICONS = {
    STATUS_PENDING: "[ ]",
    STATUS_IN_PROGRESS: "[~]",
    STATUS_COMPLETED: "[x]",
    STATUS_BLOCKED: "[!]",
}

# ── 依赖边类型（P1 依赖层）────────────────────────────────
# 四种边共享同一套存储与命令，差别只在语义与成环规则。
EDGE_BLOCKS = "blocks"
EDGE_INFORMS = "informs"
EDGE_SUPERSEDES = "supersedes"
EDGE_DERIVES_FROM = "derives-from"
EDGE_TYPES = (EDGE_BLOCKS, EDGE_INFORMS, EDGE_SUPERSEDES, EDGE_DERIVES_FROM)

MODE_EXPLORE = "explore"
MODE_EXPLOIT = "exploit"

MODE_TAG = {
    MODE_EXPLORE: "[X+]",
    MODE_EXPLOIT: "[Y+]",
}

BLOCKED_CHAIN_LIMIT = 5
"""md 阻塞链的节点上限。

Human 主视图里树才是主体：一条几十节点的链会把树顶出视线，所以只列前几条，
其余用一行说明丢了多少。这是"不把整张边图倒进 md"那条验收的落地。
"""

DEFAULT_LOCK_TIMEOUT_SECONDS = 10.0
LOCK_RETRY_INTERVAL_SECONDS = 0.05

# ── 错误码 ──────────────────────────────────────────────
# case 1 只需要一个码；P0 会把剩余码（E_NODE_NOT_FOUND / E_CYCLE / ...）
# 补进同一张表，不要另起一套机制。退出码 0=成功 / 1=通用错误 / 2=锁超时。

class RoadmapError(Exception):
    """带稳定错误码的 roadmap 失败。Agent 应按 code 分支，不要匹配文案。"""

    code = "E_ROADMAP"
    exit_code = 1


class BudgetExceeded(RoadmapError):
    """explore 节点的结构预算（子节点数 / 开工轮次）已用尽。"""

    code = "E_BUDGET_EXCEEDED"
    exit_code = 3


class NodeNotFound(RoadmapError):
    """引用了一个不存在的节点。

    只用于 P1 的边端点校验。既有命令抛的 KeyError 一律不动——改它们会改变
    那些命令的错误输出，而 P1 的硬验收之一是"没有边时输出与今天完全一致"。
    """

    code = "E_NODE_NOT_FOUND"
    exit_code = 1


class CycleError(RoadmapError):
    """一条 blocks 边会让依赖图成环——环上每个节点都在等别人先动。

    只有 blocks 会成环死锁；informs / derives-from 成环是允许的。
    """

    code = "E_CYCLE"
    exit_code = 1


class InvalidStatus(RoadmapError):
    """试图设置一个不可人工设置的 status。

    `blocked` 是读取时由 blocks 边派生的，不是人能写进 carrier 的值。
    """

    code = "E_INVALID_STATUS"
    exit_code = 1


ERROR_EXIT_CODES = {
    RoadmapError.code: RoadmapError.exit_code,
    BudgetExceeded.code: BudgetExceeded.exit_code,
    NodeNotFound.code: NodeNotFound.exit_code,
    CycleError.code: CycleError.exit_code,
    InvalidStatus.code: InvalidStatus.exit_code,
}


def exit_code_for(exc: BaseException) -> int:
    """把异常映射为进程退出码。"""
    return ERROR_EXIT_CODES.get(getattr(exc, "code", ""), 1)


# ── 派生阻塞的共享语义（#80）────────────────────────────
# 两个 carrier 共用下面四个函数，跟 budget 复用同一套实现的理由相同
# （见 roadmap_bundle 的导入注释）：#80 的验收之一是"两种载体行为一致"，
# 规则写两遍就有机会各自漂移——而漂移在这里是静默的，因为两边各自都对。


def is_blocking(edge: dict, predecessor: Optional[dict]) -> bool:
    """这条边是否挡住了它的 to 端。

    只有 blocks 会挡。前驱不存在（悬空边）按未完成算：它永远等不到"完成"
    那天，静默放行等于把一条悬空边当成已满足的依赖。
    """
    if edge["type"] != EDGE_BLOCKS:
        return False
    return predecessor is None or predecessor.get("status") != STATUS_COMPLETED


def blocked_view(node: dict, blockers: list) -> dict:
    """把派生的 blocked / blocked_reason 贴到节点副本上。

    没被阻塞时一字不加——"消失"比 `blocked: false` 更难被误读，也让
    "没有边时输出与派生之前逐字节一致"这条控制例成立。
    """
    if not blockers:
        return node
    return {**node, "blocked": True, "blocked_reason": blockers}


def assert_settable_status(status: str) -> None:
    """校验一个待写入的 status：blocked 只能派生，不能人设。"""
    if status not in SETTABLE_STATUSES:
        raise InvalidStatus(f"不可设置的状态: {status}（blocked 由 blocks 边派生）")


def status_icon(node: dict) -> str:
    """节点的 status 图标。认不出的 status 给 `[?]`。

    不认识的值不能落成 `[ ]`：那是替 Human 断言"还没开工"。
    """
    return STATUS_ICONS.get(node.get("status"), "[?]")


def tree_line(node: dict, prefix: str, last: bool, depth: int, blocked: set) -> str:
    """渲染一行树；blocked 图标来自边，不来自 status——status 里永远不该有它。

    渲染是给 Human 看的唯一视图。它跟 `get` 打架（一个说被挡、一个说没开工）
    比任何内部实现差异都贵，所以行格式两个 carrier 共用一份。
    """
    icon = STATUS_ICONS[STATUS_BLOCKED] if node["id"] in blocked else status_icon(node)
    mode_tag = MODE_TAG.get(node.get("mode"), "")
    connector = "" if depth == 0 else ("└── " if last else "├── ")
    return f"{prefix}{connector}{icon}{mode_tag} {node['id']}. {node['label']}"


# ── md 阻塞链（#82）──────────────────────────────────────
# 同一份数据在两个 md 出口上取不同的折叠取舍，但**条目内容、取舍规则、上限**
# 必须两边一致，所以写在模块层，两个 carrier 只负责喂各自的边与节点。


def edge_sort_key(edge_id: str):
    """边 id 按计数器数值排序，不按字面序（否则 e10 会排在 e2 前面）。"""
    try:
        return (0, int(edge_id[1:]))
    except ValueError:
        return (1, edge_id)


def blocked_chain_lines(edges, resolve_node) -> list:
    """md 阻塞链的条目：每个被阻塞节点一条，说清它被哪几条边挡住。

    每条都给出边 id 和派出它的前驱（连同前驱当前图标）——少了前驱，Human 只
    知道"被某条边挡住"，还得回头去数 JSON 才能知道该去推谁完工。

    `resolve_node` 返回 None 表示节点不存在：两个 carrier 找节点的方式不同
    （一个是 dict 取，一个是读分片），这里只依赖"能不能找到"这一个约定。
    """
    blockers: dict = {}
    for edge in edges:
        predecessor = resolve_node(edge["from"])
        if not is_blocking(edge, predecessor):
            continue
        blockers.setdefault(edge["to"], []).append((edge["id"], predecessor))

    lines = []
    for to_id in sorted(blockers):
        node = resolve_node(to_id)
        label = node["label"] if node else "?"
        parts = []
        for edge_id, predecessor in sorted(blockers[to_id], key=lambda pair: edge_sort_key(pair[0])):
            if predecessor is None:
                parts.append(edge_id)
            else:
                parts.append(
                    f"{edge_id}: {predecessor['id']}. {predecessor['label']} "
                    f"{status_icon(predecessor)}"
                )
        lines.append(f"- {to_id}. {label} ← {', '.join(parts)}")
    return lines


def cap_chain(lines: list) -> list:
    """截断到 BLOCKED_CHAIN_LIMIT 条，丢掉的部分用一行写明。

    不截断的话，一张几十条边的图会把整棵树顶出视线，而树正是这条链要保护的
    东西。丢掉的部分必须写明，否则 Human 会以为看到的是全景。
    """
    if len(lines) <= BLOCKED_CHAIN_LIMIT:
        return lines
    omitted = len(lines) - BLOCKED_CHAIN_LIMIT
    return [
        *lines[:BLOCKED_CHAIN_LIMIT],
        f"- ... 另有 {omitted} 个节点被阻塞未列出",
    ]


def _chain_block(lines: list, opening: str, closing: str) -> str:
    """两个 md 出口共用的拼装。

    空链一律不成块——这正是"没有东西被阻塞时 md 与改动前逐字节一致"那条硬验收
    的全部内容，所以它只能住在一处：让每个出口各自记得判断一次，等于把它变成
    一条谁都可以顺手漏掉的约定。
    """
    if not lines:
        return ""
    return opening + "\n".join(cap_chain(lines)) + closing


def render_chain_plain(lines: list) -> str:
    """导出视图（`section`）里的阻塞链：非折叠，能一路 grep 到底。"""
    return _chain_block(lines, "\n### 阻塞链\n\n", "\n")


def render_chain_collapsed(lines: list) -> str:
    """Human 主视图里的阻塞链：折叠成一行摘要，展开才看到条目。

    摘要报的是真实总数：那才是 Human 要知道的事实，列出了几条只是排版。
    """
    summary = f"阻塞链：{len(lines)} 个节点被阻塞"
    return _chain_block(
        lines, f"\n<details><summary>{summary}</summary>\n\n", "\n\n</details>\n"
    )


# ── 结构预算（case 1） ───────────────────────────────────
# budget 的单位是结构单位（子节点数 / 开工轮次），不是 token：
# token 不可跨模型比较，也无法在规划期预估（见 docs/plans 的 P5 §8.5）。

def normalize_budget_limit(name: str, value: Any) -> Optional[int]:
    """校验并归一化一个预算上限。None 表示"不设置"，负数是参数错误。"""
    if value is None:
        return None
    try:
        limit = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} 必须是整数: {value!r}")
    if limit < 0:
        raise ValueError(f"{name} 不能为负数: {limit}")
    return limit


def build_budget(max_children: Any, max_rounds: Any) -> dict:
    """组装 budget 字段。两个子项都可缺省，缺省的那一项表示不限。"""
    budget: dict = {}
    children_limit = normalize_budget_limit("max_children", max_children)
    rounds_limit = normalize_budget_limit("max_rounds", max_rounds)
    if children_limit is not None:
        budget["max_children"] = children_limit
    if rounds_limit is not None:
        budget["max_rounds"] = rounds_limit
    return budget


def check_child_budget(parent: dict) -> None:
    """父节点的 max_children 是否已用尽。无 budget 或只设了 max_rounds 时不限。"""
    limit = (parent.get("budget") or {}).get("max_children")
    if limit is None:
        return
    children = parent.get("children") or []
    if len(children) >= int(limit):
        raise BudgetExceeded(
            f"节点 {parent.get('id')} 的子节点预算已用尽 ({len(children)}/{limit})。"
            f"提高 --max-children、先收敛现有子节点，或 --clear-budget 解除限制"
        )


def count_round_start(node: dict, new_status: str) -> None:
    """开工计数 + max_rounds 校验。

    一次"开工"= 从非 in_progress 转入 in_progress。第一次开工记 rounds=1；
    之后每次重开都记一轮。无 max_rounds 的节点照样计数（记了才能事后决策）。
    """
    if new_status != STATUS_IN_PROGRESS or node.get("status") == STATUS_IN_PROGRESS:
        return
    limit = (node.get("budget") or {}).get("max_rounds")
    rounds = node.get("rounds")
    if rounds is None:
        # 迁移进来的老节点没有 rounds：此刻正在施工的按已开工一轮计。
        rounds = 1 if node.get("status") == STATUS_IN_PROGRESS else 0
    rounds = int(rounds)
    if limit is not None and rounds >= int(limit):
        raise BudgetExceeded(
            f"节点 {node.get('id')} 的轮次预算已用尽 ({rounds}/{limit})。"
            f"提高 --max-rounds 或 --clear-budget 解除限制"
        )
    node["rounds"] = rounds + 1

# ── 节点 ID 生成 ──────────────────────────────────────────

def gen_child_id(parent_id: str, index: int) -> str:
    """从父节点 id 生成子节点 id。
    "1" + 1 → "1-1", "1-1" + 2 → "1-1-2"
    """
    if parent_id == "":
        return str(index)
    return f"{parent_id}-{index}"


def next_child_index(roadmap: dict, parent_id: str) -> int:
    """计算父节点下下一个子节点的序号。"""
    parent = roadmap["nodes"].get(parent_id)
    if not parent or not parent["children"]:
        return 1
    # 从最后一个 child id 提取序号
    last = parent["children"][-1]
    parts = last.split("-")
    return int(parts[-1]) + 1


def node_depth(node_id: str) -> int:
    """节点深度。1 → 1, 1-1 → 2, 1-1-1 → 3"""
    return node_id.count("-") + 1


def parent_id_of(node_id: str) -> Optional[str]:
    """获取父节点 id。1-1 → 1, 1 → None"""
    parts = node_id.rsplit("-", 1)
    if len(parts) == 1:
        return None
    return parts[0]


def _fsync_dir_best_effort(path: str):
    """Best-effort directory fsync for atomic rename durability."""
    if not hasattr(os, "O_DIRECTORY"):
        return
    try:
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def atomic_write_text(path: str, content: str):
    """Atomically write text: temp file, fsync, replace, best-effort dir fsync."""
    abs_path = os.path.abspath(path)
    directory = os.path.dirname(abs_path)
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=f".{os.path.basename(abs_path)}.",
        suffix=".tmp",
        dir=directory,
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, abs_path)
        _fsync_dir_best_effort(directory)
    except Exception:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise


class RoadmapLockTimeout(TimeoutError):
    """Raised when a roadmap lock cannot be acquired before timeout."""

    def __init__(self, lock_dir: str, owner: dict, timeout_seconds: float):
        self.lock_dir = lock_dir
        self.owner = owner
        self.timeout_seconds = timeout_seconds
        owner_text = json.dumps(owner, ensure_ascii=False, indent=2) if owner else "(unavailable)"
        super().__init__(
            "Roadmap file is locked; retry later or avoid parallel roadmap mutations.\n"
            f"Lock path: {lock_dir}\n"
            f"Owner: {owner_text}\n"
            f"Timed out after {timeout_seconds:g}s. "
            f"If no roadmap_cli process is writing, run: python roadmap_cli.py unlock <json_path>"
        )


def roadmap_lock_dir(json_path: str) -> str:
    return os.path.abspath(json_path) + ".lock"


# Filesystem failures that must never be mistaken for lock contention. They are
# permanent: retrying cannot make them succeed, so waiting out the lock deadline
# would only produce a misleading "roadmap is locked" report.
_HARD_OS_ERRORS = frozenset({
    errno.EACCES,
    errno.EPERM,
    errno.ENOENT,
    errno.ENOSPC,
    errno.EROFS,
    errno.ENAMETOOLONG,
})


def _is_lock_contention(lock_dir: str, exc: BaseException) -> bool:
    """True when `exc` means "another writer already owns this lock".

    `os.mkdir` on an existing path is specified to raise FileExistsError, and
    the wait/retry loop below was written against that contract. It is not the
    only thing that happens in practice: some runtimes interpose `os.mkdir`
    (this repository's own safe-delete shim, and any sitecustomize doing the
    same) and re-raise EEXIST as PermissionError with `errno` unset. Catching
    only FileExistsError therefore turns ordinary lock contention into an
    uncaught crash — which is exactly how the write loss described in
    `docs/plans/zj-roadmap-dag-concurrency.md` Problem #1 actually manifests:
    writers die with exit 1 instead of waiting their turn. (It is not a
    classic lost update: the whole command runs under the lock, so nothing is
    ever overwritten — the write simply never lands.)

    Classification order matters, and the last rule is the subtle one:

      1. FileExistsError, or errno == EEXIST, or an EEXIST message → contention.
      2. The lock directory is on disk → contention.
      3. errno names a permanent failure (EACCES, ENOSPC, …) → not contention,
         let it propagate so the caller sees the real diagnosis.
      4. Anything else that still carries an errno → not contention, propagate.
      5. errno is None → contention, even if the directory is gone by now.

    Rule 5 is not defensive padding, it is the point of this function. A lock
    directory that has *just* been released is indistinguishable from one that
    never existed: the holder can unlink it between our failed mkdir and the
    stat in rule 2, so "the directory is absent" is not evidence that the
    failure was permanent. Treating it as permanent reintroduces the original
    crash, only now intermittently — roughly one writer in five under eight
    concurrent writers. An errno is the only reliable witness, so when the
    platform withholds it we take the conservative reading: wait and retry, and
    if the lock genuinely never becomes free, the deadline still fires and
    reports RoadmapLockTimeout.
    """
    if isinstance(exc, FileExistsError):
        return True
    if not isinstance(exc, OSError):
        return False
    if exc.errno == errno.EEXIST:
        return True
    message = str(exc).lower()
    if "eexist" in message or "already exists" in message:
        return True
    try:
        if os.path.isdir(lock_dir):
            return True
    except OSError:
        return False
    if exc.errno is None:
        return True
    return exc.errno not in _HARD_OS_ERRORS


def read_lock_owner(json_path: str) -> dict:
    owner_path = os.path.join(roadmap_lock_dir(json_path), "owner.json")
    try:
        with open(owner_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def unlock_roadmap(json_path: str) -> str:
    lock_dir = roadmap_lock_dir(json_path)
    if not os.path.isdir(lock_dir):
        return lock_dir
    shutil.rmtree(lock_dir)
    return lock_dir


@contextmanager
def roadmap_file_lock(json_path: str, timeout_seconds: float = DEFAULT_LOCK_TIMEOUT_SECONDS):
    """Cross-platform per-roadmap lock based on atomic directory creation."""
    lock_dir = roadmap_lock_dir(json_path)
    deadline = time.monotonic() + timeout_seconds
    acquired = False
    while not acquired:
        try:
            os.mkdir(lock_dir)
            acquired = True
        except OSError as exc:
            if not _is_lock_contention(lock_dir, exc):
                raise
            if time.monotonic() >= deadline:
                raise RoadmapLockTimeout(lock_dir, read_lock_owner(json_path), timeout_seconds)
            time.sleep(LOCK_RETRY_INTERVAL_SECONDS)

    owner = {
        "pid": os.getpid(),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "roadmap_path": os.path.abspath(json_path),
    }
    try:
        atomic_write_text(
            os.path.join(lock_dir, "owner.json"),
            json.dumps(owner, ensure_ascii=False, indent=2),
        )
        yield
    finally:
        # Best-effort cleanup. Some interposers (e.g. safe-delete wrappers)
        # turn os.unlink into a failing OSError instead of FileNotFoundError,
        # so swallow OSError broadly to avoid crashing __exit__. If owner.json
        # could not be removed, rmtree the whole lock dir as a fallback so
        # stale lock directories never accumulate.
        try:
            os.unlink(os.path.join(lock_dir, "owner.json"))
        except OSError:
            pass
        try:
            os.rmdir(lock_dir)
        except OSError:
            shutil.rmtree(lock_dir, ignore_errors=True)


# ── Roadmap 类 ────────────────────────────────────────────

class Roadmap:
    """路线图核心类。"""

    def __init__(self, json_path: str):
        self.json_path = os.path.abspath(json_path)
        self.data: dict = {}
        # 上一次 delete 级联掉多少边；CLI 读完就打印，不参与业务判定。
        self.last_edge_cascade: dict = {"total": 0, "by_type": {}}

    # ── 文件 I/O ───────────────────────────────────────

    def load(self) -> dict:
        """从 JSON 文件加载路线图数据。"""
        if not os.path.exists(self.json_path):
            raise FileNotFoundError(f"路线图文件不存在: {self.json_path}")
        with open(self.json_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        return self.data

    def save(self) -> str:
        """保存路线图数据到 JSON 文件，自动更新 metadata.updated。"""
        self.data.setdefault("metadata", {})
        self.data["metadata"]["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = json.dumps(self.data, ensure_ascii=False, indent=2)
        atomic_write_text(self.json_path, content)
        return self.json_path

    # ── 初始化 ─────────────────────────────────────────

    def init(self, title: str, description: str = "", md_file: str = "") -> dict:
        """创建空路线图，带一个 root 节点。"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.data = {
            "title": title,
            "description": description,
            "version": 1,
            "nodes": {
                "1": {
                    "id": "1",
                    "label": title,
                    "status": STATUS_IN_PROGRESS,
                    "mode": MODE_EXPLORE,
                    "parent": None,
                    "children": [],
                    "decisions": [],
                    "notes": "",
                    # init 出来的根节点已经在施工，它就是第 1 轮；
                    # 否则 max_rounds=1 会被解释成"还能再开工一次"。
                    "rounds": 1,
                }
            },
            "metadata": {
                "created": now,
                "updated": now,
                "md_file": md_file,
            },
        }
        return self.data

    # ── 节点 CRUD ──────────────────────────────────────

    def add_node(
        self,
        parent_id: str,
        label: str,
        status: str = STATUS_PENDING,
        mode: str = MODE_EXPLORE,
        max_children: Any = None,
        max_rounds: Any = None,
        exit_criteria: Optional[list] = None,
    ) -> dict:
        """在父节点下添加子节点。返回新节点。

        max_children / max_rounds 只写进新节点自己的 budget，不影响本次能否添加；
        能否添加由**父节点**的 max_children 决定。
        """
        if parent_id not in self.data["nodes"]:
            raise KeyError(f"父节点不存在: {parent_id}")
        assert_settable_status(status)

        parent = self.data["nodes"][parent_id]
        check_child_budget(parent)

        index = next_child_index(self.data, parent_id)
        node_id = gen_child_id(parent_id, index)

        # 先以 pending 落形，让"开工"这件事只走 count_round_start 一条路径，
        # 否则 add 与 update 会对 rounds 各算一套。
        node = {
            "id": node_id,
            "label": label,
            "status": STATUS_PENDING,
            "mode": mode,
            "parent": parent_id,
            "children": [],
            "decisions": [],
            "notes": "",
        }

        budget = build_budget(max_children, max_rounds)
        if budget:
            node["budget"] = budget
        if exit_criteria:
            node["exit_criteria"] = list(exit_criteria)

        count_round_start(node, status)
        node["status"] = status

        self.data["nodes"][node_id] = node
        parent["children"].append(node_id)

        self._sync_parent_status(node_id)

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
    ) -> dict:
        """更新节点的属性。只更新传入的非 None 字段。

        exit_criteria 是**追加**语义（一条一条加）；清空用 clear_exit_criteria。
        budget 的两个子项分别覆盖，整体解除用 clear_budget。
        """
        if node_id not in self.data["nodes"]:
            raise KeyError(f"节点不存在: {node_id}")

        node = self.data["nodes"][node_id]
        if label is not None:
            node["label"] = label
        if status is not None:
            assert_settable_status(status)
            count_round_start(node, status)  # 超限则抛，节点保持原状
            node["status"] = status
        if mode is not None:
            if mode not in (MODE_EXPLORE, MODE_EXPLOIT):
                raise ValueError(f"无效模式: {mode}")
            node["mode"] = mode
        if notes is not None:
            node["notes"] = notes

        if clear_budget:
            node.pop("budget", None)
        budget = build_budget(max_children, max_rounds)
        if budget:
            node.setdefault("budget", {}).update(budget)
        elif max_children is not None or max_rounds is not None:
            # 只允许"设置"，不允许"把某一项改成不限"——那用 clear_budget 后重设。
            raise ValueError("预算子项只能设置为非负整数")

        if clear_exit_criteria:
            node["exit_criteria"] = []
        if exit_criteria:
            node.setdefault("exit_criteria", []).extend(exit_criteria)

        self._sync_parent_status(node_id)

        return node

    def delete_node(self, node_id: str) -> list[str]:
        """删除节点及其所有子节点。返回被删除的 id 列表。"""
        if node_id not in self.data["nodes"]:
            raise KeyError(f"节点不存在: {node_id}")
        if node_id == "1":
            raise ValueError("不能删除根节点")

        # 递归收集所有子孙节点
        deleted = []

        def _collect(nid):
            node = self.data["nodes"].get(nid)
            if not node:
                return
            for cid in list(node["children"]):
                _collect(cid)
            deleted.append(nid)

        _collect(node_id)

        # 先删边、后删节点（#79 定的写顺序）。中断后的半态因此是"边没了、
        # 节点还在"——命令重跑一次即可——而不是悬空边那种要人工修的状态。
        self.last_edge_cascade = self.remove_edges_touching(set(deleted))

        # 从父节点的 children 中移除
        parent_id = self.data["nodes"][node_id]["parent"]
        if parent_id and parent_id in self.data["nodes"]:
            self.data["nodes"][parent_id]["children"].remove(node_id)

        # 删除节点
        for nid in deleted:
            del self.data["nodes"][nid]

        self._sync_parent_status(node_id)

        return deleted

    # ── 依赖边（P1 依赖层）──────────────────────────────

    def _edge_list(self) -> list:
        """惰性建立边表：从未加过边的 roadmap，数据形状与 P1 之前完全一致。"""
        return self.data.setdefault("edges", [])

    def add_edge(self, from_id: str, to_id: str, edge_type: str) -> dict:
        """在两个节点之间记一条边。返回写入的边。"""
        for endpoint in (from_id, to_id):
            if endpoint not in self.data["nodes"]:
                raise NodeNotFound(f"节点不存在: {endpoint}")
        if edge_type not in EDGE_TYPES:
            raise ValueError(f"无效的边类型: {edge_type}")
        if edge_type == EDGE_BLOCKS and self._blocks_reachable(to_id, from_id):
            raise CycleError(
                f"{from_id} -blocks-> {to_id} 会让依赖图成环"
                f"（{to_id} 已经直接或间接阻塞 {from_id}）"
            )
        edges = self._edge_list()
        seq = int(self.data.get("edge_seq", 0)) + 1
        self.data["edge_seq"] = seq
        edge = {"id": f"e{seq}", "from": from_id, "to": to_id, "type": edge_type}
        edges.append(edge)
        if edge_type == EDGE_SUPERSEDES:
            # 被取代的节点转 archived 但不删除：它的决策与历史仍然可读。
            # 用标记而不是 status，因为"completed 且 archived"（做完了但被取代）
            # 是合理组合，塞进 status 会丢掉"完成过"这个信息。
            self.data["nodes"][to_id]["archived"] = True
        return edge

    def remove_edges_touching(self, node_ids: set) -> dict:
        """删掉所有端点落在 node_ids 里的边。返回 {"total": n, "by_type": {...}}。

        边不能独立于节点存在——节点没了，它的边就没有信息量，留着只会变成
        悬空边。所以 delete 默认级联，不设 --cascade 之类的开关。
        """
        # 一条边都没有时别碰数据：否则 delete 会给从未用过边的 roadmap
        # 写入 `edges: []`，违反"没有边时与 P1 之前完全一致"。
        if not self.data.get("edges"):
            return {"total": 0, "by_type": {}}
        by_type: dict = {}
        kept = []
        for edge in self._edge_list():
            if edge["from"] in node_ids or edge["to"] in node_ids:
                by_type[edge["type"]] = by_type.get(edge["type"], 0) + 1
            else:
                kept.append(edge)
        self.data["edges"] = kept
        return {"total": sum(by_type.values()), "by_type": by_type}

    def _blocks_reachable(self, start: str, target: str) -> bool:
        """沿 blocks 边从 start 出发能否走到 target。自环也算（start == target）。"""
        adjacency: dict = {}
        for edge in self._edge_list():
            if edge["type"] == EDGE_BLOCKS:
                adjacency.setdefault(edge["from"], []).append(edge["to"])
        seen = set()
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

    def remove_edge(self, edge_id: str) -> dict:
        """删掉一条边。返回被删掉的边。"""
        edges = self._edge_list()
        for index, edge in enumerate(edges):
            if edge["id"] == edge_id:
                return edges.pop(index)
        raise KeyError(f"边不存在: {edge_id}")

    def list_edges(self, node_id: Optional[str] = None) -> list:
        """列出全部边；给了 node_id 就只列与它相连的（入边 + 出边）。"""
        edges = self._edge_list()
        if node_id is None:
            return list(edges)
        return [e for e in edges if e["from"] == node_id or e["to"] == node_id]

    def get_node(self, node_id: str) -> dict:
        """获取节点。"""
        if node_id not in self.data["nodes"]:
            raise KeyError(f"节点不存在: {node_id}")
        return self.data["nodes"][node_id]

    # ── 派生阻塞（#80）─────────────────────────────────
    # blocked / blocked_reason 只在读视图里出现，永不落盘：唯一权威是 blocks 边。
    # 落盘就必须维护一份"什么时候该重算"的清单（加边、删边、前驱完成、delete、
    # supersedes、carrier 迁移…），漏一个就是静默陈旧。

    def blocking_edges(self, node_id: str) -> list:
        """阻塞 node_id 的 blocks 边 id 列表：即前驱尚未完成的那几条。"""
        blockers = []
        for edge in self.data.get("edges", []):
            if edge["to"] != node_id:
                continue
            if is_blocking(edge, self.data["nodes"].get(edge["from"])):
                blockers.append(edge["id"])
        return blockers

    def blocked_node_ids(self) -> set:
        """一次算出整张图里被阻塞的节点 id。

        渲染要按整棵树取图标，逐节点问 `blocking_edges` 会退化成 O(V*E)。
        """
        blocked = set()
        for edge in self.data.get("edges", []):
            if is_blocking(edge, self.data["nodes"].get(edge["from"])):
                blocked.add(edge["to"])
        return blocked

    def get_node_view(self, node_id: str) -> dict:
        """读视图：节点本体 + 派生的 blocked / blocked_reason。"""
        return blocked_view(self.get_node(node_id), self.blocking_edges(node_id))

    # ── 决策 ───────────────────────────────────────────

    def add_decision(self, node_id: str, question: str, answer: str, note: str = "") -> dict:
        """为节点添加决策记录。"""
        node = self.get_node(node_id)
        decision = {"q": question, "answer": answer, "note": note}
        node["decisions"].append(decision)
        return decision

    def remove_decision(self, node_id: str, index: Optional[int] = None,
                        question: Optional[str] = None) -> int:
        """删除节点决策。按 index 或按 question 精确匹配删除，返回删除条数。

        用于清理重复决策或撤销误记。index 与 question 都未提供时报错；
        两者都提供时优先 index。
        """
        node = self.get_node(node_id)
        decisions = node["decisions"]
        if index is not None:
            if not (0 <= index < len(decisions)):
                raise IndexError(f"决策索引越界: {index} (共 {len(decisions)} 条)")
            removed = [decisions.pop(index)]
            return len(removed)
        if question is not None:
            before = len(decisions)
            node["decisions"] = [d for d in decisions if d.get("q") != question]
            return before - len(node["decisions"])
        raise ValueError("remove_decision 需提供 index 或 question 之一")

    def get_decisions(self, node_id: Optional[str] = None) -> list:
        """获取决策记录。无 node_id 则返回全部。"""
        if node_id:
            return self.get_node(node_id)["decisions"]
        result = []
        for nid, node in self.data["nodes"].items():
            for d in node["decisions"]:
                result.append({"node_id": nid, "node_label": node["label"], **d})
        return result

    # ── 树遍历 ─────────────────────────────────────────

    def get_tree(self, root_id: str = "1", max_depth: int = 10) -> str:
        """生成 Unicode 盒状树形文本视图。"""
        if root_id not in self.data["nodes"]:
            return f"(节点 {root_id} 不存在)"

        blocked = self.blocked_node_ids()
        root = self.data["nodes"][root_id]
        # 根不带 connector，也不给子节点垫缩进——所以根单独走一行。
        lines = [tree_line(root, "", True, 0, blocked)]

        def _render(nid: str, prefix: str, is_last: bool, depth: int):
            if depth > max_depth:
                return
            node = self.data["nodes"].get(nid)
            if not node:
                return
            lines.append(tree_line(node, prefix, is_last, depth, blocked))

            children = node.get("children", [])
            for i, cid in enumerate(children):
                child_prefix = prefix + ("    " if is_last else "│   ")
                _render(cid, child_prefix, i == len(children) - 1, depth + 1)

        children = root.get("children", [])
        for i, cid in enumerate(children):
            _render(cid, "", i == len(children) - 1, 1)

        return "\n".join(lines)

    def get_path(self, node_id: str) -> list[str]:
        """获取从根到目标节点的路径（id 列表）。"""
        path = []
        current = node_id
        while current:
            path.insert(0, current)
            current = self.data["nodes"][current]["parent"]
        return path

    def get_siblings(self, node_id: str) -> list[str]:
        """获取兄弟节点 id 列表（不含自身）。"""
        node = self.get_node(node_id)
        parent_id = node["parent"]
        if not parent_id:
            return []
        parent = self.data["nodes"][parent_id]
        return [cid for cid in parent["children"] if cid != node_id]

    def get_current_focus(self) -> Optional[str]:
        """找到最深的 in_progress 节点作为当前施工点。

        只考虑 in_progress 叶子节点（非叶 in_progress 是 _sync_parent_status 的级联降级
        临时态，不是用户主动设置的施工点）。无 in_progress 叶子时返回 None，
        调用方应据此判断"全部完工或全部未开工"状态。
        """
        candidates = [
            nid for nid, node in self.data["nodes"].items()
            if node["status"] == STATUS_IN_PROGRESS
            and not node.get("children")  # 排除非叶 (级联降级临时态)
        ]
        if not candidates:
            return None
        return max(candidates, key=node_depth)

    def _sync_parent_status(self, node_id: str):
        """自底向上级联同步父节点状态。

        规则：
        - 全部子节点 completed → 父节点 = completed
        - 任一子节点非 completed → 父节点 ≠ completed（降为 in_progress）
        """
        current = self.data["nodes"].get(node_id)
        if not current:
            return
        parent_id = current.get("parent")
        while parent_id and parent_id in self.data["nodes"]:
            parent = self.data["nodes"][parent_id]
            children = parent.get("children", [])
            if not children:
                break
            all_done = all(
                self.data["nodes"][cid]["status"] == STATUS_COMPLETED
                for cid in children if cid in self.data["nodes"]
            )
            if all_done:
                parent["status"] = STATUS_COMPLETED
            elif parent["status"] == STATUS_COMPLETED:
                parent["status"] = STATUS_IN_PROGRESS
            parent_id = parent.get("parent")

    # ── Markdown 渲染 ──────────────────────────────────

    def _blocked_chain_lines(self) -> list:
        """本 carrier 的阻塞链条目：喂的是自己的边与节点，取舍规则共用。"""
        return blocked_chain_lines(self.data.get("edges", []), self.data["nodes"].get)

    def render_full_section(
        self,
        all_nodes: bool = False,
        max_depth: int = 2,
        max_bytes: Optional[int] = None,
    ) -> str:
        """Render a bounded section unless the caller explicitly requests export."""
        now = self.data["metadata"].get("updated", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        focus_id = self.get_current_focus()
        focus_line = ""
        if focus_id:
            focus_node = self.data["nodes"][focus_id]
            focus_line = f"> 当前施工: {focus_id}. {focus_node['label']}"

        tree_text = self.get_tree(max_depth=50 if all_nodes else max_depth)

        all_decisions = self.get_decisions() if all_nodes else []
        decision_lines = ""
        if all_nodes and all_decisions:
            decision_lines = "| 节点 | 问题 | 答案 | 备注 |\n"
            decision_lines += "|------|------|------|------|\n"
            for d in all_decisions:
                note = d.get("note", "")
                decision_lines += f"| {d['node_id']} | {d['q']} | {d['answer']} | {note} |\n"

        current_detail = ""
        if focus_id:
            current_detail = f"\n### 当前施工点\n\n**{focus_id}. {self.data['nodes'][focus_id]['label']}**\n"
            if self.data["nodes"][focus_id].get("notes"):
                current_detail += f"\n{self.data['nodes'][focus_id]['notes']}\n"

        section = f"""## ZJ Roadmap

> 数据文件: `{os.path.basename(self.json_path)}` | 最后更新: {now}
{focus_line}

<!-- ROADMAP_TREE_START -->
<!-- 由 zj-roadmap-driven 自动生成，请勿手动编辑 -->
{tree_text}
<!-- ROADMAP_TREE_END -->
"""
        # 树之后立刻给出"为什么没进展"——Human 的视线顺序是先扫树看见 `[!]`，
        # 再需要一个不用翻 JSON 的答案。
        section += render_chain_plain(self._blocked_chain_lines())

        if decision_lines:
            section += f"\n### 决策历史\n\n{decision_lines}\n"

        if current_detail:
            section += current_detail

        if max_bytes is not None and max_bytes < 0:
            raise ValueError("max_bytes must be non-negative")
        if max_bytes is not None and len(section.encode("utf-8")) > max_bytes:
            encoded = section.encode("utf-8")[:max_bytes]
            section = encoded.decode("utf-8", errors="ignore")
            section += "\n> View truncated at --max-bytes. Use section --all with a larger limit for export.\n"
        return section

    def render_light_section(self) -> str:
        """轻量渲染（Human 视图）：树 depth=2 + 焦点节点展开。"""
        now = self.data["metadata"].get("updated", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        tree_text = self.get_tree(max_depth=2)

        focus_id = self.get_current_focus()
        focus_detail = ""
        if focus_id:
            focus_node = self.data["nodes"][focus_id]
            focus_detail = f"\n### 当前施工：{focus_id}. {focus_node['label']}\n"
            if focus_node.get("notes"):
                focus_detail += f"\n{focus_node['notes']}\n"
            decisions = focus_node.get("decisions", [])
            if decisions:
                focus_detail += "\n**决策：**\n"
                for d in decisions:
                    note = f" ({d.get('note', '')})" if d.get("note") else ""
                    focus_detail += f"- Q: {d['q']} → {d['answer']}{note}\n"
            focus_subtree = self.get_focus_subtree(focus_id, max_depth=1)
            if focus_subtree:
                focus_detail += f"\n**当前子树：**\n{focus_subtree}\n"

        # 空链时这里得到空串：下面那个模板因此在无阻塞时与 #82 之前逐字节相同。
        chain = render_chain_collapsed(self._blocked_chain_lines())
        section = f"""<!-- ROADMAP_SECTION_START -->
## ZJ Roadmap

> 数据文件: `{os.path.basename(self.json_path)}` | 最后更新: {now}

{tree_text}{chain}
"""
        if focus_detail:
            section += focus_detail

        section += "<!-- ROADMAP_SECTION_END -->\n"

        return section

    def get_focus_subtree(self, root_id: str, max_depth: int = 1) -> str:
        """Render a bounded subtree under the focus node."""
        if root_id not in self.data["nodes"]:
            return ""

        lines = []
        root = self.data["nodes"][root_id]
        children = root.get("children", [])
        blocked = self.blocked_node_ids()

        def _render(nid: str, prefix: str, is_last: bool, depth: int):
            node = self.data["nodes"].get(nid)
            if not node:
                return
            lines.append(tree_line(node, prefix, is_last, depth, blocked))

            child_ids = node.get("children", [])
            child_prefix = prefix + ("    " if is_last else "│   ")
            if depth >= max_depth:
                if child_ids:
                    lines.append(
                        f"{child_prefix}... {len(child_ids)} more child nodes; "
                        f"run tree {nid} --depth 2 for full view"
                    )
                return

            for i, cid in enumerate(child_ids):
                _render(cid, child_prefix, i == len(child_ids) - 1, depth + 1)

        for i, cid in enumerate(children):
            _render(cid, "", i == len(children) - 1, 1)

        return "\n".join(lines)

    @staticmethod
    def _consume_legacy_focus_tail(content: str, end: int) -> int:
        """Consume focus detail left outside old ROADMAP_SECTION markers.

        Earlier light renders wrote `### 当前施工` after ROADMAP_SECTION_END.
        Marker-based replacement therefore refreshed only the tree block and left
        stale focus decisions behind. When that legacy tail appears immediately
        after the marker, consume it up to the next top-level section.
        """
        tail = content[end:]
        stripped = tail.lstrip()
        whitespace_len = len(tail) - len(stripped)
        if not stripped.startswith("### 当前施工"):
            return end

        focus_start = end + whitespace_len
        next_section = content.find("\n## ", focus_start)
        if next_section < 0:
            return len(content)
        return next_section

    def write_markdown_section(self) -> Optional[str]:
        """将 ZJ Roadmap section 写入关联的 md 文件。

        在 md 文件中查找 `## ZJ Roadmap` section 并替换，
        不存在则追加到文件末尾。
        返回写入的文件路径，无关联 md 文件则返回 None。
        """
        md_file = self.data.get("metadata", {}).get("md_file", "")
        if not md_file:
            return None

        section = self.render_light_section()

        if os.path.exists(md_file):
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 查找并替换已有的 auto-generated section. Prefer explicit
            # ROADMAP_SECTION markers so repeated renders do not duplicate the
            # opening marker; fall back to the historical heading-based replacement.
            start_marker = "<!-- ROADMAP_SECTION_START -->"
            end_marker = "<!-- ROADMAP_SECTION_END -->"
            start = content.find(start_marker)
            end = content.find(end_marker, start + len(start_marker)) if start >= 0 else -1
            if start >= 0 and end >= 0:
                end += len(end_marker)
                end = self._consume_legacy_focus_tail(content, end)
                content = content[:start] + section.rstrip() + content[end:]
            elif start >= 0 and end < 0:
                # START 存在但 END 缺失(截断/半写入/格式 flip 残留):
                # 绝不 append 第二段,否则会制造重复 marker,下次 render 时
                # find 取首个 START/END 不配对 → 错拼(缺陷 B)。直接把从 START
                # 到文件末尾整段替换掉,保证 render 后只存在「指定的一段」。
                content = content[:start] + section.rstrip()
            else:
                marker = "## ZJ Roadmap"
                next_marker = "\n## "
                idx = content.find(marker)
                if idx >= 0:
                    # 找到下一个 ## section 或文件末尾
                    end = content.find(next_marker, idx + len(marker))
                    if end < 0:
                        end = len(content)
                    content = content[:idx] + section + content[end:]
                else:
                    content = content.rstrip() + "\n\n" + section
        else:
            content = section

        atomic_write_text(md_file, content)

        return md_file

    def link_md_file(self, md_file: str):
        """关联一个 md 文件。"""
        self.data.setdefault("metadata", {})
        self.data["metadata"]["md_file"] = os.path.abspath(md_file)

    # ── 验证 ───────────────────────────────────────────

    def validate(self) -> list[str]:
        """验证路线图数据完整性，返回错误列表。"""
        errors = []

        # 必须有根节点
        if "1" not in self.data.get("nodes", {}):
            errors.append("缺少根节点 '1'")

        for nid, node in self.data.get("nodes", {}).items():
            # id 一致性
            if node.get("id") != nid:
                errors.append(f"节点 {nid}: id 字段不一致 ({node.get('id')})")

            # parent 引用有效性
            parent = node.get("parent")
            if parent is not None:
                if parent not in self.data["nodes"]:
                    errors.append(f"节点 {nid}: 父节点 {parent} 不存在")
                elif nid not in self.data["nodes"][parent].get("children", []):
                    errors.append(f"节点 {nid}: 父节点 {parent} 的 children 列表中缺少此节点")

            # children 引用有效性
            for cid in node.get("children", []):
                if cid not in self.data["nodes"]:
                    errors.append(f"节点 {nid}: 子节点 {cid} 不存在")
                elif self.data["nodes"][cid].get("parent") != nid:
                    errors.append(f"节点 {nid}: 子节点 {cid} 的 parent 指向不一致")

            # 状态合法性
            if node.get("status") not in (STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_COMPLETED, STATUS_BLOCKED):
                errors.append(f"节点 {nid}: 无效状态 '{node.get('status')}'")

        # 悬空边：端点节点已经不在了。来源只有两种——外部手改文件，或
        # bundle 上"删节点后、删边前"崩溃留下的半态。它必须被检出，不能
        # 静默参与调度；修法见 `edge remove`（不需要事务来防，检出即可）。
        nodes = self.data.get("nodes", {})
        for edge in self.data.get("edges", []):
            for key in ("from", "to"):
                endpoint = edge.get(key)
                if endpoint not in nodes:
                    errors.append(f"边 {edge.get('id')}: {key} 端点 {endpoint} 不存在（悬空边）")

        return errors

    # ── 统计 ───────────────────────────────────────────

    def stats(self) -> dict:
        """路线图统计信息。"""
        nodes = self.data.get("nodes", {})
        status_counts = {
            STATUS_PENDING: 0,
            STATUS_IN_PROGRESS: 0,
            STATUS_COMPLETED: 0,
            STATUS_BLOCKED: 0,
        }
        for n in nodes.values():
            s = n.get("status", STATUS_PENDING)
            if s in status_counts:
                status_counts[s] += 1

        total_decisions = sum(len(n.get("decisions", [])) for n in nodes.values())

        return {
            "total_nodes": len(nodes),
            "status_counts": status_counts,
            "total_decisions": total_decisions,
            "max_depth": max((node_depth(nid) for nid in nodes), default=0),
        }
