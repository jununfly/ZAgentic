---
name: zj-doc-health
description: "Human-invoked, opt-in documentation health metering for one codebase: line budgets, freshness against declared Source map targets, orphan and zero-indegree pages. Report-only; never mutates."
disable-model-invocation: true
source: zagentic

---

# Meter Documentation Health

One explicit measurement pass over one repository's docs. Health is a
different axis from correctness: `/zj-docs-ontology` answers "is the map
right", `/zj-docs-architecture` answers "is the structure right", this skill
answers "are the pages alive" — and it answers only what the Human asked it
to meter.

## Opt-in boundary

Measurement runs **only** against a config file the Human committed —
`docs/doc-health.json` by default, or `--config <path>`. No config means no
measurement and exit zero; nothing is metered by default, and a mechanical
health *gate* is explicitly a rejected default (see the governance contract's
`Rejected defaults`). Budgets are Human-set values, not skill constants.

## Workflow

1. **Read the contract.** Read
   [health-contract.md](references/health-contract.md) before the first run
   or any change to the tool — it defines the config schema, the four
   meters, and the time-source degradation rule.
2. **Run, read-only.** `python3 scripts/doc_health.py <repo> [--config <path>]`.
   The tool never writes. Without a config it prints `status: opt-in` and
   exits zero.
3. **Report, don't fix.** Outliers are a proposal surface, like every other
   governance report. Route fixes to their owners: budget rewrites and
   reparenting to `/zj-docs-ontology` proposals, stale claims to the page's
   owner, retirement candidates to the retirement path.

## Meters (v1)

- `BUDGET_EXCEEDED` — physical lines over a glob-scoped cap.
- `FRESHNESS_DRIFT` — the newest file declared under the page's
  `## Source map` is more than N days newer than the page.
- `ORPHAN_PAGE` — no inbound link from any living page, not even the map.
- `ZERO_INDEGREE` — linked from the map only; no living page cites it.

Exit code: 1 when outliers are reported, 0 when clean or unconfigured.

## Boundaries

- Report-only. `mutations` is not a concept here; nothing is proposed to be
  written by this tool itself.
- Evidence surfaces and process material are never metered and never read as
  link sources — they are frozen or transient, not living pages.
- Freshness consumes the architecture layer's `## Source map` declaration; it
  does not define a second mapping syntax.
