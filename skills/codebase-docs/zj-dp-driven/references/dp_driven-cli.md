# dp_driven CLI

Command surface for the `zj-dp-driven` carrier. Design baseline: `zj-dp-driven-skill-design.md` §4.
Source of truth: `scripts/dp_driven_cli.py`; every mutating subcommand runs inside
`scripts/dp_driven_lock.py` (single-writer, §4.4 [定稿]).

## Invocation

```bash
# $SKILL_ROOT = absolute path to this SKILL.md's directory (resolved by the loading agent).
# Carrier lives in a Human-specified dir, default `docs/plans/dp-driven/<topic>/` (ADR 0010, §5.4).
PYTHONPATH="$SKILL_ROOT/scripts" python3 "$SKILL_ROOT/scripts/dp_driven_cli.py" \
    <subcommand> <db-path> [flags]
```

## Subcommands

| Command | Design anchor | Model method |
|---|---|---|
| `init DB --destination TEXT` | §4.0 step 1 | `dp_driven_model.py:87` `DpDriven.init` |
| `task add DB --name TEXT [--context-md P] [--memory-md P]` | §4.0 step 2 | `:114` `add_task` |
| `task status DB <id> --set {未完成\|已完成\|已放弃} [--agent A] [--summary S]` | §3.1 / §4.4 gate | `:132` `set_plan_status` |
| `task summary DB <id> --text TEXT` | §2 终态总结 | `:158` `plan_summary` |
| `task view DB <id>` | §3.3 派生投影 | `:344` `task_view` |
| `finding add DB [--md-path P] [--external-hold R]` | §2 / §3.5 | `:167` `add_finding` |
| `finding dispose DB <id> --to {已完成\|已放弃}` | §3.5 处置 | `:193` `dispose_finding` |
| `finding membership add DB <fid> --task <tid>` | §3.4 多归属 | `:176` `add_finding_membership` |
| `finding membership remove DB <fid> --task <tid>` | §3.4 | `:184` `remove_finding_membership` |
| `ticket add DB [--task T] [--ref R] [--kv JSON] [--md-path P] [--derived-from-finding F] [--parent T] [--external-hold R]` | §2 / §3.4 / §7 Q1 | `:209` `add_ticket` |
| `ticket assign DB <id> --task <tid\|NULL>` | §4.3 热插 (§4.4 lock-free) | `:230` `assign_ticket` |
| `ticket status DB <id> --set {…} [--agent A]` | §4.4 ticket-claim gate | `:238` `set_ticket_status` |
| `blocks add DB --from KIND:ID --to KIND:ID` | §3.2 blocks edge | `:254` `add_blocks` |
| `edge remove DB <edge-id>` | §3.2 | `:268` `remove_edge` |
| `hold DB KIND:ID [--reason TEXT]` | §3.2.1 | `:273` `set_external_hold` |
| `status DB KIND:ID` | §3.2 派生读取 | `:300` `node_view` |
| `pool DB` | §2 available pool | `:363` `pool` |
| `validate DB` | §3 invariants | `:565` `validate` |
| `complete-check DB` | §5.1 完成判据 | `:377` `is_complete` |
| `claim DB {plan\|ticket} <id> --agent A` | §4.4 | `:385` `claim` |
| `release DB {plan\|ticket} <id> [--agent A \| --force]` | §4.4 / §4.1 抢占 | `:411` `release` |
| `claims list DB` | §4.4 观测 | `:434` `list_claims` |
| `settlement run DB [--name TEXT]` | §4.5 | `:439` `settlement_run` |
| `suggest DB [--threshold F] [--max-size N]` | §3.6 F3 / §4.2 (read-only) | `dp_driven_optimize.py:suggest` |
| `orchestrate DB --agent A [--execute] [--name T] [--threshold F] [--max-size N]` | §4.2 routing | `dp_driven_optimize.py:suggest/execute` |
| `closeout summary DB --out PATH` | §5.2 步 1 | `:462` `closeout_export_summary` |
| `closeout check DB [--marker PATH]` | §5.2 步 2 门 | `:519` `closeout_verify_governed` |
| `closeout delete DB [--marker PATH] --force` | §5.2 步 3 | `:539` `closeout_delete_carrier` |

## Exit codes

| Code | Meaning | Source |
|---|---|---|
| 0 | OK | `dp_driven_cli.py:main` |
| 1 | usage / argparse error | `SystemExit` from argparse |
| 2 | `DpDrivenError` (business code on stderr) | `dp_driven_cli.py:main` maps `e.code` |
| 3 | carrier file not found | `FileNotFoundError` |
| 4 | single-writer lock timeout | `dp_driven_lock.py:LockTimeout` |

## Error codes (business)

Emitted on stderr as `<CODE>: <message>`. Codes originate from `dp_driven_model.py` (`DpDrivenError.code`) and `dp_driven_lock.py` (`LockTimeout`).

| Code | Trigger |
|---|---|
| `E_INVALID_NAME` / `E_INVALID_STATUS` / `E_INVALID_KIND` / `E_INVALID_EDGE_TYPE` | schema guard |
| `E_SELF_EDGE` | `blocks add` where from == to |
| `E_NO_SUCH_TASK` / `E_NO_SUCH_PLAN` / `E_NO_SUCH_FINDING` / `E_NO_SUCH_TICKET` | ref resolution |
| `E_REF_MISSING` / `E_EDGE_ENDPOINT_MISSING` / `E_PLAN_NOT_1TO1` | `validate` |
| `E_CLAIM_HELD_BY_OTHER` | claim conflict / status-write gate (§4.4) |
| `E_CLAIM_NOT_OWNER` | release with wrong agent, no `--force` |
| `E_POOL_EMPTY` | `settlement run` on empty pool (§4.5) |
| `E_NOT_COMPLETE` | `closeout` before §5.1 satisfied |
| `E_CLOSEOUT_NOT_GOVERNED` | closeout without `.governed.json` marker (§5.2 步 2) |
| `E_CLOSEOUT_MARKER_MALFORMED` | marker present but invalid JSON / missing `governed_at` |
| `E_CLOSEOUT_CONFIRM_REQUIRED` | `closeout delete` without `--force` |
| `E_DB_MISSING` | carrier path does not exist |
| `E_LOCK_TIMEOUT` | single-writer acquire exceeded 10 s (§4.4) |

## Output contract

Read commands emit pretty-printed JSON on stdout (`ensure_ascii=false`, `indent=2`,
`default=str`). Write commands emit a small `{ "ok": true, ... }` confirmation object
including the new entity id when applicable. Deterministic ordering everywhere so a
byte-equal replay is a valid regression test.

## Known Phase-2/3a gaps (not defects, deferred per design)

- **§3.6 F3 optimizer + scorer** — landed in Phase 3a as `dp_driven_optimize.suggest` /
  `CohesionScorer` (seed-and-grow greedy). No `learned` or adaptive weights; defaults are
  reference values for Human confirmation (§4.2).
- **§4.4 claim TTL / heartbeat** — Phase 3a did NOT add this; releases remain explicit
  (`release --force` = Human privilege). Design §8 `[未决]` for the concrete strategy.
- **§4.4 claim TTL / heartbeat** — Phase 2 releases are explicit; a crashed agent's claim
  persists until `release --force` (Human privilege). Strategy deferred per design §8.
- **§6 visualization** — no `render` command; carrier is inspected via `pool` / `status` /
  `task view`. Rendering lands later.
- **Windows file lock** — `fcntl.flock` is POSIX. §5.4 assumes a POSIX Human-specified
  directory; porting to Windows `msvcrt.locking` is out of Phase 2 scope.
