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

## Status: Phase 1 + 2 + 3a + 3b + 3c + 4a + 4b + 4c + 4d-fix + W5 (carrier→model→CLI/claim/settlement/closeout→optimizer→derivation→viz→claim TTL→R7 HTML viewer→§9 metrics→lease-clock wiring→single settlement implementation)

Implemented: **carrier schema** (`scripts/dp_driven_carrier.py`), **five-entity model +
derived-state core** (`scripts/dp_driven_model.py`), **orchestration CLI** (`scripts/dp_driven_cli.py`),
**single-writer lock** (`scripts/dp_driven_lock.py`), **two-layer claim (§4.4) + settlement round
(§4.5) + two-stage closeout (§5.2)**, **greedy cohesion optimizer + scorer (§3.6 F3 / §4.2)**
(`scripts/dp_driven_optimize.py`), **§3.5 form-②③ derivation columns** (`finding/task.derived_from_finding`),
**§6 Mermaid visualization** (`scripts/dp_driven_viz.py`, read-only) + **§6 R7 interactive HTML card**
(`scripts/dp_driven_viz_html.py`), **§4.4 claim TTL / heartbeat lease**
(`claim/renew`, derived `expired`) — with the lease clock injected on **every** CLI path that
consults it (`claim/renew/claims list`, both `status` writers, `orchestrate --execute`, `viz`),
**§9 metrics collection** (`scripts/dp_driven_metrics.py`:
sidecar event log + `report` / `reflow-check` double-entry audit). 240 tests in `tests/` lock
every invariant.

Deferred to later phases (design `[未决]` / progressive-rollout §8): **calibration only** — the §9
thresholds need Project B's first real-run data (token / round counts explicitly have no prior),
which also feeds re-calibration of the optimizer's default weights and the claim lease default.

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
    from every plan it belongs to, so it is never re-processed. Disposition may materialize downstream
    tickets (form-① `ticket.derived_from_finding`), new findings (form-② `finding.derived_from_finding`),
    or new tasks (form-③ `task.derived_from_finding`) — all single-parent provenance columns (§7 Q1).
6. **Two-layer quotient (§3.6 F2).** Outer task/plan `blocked` is the projection of inner
   cross-region `blocks` edges — the inner layer is the sole truth; nothing stores outer `blocked`.

6. **Two-layer quotient (§3.6 F2).** Outer task/plan `blocked` is the projection of inner
   cross-region `blocks` edges — the inner layer is the sole truth; nothing stores outer `blocked`.
7. **Two-layer claim + lease (§4.4).** plan-claim guards re-optimization (`set_plan_status`); ticket-claim
   guards duplicate execution (`set_ticket_status`). `dispose_finding`, `assign_ticket` (hot-plug),
   and `add_blocks` are **lock-free** by design. Single-writer atomicity = `dp_driven_lock.acquire`
   around every CLI write. **TTL is heartbeat/lease**: `claim` stores `last_seen_at`(epoch) +
   `lease_seconds`; `expired` is **derived at read** (`_is_expired`), never a stored field (§3.1/§3.2
   anti-drift); **lease/expiry evaluation never reads the wall clock** — callers inject `epoch`.
   (Scope note: the model does call `_now()` to write `created_at`/`completed_at`/`claimed_at`
   *text*, but no decision ever derives from it.) The CLI owns the clock and wires it into every
   lease-aware path: `claim`, `renew`, `claims list`, both `status` writers, `orchestrate
   --execute` and `viz` — so an expired claim is inert on the real write path, not only in the
   library. `renew` is the heartbeat; `--no-lease` pins a claim (never expires).
8. **Settlement round (§4.5).** A special plan absorbs the whole pool, `SETTLEMENT_AGENT` sentinel
   bypasses its plan-claim gate so any agent may claim tickets inside it. One implementation only:
   `settlement_run` — the `settlement run` command and the optimizer's `settle` step are two entry
   points into it, so `Step.items` is a preview and the live pool decides (§4.5 实现唯一性).
9. **Two-stage closeout (§5.2).** Export snapshot → require `.governed.json` marker → delete sqlite
   + WAL/SHM/lock sidecars only, never the `.md` corpus. Order is code-enforced (`E_NOT_COMPLETE`,
   `E_CLOSEOUT_NOT_GOVERNED`, `E_CLOSEOUT_CONFIRM_REQUIRED`).
 10. **Suggestion / view ≠ state (§3.6 F3 / §4.2 / §6).** The optimizer's `suggest()` and the §6
     renderer are pure reads over the graph — greedy cohesion seed-and-grow (never exhaustive) and
     deterministic Mermaid text; both **never mutate or persist** the model. A plan-subset or a view is
     recomputed each call; storing it would be a second source of truth (§3.1). The R7 HTML/IR snapshot
     likewise never writes back — freshness = re-run `viz`. Locked by
      `test_dp_driven_optimize.py::test_suggest_is_pure_readonly`, `test_dp_driven_viz.py::
      test_render_is_pure_readonly`, and `test_dp_driven_viz_html.py::test_render_html_is_pure_readonly`.
 11. **Observation log ≠ state (§3.1 / §9).** The §9 metrics channel is an append-only sidecar
     (`<db-stem>.events.jsonl`) written by the **CLI layer only** — the model stays a pure state
     machine. No derivation (`node_view` / `task_view` / `pool` / `is_complete` / `render` /
     `suggest`) may read it: an observation history must never become a second source of truth,
     and its absence must never change the graph. Locked by `test_dp_driven_metrics.py::
     test_events_inert_to_state`; dry runs log nothing (`test_dry_run_writes_no_event`).


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

$DP claim   "$DB" plan 0 --agent alice                 # §4.4 (grants a 300s lease by default)
$DP renew   "$DB" plan 0 --agent alice                 # §4.4 TTL heartbeat (extends last_seen_at)
$DP ticket  status "$DB" 0 --set 已完成 --agent alice   # gate reads the lease clock
$DP ticket  status "$DB" 0 --set 已完成 --agent bob --now 1700000000   # expired lease ⇒ bob may write
$DP status  "$DB" ticket:1                             # blocked gone, nothing stored changed
$DP complete-check "$DB"

$DP suggest     "$DB"                       # §4.2 read-only: propose cohesive subset / hotplug / settle
$DP orchestrate "$DB" --agent alice         # same preview
$DP orchestrate "$DB" --agent alice --execute   # apply it; the new plan's claim carries a real lease (§4.4)

$DP viz "$DB"                                # §6 read-only Mermaid to stdout
$DP viz "$DB" --out docs/plans/dp-driven/login/dp_driven.mmd   # process-zone .mmd (not durable, not git)
$DP viz "$DB" --format html --out docs/plans/dp-driven/login/dp_driven.html   # §6 R7 click→card viewer

$DP metrics record "$DB" --type token --value 1234 --agent alice   # §9-1 external fact input
$DP metrics annotate "$DB" plan 1 --verdict kept                    # §9-3 Human verdict on an optimizer plan
$DP metrics report "$DB"                       # §9 read-only: 5 metrics, all flagged calibrated:false
$DP metrics reflow-check "$DB"                 # §9-4 double-entry audit; violations → exit 2
```

`orchestrate --execute` / `settlement run` / `task status`(terminal) / `ticket assign` /
`finding membership add|remove` append one line each to `$DB.events.jsonl` (process zone, §9);
previews log nothing. See [metrics reference](references/dp_driven-metrics.md).

`ticket:1` shows `derived_blocked: true` until `ticket:0` reaches `已完成`; then the next read
clears it with no stored field touched (see [data model](references/dp_driven-data-model.md)).

### Closeout (§5.2)

```bash
$DP closeout summary "$DB" --out docs/plans/dp-driven/login/process-summary.md  # 步 1
$DP metrics report    "$DB" --out docs/plans/dp-driven/login/metrics.md         # 步 1b (§9 numbers into the corpus)
# 步 2: Human 用 zj-docs-ontology 治理该目录 md，然后写 dp_driven.governed.json
$DP closeout delete  "$DB" --force                                               # 步 3 (also removes the event log + the consumed marker)
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
  deleted at closeout, together with its process-zone siblings (`.lock`, `.events.jsonl`, and the
  regenerable `.mmd` / `.html` views). Only the same-directory `.md` corpus is durable (handled by
  zj-docs-ontology).
- **§5.4**: the carrier directory is Human-specified; the skill writes only inside it, at current
  user privilege — no network, no credentials, never outside the directory.
- **Runtime closure**: this skill reads no file outside its own directory; `scripts/` touches only
  the carrier path it is given.
