# dp_driven data model

Carrier schema + derived-state contract for `zj-dp-driven`. This is the field-level
landing of the design's `[目标]`「实现时定列/类型」 (design §2, §3, §7). Source of truth
for the columns is `scripts/dp_driven_carrier.py` (`_SCHEMA`); the derivation rules live
in `scripts/dp_driven_model.py`.

> **Carrier is process state.** The `.sqlite` file is deleted at closeout (§5.2) and must
> never be referenced by a long-lived doc (§5.3). Only the scoped `.md` files it points at
> are durable. Placement: Human-specified directory, default `docs/plans/dp-driven/<topic>/`
> (ADR 0010); never `~/` / repo root / cwd (§5.4).

## Entities and stored columns

Five entities (design §2). `status` always uses the stored three-state word table below;
`被阻塞` has **no column** anywhere (§3.2).

### `meta` — carrier header

| Key | Meaning |
|---|---|
| `destination` | §4.0 bootstrap: the terminal state this DP run aims at |
| `version` | carrier schema version (string) |
| `created_at` / `updated` | timestamps |

### `task` — layer-1 node (§2)

| Column | Type | Meaning |
|---|---|---|
| `id` | INTEGER PK | auto `0,1,2…` |
| `name` | TEXT | self-explain one-line goal (must be non-empty; `E_INVALID_NAME`) |
| `context_md` | TEXT\|NULL | path to the task's scoped context md |
| `memory_md` | TEXT\|NULL | path to the task's scoped memory md |
| `created_at` | TEXT | structural creation time |

**No `status`, no `completed_at` column.** Both are derived from the 1:1 `task_plan` (§3.1, §3.3).

### `task_plan` — layer-2 region, 1:1 with task (§2, §3.1)

| Column | Type | Meaning |
|---|---|---|
| `task_id` | INTEGER PK | the 1:1 key (index = task number) |
| `status` | TEXT | **the single stored source** of the task↔plan lifecycle |
| `summary` | TEXT\|NULL | concise summary at terminal state |
| `created_at` / `completed_at` | TEXT | lifecycle timestamps |

`被阻塞` is never written here — attempting it raises `E_INVALID_STATUS`.

### `finding` — memoized subproblem node (§2, §3.4, §3.5)

| Column | Type | Meaning |
|---|---|---|
| `id` | INTEGER PK | auto `0,1,2…` |
| `status` | TEXT | stored three-state |
| `md_path` | TEXT\|NULL | scoped md holding its content + disposition record |
| `external_hold` | TEXT\|NULL | §3.2.1 off-graph blocker note (orthogonal, never status) |
| `created_at` / `completed_at` | TEXT | |

Multi-membership (a finding on many plans) is NOT a column — see `finding_membership`.

### `finding_membership` — finding ↔ task_plan, many-to-many (§3.4)

| Column | Type | Meaning |
|---|---|---|
| `finding_id` | INTEGER | |
| `task_id` | INTEGER | PK `(finding_id, task_id)` |

This table is the overlapping-subproblem landing point; disposition (§3.5) deletes a
finding's rows across **all** plans.

### `ticket` — atomic action node (§2, §3.4, §7 Q1)

| Column | Type | Meaning |
|---|---|---|
| `id` | INTEGER PK | auto `0,1,2…` |
| `status` | TEXT | stored three-state |
| `task_id` | INTEGER\|NULL | **single owner** (§3.4); `NULL` = unclaimed = in pool |
| `derived_from_finding` | INTEGER\|NULL | §7 Q1 物化 edge (1→n); set null to re-derive |
| `parent_id` | INTEGER\|NULL | ticket↔ticket parent (§2) — **never blocks** (§3.2) |
| `ref` | TEXT\|NULL | bound github/gitlab issue url or local md |
| `kv` | TEXT(JSON)\|NULL | free-form `json-string` record (§2) |
| `md_path` | TEXT\|NULL | scoped md holding详情 + 执行记录 |
| `external_hold` | TEXT\|NULL | §3.2.1 |
| `created_at` / `completed_at` | TEXT | |

### `edge` — blocks dependency among layer-2 nodes (§3.2)

| Column | Type | Meaning |
|---|---|---|
| `id` | INTEGER PK | auto |
| `type` | TEXT | `blocks` only in Phase 1 (`E_INVALID_EDGE_TYPE` otherwise) |
| `from_kind` / `from_id` | TEXT / INTEGER | **prereq** (must reach `已完成`) |
| `to_kind` / `to_id` | TEXT / INTEGER | **dependent** (blocked while prereq unfinished) |

Edge endpoints may be any `ticket`/`finding` pair — `blocks` is the cross-kind join that
makes finding→ticket and ticket→ticket dependencies and cross-plan (§3.6 F2) projection work
from a single edge table.

## Status word table (§2)

| State | Stored? | Meaning |
|---|---|---|
| `未完成` | yes | open |
| `被阻塞` | **no — derived** | unfinished prereq via `blocks` edge (§3.2) |
| `已完成` | yes | done (terminal) |
| `已放弃` | yes | abandoned (terminal) |

`STORED_STATUSES = (未完成, 已完成, 已放弃)`; `TERMINAL_STATUSES = (已完成, 已放弃)`.

## Derived state (computed on read, never stored)

- **item `blocked`** (`node_view`): a `未完成` ticket/finding is blocked iff some `blocks`
  edge points at it from a node whose stored status ≠ `已完成`. When unblocked, `blocked`
  and `blocked_reason` are **absent** (not `False`) — §3.2 forbids a `false` copy that could
  drift. `parent_id` edges never participate.
- **`shown_blocked`** (§3.2.1): `derived_blocked OR external_hold is not None`. Two orthogonal
  paths; the stored status stays `未完成` either way.
- **plan `blocked`** (§3.6 F2 商图): a non-terminal plan is blocked iff a `blocks` edge runs
  from an unfinished node **in another plan** into an open node **in this plan**. Inner
  cross-region edges are the sole truth; the outer layer stores no `blocked`.
- **task `status`** (`task_view`, §3.3): projection of the 1:1 plan —
  `已完成`⇔plan 已完成; `已放弃`⇔plan 已放弃; `被阻塞`⇔plan derived blocked; else `未完成`.
  `task.completed_at` mirrors the plan (derived).
- **pool** (§2 available pool): derived list of open, unclaimed nodes — tickets with
  `task_id IS NULL`, findings with no `finding_membership` rows. A blocked-but-unclaimed
  node is still pool input (the design's def is `status=未完成 ∧ 未被收纳`).

## Model API surface (Phase 1)

| Method | Effect |
|---|---|
| `DpDriven.init(db, destination)` / `.open(db)` | open / create carrier (§4.0) |
| `add_task(name, context_md?, memory_md?)` | task + 1:1 plan (§3.1) |
| `set_plan_status(task_id, status, summary?)` | the single lifecycle write; rejects `被阻塞` (§3.2) |
| `plan_summary(task_id, text)` | §2 终态总结 |
| `add_finding(md_path?, external_hold?)` | open finding |
| `add_finding_membership(f, task_id)` / `remove_finding_membership` / `find_memberships` | §3.4 多归属 |
| `dispose_finding(f, to∈{已完成,已放弃})` | §3.5: mark + **clear all memberships** |
| `add_ticket(...)` / `assign_ticket(t, task_id?)` / `set_ticket_status` | §2/§3.4; `assign(...,None)` = release (§4.1) |
| `add_blocks(from_kind, from_id, to_kind, to_id)` / `remove_edge` | §3.2 the only blocker |
| `set_external_hold(kind, id, reason?)` | §3.2.1 orthogonal hold |
| `node_view` / `task_view` / `plan_is_blocked` / `plan_shown_blocked` / `pool` / `is_complete` | derived reads |
| `validate()` | structural invariants (§3.1/§3.4/§5.1) |

## Error codes (model raises `DpDrivenError`, `.code` stable)

`E_INVALID_NAME`, `E_INVALID_STATUS` (illegal stored status / writing `被阻塞`),
`E_INVALID_KIND`, `E_INVALID_EDGE_TYPE`, `E_SELF_EDGE`, `E_NO_SUCH_TASK`,
`E_NO_SUCH_PLAN`, `E_NO_SUCH_FINDING`, `E_NO_SUCH_TICKET`, `E_REF_MISSING`,
`E_EDGE_ENDPOINT_MISSING`, `E_PLAN_NOT_1TO1`.

Phase-2 adds (claims / settlement / closeout):

`E_CLAIM_HELD_BY_OTHER`, `E_CLAIM_NOT_OWNER`, `E_CLAIM_REF_MISSING`, `E_CLAIM_KIND`,
`E_DUP_CLAIM`, `E_POOL_EMPTY`, `E_NOT_COMPLETE`, `E_CLOSEOUT_NOT_GOVERNED`,
`E_CLOSEOUT_MARKER_MALFORMED`, `E_CLOSEOUT_CONFIRM_REQUIRED`. CLI-side: `E_DB_MISSING`,
`E_LOCK_TIMEOUT` (from `dp_driven_lock.LockTimeout`), `E_USAGE`.

## Phase-2 / Phase-3 carrier additions

### `claim` — two-layer claim (§4.4), `dp_driven_carrier.py:108`

| Column | Type | Meaning |
|---|---|---|
| `kind` | TEXT | `plan` \| `ticket` |
| `ref_id` | INTEGER | task_id (plan) or ticket_id (ticket) |
| `agent` | TEXT | opaque claimant id (no auth in Phase 2; `__settlement__` is the reserved settlement sentinel) |
| `claimed_at` | TEXT | timestamp |

PK `(kind, ref_id)` → a plan or ticket has at most one holder. `validate` checks ref
existence and duplicate rows (`E_CLAIM_REF_MISSING` / `E_CLAIM_KIND` / `E_DUP_CLAIM`).

### claim gate + lock-free set (§4.4 [定稿])

- `set_plan_status(task_id, status, agent=None)` — if `agent` given, must hold (or nobody
  holds) the plan claim; the settlement sentinel bypasses the gate (§4.5). `agent=None` = Human direct.
- `set_ticket_status(ticket_id, status, agent=None)` — same, ticket-level.
- **Lock-free (never claim-checked):** `dispose_finding` (§3.5), `assign_ticket` (§4.3 hotplug),
  `add_blocks` / `add_finding_membership` (§3.4). A finding is a global node; adding/hot-plugging
  items into a plan is not "re-optimizing its structure".

### derivation columns — §3.5 form-②③ / §7 Q1 扩展 (Phase-3b)

`finding` 表与 `task` 表各加 `derived_from_finding INTEGER`（`dp_driven_carrier.py:73` / `:58`），
镜像 §7 Q1(a) ticket 的单父物化列：一个 finding 处置时可派生**新 finding**（形态②，写
`add_finding(derived_from_finding=…)`）或开辟**新 task**（形态③，写 `add_task(..., derived_from_finding=…)`）。
单父、1→n 天然满足；`validate` 检查源 finding 存在（否则 `E_REF_MISSING`）。optimizer `_relations`
（`dp_driven_optimize.py:64`）把这两类溯源计入内聚邻接（向后安全：旧数据不置该列 → 邻接不变）。
closeout 快照新增「Finding derivation」节。

## Out of Phase-3b scope (deferred by the design)

Claim **TTL / heartbeat** (§4.4 释放条件包含超时, §8 `[未决]`) — releases remain explicit
(`release --force` is the Human-privilege escape). Visualization (§6). Metrics collection (§9) and
optimizer weight calibration against §9 内聚命中率 ≥ 80% — both need Project B first real-run data.
These land in Phase 3c+. (Optimizer + scorer §3.6 F3/§4.2 and provenance §7 landed in 3a/3b.)
