"""zj-dp-driven optimizer (§3.6 F3 / §4.2) — cohesion scorer + orchestration advisor.

Design status: F3 was `[未决]` ("V = 编排 optimizer 评估候选子集的内聚得分；具体算分因子与
触发时机随实现期定，§8"). Phase-3a lands a **reference** implementation:

* **Not a solver.** §4.2 [定稿]: densest-k-subgraph is NP-hard → we use **greedy
  seed-and-grow**, never exhaustive search. Scores are reference values for Human
  confirmation, not an optimum.
* **Read-only.** `suggest()` must NOT mutate the model or write the carrier — the
  suggestion is not state (§3.1 single-source-of-truth). `test_dp_driven_optimize.py::
  test_suggest_is_pure_readonly` locks this.
* **Advisory routing.** §4.2 [定稿] optimizer has the routing decision (hotplug vs new-plan
  vs settle); §4.3 agent-side local additions are a *supplement*, not a replacement.

Scoring: 4 of the 5 §8 candidate factors — `density`, `cut`, `unlock`, `staleness`.
`effort` is **deliberately dropped**: §8 never defines its unit, and adopting it would
require a new stored field, colliding with §3.1. Revisit only once §9 real-run data exists.

Determinism: every factor is a pure function of `model.data` plus `created_at` ordering
(lexicographic — monotonic for both the ISO timestamps the CLI writes and the short
`t0/t1/...` fixture labels), so two calls on identical state return byte-equal steps.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dp_driven_model import (
    CLAIM_PLAN, DEFAULT_CLAIM_LEASE_SECONDS, DpDriven, DpDrivenError,
    EDGE_BLOCKS, KIND_FINDING, KIND_TASK, KIND_TICKET, S_DONE, S_OPEN,
)

# ── tunable constants (起手值，可解释，非最优) ──────────────
COHESION_THRESHOLD_DEFAULT = 1.0   # new-plan / grow step must exceed this
HOTPLUG_MIN_GAIN = 0.5             # §4.3 hotplug into an in-flight plan
MAX_PLAN_SIZE_DEFAULT = 8
W_DENSITY = 1.0
W_CUT = -0.7
W_UNLOCK = 0.3
W_STALENESS = 0.5

ACT_NEW_PLAN = "new_plan"
ACT_HOTPLUG = "hotplug"
ACT_SETTLE = "settle"

Node = tuple[str, int]


@dataclass
class CohesionScore:
    total: float
    factors: dict[str, float] = field(default_factory=dict)


@dataclass
class Step:
    action: str                 # ACT_NEW_PLAN | ACT_HOTPLUG | ACT_SETTLE
    task_id: int | None         # set for ACT_HOTPLUG (existing plan); None otherwise
    items: list[Node]           # [(kind, id), ...] in placement order
    score: CohesionScore | None
    rationale: str


def _relations(model: DpDriven) -> set[frozenset]:
    """Undirected adjacency over the three §2 edge-ish relations: blocks / parent /
    derived-from. Normalized via frozenset so the same pair reached from either endpoint
    counts exactly once (direction-independent density/cut)."""
    rels: set[frozenset] = set()

    def add(a: Node, b: Node) -> None:
        if a != b:
            rels.add(frozenset((a, b)))

    for e in model.data["edges"]:
        if e["type"] == EDGE_BLOCKS:
            add((e["from_kind"], e["from_id"]), (e["to_kind"], e["to_id"]))
    for t in model.data["tickets"].values():
        if t.get("parent_id") is not None:
            add((KIND_TICKET, t["id"]), (KIND_TICKET, t["parent_id"]))
        if t.get("derived_from_finding") is not None:
            add((KIND_TICKET, t["id"]), (KIND_FINDING, t["derived_from_finding"]))
    # §3.5 form-②③ provenance (Phase-3b): finding→new-finding and finding→new-task
    # are related work; include them as cohesion adjacency. Backward-safe: existing
    # fixtures never set these, so prior inputs yield identical relations.
    for f in model.data["findings"].values():
        if f.get("derived_from_finding") is not None:
            add((KIND_FINDING, f["id"]), (KIND_FINDING, f["derived_from_finding"]))
    for t in model.data["tasks"].values():
        if t.get("derived_from_finding") is not None:
            add((KIND_TASK, t["id"]), (KIND_FINDING, t["derived_from_finding"]))
    return rels


def _stale_order(model: DpDriven) -> list[Node]:
    """Pool nodes ordered oldest→newest by (created_at, kind, id). created_at is
    lexicographically monotonic for ISO timestamps and fixture labels alike."""
    items = [(it["kind"], it["id"]) for it in model.pool()]
    created = {}
    for kind, nid in items:
        node = model._resolve(kind, nid)
        created[(kind, nid)] = node.get("created_at") or ""
    return sorted(items, key=lambda k: (created[k], k[0], k[1]))


def _blocked_nodes(model: DpDriven) -> set[Node]:
    blocked = set()
    for it in model.pool():
        if model.node_view(it["kind"], it["id"])["derived_blocked"]:
            blocked.add((it["kind"], it["id"]))
    return blocked


def score_subset(model: DpDriven, S: frozenset, rels: set[frozenset],
                 pool: set[Node], blocked: set[Node]) -> CohesionScore:
    """Pure scoring of candidate subset S. `pool` = full available-pool set (for cut/unlock
    denominators & out-of-pool exclusion), `blocked` = currently derived-blocked pool nodes."""
    n = len(S)
    if n == 0:
        return CohesionScore(0.0, {})

    # density: internal relations / |S|
    internal = sum(1 for r in rels if r <= S)
    density = internal / n

    # cut: relations from S to items STILL in the pool but not in S. Connections leaving
    # the pool (done / already-placed) are excluded — those are satisfied dependencies,
    # not a "cut" that strands work.
    cut_edges = 0
    for r in rels:
        a, b = tuple(r)
        in_a, in_b = a in S, b in S
        if in_a != in_b:
            other = b if in_a else a
            if other in pool and other not in S:
                cut_edges += 1
    cut = cut_edges / n

    # unlock: pool nodes outside S that are blocked and have >=1 blocker in S
    unlocked = 0
    for x in pool - S:
        if x not in blocked:
            continue
        if any((frozenset((x, s)) in rels) and _is_prereq(model, s, x) for s in S):
            unlocked += 1
    denom = max(1, len(pool) - n)
    unlock = unlocked / denom

    # staleness: reward sets containing the OLDEST pool items. `_stale_order` is
    # oldest→newest, so the oldest present has the *smallest* index; invert so an
    # old item scores near 1.0 and a brand-new one near 0.
    order = _stale_order(model)
    rank = {node: i for i, node in enumerate(order)}
    last = max(len(order) - 1, 0)
    oldest_idx = min((rank[s] for s in S if s in rank), default=0)
    staleness = ((last - oldest_idx) / last) if last else 1.0

    total = (W_DENSITY * density + W_CUT * cut
             + W_UNLOCK * unlock + W_STALENESS * staleness)
    return CohesionScore(
        round(total, 6),
        {
            "density": round(density, 6),
            "cut": round(cut, 6),
            "unlock": round(unlock, 6),
            "staleness": round(staleness, 6),
        },
    )


def _is_prereq(model: DpDriven, pre: Node, dep: Node) -> bool:
    """True iff a `blocks` edge pre→dep exists (pre is the unmet prerequisite of dep)."""
    for e in model.data["edges"]:
        if (e["type"] == EDGE_BLOCKS
                and (e["from_kind"], e["from_id"]) == pre
                and (e["to_kind"], e["to_id"]) == dep):
            return True
    return False


def _grow(model, seed, remaining, rels, pool, blocked, threshold, max_size):
    """Seed-and-grow over CONNECTED items only (§4.2 cohesion = connectivity): a candidate
    must be adjacent to the current set, then is added while its marginal score ≥ threshold.
    Never exhaustive (densest-k-subgraph is NP-hard per §4.2 [定稿])."""
    S = {seed}
    current = score_subset(model, frozenset(S), rels, pool, blocked).total
    while len(S) < max_size:
        best, best_delta = None, None
        for x in sorted(remaining - S, key=lambda k: (k[0], k[1])):
            if not any(frozenset((x, s)) in rels for s in S):   # adjacency required
                continue
            trial = frozenset(S | {x})
            delta = score_subset(model, trial, rels, pool, blocked).total - current
            if best_delta is None or delta > best_delta:
                best, best_delta = x, delta
        if best is None or best_delta < threshold:
            break
        S.add(best)
        current += best_delta
    return frozenset(S), current


def suggest(model: DpDriven, *, threshold: float = COHESION_THRESHOLD_DEFAULT,
            max_size: int = MAX_PLAN_SIZE_DEFAULT) -> list[Step]:
    """Read-only orchestration advisor for one trigger (§4.2). Returns steps in
    application order: hotplugs first (fit existing plans), then ONE new-plan OR
    ONE settle for what remains. Never mutates `model`."""
    pool_nodes = [(it["kind"], it["id"]) for it in model.pool()]
    if not pool_nodes:
        raise DpDrivenError("E_POOL_EMPTY", "pool 为空，无可编排 items")

    pool = set(pool_nodes)
    rels = _relations(model)
    blocked = _blocked_nodes(model)
    steps: list[Step] = []
    remaining = set(pool)

    # 1) §4.3 hotplug pass — items linked to an in-flight plan and not blocked.
    #    "高关联且无阻塞" per §4.3; optimizer's global routing (§4.2 [定稿]).
    inflight = model.in_flight_plans()
    for tid in inflight:
        members = model._plan_inner_nodes(tid)
        for x in sorted(remaining, key=lambda k: (k[0], k[1])):
            if x in blocked:
                continue
            linked = any(frozenset((x, m)) in rels for m in members)
            if not linked:
                continue
            plan_gain = _plan_marginal(model, tid, x, rels, pool, blocked)
            steps.append(Step(ACT_HOTPLUG, tid, [x],
                              CohesionScore(round(plan_gain, 6), {"marginal": round(plan_gain, 6)}),
                              f"hotplug {x} → in-flight plan {tid}（关联且无阻塞）"))
            remaining.discard(x)

    # 2) §4.2 new-plan via best cohesive subset (seed-and-grow), else §4.5 settle.
    if remaining:
        order = [s for s in _stale_order(model) if s in remaining]
        best_set: frozenset | None = None
        best_score = None
        for seed in order:
            grown, sc = _grow(model, seed, remaining, rels, pool, blocked, threshold, max_size)
            if (best_score is None or sc > best_score
                    or (sc == best_score and best_set is not None
                        and min(grown) < min(best_set))):
                best_set, best_score = grown, sc
        # Cohesion = a connected subset of ≥2 exists (threshold governs growth eagerness,
        # not plan feasibility — §4.2 "凑不出高内聚子集" == no adjacency-linked set forms).
        feasible = best_set is not None and len(best_set) >= 2
        if feasible:
            steps.append(Step(ACT_NEW_PLAN, None, sorted(best_set, key=lambda k: (k[0], k[1])),
                              CohesionScore(round(best_score, 6), {}),
                              f"新建 plan，收纳高内聚子集 {sorted(best_set)}"))
        else:
            # §4.5 no cohesive subset → settle the remainder (main-line topological order)
            settle_items = _settle_order(model, remaining)
            steps.append(Step(ACT_SETTLE, None, settle_items, None,
                              "无满足内聚阈值的子集 → 结算轮收纳剩余 items"))
    return steps


def _plan_marginal(model, tid, x, rels, pool, blocked) -> float:
    members = model._plan_inner_nodes(tid)
    if not members:
        return 0.0
    base = score_subset(model, frozenset(members), rels, pool, blocked).total
    withx = score_subset(model, frozenset(members | {x}), rels, pool, blocked).total
    return withx - base


def _settle_order(model, remaining):
    """Delegate to the model's deterministic topological pool order (§4.5)."""
    items = [{"kind": k, "id": i} for (k, i) in remaining]
    ordered = model._topo_order_pool(items)
    return [(o["kind"], o["id"]) for o in ordered]


def execute(model: DpDriven, steps: list[Step], agent: str | None = None,
           name: str | None = None, now: str | None = None,
           epoch: int | None = None,
           lease_seconds: int | None = DEFAULT_CLAIM_LEASE_SECONDS) -> list[dict]:
    """Apply suggested steps (called only from CLI `--execute`, inside the write lock).
    new_plan → add_task + place items; hotplug → assign/add-membership (lock-free §4.4);
    settle → delegates to model.settlement_run (§4.5's ONE implementation: the live pool owns
    what is absorbed, in which order, and which claim row is written). Returns applied summary.
    `epoch`/`lease_seconds` (§4.4, Phase-4d): the plan-level claim minted for a new plan
    carries a real lease clock, so an agent that dies mid-plan no longer holds the plan
    forever — the claim goes inert at expiry and any agent may take it over."""
    applied: list[dict] = []
    for st in steps:
        if st.action == ACT_NEW_PLAN:
            tid = model.add_task(name or "编排计划", now=now)
            if agent:
                model.claim(CLAIM_PLAN, tid, agent, now=now, epoch=epoch,
                            lease_seconds=lease_seconds)
            for kind, nid in _placement_order(model, st.items):
                if kind == KIND_TICKET:
                    model.assign_ticket(nid, tid)
                else:
                    model.add_finding_membership(nid, tid)
            applied.append({"action": st.action, "task_id": tid,
                            "items": [list(i) for i in st.items]})
        elif st.action == ACT_HOTPLUG:
            kind, nid = st.items[0]
            if kind == KIND_TICKET:
                model.assign_ticket(nid, st.task_id)      # §4.4 lock-free
            else:
                model.add_finding_membership(nid, st.task_id)
            applied.append({"action": st.action, "task_id": st.task_id,
                            "items": [[kind, nid]]})
        elif st.action == ACT_SETTLE:
            # §4.5: one implementation only. `settlement_run` takes the LIVE pool — which at
            # this point equals `st.items`, because suggest() emits at most one of new_plan/settle
            # and every hotplug step has already been applied above (locked by
            # test_dp_driven_wiring.SettleDelegation.test_settle_step_items_equal_live_pool).
            # It also owns the topological order and the SETTLEMENT_AGENT sentinel row, and raises
            # E_POOL_EMPTY rather than minting an empty settlement plan.
            tid, absorbed = model.settlement_run(name=name, now=now)
            applied.append({"action": st.action, "task_id": tid,
                            "items": [[it["kind"], it["id"]] for it in absorbed]})
    return applied


def _placement_order(model, items):
    nodes = set(items)
    plain = [{"kind": k, "id": i} for (k, i) in items]
    ordered = model._topo_order_pool(plain)
    return [(o["kind"], o["id"]) for o in ordered]
