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

| `init DB --destination TEXT` | §4.0 step 1 | `dp_driven_model.py:94` `DpDriven.init` |
| `task add DB --name TEXT [--context-md P] [--memory-md P] [--derived-from-finding F]` | §4.0 step 2 / §3.5 form-③ | `:121` `add_task` |
| `task status DB <id> --set {未完成\|已完成\|已放弃} [--agent A] [--summary S]` | §3.1 / §4.4 gate | `:144` `set_plan_status` |
| `task summary DB <id> --text TEXT` | §2 终态总结 | `:170` `plan_summary` |
| `task view DB <id>` | §3.3 派生投影 | `:362` `task_view` |
| `finding add DB [--md-path P] [--external-hold R] [--derived-from-finding F]` | §2 / §3.5 form-② | `:179` `add_finding` |
| `finding dispose DB <id> --to {已完成\|已放弃}` | §3.5 处置 | `:211` `dispose_finding` |
| `finding membership add DB <fid> --task <tid>` | §3.4 多归属 | `:194` `add_finding_membership` |
| `finding membership remove DB <fid> --task <tid>` | §3.4 | `:202` `remove_finding_membership` |
| `ticket add DB [--task T] [--ref R] [--kv JSON] [--md-path P] [--derived-from-finding F] [--parent T] [--external-hold R]` | §2 / §3.4 / §7 Q1 | `:227` `add_ticket` |
| `ticket assign DB <id> --task <tid\|NULL>` | §4.3 热插 (§4.4 lock-free) | `:248` `assign_ticket` |
| `ticket status DB <id> --set {…} [--agent A]` | §4.4 ticket-claim gate | `:256` `set_ticket_status` |
| `blocks add DB --from KIND:ID --to KIND:ID` | §3.2 blocks edge | `:272` `add_blocks` |
| `edge remove DB <edge-id>` | §3.2 | `:286` `remove_edge` |
| `hold DB KIND:ID [--reason TEXT]` | §3.2.1 | `:291` `set_external_hold` |
| `status DB KIND:ID` | §3.2 派生读取 | `:318` `node_view` |
| `pool DB` | §2 available pool | `:381` `pool` |
| `validate DB` | §3 invariants | `:657` `validate` |
| `complete-check DB` | §5.1 完成判据 | `:395` `is_complete` |
| `claim DB {plan\|ticket} <id> --agent A [--lease-seconds S \| --no-lease] [--now EPOCH]` | §4.4 + §4.4 TTL | `:403` `claim` |
| `renew DB {plan\|ticket} <id> --agent A [--now EPOCH]` | §4.4 heartbeat 续租 | `:449` `renew` |
| `release DB {plan\|ticket} <id> [--agent A \| --force]` | §4.4 / §4.1 抢占 | `:479` `release` |
| `claims list DB [--now EPOCH]` | §4.4 观测（含派生 `expired`） | `:505` `list_claims` |
| `settlement run DB [--name TEXT]` | §4.5 | `:516` `settlement_run` |
| `suggest DB [--threshold F] [--max-size N]` | §3.6 F3 / §4.2 (read-only) | `dp_driven_optimize.py:suggest` |
| `orchestrate DB --agent A [--execute] [--name T] [--threshold F] [--max-size N]` | §4.2 routing | `dp_driven_optimize.py:suggest/execute` |
| `closeout summary DB --out PATH` | §5.2 步 1 | `:540` `closeout_export_summary` |
| `closeout check DB [--marker PATH]` | §5.2 步 2 门 | `:611` `closeout_verify_governed` |
| `closeout delete DB [--marker PATH] --force` | §5.2 步 3 | `:631` `closeout_delete_carrier` |

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
| `E_CLAIM_HELD_BY_OTHER` | claim conflict / status-write gate (§4.4); NOT raised if the held claim is expired (§4.4 TTL) |
| `E_CLAIM_NOT_OWNER` | release / renew with wrong agent, no `--force` |
| `E_CLAIM_LEASE_INVALID` | `lease_seconds ≤ 0` on claim, or an invalid stored lease (§4.4 TTL) |
| `E_CLAIM_REF_MISSING` / `E_CLAIM_KIND` / `E_DUP_CLAIM` | claim row integrity (`validate`) |
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

## Known remaining gaps (not defects, deferred per design)

- **§3.6 F3 optimizer + scorer** — landed (Phase-3a) as `dp_driven_optimize.suggest`
  (seed-and-grow greedy). No learned/adaptive weights; defaults are reference values for
  Human confirmation (§4.2); calibration awaits §9 real-run data.
- **§4.4 claim TTL / heartbeat** — landed (Phase-4a): heartbeat lease + derived `expired`,
  `renew`, `--no-lease`, `--now` epoch injection (§8 strategy now fixed as heartbeat).
- **§6 visualization** — landed (Phase-3c) as `viz` (stdlib Mermaid). Still open: **R7
  interactive HTML card** (today served by `task view` / `status` / `claims list`).
- **§9 metrics + weight calibration** — not implemented; needs Project B first real-run data.
- **Windows file lock** — `fcntl.flock` is POSIX. §5.4 assumes a POSIX Human-specified
  directory; porting to Windows `msvcrt.locking` is out of Phase 2 scope.
