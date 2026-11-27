# dp_driven metrics (§9)

The §9 observation contract. Source of truth: `scripts/dp_driven_metrics.py`. Design
baseline: `zj-dp-driven-skill-design.md` §9 (5 metrics), §8 (exit condition), §3.1 (log ≠
state).

**This phase delivers the measurement methods, not the baselines.** §9's exit condition has
two halves: "5 metrics each have a repeatable measurement method" + "first real-run data
lands". Only the first is in scope for Phase-4c — the second needs Project B's first real
destination. Every threshold here is therefore reported as `calibrated: false`.

## Why a sidecar log at all (decision 1 = A)

Three of the five §9 metrics are **cross-round history**, not current state:

| Metric | Question it answers |
|---|---|
| 编排轮次 | how many rounds did this destination take to close out? |
| 内聚命中率 | was a plan the optimizer proposed later split/regrouped by a Human? |
| 结算轮触发率 | what share of rounds were settlement (rather than optimizer grouping)? |

The carrier (six tables) stores only "what is true right now", and invariant 10 keeps
`suggest()` from ever persisting a recommendation. So there is no place to ask "what
happened over rounds" — an append-only observation channel has to be added.

**Storage = `<db-stem>.events.jsonl`** (process zone, §5.4), *not* a new carrier table:

* Physical separation makes the §3.1 red line *testable*: `test_events_inert_to_state`
  asserts that appending arbitrary events leaves `render()` / `suggest()` byte-identical.
  If events lived inside the carrier, "derive from the log" would have a natural doorway.
* Logs are append-only by nature; JSONL is that shape, and writes already serialize under
  the existing single-writer lock (`dp_driven_lock.acquire`).
* It follows the precedent Phase-3c/4b set: `.mmd` / `.html` siblings in the same zone.
* Zero line-number drift in carrier/model, so the §10 anchor set stays valid.

Accepted costs: the process zone is multi-file (closeout must delete the log with the
carrier), and appends are non-transactional (a torn line is refused by `E_METRICS_LOG`
rather than silently skipped).

## Who writes events (decision 2 = CLI layer)

`dp_driven_model.py` stays a pure state machine. The five CLI write commands append their
own evidence **inside the lock, after `m.save()`**:

| Command | Event `type` | Payload |
|---|---|---|
| `orchestrate --execute` | `orchestrate` | `execute()`'s `applied` steps (which plans were created/extended) |
| `settlement run` | `settlement` | `{"items": n}` |
| `orchestrate --execute` with a settle step | `settlement` (extra line, W5) | `{"items": n}` |
| `task status --set 已完成\|已放弃` | `plan_terminal` | `{"status": …}` |
| `ticket assign` | `reassign` | `{"task_id": …}` |
| `finding membership add\|remove` | `membership` | `{"op": …, "task_id": …}` |
| `metrics record --type token` | `token` | `{"value": n}` (external fact) |
| `metrics annotate` | `verdict` | `{"verdict": kept\|split\|regrouped}` |

`orchestrate` **without** `--execute` (and `suggest`) log nothing — the dry-run surface
stays pure (locked by `test_dry_run_writes_no_event`). A non-terminal `task status` logs
nothing (`test_nonterminal_status_writes_no_plan_terminal`).

Library callers that bypass the CLI produce no events by design: metrics is a session
concern, and the CLI is this skill's usage surface.

## Event schema

One JSON object per line, keys sorted (`sort_keys=True`) so the log is byte-diffable:

```json
{"agent": null, "at": "2026-11-27 14:20:31", "kind": "plan", "payload": {"items": 3},
 "ref_id": 2, "type": "settlement", "value": null}
```

`EVENT_TYPES = orchestrate | settlement | plan_terminal | reassign | membership | token |
verdict`. `kind ∈ {plan, ticket, finding}`. `value` is the numeric observation channel (token
counts); `payload` is structured evidence. Unknown type/kind or a malformed line ⇒
`E_METRICS_LOG`.

## The five metrics (`report()`)

| §9 metric | key | computation | threshold |
|---|---|---|---|
| 单 effort token 消耗 | `token_per_effort` | Σ `token` events (`value`) | `null` — §9 forbids a prior |
| 编排轮次 | `orchestration_rounds` | `orchestrate` + `settlement` counts, with breakdown | `null` — §9 forbids a prior |
| 内聚命中率 | `cohesion_hit_rate` | `kept` / annotated optimizer-created plans; `unannotated_plans` listed and **excluded** from the denominator | 80% seed, `gte`, `calibrated: false` |
| 回灌正确性 | `reflow_correctness` | `reflow_check(model)` double-entry rate | 100% seed, `eq`, `calibrated: false` |
| 结算轮触发率 | `settlement_trigger_rate` | `settlement` / (`orchestrate`+`settlement`) | 10% seed, `lte`, `calibrated: false` |

With no events, values are `null` — never `0` (`test_no_events_yields_null_not_zero`): a
missing measurement must not masquerade as a score of zero.

### 内聚命中率 needs a Human verdict (decision 3)

§9's method line is literally "optimizer 产出的 plan 被 Human 标注完成时无人工拆分/重组". So
the measurement is evidence + annotation:

* evidence: which plans came from `orchestrate --execute` (`optimizer_applied_plans`);
* verdict: `metrics annotate plan <id> --verdict kept|split|regrouped`.

A pure automatic proxy (treating every `reassign`/`membership remove` as a split) was
rejected: during normal execution a *newly discovered* finding legitimately joins a plan,
so the automatic signal would count legitimate work as regrouping and poison the metric.
The un-annotated set is reported explicitly rather than silently counted either way.

### 回灌正确性 = double-entry audit (decision 4)

The original §9 formula counted "recomputations of `blocked` after a ticket reaches terminal".
Under this implementation that is vacuous: `blocked` is never cached, it is derived on every
`node_view` call (§3.2), so there is no recompute count to observe. The equivalent testable
form is **double-entry bookkeeping**:

`reflow_check(model)` independently re-derives §3.2's item-level rule straight from the edge
set — `blocked ⇔ node open ∧ ∃ blocks in-edge whose prereq status ≠ 已完成` — and compares
against `node_view`'s `blocked` / `shown_blocked`. Any disagreement is a violation.

* Scope is **item-level (§3.2)** only. Plan-level §3.6 F2 quotient blocking is covered by
  its existing lock tests; re-implementing `plan_is_blocked` a second time inside the audit
  would risk false positives from divergent edge-case handling rather than catching bugs.
* The audit is non-vacuous: `test_reflow_detects_stale_derivation_canary` feeds a model
  subclass whose `node_view` deliberately inverts the flag, and asserts it is caught.
* `test_reflow_tracks_derivation_as_prereq_completes` covers the real transition: complete
  the prereq, dependent flips blocked→free, `blocked` key **absent** (not `false`), audit
  still clean.
* CLI: `metrics reflow-check DB` emits the JSON audit, then raises `E_REFLOW_STALE` (exit 2)
  when violations exist — so it is usable as a pre-commit / pre-closeout gate.

## Report surfaces

* `metrics report DB` — JSON to stdout, read-only (no lock, no write). Deterministic:
  sorted iteration, no wall clock.
* `metrics report DB --out <stem>.metrics.md` — markdown table for the §5.2 governance
  corpus (**decision 5: separate file**, so `closeout_export_summary` keeps its §10 anchors
  and the metrics section stays independently regenerable). Written only to the given path.
* The md always prints the `calibration: uncalibrated` line plus a `Calibrated` column, so a
  reader cannot mistake a seed target for an achieved baseline.

## Lifecycle (§5.2 / §5.4)

The log lives in the process zone beside the carrier: not durable, not git-tracked, deleted
with the carrier at closeout step 3 (after step 1 has exported the numbers into the md
corpus). Metrics are therefore "process becomes fuel": the *observations* survive as text,
the raw event log does not.

## Error codes

| Code | Meaning |
|---|---|
| `E_METRICS_LOG` | unknown event type/kind, or a malformed line in the sidecar log |
| `E_REFLOW_STALE` | `reflow-check` found derived-view disagreement (exit 2) |
| `E_NO_SUCH_TASK` | `metrics annotate` on a plan that does not exist |
