---
name: zj-dp-driven
description: >-
  Drive a complex task as one dynamic-programming run over a partially observable,
  two-layer state graph: plan = expand states, discover = turn findings into new
  states, execute = push tickets to a terminal state, all inside a single orchestration
  loop. Process state lives in a SQLite carrier that is deleted at closeout; only the
  scoped markdown it points at is durable and handed to zj-docs-ontology. Use when the
  user asks for 动态规划驱动 / dp-driven / 状态图编排 / 任务展开回灌 / finding memoization,
  or wants a large task solved incrementally where已做的事不被重复编排.
source: zagentic

---

# zj-dp-driven — 动态规划驱动开发

> **Design baseline**: source repo `docs/designs/zj-dp-driven-skill-design.md`
> (authority-id `design.dp-driven-skill`; not shipped with the install). This `SKILL.md`
> and `references/` are the runtime-self-contained view; the design page is reviewer context only.

## Status: Phase 1 + Phase 2 + Phase 3a (optimizer)

Implemented: **carrier schema** (`scripts/dp_driven_carrier.py`), **five-entity model +
derived-state core** (`scripts/dp_driven_model.py`), **orchestration CLI** (`scripts/dp_driven_cli.py`),
**single-writer lock** (`scripts/dp_driven_lock.py`), **two-layer claim (§4.4) + settlement round
(§4.5) + two-stage closeout (§5.2)**, **greedy cohesion optimizer + scorer (§3.6 F3 / §4.2)**
(`scripts/dp_driven_optimize.py`). 105 tests in `tests/` lock every invariant.

Deferred to later phases (design `[未决]` / progressive-rollout §8): claim **TTL / heartbeat** (§4.4 —
releases stay explicit, `release --force` is the Human escape), visualization (§6), `finding→new
finding/task` provenance edges (§7 Q1), metrics collection (§9), and any re-calibration of the
optimizer's default weights against real-run data (§9).

## The model in one breath (§1–§2)

Five entities. A **task** is a layer-1 state node (粗粒度); each task has a 1:1 **task-plan**
that owns a region of the single global **layer-2 `ticket/finding` state graph**. A **finding**
is an atomic observation (memoized, may belong to many plans); a **ticket** is an atomic action
(single-owner; global-unique, its completion radiates over `blocks` edges). Process state is the
SQLite carrier; its referenced `.md` files are the durable corpus.

## Non-downgradable invariants (§3 — the 一致性根)

These are enforced by code and by failing tests; do not weaken them to make a caller happy:

1. **Single source of status (§3.1).** ticket / finding store their own status; task_plan stores
   the task↔plan lifecycle; **task status is always derived, never stored.**
2. **`被阻塞` is always derived, never a stored column (§3.2).** Only `blocks` edges block
   (parent-child does not). When nothing blocks a node, `blocked` / `blocked_reason` are **absent**,
   not `False` — a stored `false` would be a driftable copy. Writing `被阻塞` into any status
   raises `E_INVALID_STATUS`.
3. **Off-graph blockers stay orthogonal (§3.2.1).** Use a node or an `external_hold` field;
   `shown_blocked = derived_blocked ∨ external_hold ≠ null`. Never fold an external wait into `status`.
4. **Ownership (§3.4).** ticket is single-owner (`task_id` column; `NULL` = in pool); finding is
   multi-owner (`finding_membership` table). A "shared ticket" is really a shared **finding**.
5. **Finding memo (§3.5).** `已完成` = 已处置: `dispose_finding` marks the node AND removes it
   from every plan it belongs to, so it is never re-processed. Downstream分派 is orchestration.
6. **Two-layer quotient (§3.6 F2).** Outer task/plan `blocked` is the projection of inner
   cross-region `blocks` edges — the inner layer is the sole truth; nothing stores outer `blocked`.

6. **Two-layer quotient (§3.6 F2).** Outer task/plan `blocked` is the projection of inner
   cross-region `blocks` edges — the inner layer is the sole truth; nothing stores outer `blocked`.
7. **Two-layer claim (§4.4).** plan-claim guards re-optimization (`set_plan_status`); ticket-claim
   guards duplicate execution (`set_ticket_status`). `dispose_finding`, `assign_ticket` (hot-plug),
   and `add_blocks` are **lock-free** by design. Single-writer atomicity = `dp_driven_lock.acquire`
   around every CLI write; no claim TTL yet (§8 `[未决]` — use `release --force`).
8. **Settlement round (§4.5).** A special plan absorbs the whole pool, `SETTLEMENT_AGENT` sentinel
   bypasses its plan-claim gate so any agent may claim tickets inside it.
9. **Two-stage closeout (§5.2).** Export snapshot → require `.governed.json` marker → delete sqlite
   + WAL/SHM/lock sidecars only, never the `.md` corpus. Order is code-enforced (`E_NOT_COMPLETE`,
   `E_CLOSEOUT_NOT_GOVERNED`, `E_CLOSEOUT_CONFIRM_REQUIRED`).
10. **Suggestion ≠ state (§3.6 F3 / §4.2).** The optimizer's `suggest()` is a pure read over the
    graph — greedy cohesion seed-and-grow, never exhaustive, and it **never mutates or persists**
    the model. A plan-subset is recomputed each trigger; storing it would be a second source of
    truth (§3.1). Locked by `test_dp_driven_optimize.py::test_suggest_is_pure_readonly` and
    `test_suggest_deterministic`.

## Quick start (CLI)

```bash
# $SKILL_ROOT = absolute path to this SKILL.md's directory (resolved by the loading agent).
# Carrier + scoped md land in a Human-specified dir, default docs/plans/dp-driven/<topic>/
# (ADR 0010 process zone). NEVER default to ~ / repo root / cwd (§5.4).
DP="python3 $SKILL_ROOT/scripts/dp_driven_cli.py"
DB=docs/plans/dp-driven/login/dp_driven.sqlite

$DP init  "$DB" --destination "上线登录 v2"
$DP task  add "$DB" --name "后端登录流水线" --context-md docs/plans/dp-driven/login/context.md
$DP ticket add "$DB" --task 0 --ref gh#10
$DP ticket add "$DB" --task 0
$DP blocks add "$DB" --from ticket:0 --to ticket:1     # b 被阻塞 until a 已完成
$DP status "$DB" ticket:1                              # derived_blocked: true

$DP claim   "$DB" plan 0 --agent alice                 # §4.4
$DP ticket  status "$DB" 0 --set 已完成 --agent alice
$DP status  "$DB" ticket:1                             # blocked gone, nothing stored changed
$DP complete-check "$DB"

$DP suggest     "$DB"                       # §4.2 read-only: propose cohesive subset / hotplug / settle
$DP orchestrate "$DB" --agent alice         # same preview
$DP orchestrate "$DB" --agent alice --execute   # apply it (takes the single-writer lock)
```

`ticket:1` shows `derived_blocked: true` until `ticket:0` reaches `已完成`; then the next read
clears it with no stored field touched (see [data model](references/dp_driven-data-model.md)).

### Closeout (§5.2)

```bash
$DP closeout summary "$DB" --out docs/plans/dp-driven/login/process-summary.md  # 步 1
# 步 2: Human 用 zj-docs-ontology 治理该目录 md，然后写 dp_driven.governed.json
$DP closeout delete  "$DB" --force                                               # 步 3
```

See [closeout contract](references/dp_driven-closeout.md) for the marker schema and ordering gates.
Full command + exit-code table in [CLI reference](references/dp_driven-cli.md).

### Library API (optional deep use)

The CLI wraps the same `DpDriven` methods (`add_task` / `add_ticket` / `dispose_finding` /
`claim` / `settlement_run` / `closeout_*` / ...); drive them directly for bulk or programmatic
work. Every mutating call still assumes single-writer — hold `dp_driven_lock.acquire(db)` around
a load→mutate→save cycle. See `tests/test_dp_driven_model.py` for each invariant's executable spec.

## Placement & closure discipline

- **§5.3**: the `.sqlite` carrier is process fuel — no long-lived doc may reference it; it is
  deleted at closeout. Only the same-directory `.md` corpus is durable (handled by zj-docs-ontology).
- **§5.4**: the carrier directory is Human-specified; the skill writes only inside it, at current
  user privilege — no network, no credentials, never outside the directory.
- **Runtime closure**: this skill reads no file outside its own directory; `scripts/` touches only
  the carrier path it is given.
