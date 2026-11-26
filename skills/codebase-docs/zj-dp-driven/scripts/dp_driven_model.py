"""zj-dp-driven model — five entities + the derived-state core.

Design baseline: docs/designs/zj-dp-driven-skill-design.md §2–§3, §7.

This is the Phase-1 foundation: the entity model plus the **state-derivation rules**
everything else (orchestration, viz, closeout) depends on. It owns the two
invariants the design calls the "一致性根":

  §3.1  single source of status, three tiers:
          ticket / finding  → store their own lifecycle status (the only hand-written base)
          task_plan         → STORES lifecycle status (explicit three-state)
          task              → DERIVED from its 1:1 task_plan, never stored
  §3.2  被阻塞 (blocked) is ALWAYS derived, NEVER a stored column — same rule on both layers.
        blocked comes only from `blocks` edges (parent-child never blocks).

Per §3.2 / §3.2.1, a node's blocked fields are **absent** (not `False`) when nothing
blocks it, and `external_hold` is an ORTHOGONAL bypass — shown_blocked = derived ∨ hold,
never folded into the stored status.

Scope: Phase 1 has NO locking (design §8 渐进策略 = single user + single agent first);
finding *disposition* here records the §3.5 step-3 摘除+标态, while downstream分派
(producing tickets / new findings / new tasks) is orchestration = later phase.
"""

from __future__ import annotations

import json
import os

import dp_driven_carrier as carrier

# ── status word table (§2). Display has four states; storage keeps three. ──
# 被阻塞 is display-only: it is computed on read (§3.2) and has no stored column.
S_OPEN = "未完成"
S_BLOCKED = "被阻塞"        # derived / display only — never written to a status column
S_DONE = "已完成"
S_ABANDONED = "已放弃"

STORED_STATUSES = (S_OPEN, S_DONE, S_ABANDONED)  # the only values a status column may hold
TERMINAL_STATUSES = (S_DONE, S_ABANDONED)        # §5.1 完成判据 counts these as 终态

KIND_TASK = "task"
KIND_TICKET = "ticket"
KIND_FINDING = "finding"

# §4.4 two-layer claim kinds (opaque identifiers on the `claim` table).
CLAIM_PLAN = "plan"
CLAIM_TICKET = "ticket"

# §4.5 sentinel agent: a plan claimed by __settlement__ is the settlement round —
# its plan-level claim gate is bypassed so any agent may claim tickets inside it.
SETTLEMENT_AGENT = "__settlement__"

EDGE_BLOCKS = "blocks"     # the only edge type that blocks (§3.2); parent-child is a column
EDGE_TYPES = (EDGE_BLOCKS,)


class DpDrivenError(ValueError):
    """Model-level failure carrying a stable `E_*` code (CLI maps codes to exit)."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _now() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _next_id(existing) -> int:
    ids = [int(k) for k in existing] if existing else []
    return (max(ids) + 1) if ids else 0


class DpDriven:
    """In-memory DP state graph + derived-state reads. Persisted via `dp_driven_carrier`."""

    def __init__(self, db_path: str, data: dict | None = None):
        self.db_path = db_path
        self.data = data if data is not None else carrier.empty_data()

    # ── lifecycle ─────────────────────────────────────────

    @classmethod
    def init(cls, db_path: str, destination: str, now: str | None = None) -> "DpDriven":
        """§4.0 bootstrap step 1–2: record destination. task0 + scoped-context creation
        is a Human/agent action layered on top; init only opens the carrier."""
        obj = cls(db_path, carrier.empty_data())
        obj.data["meta"] = {
            "destination": destination,
            "version": "1",
            "created_at": now or _now(),
        }
        obj.save()
        return obj

    @classmethod
    def open(cls, db_path: str) -> "DpDriven":
        return cls(db_path, carrier.load(db_path))

    def load(self) -> dict:
        self.data = carrier.load(self.db_path)
        return self.data

    def save(self) -> str:
        self.data["meta"].setdefault("created_at", _now())
        self.data["meta"]["updated"] = _now()
        return carrier.save(self.db_path, self.data)

    # ── task / task_plan (§2, §3.1) ───────────────────────

    def add_task(self, name: str, context_md: str | None = None,
                 memory_md: str | None = None, now: str | None = None,
                 derived_from_finding: int | None = None) -> int:
        """Create a layer-1 task AND its 1:1 task_plan. task carries no status (§3.1);
        the plan is the single lifecycle source, starting 未完成. `derived_from_finding`
        records §3.5 form-③ origin — a new task a finding's disposition opened up."""
        if not name or not name.strip():
            raise DpDrivenError("E_INVALID_NAME", "task name 必须是非空、self-explain 的一句话")
        if derived_from_finding is not None:
            self._require_finding(derived_from_finding)
        tid = _next_id(self.data["tasks"])
        ts = now or _now()
        self.data["tasks"][str(tid)] = {
            "id": tid, "name": name.strip(), "context_md": context_md,
            "memory_md": memory_md, "derived_from_finding": derived_from_finding,
            "created_at": ts,
        }
        self.data["plans"][str(tid)] = {
            "task_id": tid, "status": S_OPEN, "summary": None,
            "created_at": ts, "completed_at": None,
        }
        return tid

    def set_plan_status(self, task_id: int, status: str,
                        summary: str | None = None, now: str | None = None,
                        agent: str | None = None) -> None:
        """Write the task↔plan lifecycle at its ONLY source: the task_plan (§3.1).
        Rejects 被阻塞 — blocked is derived, never stored (§3.2).
        §4.4 claim gate: if `agent` is provided, that agent must hold (or nobody holds)
        the plan-level claim. `agent=None` = Human direct action, no gate."""
        if status == S_BLOCKED:
            raise DpDrivenError("E_INVALID_STATUS",
                                "被阻塞 是派生态，不能写入 status（§3.2 单一状态源）")
        if status not in STORED_STATUSES:
            raise DpDrivenError("E_INVALID_STATUS",
                                f"status 必须 ∈ {list(STORED_STATUSES)}")
        plan = self.data["plans"].get(str(task_id))
        if plan is None:
            raise DpDrivenError("E_NO_SUCH_PLAN", f"task {task_id} 没有 1:1 task_plan")
        if agent is not None:
            self._require_claim_free_or_mine(CLAIM_PLAN, task_id, agent)
        plan["status"] = status
        if summary is not None:
            plan["summary"] = summary
        if status in TERMINAL_STATUSES:
            plan["completed_at"] = now or _now()
        elif status == S_OPEN:
            plan["completed_at"] = None  # reopen clears the terminal timestamp

    def plan_summary(self, task_id: int, text: str) -> None:
        """§2 task-plan '到终态时的简洁总结'."""
        plan = self.data["plans"].get(str(task_id))
        if plan is None:
            raise DpDrivenError("E_NO_SUCH_PLAN", f"task {task_id} 没有 1:1 task_plan")
        plan["summary"] = text

    # ── finding (§2, §3.4, §3.5) ──────────────────────────

    def add_finding(self, md_path: str | None = None, external_hold: str | None = None,
                    now: str | None = None,
                    derived_from_finding: int | None = None) -> int:
        """Create a finding. `derived_from_finding` records §3.5 form-② origin — a new
        finding split out of a parent finding's disposition (NULL = a root observation)."""
        if derived_from_finding is not None:
            self._require_finding(derived_from_finding)   # source must already exist
        fid = _next_id(self.data["findings"])
        self.data["findings"][str(fid)] = {
            "id": fid, "status": S_OPEN, "md_path": md_path,
            "external_hold": external_hold, "derived_from_finding": derived_from_finding,
            "created_at": now or _now(), "completed_at": None,
        }
        return fid

    def add_finding_membership(self, finding_id: int, task_id: int) -> None:
        """§3.4 finding 多归属: a finding may hang on many plans (overlapping subproblem)."""
        self._require_finding(finding_id)
        self._require_task(task_id)
        pair = {"finding_id": finding_id, "task_id": task_id}
        if pair not in self.data["memberships"]:
            self.data["memberships"].append(pair)

    def remove_finding_membership(self, finding_id: int, task_id: int) -> None:
        self.data["memberships"] = [
            m for m in self.data["memberships"]
            if not (m["finding_id"] == finding_id and m["task_id"] == task_id)
        ]

    def find_memberships(self, finding_id: int) -> list[int]:
        return [m["task_id"] for m in self.data["memberships"] if m["finding_id"] == finding_id]

    def dispose_finding(self, finding_id: int, to: str = S_DONE, now: str | None = None) -> None:
        """§3.5 memo step 3: 处置一次 = 标态 + **从所有归属它的 plan 中摘除**，之后只读复用。
        Downstream分派 (tickets / new findings / new tasks / scoped 细节) is orchestration
        (later phase) — this method only finalizes the node and clears its memberships so
        the finding is never re-processed. 已放弃 也走同一路径（形态⑤）。"""
        f = self._require_finding(finding_id)
        if to == S_BLOCKED:
            raise DpDrivenError("E_INVALID_STATUS", "finding 处置目标态不能是 被阻塞（派生态）")
        if to not in TERMINAL_STATUSES:
            raise DpDrivenError("E_INVALID_STATUS", f"finding 处置目标态必须 ∈ {list(TERMINAL_STATUSES)}")
        f["status"] = to
        f["completed_at"] = now or _now()
        self.data["memberships"] = [m for m in self.data["memberships"] if m["finding_id"] != finding_id]

    # ── ticket (§2, §3.4, §7 Q1) ──────────────────────────

    def add_ticket(self, ref: str | None = None, kv: dict | None = None,
                   md_path: str | None = None, derived_from_finding: int | None = None,
                   parent_id: int | None = None, task_id: int | None = None,
                   external_hold: str | None = None, now: str | None = None) -> int:
        """Create a ticket. `task_id=None` ⇒ unassigned ⇒ in pool (§2 pool view).
        `derived_from_finding` is the §7 Q1 物化 edge (1→n from a finding's disposition)."""
        if derived_from_finding is not None:
            self._require_finding(derived_from_finding)
        if parent_id is not None:
            self._require_ticket(parent_id)
        if task_id is not None:
            self._require_task(task_id)
        tkid = _next_id(self.data["tickets"])
        self.data["tickets"][str(tkid)] = {
            "id": tkid, "status": S_OPEN, "task_id": task_id,
            "derived_from_finding": derived_from_finding, "parent_id": parent_id,
            "ref": ref, "kv": kv, "md_path": md_path,
            "external_hold": external_hold, "created_at": now or _now(), "completed_at": None,
        }
        return tkid

    def assign_ticket(self, ticket_id: int, task_id: int | None) -> None:
        """§3.4 ticket 单归属: set the single owning plan. `None` releases back to pool
        (used by priority preemption §4.1 — release the claim, no fifth status)."""
        t = self._require_ticket(ticket_id)
        if task_id is not None:
            self._require_task(task_id)
        t["task_id"] = task_id

    def set_ticket_status(self, ticket_id: int, status: str, now: str | None = None,
                          agent: str | None = None) -> None:
        """§4.4 ticket-level claim gate: if `agent` is provided and someone else holds
        this ticket's claim, the write is rejected. `agent=None` = Human direct."""
        t = self._require_ticket(ticket_id)
        if status == S_BLOCKED:
            raise DpDrivenError("E_INVALID_STATUS", "被阻塞 是派生态，不能写入 ticket.status")
        if status not in STORED_STATUSES:
            raise DpDrivenError("E_INVALID_STATUS", f"status 必须 ∈ {list(STORED_STATUSES)}")
        if agent is not None:
            self._require_claim_free_or_mine(CLAIM_TICKET, ticket_id, agent)
        t["status"] = status
        t["completed_at"] = (now or _now()) if status in TERMINAL_STATUSES else None

    # ── edges (§3.2) ──────────────────────────────────────

    def add_blocks(self, from_kind: str, from_id: int, to_kind: str, to_id: int) -> int:
        """blocks edge: `from` (prereq) must reach 已完成 before `to` (dependent) unblocks.
        Only blocks edges block; they may span tickets and findings (layer-2 graph)."""
        for kind, nid in ((from_kind, from_id), (to_kind, to_id)):
            self._require_layer2_node(kind, nid)
        if from_kind == to_kind and from_id == to_id:
            raise DpDrivenError("E_SELF_EDGE", "blocks 边不能自环")
        eid = _next_id({str(e["id"]) for e in self.data["edges"]})
        self.data["edges"].append({
            "id": eid, "type": EDGE_BLOCKS,
            "from_kind": from_kind, "from_id": from_id, "to_kind": to_kind, "to_id": to_id,
        })
        return eid

    def remove_edge(self, edge_id: int) -> None:
        self.data["edges"] = [e for e in self.data["edges"] if e["id"] != edge_id]

    # ── external hold (§3.2.1) ────────────────────────────

    def set_external_hold(self, kind: str, node_id: int, reason: str | None) -> None:
        """§3.2.1 次选: an off-graph blocker. Orthogonal to derived blocked — sets a
        `external_hold` note, NEVER status=被阻塞. reason=None clears the hold."""
        node = self._require_layer2_node(kind, node_id)
        node["external_hold"] = reason

    # ── derived-state reads (the core) ────────────────────

    def _resolve(self, kind: str, node_id: int) -> dict:
        if kind == KIND_TICKET:
            return self._require_ticket(node_id)
        if kind == KIND_FINDING:
            return self._require_finding(node_id)
        raise DpDrivenError("E_INVALID_KIND", f"未知 layer-2 节点类型: {kind}")

    def _holding_edges(self, kind: str, node_id: int) -> list[int]:
        """blocks edges pointing AT this node whose prereq is not yet 已完成 (§3.2)."""
        out = []
        for e in self.data["edges"]:
            if e["type"] != EDGE_BLOCKS:
                continue
            if e["to_kind"] == kind and e["to_id"] == node_id:
                prereq = self._resolve(e["from_kind"], e["from_id"])
                if prereq["status"] != S_DONE:
                    out.append(e["id"])
        return out

    def node_view(self, kind: str, node_id: int) -> dict:
        """Item view + derived blocked. §3.2: when nothing blocks, `blocked`/`blocked_reason`
        are ABSENT — not False. `shown_blocked` folds the orthogonal external_hold (§3.2.1)."""
        node = dict(self._resolve(kind, node_id))
        hold = node.get("external_hold")
        if node["status"] == S_OPEN:
            reasons = self._holding_edges(kind, node_id)
            node["derived_blocked"] = bool(reasons)
            if reasons:
                node["blocked"] = True
                node["blocked_reason"] = reasons
        else:
            node["derived_blocked"] = False  # a terminal item is never "blocked"
        node["shown_blocked"] = node["derived_blocked"] or (hold is not None)
        return node

    def plan_is_blocked(self, task_id: int) -> bool:
        """§3.6 F2 商图: plan blocked ⇔ ∃ cross-plan blocks edge whose prereq is unfinished
        and whose dependent (still open) lives in THIS plan. Blocked's唯一真相源 is inner edges."""
        self._require_task(task_id)
        plan = self.data["plans"][str(task_id)]
        if plan["status"] in TERMINAL_STATUSES:
            return False
        inner = self._plan_inner_nodes(task_id)
        for e in self.data["edges"]:
            if e["type"] != EDGE_BLOCKS:
                continue
            dep = (e["to_kind"], e["to_id"])
            pre = (e["from_kind"], e["from_id"])
            if dep in inner and pre not in inner:  # cross-plan edge INTO this plan
                prereq = self._resolve(e["from_kind"], e["from_id"])
                if prereq["status"] != S_DONE and self._resolve(*dep)["status"] == S_OPEN:
                    return True
        return False

    def plan_shown_blocked(self, task_id: int) -> bool:
        """§3.2.1: derived 商图 blocked OR any in-plan item carries external_hold (two orthogonal paths)."""
        if self.plan_is_blocked(task_id):
            return True
        for kind, nid in self._plan_inner_nodes(task_id):
            if self._resolve(kind, nid).get("external_hold") is not None:
                return True
        return False

    def task_view(self, task_id: int) -> dict:
        """§3.3 task status is a projection of the 1:1 plan — never read from a task column."""
        self._require_task(task_id)
        plan = self.data["plans"][str(task_id)]
        if plan["status"] == S_DONE:
            status = S_DONE
        elif plan["status"] == S_ABANDONED:
            status = S_ABANDONED
        elif self.plan_is_blocked(task_id):
            status = S_BLOCKED
        else:
            status = S_OPEN
        t = dict(self.data["tasks"][str(task_id)])
        t["plan_status"] = plan["status"]         # the stored source
        t["status"] = status                       # the derived projection
        t["completed_at"] = plan.get("completed_at")
        t["shown_blocked"] = self.plan_shown_blocked(task_id)
        return t

    def pool(self) -> list[dict]:
        """§2 available pool (derived view): open + not claimed by any plan.
        tickets: task_id IS NULL; findings: no membership rows."""
        out = []
        for t in self.data["tickets"].values():
            if t["status"] == S_OPEN and t["task_id"] is None:
                out.append({"kind": KIND_TICKET, "id": t["id"]})
        membered = {m["finding_id"] for m in self.data["memberships"]}
        for f in self.data["findings"].values():
            if f["status"] == S_OPEN and f["id"] not in membered:
                out.append({"kind": KIND_FINDING, "id": f["id"]})
        out.sort(key=lambda x: (x["kind"], x["id"]))
        return out

    def is_complete(self) -> bool:
        """§5.1 完成判据: every task at 终态 (已完成/已放弃)."""
        if not self.data["plans"]:
            return False
        return all(p["status"] in TERMINAL_STATUSES for p in self.data["plans"].values())

    # ── claims (§4.4 two-layer) ───────────────────────────

    def claim(self, kind: str, ref_id: int, agent: str, now: str | None = None) -> bool:
        """Acquire a plan-level or ticket-level claim (§4.4).
        Returns True if newly acquired, False if the same agent already holds it.
        Raises E_CLAIM_HELD_BY_OTHER if a different agent holds it,
        E_INVALID_KIND if kind is not 'plan' | 'ticket',
        E_NO_SUCH_TASK / E_NO_SUCH_TICKET if the ref does not exist.
        No TTL in Phase 2 (§4.4 释放条件包含超时 is `[未决]` §8) — release is explicit.
        """
        if kind == CLAIM_PLAN:
            self._require_task(ref_id)
        elif kind == CLAIM_TICKET:
            self._require_ticket(ref_id)
        else:
            raise DpDrivenError("E_INVALID_KIND", f"claim kind 必须是 {CLAIM_PLAN} | {CLAIM_TICKET}")
        existing = self._find_claim(kind, ref_id)
        if existing is None:
            self.data["claims"].append({
                "kind": kind, "ref_id": ref_id, "agent": agent,
                "claimed_at": now or _now(),
            })
            return True
        if existing["agent"] == agent:
            return False
        raise DpDrivenError("E_CLAIM_HELD_BY_OTHER",
                            f"{kind}#{ref_id} 已被 agent {existing['agent']!r} claim")

    def release(self, kind: str, ref_id: int, agent: str | None = None,
                force: bool = False) -> bool:
        """Release a claim. `force=True` (Human 特权) 或 `agent=None` 无条件释放；
        否则必须由持有人释放。缺 claim 视为 no-op (False)。§4.1 优先级抢占 = 持有人
        显式 release 而不新增第五态。"""
        if force or agent is None:
            before = len(self.data["claims"])
            self.data["claims"] = [c for c in self.data["claims"]
                                   if not (c["kind"] == kind and c["ref_id"] == ref_id)]
            return len(self.data["claims"]) != before
        existing = self._find_claim(kind, ref_id)
        if existing is None:
            return False
        if existing["agent"] != agent:
            raise DpDrivenError("E_CLAIM_NOT_OWNER",
                                f"{kind}#{ref_id} 由 {existing['agent']!r} 持有，{agent!r} 无权 release")
        self.data["claims"] = [c for c in self.data["claims"] if c is not existing]
        return True

    def claim_owner(self, kind: str, ref_id: int) -> str | None:
        c = self._find_claim(kind, ref_id)
        return c["agent"] if c else None

    def list_claims(self) -> list[dict]:
        return [dict(c) for c in sorted(self.data["claims"], key=lambda c: (c["kind"], c["ref_id"]))]

    # ── settlement round (§4.5) ───────────────────────────

    def settlement_run(self, name: str | None = None, now: str | None = None) -> tuple[int, list[dict]]:
        """§4.5 结算轮: 建一个特殊 task-plan 收纳 pool 中所有未解决 items，
        次序退化为主线顺序（blocks 拓扑优先，其余按 id 递增）。Plan-level claim 退化——
        用 SETTLEMENT_AGENT 哨兵，set_plan_status 对该哨兵 bypass。
        返回 (task_id, items)。空 pool → E_POOL_EMPTY。"""
        items = self.pool()
        if not items:
            raise DpDrivenError("E_POOL_EMPTY", "pool 为空，无需结算轮")
        ordered = self._topo_order_pool(items)
        tid = self.add_task(name or f"结算轮", now=now)
        self.data["claims"].append({
            "kind": CLAIM_PLAN, "ref_id": tid, "agent": SETTLEMENT_AGENT,
            "claimed_at": now or _now(),
        })
        for it in ordered:
            if it["kind"] == KIND_TICKET:
                self.assign_ticket(it["id"], tid)
            else:
                self.add_finding_membership(it["id"], tid)
        return tid, ordered

    # ── two-stage closeout (§5.2) ─────────────────────────

    def closeout_export_summary(self, out_path: str) -> str:
        """§5.2 步 1: 把过程图的关键结构性关系（跨 plan 依赖 / finding 多归属映射 /
        物化链路）导出为 markdown 落进同目录，供治理者查阅。
        Deterministic ordering → 相同输入两次输出字节相等。"""
        lines: list[str] = []
        dest = self.data["meta"].get("destination", "")
        lines.append("# Process summary")
        lines.append("")
        lines.append(f"- destination: {dest}")
        lines.append(f"- is_complete: {self.is_complete()}")
        lines.append("")
        lines.append("## Tasks")
        lines.append("")
        lines.append("| id | name | status | completed_at |")
        lines.append("| --- | --- | --- | --- |")
        for t in sorted(self.data["tasks"].values(), key=lambda x: x["id"]):
            tv = self.task_view(t["id"])
            lines.append(f"| {t['id']} | {t['name']} | {tv['status']} | {tv.get('completed_at') or ''} |")
        lines.append("")
        lines.append("## Cross-plan blocks (§3.6 F2 商图边)")
        lines.append("")
        lines.append("| edge_id | from (kind#id @ plan) | to (kind#id @ plan) |")
        lines.append("| --- | --- | --- |")
        for e in sorted(self.data["edges"], key=lambda x: x["id"]):
            if e["type"] != EDGE_BLOCKS:
                continue
            fplan = self._item_plan(e["from_kind"], e["from_id"])
            tplan = self._item_plan(e["to_kind"], e["to_id"])
            lines.append(
                f"| {e['id']} | {e['from_kind']}#{e['from_id']} @ {fplan if fplan is not None else '-'} | "
                f"{e['to_kind']}#{e['to_id']} @ {tplan if tplan is not None else '-'} |"
            )
        lines.append("")
        lines.append("## Finding multi-membership (§3.4)")
        lines.append("")
        lines.append("| finding_id | plans | status |")
        lines.append("| --- | --- | --- |")
        for f in sorted(self.data["findings"].values(), key=lambda x: x["id"]):
            plans = sorted(self.find_memberships(f["id"]))
            lines.append(f"| {f['id']} | {','.join(str(p) for p in plans) or '-'} | {f['status']} |")
        lines.append("")
        lines.append("## Ticket materialization (§7 Q1 derived_from_finding + parent_id + §2 ref)")
        lines.append("")
        lines.append("| ticket_id | ref | derived_from_finding | parent_id | task_id | status |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for t in sorted(self.data["tickets"].values(), key=lambda x: x["id"]):
            lines.append(
                f"| {t['id']} | {t.get('ref') or '-'} | "
                f"{t.get('derived_from_finding') if t.get('derived_from_finding') is not None else '-'} | "
                f"{t.get('parent_id') if t.get('parent_id') is not None else '-'} | "
                f"{t['task_id'] if t['task_id'] is not None else '-'} | {t['status']} |"
            )
        lines.append("")
        lines.append("## Finding derivation (§3.5 形态② finding→finding / 形态③ finding→task)")
        lines.append("")
        lines.append("| source_finding | target_kind | target_id |")
        lines.append("| --- | --- | --- |")
        derived_rows = []
        for f in sorted(self.data["findings"].values(), key=lambda x: x["id"]):
            if f.get("derived_from_finding") is not None:
                derived_rows.append((f["derived_from_finding"], KIND_FINDING, f["id"]))
        for t in sorted(self.data["tasks"].values(), key=lambda x: x["id"]):
            if t.get("derived_from_finding") is not None:
                derived_rows.append((t["derived_from_finding"], KIND_TASK, t["id"]))
        for src, kind, tid in sorted(derived_rows, key=lambda r: (r[0], r[1], r[2])):
            lines.append(f"| {src} | {kind} | {tid} |")
        lines.append("")
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        return out_path

    def closeout_verify_governed(self, marker_path: str | None = None) -> dict:
        """§5.2 步 2 门：治理完成 = 存在 .governed.json marker（由 zj-docs-ontology
        侧写入）。校验 is_complete() + marker 存在 + schema 合理。返回 marker payload；
        任一失败抛 DpDrivenError。"""
        if not self.is_complete():
            raise DpDrivenError("E_NOT_COMPLETE", "closeout 前所有 task 必须到终态（§5.1）")
        path = marker_path or self._default_marker_path()
        if not os.path.exists(path):
            raise DpDrivenError("E_CLOSEOUT_NOT_GOVERNED",
                                f"未找到治理 marker: {path}（zj-docs-ontology 完成时应写入）")
        with open(path, encoding="utf-8") as fh:
            try:
                payload = json.loads(fh.read())
            except json.JSONDecodeError as e:
                raise DpDrivenError("E_CLOSEOUT_MARKER_MALFORMED", f"{path}: {e}")
        if not isinstance(payload, dict) or "governed_at" not in payload:
            raise DpDrivenError("E_CLOSEOUT_MARKER_MALFORMED",
                                f"{path} 缺 governed_at 字段")
        return payload

    def closeout_delete_carrier(self, force: bool = False,
                                marker_path: str | None = None) -> str:
        """§5.2 步 3: 顺序门 (a) is_complete + governed marker（先跑 verify），
        (b) 显式 force。删除 sqlite 与 sidecar (.lock/.sqlite-wal/.sqlite-shm)。
        返回被删的 carrier 路径。"""
        self.closeout_verify_governed(marker_path)
        if not force:
            raise DpDrivenError("E_CLOSEOUT_CONFIRM_REQUIRED",
                                "删除 sqlite 是终结动作，需显式 force=True")
        db = self.db_path
        for suffix in ("", "-wal", "-shm", ".lock"):
            p = db + suffix
            if os.path.exists(p):
                os.remove(p)
        return db

    def _default_marker_path(self) -> str:
        base = self.db_path
        for ext in (".sqlite", ".sqlite3", ".db"):
            if base.endswith(ext):
                base = base[: -len(ext)]
                break
        return base + ".governed.json"

    # ── invariants ────────────────────────────────────────

    def validate(self) -> list[str]:
        """Mechanical checks of the §3 invariants. Returns a list of violation strings
        (empty = consistent). The blocked-derivation and single-source rules are asserted
        positively by tests; here we catch structural drift (dangling refs, illegal stored
        status, plan↔task 1:1 breach)."""
        errs: list[str] = []
        for tid in self.data["tasks"]:
            if tid not in self.data["plans"]:
                errs.append(f"E_PLAN_NOT_1TO1: task {tid} 没有对应 task_plan")
        for tid in self.data["plans"]:
            if tid not in self.data["tasks"]:
                errs.append(f"E_PLAN_NOT_1TO1: task_plan {tid} 没有对应 task")
        for p in self.data["plans"].values():
            if p["status"] not in STORED_STATUSES:
                errs.append(f"E_INVALID_STATUS: task_plan {p['task_id']}.status={p['status']!r} 非法")
        for kind, table in ((KIND_FINDING, "findings"), (KIND_TICKET, "tickets")):
            for n in self.data[table].values():
                if n["status"] not in STORED_STATUSES:
                    errs.append(f"E_INVALID_STATUS: {kind} {n['id']}.status={n['status']!r} 非法")
        for t in self.data["tickets"].values():
            if t["task_id"] is not None and str(t["task_id"]) not in self.data["tasks"]:
                errs.append(f"E_REF_MISSING: ticket {t['id']} 归属不存在的 task {t['task_id']}")
            if t["derived_from_finding"] is not None and str(t["derived_from_finding"]) not in self.data["findings"]:
                errs.append(f"E_REF_MISSING: ticket {t['id']} derived_from_finding 指向不存在的 finding")
            if t["parent_id"] is not None and str(t["parent_id"]) not in self.data["tickets"]:
                errs.append(f"E_REF_MISSING: ticket {t['id']} parent 指向不存在的 ticket")
        for m in self.data["memberships"]:
            if str(m["finding_id"]) not in self.data["findings"]:
                errs.append(f"E_REF_MISSING: membership 指向不存在的 finding {m['finding_id']}")
            if str(m["task_id"]) not in self.data["tasks"]:
                errs.append(f"E_REF_MISSING: membership 指向不存在的 task {m['task_id']}")
        # §3.5 form-②③ provenance: finding.derived_from_finding and task.derived_from_finding
        # must reference an existing finding (E_REF_MISSING).
        for kind, table in (("finding", "findings"), ("task", "tasks")):
            for n in self.data[table].values():
                src = n.get("derived_from_finding")
                if src is not None and str(src) not in self.data["findings"]:
                    errs.append(f"E_REF_MISSING: {kind} {n['id']}.derived_from_finding "
                                f"指向不存在的 finding {src}")
        for e in self.data["edges"]:
            if e["type"] not in EDGE_TYPES:
                errs.append(f"E_INVALID_EDGE_TYPE: edge {e['id']}.type={e['type']!r} 不支持")
            for kind, nid in ((e["from_kind"], e["from_id"]), (e["to_kind"], e["to_id"])):
                try:
                    self._resolve(kind, nid)
                except DpDrivenError:
                    errs.append(f"E_EDGE_ENDPOINT_MISSING: edge {e['id']} 端点 {kind}#{nid} 不存在")
        seen_claim: set[tuple[str, int]] = set()
        for c in self.data["claims"]:
            key = (c["kind"], c["ref_id"])
            if key in seen_claim:
                errs.append(f"E_DUP_CLAIM: {c['kind']}#{c['ref_id']} 重复 claim")
            seen_claim.add(key)
            if c["kind"] == CLAIM_PLAN:
                if str(c["ref_id"]) not in self.data["tasks"]:
                    errs.append(f"E_CLAIM_REF_MISSING: plan claim → 不存在的 task {c['ref_id']}")
            elif c["kind"] == CLAIM_TICKET:
                if str(c["ref_id"]) not in self.data["tickets"]:
                    errs.append(f"E_CLAIM_REF_MISSING: ticket claim → 不存在的 ticket {c['ref_id']}")
            else:
                errs.append(f"E_CLAIM_KIND: 未知 claim.kind={c['kind']!r}")
        return errs

    # ── helpers ───────────────────────────────────────────

    def _plan_inner_nodes(self, task_id: int) -> set[tuple[str, int]]:
        nodes: set[tuple[str, int]] = set()
        for t in self.data["tickets"].values():
            if t["task_id"] == task_id:
                nodes.add((KIND_TICKET, t["id"]))
        for m in self.data["memberships"]:
            if m["task_id"] == task_id:
                nodes.add((KIND_FINDING, m["finding_id"]))
        return nodes

    def _find_claim(self, kind: str, ref_id: int) -> dict | None:
        for c in self.data["claims"]:
            if c["kind"] == kind and c["ref_id"] == ref_id:
                return c
        return None

    def _require_claim_free_or_mine(self, kind: str, ref_id: int, agent: str) -> None:
        """§4.4 claim gate helper: no claim OR claim by same agent OR settlement sentinel
        → allowed. Any other holder → E_CLAIM_HELD_BY_OTHER."""
        existing = self._find_claim(kind, ref_id)
        if existing is None or existing["agent"] == agent:
            return
        if kind == CLAIM_PLAN and existing["agent"] == SETTLEMENT_AGENT:
            return  # §4.5: settlement plan bypasses plan-claim gate
        raise DpDrivenError("E_CLAIM_HELD_BY_OTHER",
                            f"{kind}#{ref_id} 由 {existing['agent']!r} 持有，{agent!r} 无权改写")

    def _item_plan(self, kind: str, node_id: int) -> int | None:
        """Return the task_id an item currently belongs to (ticket.owner / first membership)."""
        if kind == KIND_TICKET:
            return self._require_ticket(node_id).get("task_id")
        plans = self.find_memberships(node_id)
        return plans[0] if plans else None

    def _topo_order_pool(self, items: list[dict]) -> list[dict]:
        """§4.5 结算轮次序：blocks 拓扑优先，剩余按 (kind=ticket-first, id) 递增。
        使用 Kahn 分层；只考虑 pool 内部边（in-pool from & to）。"""
        ids = {(it["kind"], it["id"]) for it in items}
        indeg = {k: 0 for k in ids}
        adj: dict[tuple, list[tuple]] = {k: [] for k in ids}
        for e in self.data["edges"]:
            if e["type"] != EDGE_BLOCKS:
                continue
            src = (e["from_kind"], e["from_id"])
            dst = (e["to_kind"], e["to_id"])
            if src in ids and dst in ids:
                adj[src].append(dst)
                indeg[dst] += 1
        def order_key(k: tuple) -> tuple:
            # ticket before finding at same "level"; then by id
            return (0 if k[0] == KIND_TICKET else 1, k[1])
        ready = sorted([k for k, d in indeg.items() if d == 0], key=order_key)
        out: list[dict] = []
        by_id = {("ticket", it["id"]): it for it in items if it["kind"] == KIND_TICKET}
        by_id.update({("finding", it["id"]): it for it in items if it["kind"] == KIND_FINDING})
        visited: set[tuple] = set()
        while ready:
            cur = ready.pop(0)
            out.append(by_id[cur])
            visited.add(cur)
            for nxt in adj[cur]:
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    ready.append(nxt)
            ready.sort(key=order_key)
        leftover = sorted([it for it in items if (it["kind"], it["id"]) not in visited],
                          key=lambda it: order_key((it["kind"], it["id"])))
        out.extend(leftover)
        return out

    def _require_task(self, task_id: int) -> dict:
        t = self.data["tasks"].get(str(task_id))
        if t is None:
            raise DpDrivenError("E_NO_SUCH_TASK", f"task {task_id} 不存在")
        return t

    def _require_finding(self, finding_id: int) -> dict:
        f = self.data["findings"].get(str(finding_id))
        if f is None:
            raise DpDrivenError("E_NO_SUCH_FINDING", f"finding {finding_id} 不存在")
        return f

    def _require_ticket(self, ticket_id: int) -> dict:
        t = self.data["tickets"].get(str(ticket_id))
        if t is None:
            raise DpDrivenError("E_NO_SUCH_TICKET", f"ticket {ticket_id} 不存在")
        return t

    def _require_layer2_node(self, kind: str, node_id: int) -> dict:
        if kind == KIND_TICKET:
            return self._require_ticket(node_id)
        if kind == KIND_FINDING:
            return self._require_finding(node_id)
        raise DpDrivenError("E_INVALID_KIND", f"未知 layer-2 节点类型: {kind}")

    # ── orchestration input helpers (read-only; Phase-3a optimizer) ──
    # Appended at EOF so every existing `basename.py:line` anchor above stays valid.

    def in_flight_plans(self) -> list[int]:
        """§4.2 optimizer 输入：未到终态、且非结算哨兵（§4.5）的 plan = 可被热插目标的
        in-flight plan。纯只读，不新增存储列（不违反 §3.1 状态单一源）。"""
        out = []
        for tid, p in self.data["plans"].items():
            if p["status"] != S_OPEN:
                continue
            if self._is_settlement_plan(int(tid)):
                continue
            out.append(int(tid))
        return sorted(out)

    def _is_settlement_plan(self, task_id: int) -> bool:
        c = self._find_claim(CLAIM_PLAN, task_id)
        return bool(c and c["agent"] == SETTLEMENT_AGENT)
