# dp_driven claim TTL (§4.4 heartbeat / lease)

Lease-based claim expiry for `zj-dp-driven`. Design baseline:
`zj-dp-driven-skill-design.md` §4.4 (claim release condition "超时释放") + §8 (strategy was
`[未决]`: "heartbeat？固定 TTL？"). Phase-4a fixes the strategy as **heartbeat / lease**.
Source of truth: `scripts/dp_driven_model.py` (`claim / renew / claim_owner / list_claims /
_require_claim_free_or_mine / _is_expired`).

## Why heartbeat (not a fixed TTL)

The problem §4.4/§8 pose is "distinguish a dead agent from one that is *still thinking*".
A fixed absolute TTL can't: a legitimate long orchestration step would be evicted mid-thought.
A **lease** decouples liveness from duration — a working agent renews, a crashed one goes
silent and its claim lapses. So:

- `claim` / `renew` stamp `last_seen_at = epoch` and record `lease_seconds`.
- A claim is `expired` when `epoch - last_seen_at > lease_seconds`.
- An expired claim is **inert**: `claim_owner` returns None, the claim gate treats it free,
  and another agent may `claim` (take over) without `E_CLAIM_HELD_BY_OTHER`.

## The two rules that make this safe (§3.1 / §3.2 anti-drift)

1. **`expired` is derived, never stored.** The `claim` table stores only `last_seen_at` and
   `lease_seconds` (facts). "expired" is computed at read by `_is_expired`. Storing an
   `expired` boolean would be a second source of truth that silently rots between writes — the
   exact failure §3.2's derived-`blocked` rule was created to kill. Locked by
   `test_dp_driven_ttl.py::test_expired_still_derived_not_stored` and
   `test_list_claims_expired_is_computed_not_stored`.

2. **Lease/expiry evaluation never reads the wall clock.** Every TTL-aware method takes an
   explicit `epoch: int` (seconds). With `epoch is None`, expiry is *not evaluated* — this preserves
   the older "explicit release only" behavior for callers (and the whole pre-4a test suite) that
   don't drive a clock, and keeps model behavior deterministic/replayable. Scope: the model *does*
   call `_now()` to write `created_at`/`completed_at`/`claimed_at` **text**, but no decision derives
   from it. Only the CLI calls `int(time.time())` (`_epoch`), and `--now EPOCH` overrides it for
   tests. The CLI injects that clock into every lease-aware path — `claim`, `renew`, `claims list`,
   `task status`, `ticket status`, `orchestrate --execute`, `viz` — so expiry is real on the write
   path, not only in the library. Locked by
   `test_dp_driven_ttl.py::test_epoch_none_never_evaluates_expiry` and
   `test_no_wall_clock_determinism`; the CLI wiring by
   `test_dp_driven_wiring.py::StatusGate` / `OrchestrateLease` / `VizClock`.

## Lease values

| Const | Default | Meaning |
|---|---|---|
| `DEFAULT_CLAIM_LEASE_SECONDS` | 300 | lease granted when `claim` is called without `--no-lease` |
| `NO_LEASE` | `None` | `--no-lease` ⇒ never expires (single-operator debug; equals pre-4a) |

The 300s default is a **starting value, not calibrated** — same stance as the optimizer's
default weights (design §1 "少 token、不追求严谨"; §9 内聚命中率-style real-run data would set
the right number later).

## CLI

```bash
# acquire with a lease (real clock), or explicit --now for tests, or --no-lease to pin it
$DP claim  DB plan 0 --agent alice [--lease-seconds 300 | --no-lease] [--now EPOCH]
# heartbeat: holder pushes last_seen_at forward; expired or non-holder ⇒ no-op / reject
$DP renew  DB plan 0 --agent alice [--now EPOCH]
$DP claims list DB [--now EPOCH]      # each row carries a computed `expired`
$DP release DB plan 0 [--agent alice | --force]
```

A claim whose holder crashed is simply not renewed; once `now - last_seen_at > lease_seconds`
the next agent's `claim` takes over (audit of the prior holder is intentionally not kept —
thin process table, §4.4).

## Interaction with the rest of §4.4

- The **claim gate** (`_require_claim_free_or_mine`, used by `set_plan_status` /
  `set_ticket_status`) treats an expired claim as free when given an `epoch`; so a stale claim
  never wedges a plan, while a live one still blocks other agents.
- **Lock-free ops** (`dispose_finding` / `assign_ticket` / `add_blocks`) remain unaffected by
  leases — they never consult the claim gate at all (§4.4 lock-free set).
- The **settlement sentinel** claim uses `lease_seconds=None` (never expires) — it marks a
  plan-kind, not a live holder.

## Deferred

Heartbeat cadence is agent-chosen (the model only extends on `renew`); no automatic
background renewal, no daemon. A future §9 metric "claim takeover rate" could inform the
default lease length once real multi-agent usage exists.
