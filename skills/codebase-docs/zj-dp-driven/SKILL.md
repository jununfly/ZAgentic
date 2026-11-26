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

## Status: Phase 1 — foundation only

Implemented now: the **carrier schema** (`scripts/dp_driven_carrier.py`) and the **five-entity
model + derived-state core** (`scripts/dp_driven_model.py`), locked by `tests/`.

Deferred to later phases (per the design's §8 渐进策略 and `[未决]` items): the orchestration
CLI, the optimizer + scorer (§4.2 / §3.6 F3), two-layer claim/lock (§4.4), settlement round
(§4.5), visualization (§6), and two-stage closeout (§5.2). Until the CLI lands, drive the
foundation through the documented `DpDriven` API (see [data model](references/dp_driven-data-model.md)).

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

## Quick start (library, Phase 1)

```bash
# $SKILL_ROOT = absolute path to this SKILL.md's directory (resolved by the loading agent).
# Carrier + scoped md land in a Human-specified dir, default docs/plans/dp-driven/<topic>/
# (ADR 0010 process zone). NEVER default to ~ / repo root / cwd (§5.4).
PYTHONPATH="$SKILL_ROOT/scripts" python3 - <<'PY'
from dp_driven_model import DpDriven, KIND_TICKET, KIND_FINDING

run = DpDriven.init("docs/plans/dp-driven/login/dp_driven.sqlite", destination="上线登录 v2")
t1 = run.add_task("后端登录流水线", context_md="docs/plans/dp-driven/login/context.md")
a  = run.add_ticket(task_id=t1, ref="gh#10")
b  = run.add_ticket(task_id=t1)
run.add_blocks(KIND_TICKET, a, KIND_TICKET, b)   # b 被阻塞 until a 已完成
run.save()
print(run.task_view(t1))                          # status derived, never stored
PY
```

`b` shows `derived_blocked: true` until `a` reaches `已完成`; then the very next read clears it
with no stored field touched. See `tests/test_dp_driven_model.py` for each invariant's executable spec.

## Placement & closure discipline

- **§5.3**: the `.sqlite` carrier is process fuel — no long-lived doc may reference it; it is
  deleted at closeout. Only the same-directory `.md` corpus is durable (handled by zj-docs-ontology).
- **§5.4**: the carrier directory is Human-specified; the skill writes only inside it, at current
  user privilege — no network, no credentials, never outside the directory.
- **Runtime closure**: this skill reads no file outside its own directory; `scripts/` touches only
  the carrier path it is given.
