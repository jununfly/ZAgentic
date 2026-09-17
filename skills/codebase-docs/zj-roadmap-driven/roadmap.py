"""
zj-roadmap-driven — 路线图核心数据模型

确定性操作：所有方法都是纯函数，输入确定则输出确定。
事实源是单个 JSON 文件（single）或一个 sqlite 文件（sqlite），Markdown 只是渲染视图。
"""

import errno
import hashlib
import json
import os
import re
import secrets
import shutil
import tempfile
import time
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, Any

# 租约策略（P2）：claim/heartbeat/steal/release/fencing 的纯函数，两个 carrier 共用，
# 避免两个 carrier 对"一次 claim 意味着什么"各算一套（remove-decision 翻过一次的车）。
# ── 节点租约策略（P2 核心，两个 carrier 共用） ───────────────────────
# 纯函数：给定租约 dict 与时钟，决定下一次租约长什么样。存储（字节落哪儿）是
# carrier 的职责，所以两个 carrier 对"一次 claim/heartbeat/steal 意味着什么"
# 只有一份真相——只能 differ 在落盘位置。时钟注入 `now` 让契约测试确定化。
# 已决参数（两个 carrier 共用，改一处即改两处）：
# TTL 300s + 心跳 60s 成对实现；都不引入提前抢占。
LEASE_TTL_SECONDS = 300
LEASE_HEARTBEAT_SECONDS = 60


def is_expired(lease: dict, now: float) -> bool:
    """True when the lease's wall-clock deadline has passed."""
    return now > float(lease["expires_at"])


def new_lease(node_uid: str, agent_id: str, device_id: str, ttl: float, now: float) -> dict:
    """First claim of a node: fencing token starts at 1."""
    return {
        "node_uid": node_uid,
        "agent_id": agent_id,
        "device_id": device_id or "",
        "fencing_token": 1,
        "claimed_at": now,
        "heartbeat_at": now,
        "expires_at": now + ttl,
        "ttl": ttl,
    }


def apply_heartbeat(lease: dict, now: float) -> dict:
    """Idempotent renewal: expires_at = now + ttl, never accumulates."""
    ttl = float(lease.get("ttl") or LEASE_TTL_SECONDS)
    renewed = dict(lease)
    renewed["heartbeat_at"] = now
    renewed["expires_at"] = now + ttl
    return renewed


def apply_steal(lease, node_uid: str, agent_id: str, device_id: str, now: float) -> dict:
    """Take over an *expired* lease: fencing token increments so the old holder's
    subsequent writes fail. Stealing an unleased node is a first claim (token 1).
    """
    if lease:
        ttl = float(lease.get("ttl") or LEASE_TTL_SECONDS)
        return {
            "node_uid": lease["node_uid"],
            "agent_id": agent_id,
            "device_id": device_id or "",
            "fencing_token": int(lease["fencing_token"]) + 1,
            "claimed_at": now,
            "heartbeat_at": now,
            "expires_at": now + ttl,
            "ttl": ttl,
        }
    return new_lease(node_uid, agent_id, device_id, LEASE_TTL_SECONDS, now)


# ── 状态常量 ──────────────────────────────────────────────
STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_BLOCKED = "blocked"

# 可人工设置的 status。`blocked` 不在其中——它只能由 blocks 边派生：
# 允许人写，就等于让"人设的 blocked"和"边推导的 blocked"并存，那又是一个真相源。
SETTABLE_STATUSES = (STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_COMPLETED)

STATUS_ICONS = {
    STATUS_PENDING: "[ ]",
    STATUS_IN_PROGRESS: "[~]",
    STATUS_COMPLETED: "[x]",
    STATUS_BLOCKED: "[!]",
}

# ── 失败语义与升级 ──────────────────
# 失败 N 次后挂 open question 升级给 Human；不改 status（blocked 仍纯派生，永不落盘）。
DEFAULT_MAX_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 60
BACKOFF_CAP_SECONDS = 3600


def compute_retry_backoff(attempts: int) -> int:
    """封顶指数退避：第 n 次失败建议等待 `min(60 * 2^(n-1), 3600)` 秒。"""
    if attempts < 1:
        attempts = 1
    return min(BACKOFF_BASE_SECONDS * (2 ** (attempts - 1)), BACKOFF_CAP_SECONDS)


def should_escalate(attempts: int, max_attempts: int) -> bool:
    """第 N 次失败（attempts == max_attempts）即触发升级。"""
    return attempts >= max_attempts


def apply_failure(node: dict, error: str, now=None, raised_by: str = None,
                  question: str = None, max_attempts: int = None) -> dict:
    """在节点 dict 上累积一次失败，两 carrier 共用此核心。

    - attempts +1；last_error / last_failed_at 记录；retry_backoff 封顶指数退避。
    - attempts 达阈值（默认 3，节点可带 max_attempts 覆盖）→ 挂 open_question 升级。
    - **不改 status**：blocked 仍纯派生，fail 不碰它（决策 #1）。
    - open_question 已存在时只刷新 attempts / last_error，保留首次 raised_at。
    返回同一个 node（原地修改）。
    """
    if max_attempts is not None:
        node["max_attempts"] = int(max_attempts)
    attempts = node.get("attempts", 0) + 1
    node["attempts"] = attempts
    node["last_error"] = str(error)
    now_val = now if now is not None else datetime.now()
    if isinstance(now_val, (int, float)):
        now_val = datetime.fromtimestamp(now_val)
    ts = now_val.isoformat()
    node["last_failed_at"] = ts
    node["retry_backoff"] = compute_retry_backoff(attempts)

    _max = node.get("max_attempts", DEFAULT_MAX_ATTEMPTS)
    if should_escalate(attempts, _max):
        existing = node.get("open_question")
        if existing:
            existing["attempts"] = attempts
            existing["last_error"] = str(error)
        else:
            node["open_question"] = {
                "question": question or (
                    f"节点在执行 {attempts} 次后仍失败，需人工决策是否继续 / 调整方向。"
                ),
                "last_error": str(error),
                "raised_at": ts,
                "raised_by": raised_by or "agent",
                "attempts": attempts,
            }
    return node



# ── 依赖边类型（P1 依赖层） ────────────────────────────────
# 四种边共享同一套存储与命令，差别只在语义与成环规则。
EDGE_BLOCKS = "blocks"
EDGE_INFORMS = "informs"
EDGE_SUPERSEDES = "supersedes"
EDGE_DERIVES_FROM = "derives-from"
EDGE_MAINLINE = "mainline"
EDGE_REFERENCE = "reference"
EDGE_TYPES = (EDGE_BLOCKS, EDGE_INFORMS, EDGE_SUPERSEDES, EDGE_DERIVES_FROM, EDGE_MAINLINE, EDGE_REFERENCE)

MODE_EXPLORE = "explore"


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()
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


class LeaseHeld(RoadmapError):
    """节点已被有效租约占据，当前调用方无权拿/抢/释放/改写它。

    触发场景：claim 一个未过期的节点、steal 未过期的租约、非持有者
    release、持过期/错误 fencing token 的僵尸写。Agent 应按 code 分支，
    不要匹配文案——租约冲突本就该被重试而不是硬闯。
    """

    code = "E_LEASE_HELD"
    exit_code = 1


class ConflictError(RoadmapError):
    """`--if-rev` 乐观并发冲突：调用方基于的旧 rev 已不是当前 rev。

    调用方应重读当前 rev（stderr 会带当前 rev）后重试，而不是覆盖别人
    已落盘的工作。退出码与 E_LEASE_HELD 同为 1——两者都是"稍后重试"。
    """

    code = "E_CONFLICT"
    exit_code = 1


class InvalidStatus(RoadmapError):
    """试图设置一个不可人工设置的 status。

    `blocked` 是读取时由 blocks 边派生的，不是人能写进 carrier 的值。
    """

    code = "E_INVALID_STATUS"
    exit_code = 1


class ScopeError(RoadmapError):
    """写到了 `--scope` 指定的子树之外。

    作用域令牌是"父 Agent 派给 subagent 的物理边界"：越界写必须失败并**报出
    允许的 scope**，让调用方改对调用，而不是静默把别人的子树改掉。
    """

    code = "E_SCOPE"
    exit_code = 1


class LayerViolation(RoadmapError):
    """试图把 trace 节点写进 plan 节点的 `children` / `parent`。

    trace 与 plan 共享一张节点表，但 trace 节点**不设 `parent`、不进任何 plan 节点的
    `children`**——它的父子与延续关系只用边（`mainline` / `reference`）表达。把 trace
    混进 `children` 的后果与"忘记过滤 `layer`"一样严重：它会沿树被渲染、被 `_sync_parent_status`
    派生状态，当场把 trace 泄进 plan 调度与 md。所以这个写入路径必须被拒绝，而不是靠
    遍历过滤兜底。
    """

    code = "E_LAYER_VIOLATION"
    exit_code = 1


class InvalidKind(RoadmapError):
    """`trace add` 的 kind 不在枚举。"""

    code = "E_INVALID_KIND"
    exit_code = 1


class TraceNotFound(RoadmapError):
    """引用了不存在的 trace 节点 / uid。"""

    code = "E_TRACE_NOT_FOUND"
    exit_code = 1


class InvalidLayer(RoadmapError):
    """对 plan 节点用 trace 命令，或反向。"""

    code = "E_INVALID_LAYER"
    exit_code = 1


class PromoteTargetInvalid(RoadmapError):
    """`trace add --under` 的目标不存在，或不是 plan 节点。"""

    code = "E_PROMOTE_TARGET_INVALID"
    exit_code = 1


class PromoteStateInvalid(RoadmapError):
    """promote 状态机非法转移：例如对已 accepted 的 proposal 再
    `--reject`，或对没有 proposal 的 trace 直接 `--accept`/`--reject`。"""

    code = "E_PROMOTE_STATE_INVALID"
    exit_code = 1


class ReferencedError(RoadmapError):
    """试图删除被引用的节点：已被 `promote --accept` 引用的
    trace、或被 `compressed_from` 引用的节点。删除会让指向它的边悬空，故拒绝。"""

    code = "E_REFERENCED"
    exit_code = 1


class PruneNoEdge(RoadmapError):
    """`prune` 默认删 mainline 边，但该 trace 没有任何 mainline 边可删。"""

    code = "E_PRUNE_NO_EDGE"
    exit_code = 1


ERROR_EXIT_CODES = {
    RoadmapError.code: RoadmapError.exit_code,
    BudgetExceeded.code: BudgetExceeded.exit_code,
    NodeNotFound.code: NodeNotFound.exit_code,
    CycleError.code: CycleError.exit_code,
    LeaseHeld.code: LeaseHeld.exit_code,
    ConflictError.code: ConflictError.exit_code,
    InvalidStatus.code: InvalidStatus.exit_code,
    ScopeError.code: ScopeError.exit_code,
    LayerViolation.code: LayerViolation.exit_code,
    InvalidKind.code: InvalidKind.exit_code,
    TraceNotFound.code: TraceNotFound.exit_code,
    InvalidLayer.code: InvalidLayer.exit_code,
    PromoteTargetInvalid.code: PromoteTargetInvalid.exit_code,
    PromoteStateInvalid.code: PromoteStateInvalid.exit_code,
    ReferencedError.code: ReferencedError.exit_code,
    PruneNoEdge.code: PruneNoEdge.exit_code,
}





def exit_code_for(exc: BaseException) -> int:
    """把异常映射为进程退出码。"""
    return ERROR_EXIT_CODES.get(getattr(exc, "code", ""), 1)


# ── 作用域令牌与字段级所有权 ────────────────────
# 与租约策略同一条纪律：判定只写一处，两个 carrier 只 differ 在字节落哪儿。
# 两个问题是分开的，别合成一个开关：作用域回答"这次写瞄没瞄错节点"（权限），
# 字段所有权回答"这次写要不要过租约守卫"（时序）。Agent 的处置完全不同——
# 前者改调用，后者稍后重试。

EXECUTOR_FIELDS = frozenset({"status", "notes"})
"""归租约持有者的字段：只有正在施工的人能推进进度、写施工笔记。"""

PLANNER_FIELDS = frozenset({"label", "mode", "budget", "exit_criteria"})
"""归 planner 的字段（规划元数据，不含 mode 之外的执行态）。

改这些不推进执行进度，所以租约期内谁都能改——"大多数并发编辑根本不冲突"，
这条是字段所有权模型的立身之本。
"""

APPEND_ONLY_FIELDS = frozenset({"decisions"})
"""只追加不覆盖的字段：追加永不冲突，因此不过租约守卫。"""


def write_requires_lease(fields) -> bool:
    """这批字段里有没有归租约持有者的？

    空集 = **结构性写**（`add` / `delete` / 撤回决策），不是"没写字段"——
    动到树本身的写一律过守卫。
    """
    touched = set(fields)
    if not touched:
        return True
    return bool(touched - PLANNER_FIELDS - APPEND_ONLY_FIELDS)


def is_within_scope(node_id: str, scope_root: str, parent_of) -> bool:
    """node_id 是否在 scope_root 的子树内（含 scope_root 自身）。

    沿 parent 链**上行**而不是下行枚举整棵子树：上行只要 O(深度) 次取节点，
    且两个 carrier 都已经有 `get_node`，不必为"列全图"再开一个 carrier 专有
    入口——那正是两 carrier 语义漂移最喜欢从哪儿进来的地方。

    `parent_of(node_id)` 返回父 id，根返回 None。`seen` 防的是父链成环的损坏
    数据：那会让 CLI 挂死而不是报错。
    """
    current = node_id
    seen = set()
    while current is not None and current not in seen:
        if current == scope_root:
            return True
        seen.add(current)
        current = parent_of(current)
    return False


# ── 派生阻塞的共享语义 ────────────────────────────
# 两个 carrier 共用下面四个函数，跟 budget 复用同一套实现的理由相同：
# 验收之一是"两个载体行为一致"，
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


# ── 调度查询 ──────────────────────────────────────
# ready / critical-path / impact 三个查询共用同一条边界：**只沿 blocks 走**。
# informs / derives-from 是上下文与来源关系，改它们不影响任何东西的调度，
# 让它们参与调度等于把"谁和谁有关"当成"谁等谁"。


def is_ready(node: dict, blocked: set) -> bool:
    """就绪 = pending 且没有未完成的 blocks 前驱。

    判定还有"无有效租约"一项，但租约不进就绪集，今天还没有这一层，
    所以它恒真——这里既不写死 True 假装实现了，也不为不存在的东西留参数。
    """
    return node.get("status") == STATUS_PENDING and node["id"] not in blocked


def ready_node_list(nodes, blocked: set) -> list:
    """就绪集，按 id 排序。

    排序不是装饰：就绪集回答的是"下一步干什么"，顺序若跟着 dict 插入顺序
    浮动，同一张图两次读会给出两个答案。
    """
    return sorted(
        (node for node in nodes if is_ready(node, blocked)),
        key=lambda node: node["id"],
    )


def critical_path(nodes, edges) -> list:
    """关键路径：依赖图里最长的未完工链。

    只沿 `blocks` 边走（与 ready / impact 同一边界）。"未完工" = status != completed：
    已完成节点不阻挡任何东西，链经过它也不贡献长度。返回**一条**链（id 列表，
    从前驱到后继），不是所有节点；同长时取最小 id，保证两次读给出同一个答案。

    空图或全完工 → 返回 []。
    """
    node_by_id = {n["id"]: n for n in nodes}
    # 只在未完工节点诱导出的子图上算：已完成节点不阻塞完成。
    active = {nid for nid, n in node_by_id.items() if n.get("status") != STATUS_COMPLETED}
    if not active:
        return []

    # blocks 邻接（两端都 active，且非自环）；同时数入度用于拓扑序。
    adj: dict = {nid: [] for nid in active}
    indeg = {nid: 0 for nid in active}
    for edge in edges:
        if edge.get("type") != EDGE_BLOCKS:
            continue
        a, b = edge.get("from"), edge.get("to")
        if a in active and b in active and a != b:
            adj[a].append(b)
            indeg[b] += 1

    # Kahn 拓扑序。DP 正确性不依赖顺序，但用有序队列出确定的 topo 序更省心。
    ready = sorted(nid for nid in active if indeg[nid] == 0)
    topo: list = []
    while ready:
        u = ready.pop(0)
        topo.append(u)
        for v in sorted(adj[u]):
            indeg[v] -= 1
            if indeg[v] == 0:
                ready.append(v)
                ready.sort()

    # DP：以 u 结尾的最长链长度 + 前驱（同长取较小 id，保证确定性）。
    best_len = {nid: 1 for nid in active}
    best_prev = {nid: None for nid in active}
    for u in topo:
        for v in adj[u]:
            cand = best_len[u] + 1
            if cand > best_len[v]:
                best_len[v] = cand
                best_prev[v] = u
            elif cand == best_len[v] and (best_prev[v] is None or u < best_prev[v]):
                best_prev[v] = u

    end = min(
        (nid for nid in active if best_len[nid] == max(best_len.values())),
        key=lambda nid: nid,
    )
    path: list = []
    cur = end
    while cur is not None:
        path.append(cur)
        cur = best_prev[cur]
    path.reverse()
    return path


def impact_node_ids(node_id: str, nodes, edges) -> list:
    """影响集：改 node_id 会波及的下游节点。

    只沿 `blocks` 边顺流（与 ready / critical-path 同一边界）：`a blocks b` 意味着
    "改 a 会波及 b"。返回受影响节点的 id 列表（不含自身），按 id 排序保证确定性。
    """
    node_by_id = {n["id"]: n for n in nodes}
    if node_id not in node_by_id:
        raise NodeNotFound(f"节点不存在: {node_id}")

    adj: dict = {}
    for edge in edges:
        if edge.get("type") == EDGE_BLOCKS:
            adj.setdefault(edge.get("from"), []).append(edge.get("to"))

    seen: set = set()
    stack = [node_id]
    result: list = []
    while stack:
        cur = stack.pop()
        for v in adj.get(cur, []):
            if v in seen:
                continue
            seen.add(v)
            result.append(v)
            stack.append(v)
    return sorted(result)


def status_icon(node: dict) -> str:
    """节点的 status 图标。认不出的 status 给 `[?]`。

    不认识的值不能落成 `[ ]`：那是替 Human 断言"还没开工"。
    """
    return STATUS_ICONS.get(node.get("status"), "[?]")


def tree_line(node: dict, prefix: str, last: bool, depth: int, blocked: set, owner: str = None) -> str:
    """渲染一行树；blocked 图标来自边，不来自 status——status 里永远不该有它。

    渲染是给 Human 看的唯一视图。它跟 `get` 打架（一个说被挡、一个说没开工）
    比任何内部实现差异都贵，所以行格式两个 carrier 共用一份。

    `owner` 是 owner 列：持有未过期租约的节点在行尾标出 `agent/device`，
    让 Human 一眼看到"谁拿着哪节点"。无租约时传 None → 行尾不动，md 字节不变。
    """
    icon = STATUS_ICONS[STATUS_BLOCKED] if node["id"] in blocked else status_icon(node)
    mode_tag = MODE_TAG.get(node.get("mode"), "")
    connector = "" if depth == 0 else ("└── " if last else "├── ")
    owner_suffix = f"  · owner: {owner}" if owner else ""
    return f"{prefix}{connector}{icon}{mode_tag} {node['id']}. {node['label']}{owner_suffix}"


# ── md 阻塞链 ──────────────────────────────────────
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


# ── md 待决问题队列 + owner 列 ──────────────────
# 与阻塞链同源：条目内容 / 取舍 / 上限两边一致，写在模块层，两个 carrier 只喂数据。
# 两个新元素都是"有状态才出现"——无待决问题、无持有租约时这些函数返回空串，
# 调用方拼进 md 后输出与改动前逐字节一致。

OPEN_QUESTION_LIMIT = 5
"""md 待决问题队列的节点上限——与 BLOCKED_CHAIN_LIMIT 同一条"不膨胀"验收。"""


def owner_label(lease: dict) -> str:
    """租约持有者展示串：agent，带 device 时 `agent/device`。"""
    agent = lease.get("agent_id", "")
    device = lease.get("device_id", "")
    return agent if not device else f"{agent}/{device}"


def open_question_items(nodes) -> list:
    """收集带 open_question 字段的节点，返回 [(display_id, label, oq), ...]。

    `nodes` 是 (display_id, node_dict) 的可迭代；两个 carrier 喂各自的数据，
    排序由这里统一（按 display id），避免两个 carrier 顺序不一致而被断言放过。
    """
    items = []
    for nid, node in nodes:
        oq = node.get("open_question")
        if not oq:
            continue
        items.append((nid, node.get("label", ""), oq))
    items.sort(key=lambda t: t[0])
    return items


def format_open_question_entry(nid: str, label: str, oq: dict) -> str:
    question = oq.get("question", "")
    raised_by = oq.get("raised_by", "")
    attempts = oq.get("attempts", "?")
    last_error = oq.get("last_error", "")
    if last_error:
        return (f"- {nid}. {label} — {question} 失败原因：{last_error} "
                f"(raised by {raised_by}, attempts {attempts})")
    return f"- {nid}. {label} — {question} (raised by {raised_by}, attempts {attempts})"


def render_open_questions_collapsed(items) -> str:
    """Human 主视图里的待决问题队列：折叠成一行摘要，展开见条目。"""
    if not items:
        return ""
    lines = [format_open_question_entry(nid, label, oq) for nid, label, oq in items]
    summary = f"待决问题：{len(items)} 个节点等待人工决策"
    return _chain_block(lines, f"\n<details><summary>{summary}</summary>\n\n", "\n\n</details>\n")


def render_open_questions_plain(items) -> str:
    """导出视图里的待决问题队列：非折叠，能一路 grep。"""
    if not items:
        return ""
    lines = [format_open_question_entry(nid, label, oq) for nid, label, oq in items]
    return _chain_block(lines, "\n### 待决问题\n\n", "\n")


# ── Markdown section 模板（两个 carrier 共用） ────────────
#
# 模板从 carrier 里搬到这里，是因为它**被抄成过两份**：两个 carrier 各一份。
# 抄两份等于承诺它们永远同步，而它们没有——另一份缺 `> 当前施工` 行、ROADMAP_TREE
# 标记与"当前施工点"块，light section 里焦点决策还丢了备注。
#
# 这里所有函数都只吃"已经渲染好的片段"：它们不知道 carrier、节点和边，因此不可能
# 对某一家的存储形状产生偏好，也就没有第二处可以漂移。

# `section --all` / `render` 里"树不再截断"的深度。这里只此一个常量，因为同一条
# 命令在两个 carrier 上对深树必须给出相同输出——这类差异没有正当理由。
ALL_NODES_TREE_DEPTH = 50


def focus_line(focus_id: Optional[str], label: str = "") -> str:
    """导出视图里那一行"当前施工"；无焦点时返回空串（模板因此与无焦点时逐字节相同）。"""
    return f"> 当前施工: {focus_id}. {label}" if focus_id else ""


def focus_export_detail(focus_id: Optional[str], label: str = "", notes: str = "") -> str:
    """导出视图（`section`）的焦点块。"""
    if not focus_id:
        return ""
    detail = f"\n### 当前施工点\n\n**{focus_id}. {label}**\n"
    if notes:
        detail += f"\n{notes}\n"
    return detail


def focus_light_detail(
    focus_id: Optional[str],
    label: str = "",
    notes: str = "",
    decisions: Optional[list] = None,
    subtree: str = "",
) -> str:
    """轻量视图（`render` 写进 md）的焦点块。

    `decisions` 带备注时括号括在答案后面。这个后缀曾在模板的第二份抄写里整段丢失，
    于是同一个焦点节点在两个 carrier 的 md 里长相不同——模板只留一份就是为防这个。
    """
    if not focus_id:
        return ""
    detail = f"\n### 当前施工：{focus_id}. {label}\n"
    if notes:
        detail += f"\n{notes}\n"
    if decisions:
        detail += "\n**决策：**\n"
        for d in decisions:
            note = f" ({d.get('note', '')})" if d.get("note") else ""
            detail += f"- Q: {d['q']} → {d['answer']}{note}\n"
    if subtree:
        detail += f"\n**当前子树：**\n{subtree}\n"
    return detail


def compose_light_section(
    artifact_name: str,
    updated: str,
    tree_text: str,
    chain: str,
    open_questions: str,
    focus_detail: str,
) -> str:
    """轻量视图：`render` 写进关联 md 文件的那一块。"""
    section = (
        "<!-- ROADMAP_SECTION_START -->\n"
        "## ZJ Roadmap\n\n"
        f"> 数据文件: `{artifact_name}` | 最后更新: {updated}\n\n"
        f"{tree_text}{chain}{open_questions}\n"
    )
    if focus_detail:
        section += focus_detail
    return section + "<!-- ROADMAP_SECTION_END -->\n"


def compose_full_section(
    artifact_name: str,
    updated: str,
    focus_head: str,
    tree_text: str,
    chain: str,
    open_questions: str,
    decision_table: str = "",
    focus_detail: str = "",
    max_bytes: Optional[int] = None,
) -> str:
    """导出视图：`section` 打给 stdout 的那一块。"""
    if max_bytes is not None and max_bytes < 0:
        raise ValueError("max_bytes must be non-negative")
    section = (
        "## ZJ Roadmap\n\n"
        f"> 数据文件: `{artifact_name}` | 最后更新: {updated}\n"
        f"{focus_head}\n\n"
        "<!-- ROADMAP_TREE_START -->\n"
        "<!-- 由 zj-roadmap-driven 自动生成，请勿手动编辑 -->\n"
        f"{tree_text}\n"
        "<!-- ROADMAP_TREE_END -->\n"
    )
    section += chain
    section += open_questions
    if decision_table:
        section += f"\n### 决策历史\n\n{decision_table}\n"
    if focus_detail:
        section += focus_detail
    if max_bytes is not None and len(section.encode("utf-8")) > max_bytes:
        encoded = section.encode("utf-8")[:max_bytes]
        section = encoded.decode("utf-8", errors="ignore")
        section += "\n> View truncated at --max-bytes. Use section --all with a larger limit for export.\n"
    return section


# ── 结构预算（case 1） ───────────────────────────────────
# budget 的单位是结构单位（子节点数 / 开工轮次），不是 token：
# token 不可跨模型比较，也无法在规划期预估。

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


def next_child_index(parent: Optional[dict]) -> int:
    """父节点下下一个子节点的序号 —— **单调递增，删除后不回收**。

    老实现取 `children[-1]` 再 +1：删掉尾部子节点后新建的节点会拿回刚删掉的
    那个 id（Problem #5）。外部引用（租约、ticket、ADR、跨设备同步）于是全部
    串号，而且这种 bug 是静默的——没有报错，只是引用悄悄指向了别的节点。

    序号水位记在父节点的 `childSequence` 上（由 `note_child_removal` 抬高），
    并且是**惰性物化**的：没删过子节点的父节点根本不会有这个字段。这样存量
    roadmap 的字节不变，不会撞 `Slice08` 那条"无边路径不被污染"的控制例。

    两个 carrier 必须共用这一份：`next_child_index` 曾经被各写了
    一遍（`int(children[-1].split("-")[-1]) + 1`），`remove-decision` 在两个
    carrier 上语义漂移是本仓库已经付过学费的一类缺陷，不得重演。
    """
    if not parent:
        return 1
    children = parent.get("children") or []
    base = int(str(children[-1]).split("-")[-1]) + 1 if children else 1
    high_water = int(parent.get("childSequence") or 0) + 1
    return max(base, high_water)


# ── layer 字段 ──────────────
# 两个 layer 共享同一张节点表，靠 `layer` 字段区分 plan / trace。
# `layer` 是**必填**字段；缺省一律按 `plan` 处理，这样存量 roadmap（没有
# `layer` 字段）迁移后仍是 plan，而 trace 节点必须显式写 `layer: 'trace'`。
# 所有遍历入口默认只看 plan；要看 trace 必须显式传
# `layer='trace'`。这是 fail-safe：漏写过滤的后果是"看不到 trace"（当场暴露），
# 而不是"trace 泄进调度与 md"（静默泄漏，与视图膨胀头号风险叠加）。
LAYER_PLAN = "plan"
LAYER_TRACE = "trace"
TRACE_KINDS = frozenset({"turn", "finding", "doubt", "attempt", "artifact"})

# `promotion` 状态机：trace 节点上的一等状态，取代"挂一个待办"——open
# question 落在节点字段上，不另设待办设施。proposal 默认由 Agent 产出（proposed），
# Human 用 `--accept` 落正式 plan 节点、用 `--reject` 记录拒绝（保留痕迹，不物理删除）。
PROMOTE_PROPOSED = "proposed"
PROMOTE_ACCEPTED = "accepted"
PROMOTE_REJECTED = "rejected"
PROMOTE_STATES = frozenset({PROMOTE_PROPOSED, PROMOTE_ACCEPTED, PROMOTE_REJECTED})
# 权限矩阵：Agent 提案、Human 决定。这里只记角色，不引入自报身份机制。
PROMOTER_AGENT = "agent"
DECIDER_HUMAN = "human"
# context --include 的三类取值。
INCLUDE_DECISIONS = "decisions"
INCLUDE_TRACE = "trace"
INCLUDE_CHILDREN = "children"
VALID_INCLUDES = frozenset({INCLUDE_DECISIONS, INCLUDE_TRACE, INCLUDE_CHILDREN})


def ensure_layer(nodes) -> int:
    """给缺 `layer` 的节点补 `'plan'`；已有则不动。返回补了几条。

    放在写入点（single-file / sqlite 的 `save`）
    做"写入时升级"，与 `ensure_uid` 同一条纪律：读命令无锁，在 load 里写文件
    并发时可能给同一节点生成不一致状态。存量 roadmap 不显式迁移也自然带
    `layer: 'plan'`，新节点在构造时显式写 `layer: 'plan'`。
    """
    items = nodes.values() if isinstance(nodes, dict) else nodes
    count = 0
    for node in items:
        if "layer" not in node:
            node["layer"] = LAYER_PLAN
            count += 1
    return count


def assert_plan_layer(node: dict) -> None:
    """硬前提：进 `children` / 设 `parent` 的必须是 plan 节点。

    缺 `layer` 的节点按 plan 处理（存量迁移后都是 plan），所以只有显式写了
    `layer: 'trace'` 的节点会被拒。trace 的父子关系只走边（mainline / reference），
    绝不进 plan 的树结构——否则它会沿树被渲染、被 `_sync_parent_status` 派生状态，
    当场把 trace 泄进 plan 调度与 md，与"忘记过滤 layer"后果相同。
    """
    if node.get("layer", LAYER_PLAN) != LAYER_PLAN:
        raise LayerViolation(
            f"节点 {node.get('id')} 的 layer 是 {node.get('layer')!r}，"
            f"不能进入 plan 节点的 children / parent；trace 节点只通过边表达父子关系"
        )


# ── 节点 uid（P0 地基） ────────────────────────────────────

def new_uid() -> str:
    """生成一个不可变的节点 uid —— 时序唯一、永不复用、零新依赖。

    形状 `<毫秒-hex>-<随机>`：前段按字典序即时间序（同一进程内递增、跨进程按
    时间大致有序），后段保证同一毫秒内不撞。spec 允许"ULID 或等价的时序唯一串"，
    这里不做 Crockford base32，因为那只是编码差异，不带来语义收益，却要多写
    一段容易写错的位运算。

    **不要拿它当时钟用**：前段是生成时刻，不是业务时间。
    """
    return f"{int(time.time() * 1000):012x}-{secrets.token_hex(5)}"


def ensure_uid(node: dict) -> bool:
    """给缺 uid 的节点补一个；已有则不动（uid 生成后只读）。

    返回是否补过，调用方据此判断是否需要升级 schema。**已有节点绝不重新生成**——
    uid 的整个价值就在于它不随时间变化，重新生成等于静默换掉外部引用。
    """
    if node.get("uid"):
        return False
    node["uid"] = new_uid()
    return True


def ensure_uids(nodes) -> int:
    """给一批节点补齐 uid（`dict` 的 values 或 list 都吃）。返回补了几条。"""
    items = nodes.values() if isinstance(nodes, dict) else nodes
    return sum(1 for node in items if ensure_uid(node))


# ── 节点引用解析 ────────────────────────────────
# 用户既可以用显示 id（1-3-1）也可以用 uid 引用节点；命令层统一经 resolve_node
# 把任意一种翻成显示 id，再交给各 carrier 方法（它们只认显示 id）。
# 解析规则：
#   1. 显示 id 直查 nodes（single-file 是 dict 键）→ 命中即返回，O(1)。
#   2. 形如 uid 的字符串 → 扫一遍 nodes 找 uid 命中 → 返回其显示 id。
#   3. uid 形状但不匹配任何节点 → 抛 NodeNotFound（清晰报错，不静默误命中）。
#   4. 非 uid 形状（如错的显示 id）→ 原样返回，交给 get_node 抛既有 KeyError
#      （沿用历史错误文案，不要"顺手修正"）。
# 命名空间天然不重叠：uid 含 hex 字母 a-f，显示 id 只有数字与 -，无法误命中。

UID_RE = re.compile(r"^[0-9a-f]{12}-[0-9a-f]{10}$")


def looks_like_uid(ref: str) -> bool:
    """这个字符串是否像是 new_uid() 产出的 uid。

    必须跟 new_uid() 的形状保持一致：`<12 hex>-<10 hex>`。改 new_uid 时这里要同步。
    """
    return bool(UID_RE.match(ref))


def resolve_node(ref: str, nodes) -> str:
    """把"显示 id 或 uid"统一解析成显示 id。

    `nodes` 接受 dict（键为显示 id）或 list（节点字典列表）。
    返回解析后的显示 id；uid 形状但不匹配时抛 NodeNotFound。
    """
    items = nodes.values() if isinstance(nodes, dict) else nodes
    # 显示 id 直查（dict 形态直接命中；list 形态走下面的 uid 段）。
    if isinstance(nodes, dict) and ref in nodes:
        return ref
    if looks_like_uid(ref):
        for node in items:
            if node.get("uid") == ref:
                return node["id"]
        raise NodeNotFound(f"节点不存在（uid 不匹配任何节点）: {ref}")
    # 非 uid 形状：原样返回，错误语义留给调用方 get_node。
    return ref


def node_context(node_id: str, nodes, edges, includes=()) -> dict:
    """节点来龙去脉，以及 edge-driven `--include`。

    - upstream / downstream / blocked_by：blocks 依赖图（默认始终给出）。
    - includes 控制额外维度，缺省为空（输出与 S5 完全一致，字节级可比对）：
      - "children"：直接子节点 id 列表；
      - "decisions"：该节点的 decisions 数组（输入约束 3：不读 trace）；
      - "trace"：涉及该节点的 trace 边（mainline / reference / derives-from /
        prompted-by），每条带对端 trace 的 kind / body 摘要，供 edge-driven 上下文。

    `nodes` 接受 dict 或 list；`edges` 是边字典列表。
    结果稳定（id 排序），便于两 carrier 比对与测试。
    """
    by_id = {n["id"]: n for n in nodes} if not isinstance(nodes, dict) else nodes

    pred: dict = {}
    succ: dict = {}
    for e in edges or []:
        if e.get("type") == EDGE_BLOCKS:
            pred.setdefault(e["to"], []).append(e["from"])
            succ.setdefault(e["from"], []).append(e["to"])

    def _bfs(start: str, adj: dict) -> set:
        seen = set()
        stack = list(adj.get(start, []))
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(adj.get(cur, []))
        return seen

    upstream = _bfs(node_id, pred)
    downstream = _bfs(node_id, succ)
    blocked_by = [
        f for f in pred.get(node_id, [])
        if is_blocking({"type": EDGE_BLOCKS, "from": f, "to": node_id}, by_id.get(f))
    ]
    result: dict = {
        "id": node_id,
        "label": by_id[node_id]["label"],
        "upstream": sorted(upstream),
        "downstream": sorted(downstream),
        "blocked_by": sorted(blocked_by),
    }
    if INCLUDE_CHILDREN in includes:
        result["children"] = sorted(by_id.get(node_id, {}).get("children", []))
    if INCLUDE_DECISIONS in includes:
        result["decisions"] = by_id.get(node_id, {}).get("decisions", [])
    if INCLUDE_TRACE in includes:
        trace_edges = []
        for e in edges or []:
            # trace 维度只暴露 trace 相关的边：mainline / reference / derives-from。
            # 注意 `prompted_by` 是 trace 节点上的**字段**而非边类型，没有 EDGE_PROMPTED_BY。
            if e.get("type") not in (EDGE_MAINLINE, EDGE_REFERENCE, EDGE_DERIVES_FROM):
                continue
            if e.get("from") != node_id and e.get("to") != node_id:
                continue
            other = e["to"] if e["from"] == node_id else e["from"]
            entry = {"id": e.get("id"), "type": e["type"], "from": e["from"], "to": e["to"]}
            other_node = by_id.get(other)
            if other_node and other_node.get("layer") == LAYER_TRACE:
                entry["other_kind"] = other_node.get("kind")
                entry["other_body"] = (other_node.get("body") or "")[:120]
            trace_edges.append(entry)
        trace_edges.sort(key=lambda x: (x["type"], x["id"] or ""))
        result["trace_edges"] = trace_edges
    return result


# ── 边 uid ───────────────────────────────────────
# 边是跨系统引用，一律用 uid 存储（from/to 存 uid，不再存显示 id）。
# 但所有读视图（edge list / 派生阻塞 / 关键路径 / 影响集 / 血缘 / 校验）对 Human
# 仍给显示 id——所以这里集中放"uid↔显示 id"的翻译，避免两个 carrier 各翻一遍漂移。
#
# 设计要点：
# - 落盘形状是唯一真相：from/to == uid。控制例（test_edges_*）钉的是"返回/列表
#   给 Human 的是显示 id"，不钉落盘字节——落盘 uid 正是这条纪律的验收。
# - 同一份翻译函数兼容"uid 边"与"存量显示 id 边"两种形状：迁移前没跑 `edge migrate`
#   的存量 roadmap 端点仍是显示 id，翻译时查不到 uid 就原样保留，于是老数据不会被
#   静默误翻。


def endpoint_to_uid(endpoint: str, nodes) -> str:
    """把边端点的"显示 id 或 uid"统一翻成 uid。

    - 已是 uid：确认对应节点存在后原样返回（不抛错——端点来自存储，uid 失配
      按悬空边交给上层校验，而不是在这里假装解析成功）。
    - 显示 id：查节点取它的 uid；找不到抛 NodeNotFound。
    """
    items = nodes.values() if isinstance(nodes, dict) else nodes
    if looks_like_uid(endpoint):
        for node in items:
            if node.get("uid") == endpoint:
                return endpoint
        raise NodeNotFound(f"节点不存在（uid 不匹配任何节点）: {endpoint}")
    if isinstance(nodes, dict) and endpoint in nodes:
        return nodes[endpoint].get("uid")
    for node in items:
        if node.get("id") == endpoint:
            return node.get("uid")
    raise NodeNotFound(f"节点不存在: {endpoint}")


def edge_endpoints_as_display(edge: dict, nodes) -> dict:
    """返回一份 from/to 已翻成显示 id 的边副本（不改原边）。

    存量显示 id 边（迁移前）的端点不是 uid，`uid_map` 查不到就原样保留，
    于是同一个函数同时兼容"uid 边"与"显示 id 边"两种存储形状。
    """
    items = nodes.values() if isinstance(nodes, dict) else nodes
    uid_map = {n["uid"]: n["id"] for n in items if n.get("uid")}
    f = uid_map.get(edge.get("from"), edge.get("from"))
    t = uid_map.get(edge.get("to"), edge.get("to"))
    return {**edge, "from": f, "to": t}


def migrate_edge_endpoints_to_uid(edges: list, nodes) -> int:
    """把 edges 里仍是显示 id 的端点就地翻译成 uid。返回改了几条。

    已是 uid 的端点不动——所以迁移幂等，对已经是 uid 的存量边返回 0。
    """
    changed = 0
    for edge in edges:
        new_f = endpoint_to_uid(edge.get("from"), nodes)
        new_t = endpoint_to_uid(edge.get("to"), nodes)
        if new_f != edge.get("from") or new_t != edge.get("to"):
            edge["from"] = new_f
            edge["to"] = new_t
            changed += 1
    return changed


def note_child_removal(parent: dict, child_id: str) -> None:
    """子节点被移除后抬高父节点的序号水位，使该序号不再被复用。

    只抬高不降低：水位是"这个父节点曾经用到过几号"，不是当前子节点数。
    """
    try:
        index = int(str(child_id).split("-")[-1])
    except ValueError:
        return
    if index > int(parent.get("childSequence") or 0):
        parent["childSequence"] = index


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
    (runtime-injected safe-delete shims, and any sitecustomize doing the same) and re-raise EEXIST as PermissionError with `errno` unset. Catching
    only FileExistsError therefore turns ordinary lock contention into an
    uncaught crash — which is exactly how the write loss actually manifests: writers die
    with exit 1 instead of waiting their turn. (It is not a
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

def apply_promotion(
    node: dict,
    action: str,
    target: Optional[str] = None,
    label: Optional[str] = None,
    reason: Optional[str] = None,
    now: Optional[str] = None,
) -> dict:
    """把一次 promote 动作应用到 trace 节点的 `promotion` 字段。

    两 carrier 共用这一份语义——`promotion` 状态机若各写一遍就是 `remove-decision`
    那类漂移。函数只改传入的 `node` dict（trace 节点的物理落盘由调用方负责），返回
    一个副作用描述，告诉 carrier 要不要去落一个 plan 节点：

        {"create_plan": {"parent_id": <显示 id>, "label": <str>} | None}

    - propose（默认）：写 `state=proposed` + target/label + proposed_by/at；exit 0，
      不落节点。重复 propose（同 target 同 label）幂等：已 accepted 的不降级、已
      proposed 的不再刷时间戳。
    - accept（Human）：从 proposal 落正式 plan 节点（调用方据此建节点 + derives-from
      边）；已 accepted 幂等（不落第二个）。无 proposal（state 为 None 或 rejected）
      则 E_PROMOTE_STATE_INVALID。
    - reject（Human）：记 `state=rejected` + reason，保留痕迹不物理删除；已 rejected
      幂等。对已 accepted 的 proposal 拒绝是 E_PROMOTE_STATE_INVALID（节点已进地图）。
    """
    now = now or datetime.now().isoformat(timespec="seconds")
    promo = node.get("promotion") or {}
    state = promo.get("state")

    if action == "propose":
        if state == PROMOTE_ACCEPTED:
            # 已落地的 proposal 不再接受改动（避免无声降级）。
            return {"create_plan": None}
        node["promotion"] = {
            "state": PROMOTE_PROPOSED,
            "target": target,
            "label": label,
            "proposed_by": PROMOTER_AGENT,
            "proposed_at": now,
            "decided_by": None,
            "decided_at": None,
            "reason": None,
        }
        return {"create_plan": None}

    if action == "accept":
        if state == PROMOTE_ACCEPTED:
            return {"create_plan": None}  # 幂等：不落第二个节点 / 不写第二条边。
        # None（从未 proposal）或 rejected 都算"无有效 proposal"，应报状态机错误，
        # 而不是掉到下面的 target 检查去报 E_PROMOTE_TARGET_INVALID。
        if state != PROMOTE_PROPOSED:
            raise PromoteStateInvalid(
                f"无法 accept 一个处于 {state} 状态的 proposal（trace={node.get('id')}），"
                f"先 promote --under 给出 proposal"
            )
        parent_id = target or promo.get("target")
        if not parent_id:
            raise PromoteTargetInvalid("accept 缺少 proposal target（先 promote --under）")
        lbl = label or promo.get("label") or f"promoted:{node.get('kind')}"
        node["promotion"] = {
            "state": PROMOTE_ACCEPTED,
            "target": parent_id,
            "label": lbl,
            "proposed_by": promo.get("proposed_by"),
            "proposed_at": promo.get("proposed_at"),
            "decided_by": DECIDER_HUMAN,
            "decided_at": now,
            "reason": None,
        }
        return {"create_plan": {"parent_id": parent_id, "label": lbl}}

    if action == "reject":
        if state == PROMOTE_REJECTED:
            return {"create_plan": None}  # 幂等：不追加痕迹条目。
        if state == PROMOTE_ACCEPTED:
            raise PromoteStateInvalid(
                f"无法 reject 已 accepted 的 proposal（trace={node.get('id')}），节点已进地图"
            )
        node["promotion"] = {
            "state": PROMOTE_REJECTED,
            "target": promo.get("target"),
            "label": promo.get("label"),
            "proposed_by": promo.get("proposed_by"),
            "proposed_at": promo.get("proposed_at"),
            "decided_by": DECIDER_HUMAN,
            "decided_at": now,
            "reason": reason,
        }
        return {"create_plan": None}

    raise ValueError(f"未知 promote 动作: {action}")


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
        """保存路线图数据到 JSON 文件，自动更新 metadata.updated。

        顺带做 **uid 迁移（写入时升级，不自动迁移）**：存量节点在这里补齐 uid。
        放在唯一写入点而不是 `load()` 里，是为了让"读"保持无副作用——只读命令
        （`ready` / `critical-path` / `impact`）不拿整图锁，在 load 里写文件
        既无锁保护，并发时还会给同一节点生成两个不同 uid。
        """
        self.data.setdefault("metadata", {})
        self.data["metadata"]["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ensure_uids(self.data.get("nodes", {}))
        ensure_layer(self.data.get("nodes", {}))
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
                    "uid": new_uid(),
                    "label": title,
                    "status": STATUS_IN_PROGRESS,
                    "mode": MODE_EXPLORE,
                    "parent": None,
                    "children": [],
                    "decisions": [],
                    "notes": "",
                    "layer": LAYER_PLAN,
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
        # 硬前提：trace 节点不设 parent。任何把 plan 节点挂到 trace 节点下的写入
        # 路径必须当场被拒，否则 trace 就会混进 children 数组，污染 tree / _sync_parent_status。
        assert_plan_layer(parent)
        check_child_budget(parent)

        index = next_child_index(parent)
        node_id = gen_child_id(parent_id, index)

        # 先以 pending 落形，让"开工"这件事只走 count_round_start 一条路径，
        # 否则 add 与 update 会对 rounds 各算一套。
        node = {
            "id": node_id,
            "uid": new_uid(),
            "label": label,
            "status": STATUS_PENDING,
            "mode": mode,
            "parent": parent_id,
            "children": [],
            "decisions": [],
            "notes": "",
            "layer": LAYER_PLAN,
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

    # ── trace 节点 ────────────────────────
    # trace 是执行期涌现的机器记录（turn / finding / doubt / attempt / artifact）。
    # 与 plan 节点共享一张节点表，但：layer=trace、parent=None、不进任何 plan
    # 节点的 children。provenance 诞生即写——`--under` 记
    # prompted-by、`--from` 记一条 mainline 边——无需审批。

    def _new_trace_id(self) -> str:
        """生成不与 plan 节点冲突的 trace id。

        plan 节点 id 都派生自根 '1'（add_node 只在已有 plan 节点下生子），
        所以 '9-*' 命名空间（NODE_ID_PATTERN 合法、不以 '1' 开头）不会撞车。
        """
        seq = 1
        while f"9-{seq}" in self.data["nodes"]:
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
    ) -> dict:
        """追加一条 trace 节点，provenance 诞生即写。返回新节点。

        - kind 不在 TRACE_KINDS → E_INVALID_KIND
        - --under 目标不存在 / 不是 plan 节点 → E_PROMOTE_TARGET_INVALID
        - --from 引用的 trace 不存在 → E_TRACE_NOT_FOUND
        - 身份 provenance：agent_id / device_id / session_ref 缺省为 ""，
          compressed_from 缺省不写；CLI 显式给才落。
        """
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
        self.data["nodes"][trace_id] = node
        if from_trace is not None:
            # 端点落盘一律 uid（与 plan 边同纪律）；mainline 不是 blocks，不触发环检测。
            self.add_edge(trace_id, from_id, EDGE_MAINLINE)
        return node

    def promote(
        self,
        trace_id: str,
        action: str,
        target: Optional[str] = None,
        label: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> dict:
        """promote 状态机。

        - propose（默认）：写 `promotion.state=proposed`，exit 0，不落节点。
        - accept（Human）：从 proposal 落正式 plan 节点并写 derives-from 边，返回新节点。
        - reject（Human）：记 rejected，保留痕迹不物理删除。

        trace 节点与 plan 节点同处 `data["nodes"]`，靠 `layer` 字段区分。
        """
        trace_id = self.resolve_node(trace_id)
        node = self.get_node(trace_id)
        if node.get("layer", LAYER_PLAN) != LAYER_TRACE:
            raise InvalidLayer(f"promote 只作用于 trace 节点，{trace_id} 是 plan 节点")
        if action == "propose":
            target_id = self.resolve_node(target) if target is not None else None
            if target_id is not None:
                tnode = self.get_node(target_id)
                if tnode.get("layer", LAYER_PLAN) != LAYER_PLAN:
                    raise PromoteTargetInvalid(f"--under 目标 {target_id} 不是 plan 节点")
            result = apply_promotion(node, action, target=target_id, label=label, reason=reason)
        else:
            result = apply_promotion(node, action, target=target, label=label, reason=reason)
        if result.get("create_plan"):
            spec = result["create_plan"]
            new_node = self.add_node(spec["parent_id"], spec["label"])
            # derives-from：定义是 trace → plan（端点落盘 uid，与既有边同纪律）。
            self.add_edge(trace_id, new_node["id"], EDGE_DERIVES_FROM)
            self.save()
            return new_node
        self.save()
        return node

    def prune(self, trace_id: str, edge_id: str = None) -> dict:
        """删一条边而非节点（借 thoughtDAG：删边即改变上下文）。

        - 给定 --edge <id>：删那条边（须是该 trace 的边，否则 E_*）。
        - 不带 --edge：默认删该 trace 的 mainline 边（先找入边，再找它的出边），
          从上下文把这条 trace 摘掉，节点仍在。无 mainline 边则 E_PRUNE_NO_EDGE。
        """
        trace_id = self.resolve_node(trace_id)
        node = self.get_node(trace_id)
        if node.get("layer", LAYER_PLAN) != LAYER_TRACE:
            raise InvalidLayer(f"prune 只作用于 trace 节点，{trace_id} 是 plan 节点")
        if edge_id is not None:
            for e in self.list_edges(trace_id):
                if e["id"] == edge_id:
                    removed = self.remove_edge(edge_id)
                    self.save()  # remove_edge 只动内存，落盘必须显式 save
                    return removed
            raise TraceNotFound(f"边 {edge_id} 不存在或不涉及 trace {trace_id}")
        # 默认：mainline 边（入边优先，其次出边）。
        mainline = [
            e for e in self.list_edges(trace_id)
            if e["type"] == EDGE_MAINLINE and e["to"] == trace_id
        ] or [
            e for e in self.list_edges(trace_id)
            if e["type"] == EDGE_MAINLINE and e["from"] == trace_id
        ]
        if not mainline:
            raise PruneNoEdge(f"trace {trace_id} 没有 mainline 边可 prune")
        removed = self.remove_edge(mainline[0]["id"])
        self.save()
        return removed

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

    def record_failure(self, node_id: str, error: str, now=None,
                       raised_by: str = None, question: str = None,
                       max_attempts: int = None) -> dict:
        """记录一次节点执行失败。见模块级 `apply_failure`。"""
        if node_id not in self.data["nodes"]:
            raise KeyError(f"节点不存在: {node_id}")
        return apply_failure(
            self.data["nodes"][node_id], error,
            now=now, raised_by=raised_by, question=question,
            max_attempts=max_attempts,
        )

    def delete_node(self, node_id: str) -> list[str]:
        """删除节点及其所有子节点。返回被删除的 id 列表。"""
        if node_id not in self.data["nodes"]:
            raise KeyError(f"节点不存在: {node_id}")
        if node_id == "1":
            raise ValueError("不能删除根节点")
        # S3 参照完整性：已被 promote --accept 落进地图的 trace 不允许删，否则指向
        # 它的 derives-from 边会悬空。
        node = self.data["nodes"][node_id]
        promo = node.get("promotion") or {}
        if node.get("layer") == LAYER_TRACE and promo.get("state") == PROMOTE_ACCEPTED:
            raise ReferencedError(
                f"trace {node_id} 已被 promote --accept 引用，删除会让 derives-from 边悬空"
            )

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

        # 先删边、后删节点。中断后的半态因此是"边没了、
        # 节点还在"——命令重跑一次即可——而不是悬空边那种要人工修的状态。
        self.last_edge_cascade = self.remove_edges_touching(set(deleted))

        # 从父节点的 children 中移除
        parent_id = self.data["nodes"][node_id]["parent"]
        if parent_id and parent_id in self.data["nodes"]:
            self.data["nodes"][parent_id]["children"].remove(node_id)
            # 抬高水位：被删掉的序号不再发第二次（Problem #5）。
            note_child_removal(self.data["nodes"][parent_id], node_id)

        # 删除节点
        for nid in deleted:
            del self.data["nodes"][nid]

        self._sync_parent_status(node_id)

        return deleted

    # ── 依赖边（P1 依赖层） ──────────────────────────────

    def _edge_list(self) -> list:
        """惰性建立边表：从未加过边的 roadmap，数据形状与 P1 之前完全一致。"""
        return self.data.setdefault("edges", [])

    def add_edge(self, from_id: str, to_id: str, edge_type: str) -> dict:
        """在两个节点之间记一条边。返回写出的边（端点翻回显示 id，保持旧契约）。

        端点接受显示 id 或 uid（复用 resolve_node）；落盘一律存 uid。
        """
        from_display = self.resolve_node(from_id)
        to_display = self.resolve_node(to_id)
        if from_display not in self.data["nodes"]:
            raise NodeNotFound(f"节点不存在: {from_id}")
        if to_display not in self.data["nodes"]:
            raise NodeNotFound(f"节点不存在: {to_id}")
        if edge_type not in EDGE_TYPES:
            raise ValueError(f"无效的边类型: {edge_type}")
        from_uid = self.data["nodes"][from_display]["uid"]
        to_uid = self.data["nodes"][to_display]["uid"]
        if edge_type == EDGE_BLOCKS and self._blocks_reachable(to_uid, from_uid):
            raise CycleError(
                f"{from_id} -blocks-> {to_id} 会让依赖图成环"
                f"（{to_id} 已经直接或间接阻塞 {from_id}）"
            )
        edges = self._edge_list()
        seq = int(self.data.get("edge_seq", 0)) + 1
        self.data["edge_seq"] = seq
        edge = {"id": f"e{seq}", "from": from_uid, "to": to_uid, "type": edge_type}
        edges.append(edge)
        if edge_type == EDGE_SUPERSEDES:
            # 被取代的节点转 archived 但不删除：它的决策与历史仍然可读。
            # 用标记而不是 status，因为"completed 且 archived"（做完了但被取代）
            # 是合理组合，塞进 status 会丢掉"完成过"这个信息。
            self.data["nodes"][to_display]["archived"] = True
        # 返回显示 id 副本：控制例钉的是"返回给 Human 的是显示 id"，不钉落盘字节。
        return edge_endpoints_as_display(edge, self.data["nodes"])

    def remove_edges_touching(self, node_ids: set) -> dict:
        """删掉所有端点落在 node_ids 里的边。返回 {"total": n, "by_type": {...}}。

        边不能独立于节点存在——节点没了，它的边就没有信息量，留着只会变成
        悬空边。所以 delete 默认级联，不设 --cascade 之类的开关。

        端点落盘是 uid：比较前翻回显示 id（node_ids 是显示 id 集合）。
        """
        # 一条边都没有时别碰数据：否则 delete 会给从未用过边的 roadmap
        # 写入 `edges: []`，违反"没有边时与 P1 之前完全一致"。
        if not self.data.get("edges"):
            return {"total": 0, "by_type": {}}
        nodes = self.data["nodes"]
        by_type: dict = {}
        kept = []
        for edge in self._edge_list():
            de = edge_endpoints_as_display(edge, nodes)
            if de["from"] in node_ids or de["to"] in node_ids:
                by_type[edge["type"]] = by_type.get(edge["type"], 0) + 1
            else:
                kept.append(edge)
        self.data["edges"] = kept
        return {"total": sum(by_type.values()), "by_type": by_type}

    def _blocks_reachable(self, start: str, target: str) -> bool:
        """沿 blocks 边从 start 出发能否走到 target。自环也算（start == target）。

        边端点统一翻成 uid 再建邻接表：存量显示 id 边（迁移前）与 uid 边（迁移后 /
        新加）在 uid 空间里一致，环检测才与存储形状无关、始终正确（验收 #4）。
        """
        adjacency: dict = {}
        nodes = self.data["nodes"]
        for edge in self._edge_list():
            if edge["type"] == EDGE_BLOCKS:
                try:
                    f = endpoint_to_uid(edge["from"], nodes)
                    t = endpoint_to_uid(edge["to"], nodes)
                except NodeNotFound:
                    continue
                adjacency.setdefault(f, []).append(t)
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
        """删掉一条边。返回被删掉的边（端点翻回显示 id，保持旧契约）。"""
        edges = self._edge_list()
        for index, edge in enumerate(edges):
            if edge["id"] == edge_id:
                removed = edges.pop(index)
                return edge_endpoints_as_display(removed, self.data["nodes"])
        raise KeyError(f"边不存在: {edge_id}")

    def list_edges(self, node_id: Optional[str] = None) -> list:
        """列出全部边；给了 node_id 就只列与它相连的（入边 + 出边）。

        端点翻回显示 id：控制例钉的是"列给 Human 的是显示 id"，不钉落盘字节。
        """
        edges = self._edge_list()
        disp = [edge_endpoints_as_display(e, self.data["nodes"]) for e in edges]
        if node_id is None:
            return disp
        return [d for d in disp if d["from"] == node_id or d["to"] == node_id]

    def migrate_edges(self) -> int:
        """把存量显示 id 边一次性转成 uid。

        直接改 `data["edges"]` 原地；改了几条由 `save()` 落盘。已是 uid 的边不动，
        所以幂等——重跑不会制造写入噪声。
        """
        return migrate_edge_endpoints_to_uid(self.data.get("edges") or [], self.data["nodes"])

    def resolve_node(self, ref: str) -> str:
        """把显示 id 或 uid 翻成显示 id（见模块级 resolve_node）。"""
        return resolve_node(ref, self.data["nodes"])

    # ── 来龙去脉 / 就绪建议 ─────────────────────

    def context(self, node_id: str, includes=()) -> dict:
        """节点来龙去脉：上游（依赖谁）/下游（谁依赖我）/阻塞链。

        single-file 的 trace 节点也在 `data["nodes"]` 里，故直接喂给 node_context
        （--include trace 需要的对端 trace 节点自然可见）。端点落盘是 uid：翻回显示 id。
        """
        if node_id not in self.data["nodes"]:
            raise KeyError(f"节点不存在: {node_id}")
        return node_context(
            node_id,
            self.data["nodes"],
            [edge_endpoints_as_display(e, self.data["nodes"]) for e in self.data.get("edges", [])],
            includes=includes,
        )

    def next_nodes(self) -> list:
        """就绪优先建议：关键路径上的就绪节点优先，其余按 id 排序。"""
        ready = self.ready_nodes()
        cp = set(self.critical_path())
        ready.sort(key=lambda n: (n["id"] not in cp, n["id"]))
        return ready

    def get_node(self, node_id: str) -> dict:
        """获取节点。"""
        if node_id not in self.data["nodes"]:
            raise KeyError(f"节点不存在: {node_id}")
        return self.data["nodes"][node_id]

    # ── 遍历入口收敛 ──────────────
    # 全图遍历分散在 stats / decisions / focus / validate / 调度查询等多处裸
    # 遍历；把它们收敛成下面两个命名入口，默认 `layer='plan'`，调用方不写过滤
    # 条件即可天然避开 trace（fail-safe：漏写 = 看不到 trace，当场暴露）。
    # 两个 carrier 各自实现一次，语义契约（默认值 / 排序 / 返回形状）在此钉死，
    # 不得各解释一套——同一语义两套实现是 `remove-decision` 那类漂移的入口。

    def iter_nodes(self, layer: str = LAYER_PLAN) -> list:
        """按 layer 遍历节点，返回节点 dict 列表（按 id 排序，确定性）。

        缺 `layer` 的节点按 plan 处理（存量 roadmap 迁移后都是 plan）。要看 trace
        必须显式传 `layer=LAYER_TRACE`——trace 不进 `children`、不设 `parent`，
        所以只会经由这个入口被显式取出，不会混进 plan 调度与 md。
        """
        nodes = self.data.get("nodes", {})
        selected = [n for n in nodes.values() if n.get("layer", LAYER_PLAN) == layer]
        selected.sort(key=lambda n: n.get("id", ""))
        return selected

    def node_ids(self, layer: str = LAYER_PLAN) -> list:
        """`iter_nodes` 的 id 视图，同样默认只看 plan。"""
        return [n["id"] for n in self.iter_nodes(layer)]

    # ── 派生阻塞 ─────────────────────────────────
    # blocked / blocked_reason 只在读视图里出现，永不落盘：唯一权威是 blocks 边。
    # 落盘就必须维护一份"什么时候该重算"的清单（加边、删边、前驱完成、delete、
    # supersedes、carrier 迁移…），漏一个就是静默陈旧。

    def blocking_edges(self, node_id: str) -> list:
        """阻塞 node_id 的 blocks 边 id 列表：即前驱尚未完成的那几条。

        端点落盘是 uid：比较前把每条边翻回显示 id（node_id 是显示 id）。
        """
        blockers = []
        nodes = self.data["nodes"]
        for edge in self.data.get("edges", []):
            de = edge_endpoints_as_display(edge, nodes)
            if de["to"] != node_id:
                continue
            if is_blocking(de, nodes.get(de["from"])):
                blockers.append(edge["id"])
        return blockers

    def blocked_node_ids(self) -> set:
        """一次算出整张图里被阻塞的节点 id（显示 id 集合）。

        渲染要按整棵树取图标，逐节点问 `blocking_edges` 会退化成 O(V*E)。
        端点落盘是 uid：比较前每条边翻回显示 id。
        """
        blocked = set()
        nodes = self.data["nodes"]
        for edge in self.data.get("edges", []):
            de = edge_endpoints_as_display(edge, nodes)
            if is_blocking(de, nodes.get(de["from"])):
                blocked.add(de["to"])
        return blocked

    # ── md 视图数据（owner 列 / 待决问题队列） ──────

    def owner_map(self) -> dict:
        """display id → `agent[/device]`：当前持有**未过期**租约的节点。

        租约侧车以 node_uid 为键；uid 与显示 id 都可能被当作键传入（claim 不解析），
        所以两端都查。过期租约不算持有者——僵尸租约留着不自动删，但 md 不该显示。
        """
        result: dict = {}
        store = self._read_lease_store()
        lookup: dict = {}
        for nid, node in self.data["nodes"].items():
            lookup[nid] = nid
            if node.get("uid"):
                lookup[node["uid"]] = nid
        now = time.time()
        for key, lease in store.get("leases", {}).items():
            if is_expired(lease, now):
                continue
            nid = lookup.get(key)
            if nid is None:
                continue
            result[nid] = owner_label(lease)
        return result

    def open_question_items(self) -> list:
        """带 open_question 字段的节点，按 display id 排序——喂给 md 渲染。

        遍历经 `iter_nodes(layer='plan')`：trace 节点无 open_question、不进队列。
        """
        return open_question_items(
            ((node["id"], node) for node in self.iter_nodes())
        )

    def get_node_view(self, node_id: str) -> dict:
        """读视图：节点本体 + 派生的 blocked / blocked_reason。"""
        return blocked_view(self.get_node(node_id), self.blocking_edges(node_id))

    # ── 调度查询 ─────────────────────────────────

    def ready_nodes(self) -> list:
        """就绪集：pending 且没有未完成的 blocks 前驱。

        按边实时算一遍（O(V+E)），不落 `pending_deps` 计数器：计数器一旦落盘
        就得维护"什么时候重算"的清单，那正是
        `blocked` 改成派生要消灭的东西。

        遍历经 `iter_nodes(layer='plan')`：trace 节点（S2 起）不进就绪集。
        """
        return ready_node_list(self.iter_nodes(), self.blocked_node_ids())

    def critical_path(self) -> list:
        """关键路径：依赖图里最长的未完工链。

        端点落盘是 uid：喂给模块级 critical_path 前翻回显示 id，使其输出显示 id。
        遍历经 `iter_nodes(layer='plan')`：trace 节点不进关键路径。
        """
        return critical_path(
            self.iter_nodes(),
            [edge_endpoints_as_display(e, self.data["nodes"]) for e in self.data.get("edges", [])],
        )

    def impact(self, node_id: str) -> list:
        """影响集：改 node_id 会波及的下游节点（不含自身）。

        端点落盘是 uid：喂给模块级 impact_node_ids 前翻回显示 id。
        遍历经 `iter_nodes(layer='plan')`：trace 节点不进影响集。
        """
        return impact_node_ids(
            node_id,
            self.iter_nodes(),
            [edge_endpoints_as_display(e, self.data["nodes"]) for e in self.data.get("edges", [])],
        )

    # ── 决策 ───────────────────────────────────────────

    def add_decision(self, node_id: str, question: str, answer: str, note: str = "") -> dict:
        """为节点添加决策记录。"""
        node = self.get_node(node_id)
        decision = {"q": question, "answer": answer, "note": note}
        node["decisions"].append(decision)
        return decision

    def remove_decision(self, node_id: str, index: Optional[int] = None,
                        question: Optional[str] = None) -> int:
        """撤回节点决策（保留原记录，附加 retracted 标记）。

        两个 carrier 语义一致：原决策保留，新增一条 retracted:True 记录
        （含 retracts = sha256(canonical_json(原决策)) 供溯源），不物理删除。
        用于撤销误记或清理重复决策，同时保留审计轨迹。
        index 与 question 都未提供时报错；两者都提供时优先 index。
        """
        node = self.get_node(node_id)
        decisions = node["decisions"]
        selected: list[dict] = []
        if index is not None:
            if not (0 <= index < len(decisions)):
                raise IndexError(f"决策索引越界: {index} (共 {len(decisions)} 条)")
            selected = [decisions[index]] if not decisions[index].get("retracted") else []
        elif question is not None:
            selected = [d for d in decisions if d.get("q") == question and not d.get("retracted")]
        else:
            raise ValueError("remove_decision 需提供 index 或 question 之一")
        if not selected:
            return 0
        for decision in selected:
            decisions.append({
                "q": decision.get("q", ""),
                "answer": "",
                "note": f"retracted: {decision.get('note', '')}".rstrip(),
                "retracted": True,
                "retracts": sha256(canonical_json(decision)),
            })
        return len(selected)

    def get_decisions(self, node_id: Optional[str] = None) -> list:
        """获取决策记录。无 node_id 则返回全部（按 id 排序，确定性）。"""
        if node_id:
            return self.get_node(node_id)["decisions"]
        result = []
        for node in self.iter_nodes():
            nid = node["id"]
            for d in node["decisions"]:
                result.append({"node_id": nid, "node_label": node["label"], **d})
        return result

    # ── 节点租约（P2 核心） ──────────────────────────────
    # 租约状态存在独立侧车文件 <json>.leases.json，不进 roadmap 主 JSON——
    # 否则每次心跳都会改写主文件、污染 --if-rev 的 rev。策略（claim/heartbeat/
    # steal/release/fencing）由 lease.py 统一提供，这里只管落盘，保证两个
    # carrier 对"一次 claim 意味着什么"只有一份真相。

    def _lease_store_path(self) -> str:
        return self.json_path + ".leases.json"

    def _read_lease_store(self) -> dict:
        try:
            with open(self._lease_store_path(), "r", encoding="utf-8") as f:
                store = json.load(f)
            if not isinstance(store, dict):
                return {"leases": {}, "events": []}
            store.setdefault("leases", {})
            store.setdefault("events", [])
            return store
        except (FileNotFoundError, json.JSONDecodeError):
            return {"leases": {}, "events": []}

    def _write_lease_store(self, store: dict) -> None:
        atomic_write_text(self._lease_store_path(), json.dumps(store, ensure_ascii=False, indent=2))

    def get_lease(self, node_uid: str) -> Optional[dict]:
        """返回该节点的当前租约 dict，无租约时返回 None。"""
        return self._read_lease_store()["leases"].get(node_uid)

    def claim_lease(self, node_uid: str, agent_id: str, ttl: float = LEASE_TTL_SECONDS,
                    device_id: str = "", now: Optional[float] = None) -> dict:
        self.get_node(node_uid)  # 节点必须存在，否则 KeyError（沿用既有错误输出）
        now = time.time() if now is None else now
        store = self._read_lease_store()
        existing = store["leases"].get(node_uid)
        if existing is not None and not is_expired(existing, now):
            raise LeaseHeld(f"node {node_uid} already leased by {existing['agent_id']} "
                            f"(fencing {existing['fencing_token']}, expires {existing['expires_at']})")
        lease = new_lease(node_uid, agent_id, device_id, ttl, now)
        store["leases"][node_uid] = lease
        store["events"].append({"operation": "lease-claimed", "node_uid": node_uid,
                                 "agent_id": agent_id, "fencing_token": lease["fencing_token"], "at": now})
        self._write_lease_store(store)
        return lease

    def heartbeat_lease(self, node_uid: str, agent_id: str, now: Optional[float] = None) -> dict:
        now = time.time() if now is None else now
        store = self._read_lease_store()
        lease = store["leases"].get(node_uid)
        if lease is None:
            raise LeaseHeld(f"node {node_uid} has no active lease to heartbeat")
        if is_expired(lease, now):
            raise LeaseHeld(f"node {node_uid} lease expired at {lease['expires_at']}; steal instead")
        if lease["agent_id"] != agent_id:
            raise LeaseHeld(f"node {node_uid} leased by {lease['agent_id']}, not {agent_id}")
        renewed = apply_heartbeat(lease, now)
        store["leases"][node_uid] = renewed
        self._write_lease_store(store)
        return renewed

    def steal_lease(self, node_uid: str, agent_id: str, device_id: str = "",
                   now: Optional[float] = None) -> dict:
        now = time.time() if now is None else now
        store = self._read_lease_store()
        existing = store["leases"].get(node_uid)
        if existing is not None and not is_expired(existing, now):
            raise LeaseHeld(f"node {node_uid} lease not expired (expires {existing['expires_at']}); "
                            f"cannot steal before TTL")
        lease = apply_steal(existing, node_uid, agent_id, device_id, now)
        store["leases"][node_uid] = lease
        store["events"].append({"operation": "lease-stolen", "node_uid": node_uid,
                                 "agent_id": agent_id, "fencing_token": lease["fencing_token"], "at": now})
        self._write_lease_store(store)
        return lease

    def release_lease(self, node_uid: str, agent_id: str, force: bool = False,
                      now: Optional[float] = None) -> None:
        now = time.time() if now is None else now
        store = self._read_lease_store()
        lease = store["leases"].get(node_uid)
        if lease is None:
            return  # 幂等：没有租约也算释放成功
        if not force:
            if is_expired(lease, now):
                raise LeaseHeld(f"node {node_uid} lease expired; use steal, not release")
            if lease["agent_id"] != agent_id:
                raise LeaseHeld(f"node {node_uid} leased by {lease['agent_id']}, not {agent_id}")
        store["leases"].pop(node_uid, None)
        store["events"].append({"operation": "lease-released", "node_uid": node_uid,
                                 "agent_id": agent_id, "force": force, "at": now})
        self._write_lease_store(store)

    def current_revision(self) -> str:
        """canonical sha256 of the semantic state, for `--if-rev` optimistic concurrency.

        Volatile `metadata.updated`/`created` are excluded so a no-op save does
        not invalidate an in-flight rev; leases live in a sidecar and are not
        part of the roadmap rev either.
        """
        nodes = {nid: node for nid, node in self.data.get("nodes", {}).items()}
        rev_data = {
            "nodes": nodes,
            "edges": self.data.get("edges", []),
            "metadata": {k: v for k, v in self.data.get("metadata", {}).items()
                         if k not in ("updated", "created")},
            "version": self.data.get("version"),
        }
        return sha256(canonical_json(rev_data))

    # ── 树遍历 ─────────────────────────────────────────

    def get_tree(self, root_id: str = "1", max_depth: int = 10, owners: dict = None) -> str:
        """生成 Unicode 盒状树形文本视图。

        `owners` 是 owner 列：display id → `agent[/device]`。传 None 或空
        dict 时树行与改动前逐字节一致（md 不膨胀的硬验收）。
        """
        if root_id not in self.data["nodes"]:
            return f"(节点 {root_id} 不存在)"

        blocked = self.blocked_node_ids()
        owners = owners or {}
        root = self.data["nodes"][root_id]
        # 根不带 connector，也不给子节点垫缩进——所以根单独走一行。
        lines = [tree_line(root, "", True, 0, blocked, owners.get(root_id))]

        def _render(nid: str, prefix: str, is_last: bool, depth: int):
            if depth > max_depth:
                return
            node = self.data["nodes"].get(nid)
            if not node:
                return
            lines.append(tree_line(node, prefix, is_last, depth, blocked, owners.get(nid)))

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

        遍历经 `iter_nodes(layer='plan')`：trace 节点无 status、不进焦点候选。
        """
        candidates = [
            node["id"] for node in self.iter_nodes()
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
    #
    # 模板只写一份，放在这一节的模块级函数里，两个 carrier 各自只负责**喂数据**
    # （自己的树、自己的链、自己的焦点）。以前是两个 carrier 各抄一份，抄出来就必然
    # 漂移：另一份少了 `> 当前施工` 行、ROADMAP_TREE 标记与
    # "当前施工点"块，light section 里焦点决策的备注也丢了。md 是
    # Human 唯一看得到的面子，"两个 carrier 同语义"在这里就得是逐字节同。
    #
    # 参数全是已经渲染好的片段：这些函数不再知道 carrier、节点与边，因此不可能
    # 对某一家的存储形状产生偏好。

    def _blocked_chain_lines(self) -> list:
        """本 carrier 的阻塞链条目：喂的是自己的边与节点，取舍规则共用。

        端点落盘是 uid：喂给 blocked_chain_lines 前每条边翻回显示 id。
        """
        return blocked_chain_lines(
            (edge_endpoints_as_display(e, self.data["nodes"]) for e in self.data.get("edges", [])),
            self.data["nodes"].get,
        )

    def render_full_section(
        self,
        all_nodes: bool = False,
        max_depth: int = 2,
        max_bytes: Optional[int] = None,
    ) -> str:
        """Render a bounded section unless the caller explicitly requests export."""
        now = self.data["metadata"].get("updated", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        focus_id = self.get_current_focus()
        focus_node = self.data["nodes"][focus_id] if focus_id else None

        tree_text = self.get_tree(
            max_depth=ALL_NODES_TREE_DEPTH if all_nodes else max_depth, owners=self.owner_map()
        )

        all_decisions = self.get_decisions() if all_nodes else []
        decision_lines = ""
        if all_nodes and all_decisions:
            decision_lines = "| 节点 | 问题 | 答案 | 备注 |\n"
            decision_lines += "|------|------|------|------|\n"
            for d in all_decisions:
                note = d.get("note", "")
                decision_lines += f"| {d['node_id']} | {d['q']} | {d['answer']} | {note} |\n"

        # 模板与片段的组装交给模块级函数：这里只负责从本 carrier 的数据里取出
        # 要显示的东西，不再自己拼 Markdown。
        return compose_full_section(
            artifact_name=os.path.basename(self.json_path),
            updated=now,
            focus_head=focus_line(focus_id, focus_node["label"] if focus_node else ""),
            tree_text=tree_text,
            # 树之后立刻给出"为什么没进展"——Human 的视线顺序是先扫树看见 `[!]`，
            # 再需要一个不用翻 JSON 的答案。
            chain=render_chain_plain(self._blocked_chain_lines()),
            # 待决问题队列（失败达阈值挂起的 open question），只在有状态时出现。
            open_questions=render_open_questions_plain(self.open_question_items()),
            decision_table=decision_lines,
            focus_detail=focus_export_detail(
                focus_id,
                focus_node["label"] if focus_node else "",
                focus_node.get("notes", "") if focus_node else "",
            ),
            max_bytes=max_bytes,
        )

    def render_light_section(self) -> str:
        """轻量渲染（Human 视图）：树 depth=2 + 焦点节点展开。"""
        now = self.data["metadata"].get("updated", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        owners = self.owner_map()
        tree_text = self.get_tree(max_depth=2, owners=owners)

        focus_id = self.get_current_focus()
        focus_node = self.data["nodes"][focus_id] if focus_id else None

        return compose_light_section(
            artifact_name=os.path.basename(self.json_path),
            updated=now,
            tree_text=tree_text,
            # 空链时这里得到空串：下面那个模板因此在无阻塞时与引入阻塞链之前逐字节相同。
            chain=render_chain_collapsed(self._blocked_chain_lines()),
            # 待决问题队列，同样只在有状态时出现（无状态时空串，md 不变）。
            open_questions=render_open_questions_collapsed(self.open_question_items()),
            focus_detail=focus_light_detail(
                focus_id,
                focus_node["label"] if focus_node else "",
                focus_node.get("notes", "") if focus_node else "",
                focus_node.get("decisions", []) if focus_node else [],
                self.get_focus_subtree(focus_id, max_depth=1, owners=owners) if focus_id else "",
            ),
        )

    def get_focus_subtree(self, root_id: str, max_depth: int = 1, owners: dict = None) -> str:
        """Render a bounded subtree under the focus node.

        `owners` 是 owner 列（display id → `agent[/device]`）；传 None 时
        子树行与改动前逐字节一致。
        """
        if root_id not in self.data["nodes"]:
            return ""

        lines = []
        owners = owners or {}
        root = self.data["nodes"][root_id]
        children = root.get("children", [])
        blocked = self.blocked_node_ids()

        def _render(nid: str, prefix: str, is_last: bool, depth: int):
            node = self.data["nodes"].get(nid)
            if not node:
                return
            lines.append(tree_line(node, prefix, is_last, depth, blocked, owners.get(nid)))

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
        """验证路线图数据完整性，返回错误列表。

        只校验 plan 层节点：trace 节点（S2 起）没有 `parent` / `children` /
        `status`，套用 plan 的结构校验会误报。它们由 S2 的 trace 契约单独保证，
        不在此处。遍历经 `iter_nodes(layer='plan')`。
        """
        errors = []

        # 必须有根节点
        if "1" not in self.data.get("nodes", {}):
            errors.append("缺少根节点 '1'")

        for nid, node in ((n["id"], n) for n in self.iter_nodes()):
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
        # 写入中断留下的半态（节点已删、边还在）。它必须被检出，不能
        # 静默参与调度；修法见 `edge remove`（不需要事务来防，检出即可）。
        # 端点落盘是 uid：有效端点要么是某个节点的 uid，要么是（迁移前）显示 id。
        nodes = self.data.get("nodes", {})
        node_ids = set(nodes.keys())
        uids = {n.get("uid") for n in nodes.values() if n.get("uid")}
        for edge in self.data.get("edges", []):
            for key in ("from", "to"):
                endpoint = edge.get(key)
                if endpoint not in uids and endpoint not in node_ids:
                    errors.append(f"边 {edge.get('id')}: {key} 端点 {endpoint} 不存在（悬空边）")

        return errors

    # ── 统计 ───────────────────────────────────────────

    def stats(self) -> dict:
        """路线图统计信息。"""
        nodes = self.iter_nodes()
        status_counts = {
            STATUS_PENDING: 0,
            STATUS_IN_PROGRESS: 0,
            STATUS_COMPLETED: 0,
            STATUS_BLOCKED: 0,
        }
        for n in nodes:
            s = n.get("status", STATUS_PENDING)
            if s in status_counts:
                status_counts[s] += 1

        total_decisions = sum(len(n.get("decisions", [])) for n in nodes)

        return {
            "total_nodes": len(nodes),
            "status_counts": status_counts,
            "total_decisions": total_decisions,
            "max_depth": max((node_depth(n["id"]) for n in nodes), default=0),
        }
