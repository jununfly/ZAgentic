# dp_driven closeout (§5.2)

The two-stage teardown that turns a completed DP run into durable docs + a deleted carrier.
Design baseline: `zj-dp-driven-skill-design.md` §5.2, §5.3. Implementation:
`dp_driven_model.py:540` `closeout_export_summary`, `:611` `closeout_verify_governed`,
`:631` `closeout_delete_carrier`. CLI: `closeout summary / check / delete`.

## Why two stages (order is load-bearing)

The design forbids the naive "delete sqlite then govern" order, because governance reads the
process graph as evidence (cross-plan dependencies, finding multi-membership, materialization
links). It also forbids "delete without snapshot", because a plain collection of independent
md files loses the *relationships* that only lived in sqlite's `blocks` edges / membership rows.

So the fixed order is:

```
所有 task 到终态 (§5.1)
  → 步 1: 导出 process-summary.md（结构性关系快照，sqlite 仍可读）
  → 步 2: Human 用 zj-docs-ontology 治理该目录那组 md（含快照）→ 写 .governed.json marker
  → 步 3: 删 sqlite（+ sidecar）
```

Between step 1 and step 3 the carrier is still present, so the ontology pass can cite the
process graph into the doc-map (§5.3: 依赖方向 `sqlite → 结构化 md → 长期文档`).

## Command sequence

```bash
# assume carrier at docs/plans/dp-driven/<topic>/dp_driven.sqlite, all tasks terminal
DP="python3 $SKILL_ROOT/scripts/dp_driven_cli.py"

$DP complete-check docs/plans/dp-driven/<topic>/dp_driven.sqlite
#  → {"is_complete": true, ...}  ; false → E_NOT_COMPLETE on the next steps

# 步 1 — snapshot (sqlite still there)
$DP closeout summary docs/plans/dp-driven/<topic>/dp_driven.sqlite \
     --out docs/plans/dp-driven/<topic>/process-summary.md
# 步 1b — metrics snapshot (§9 numbers join the same corpus; Phase-4c decision 5: separate file)
$DP metrics report docs/plans/dp-driven/<topic>/dp_driven.sqlite \
     --out docs/plans/dp-driven/<topic>/metrics.md

# 步 2 — external: run zj-docs-ontology on that md directory, then the Human writes the marker
#         (see marker contract below)

# 步 3 — teardown (guarded)
$DP closeout check   docs/plans/dp-driven/<topic>/dp_driven.sqlite      # verifies marker
$DP closeout delete  docs/plans/dp-driven/<topic>/dp_driven.sqlite --force
```

## The governed marker (step-2 handoff, mechanical gate)

`closeout_verify_governed` requires a marker file — default path `<db-without-ext>.governed.json`
(override with `--marker`). This is how "the ontology pass finished" becomes a *failing* condition
in code instead of a prose hope (§5.2's order must be enforceable, not advisory).

```json
{
  "governed_at": "<ts>",
  "corpus": ["<path/to/md>", "..."]
}
```

- Missing file → `E_CLOSEOUT_NOT_GOVERNED`.
- Invalid JSON / missing `governed_at` → `E_CLOSEOUT_MARKER_MALFORMED`.
- Not all tasks terminal → `E_NOT_COMPLETE` (checked first, independent of the marker).

> **Boundary**: the marker is produced by the zj-docs-ontology workflow, not by this skill. This
> skill only *requires its presence* before deleting. That keeps §5.3's authority direction intact:
> dp-driven never writes durable docs; ontology owns them. It also keeps runtime closure (AGENTS.md):
> the skill reads only a file in its own Human-specified carrier directory, not `docs/`.

## What `closeout_delete` removes

Only the process artifacts, in the same directory as the carrier:

- `dp_driven.sqlite`, `dp_driven.sqlite-wal`, `dp_driven.sqlite-shm` (§5.4 ADR-0010:
  sqlite WAL sidecars are process residue)
- `dp_driven.sqlite.lock` (the `dp_driven_lock.py` sidecar)
- `dp_driven.events.jsonl` (the §9 observation log — CLI-layer removal in
  `cmd_closeout_delete`, reported as `sidecars_removed`; locked by
  `test_dp_driven_metrics.py::MetricsCloseout.test_closeout_delete_removes_event_log`)

It **never** touches the `.md` corpus — those are the durable output (§5.3). Enforced by
`test_dp_driven_closeout.py:CloseoutDelete.test_md_corpus_survives_delete` and by the
metrics case above (the exported `metrics.md` must survive). If the sequence gate fails
(e.g. missing marker) **nothing** is deleted — including the event log
(`test_closeout_delete_blocked_without_marker`).

## What `closeout_export_summary` writes

A deterministic markdown snapshot (byte-identical on replay — `test_..._byte_equal`) containing
five sections, each a table:

1. **Tasks** — id / name / derived `task_view` status / completed_at (so the terminal projection
   survives the carrier's deletion).
2. **Cross-plan blocks (§3.6 F2 商图边)** — every `blocks` edge with the owning plan of each
   endpoint; this is exactly the structure that only lived in sqlite and would otherwise be lost.
3. **Finding multi-membership (§3.4)** — finding → its plan list, so a governance reader sees
   which findings were overlapping subproblems.
4. **Ticket materialization (§7 Q1 + §2 ref/parent)** — ticket → `ref` / `derived_from_finding` /
   `parent_id` / owning plan / status.
5. **Finding derivation (§3.5 形态②③)** — source finding → derived finding / derived task.

The §9 numbers are **not** inside this snapshot: `metrics report --out metrics.md` emits them
as a sibling file (Phase-4c decision 5), so the summary's §10 anchors stay put and each report
regenerates independently.

## Postconditions (acceptance)

After `closeout delete --force`:

- carrier, both sqlite sidecars, the lock sidecar and the event log are gone;
- `process-summary.md`, `metrics.md` and the governed md corpus remain;
- a follow-up `open(db)` raises `FileNotFoundError` (the run is closed).

This is the "过程即燃料" payoff (§1 差异化判据 2): the DP table is consumed and discarded; only
its referenced markdown persists.
