# dp_driven optimizer (§3.6 F3 / §4.2)

The orchestration advisor: given the current available pool + in-flight plans + the
layer-2 graph topology, it recommends **one** orchestration action per trigger. Source of
truth: `scripts/dp_driven_optimize.py`; model read-helper `in_flight_plans` lives in
`scripts/dp_driven_model.py` (appended at EOF).

## What it is NOT

- **Not a solver.** §4.2 [定稿]: "从 pool 选高内聚子集" is a densest-k-subgraph variant
  (NP-hard). We use **greedy seed-and-grow**, never exhaustive search. Scores are
  *reference values for Human confirmation*, never a claimed optimum.
- **Not state.** `suggest()` is read-only — it never mutates the model and never writes the
  carrier. A suggestion is recomputed each trigger; storing it would create a second source
  of truth (violates §3.1). Locked by `test_dp_driven_optimize.py::test_suggest_is_pure_readonly`.
- **Not a replacement for agent judgement.** §4.2 [定稿]: the optimizer holds the *global*
  routing decision; §4.3 agent-side local additions are a *supplement*, never overridden but
  never mandatory either.

## Cohesion factors (4 of §8's 5 candidates)

§8 named `effort / 关联密度 / 切割面 / 解锁度 / 未标时长` as candidate factors. Phase-3a
lands four; **`effort` is dropped** because §8 never fixes its unit, and adding it would need
a new stored field that collides with §3.1. It returns only once §9 real-run data defines it.

| Factor | Definition | Weight | Direction |
|---|---|---|---|
| `density` | internal relations in S ÷ \|S\| | 1.0 | + (cohesion) |
| `cut` | relations from S to still-pool items outside S ÷ \|S\| | -0.7 | − (dangling deps) |
| `unlock` | pool items outside S, currently blocked, whose prereq ∈ S ÷ (pool−\|S\|) | 0.3 | + (positive externality) |
| `staleness` | how old the oldest item in S is, normalized | 0.5 | + (anti-long-tail, §9) |

**Relations** (§2 adjacency, direction-normalized, deduped): every `blocks` edge, every
ticket `parent_id` link, every ticket `derived_from_finding` link. A `blocks` dependency,
a parent/child split, and a finding→ticket materialization all count as "these two belong
together" for cohesion purposes.

**Determinism**: `staleness` orders the pool by `created_at` lexicographically (monotonic for
both the ISO timestamps the CLI writes and the `t0/t1/…` fixture labels). No wall-clock read.
Two calls on identical state return byte-equal steps (`test_suggest_deterministic`).

## Algorithm (seed-and-grow, §4.2 transfer)

```
1. hotplug pass (§4.3): for each in-flight plan, every unblocked pool item that is
   related to a member of that plan → Step(HOTPLUG, that plan, [item]); remove it from the
   working pool. ("高关联且无阻塞")
2. for each seed in pool (oldest→newest): greedily grow a CONNECTED subset —
     - only adjacency-linked candidates are considered;
     - add the one with the highest marginal score while marginal ≥ threshold;
     - cap at max_size.
   pick the highest-scoring grown set (ties → set containing the stalest seed).
3. one action per trigger:
     - grown set has ≥2 nodes (a connected cohesive subset exists) → Step(NEW_PLAN, items);
     - else (nothing coheres) → Step(SETTLE, remaining)  ← §4.5 hand-off.
```

Note the one-action rule: if a cohesive pair exists, the round returns *that* new plan and
leaves the rest of the pool for the next trigger — it does not both spawn a plan and settle
in a single call. This mirrors §4 "每轮产出一个 task-plan".

## Tunables

| Const | Default | Meaning |
|---|---|---|
| `COHESION_THRESHOLD_DEFAULT` | 1.0 | min marginal score to pull an adjacent item in |
| `MAX_PLAN_SIZE_DEFAULT` | 8 | largest subset a single plan absorbs |
| `HOTPLUG_MIN_GAIN` | 0.5 | reserved floor for hotplug eagerness |
| `W_DENSITY / W_CUT / W_UNLOCK / W_STALENESS` | 1.0 / -0.7 / 0.3 / 0.5 | factor weights |

These are a **starting point, not calibrated**. §9 sets 内聚命中率 ≥ 80% as the metric to
tune against once Project B produces first real-run data (Phase 3b+). Do not present the
defaults as optimal.

## CLI surface

```bash
# read-only preview (no write lock, no save)
$DP suggest     DB [--threshold F] [--max-size N]
# preview + optionally apply (apply takes the single-writer lock, §4.4)
$DP orchestrate DB --agent A [--execute] [--name T] [--threshold F] [--max-size N] \
                   [--now EPOCH] [--lease-seconds N | --no-lease]
```

`suggest` and `orchestrate` (without `--execute`) are pure reads. `orchestrate --execute`
applies the steps — `new_plan` creates a task and places items; `hotplug` uses the §4.4
lock-free `assign_ticket` / `add_finding_membership`; `settle` creates a `SETTLEMENT_AGENT`
sentinel plan (§4.5). Empty pool on either → `E_POOL_EMPTY` (exit 2), reusing the settlement
round's code rather than minting a new one.

**Lease wiring (Phase-4d-fix)**: a `new_plan` created by `execute` claims the plan for `--agent`
with a *real* lease — `epoch` (default: wall clock, `--now` to replay) stamps `last_seen_at` and
`--lease-seconds`/`--no-lease` behave exactly like `claim`. Without this, the automation loop's own
plans were the one case §8's "dead vs thinking" problem could not recover from. The `settle` step's
sentinel row keeps the same column shape as `settlement_run` (both lease fields present, `NULL`).

## Boundaries (what this module does NOT do)

- No learned / adaptive weights; no multi-scorer blending. Weights are starter values pending §9 data.
- Module-local only: TTL, §6 rendering, §7 provenance edges and §9 collection all landed in
  other modules (`dp_driven_model.py` / `dp_driven_viz*.py` / carrier columns /
  `dp_driven_metrics.py`); see design page §10 for their anchors, not this file.
