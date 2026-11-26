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
                 memory_md: str | None = None, now: str | None = None) -> int:
        """Create a layer-1 task AND its 1:1 task_plan. task carries no status (§3.1);
        the plan is the single lifecycle source, starting 未完成."""
        if not name or not name.strip():
            raise DpDrivenError("E_INVALID_NAME", "task name 必须是非空、self-explain 的一句话")
        tid = _next_id(self.data["tasks"])
        ts = now or _now()
        self.data["tasks"][str(tid)] = {
            "id": tid, "name": name.strip(), "context_md": context_md,
            "memory_md": memory_md, "created_at": ts,
        }
        self.data["plans"][str(tid)] = {
            "task_id": tid, "status": S_OPEN, "summary": None,
            "created_at": ts, "completed_at": None,
        }
        return tid

    def set_plan_status(self, task_id: int, status: str,
                        summary: str | None = None, now: str | None = None) -> None:
        """Write the task↔plan lifecycle at its ONLY source: the task_plan (§3.1).
        Rejects 被阻塞 — blocked is derived, never stored (§3.2)."""
        if status == S_BLOCKED:
            raise DpDrivenError("E_INVALID_STATUS",
                                "被阻塞 是派生态，不能写入 status（§3.2 单一状态源）")
        if status not in STORED_STATUSES:
            raise DpDrivenError("E_INVALID_STATUS",
                                f"status 必须 ∈ {list(STORED_STATUSES)}")
        plan = self.data["plans"].get(str(task_id))
        if plan is None:
            raise DpDrivenError("E_NO_SUCH_PLAN", f"task {task_id} 没有 1:1 task_plan")
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
                    now: str | None = None) -> int:
        fid = _next_id(self.data["findings"])
        self.data["findings"][str(fid)] = {
            "id": fid, "status": S_OPEN, "md_path": md_path,
            "external_hold": external_hold, "created_at": now or _now(), "completed_at": None,
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

    def set_ticket_status(self, ticket_id: int, status: str, now: str | None = None) -> None:
        t = self._require_ticket(ticket_id)
        if status == S_BLOCKED:
            raise DpDrivenError("E_INVALID_STATUS", "被阻塞 是派生态，不能写入 ticket.status")
        if status not in STORED_STATUSES:
            raise DpDrivenError("E_INVALID_STATUS", f"status 必须 ∈ {list(STORED_STATUSES)}")
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
        for e in self.data["edges"]:
            if e["type"] not in EDGE_TYPES:
                errs.append(f"E_INVALID_EDGE_TYPE: edge {e['id']}.type={e['type']!r} 不支持")
            for kind, nid in ((e["from_kind"], e["from_id"]), (e["to_kind"], e["to_id"])):
                try:
                    self._resolve(kind, nid)
                except DpDrivenError:
                    errs.append(f"E_EDGE_ENDPOINT_MISSING: edge {e['id']} 端点 {kind}#{nid} 不存在")
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
