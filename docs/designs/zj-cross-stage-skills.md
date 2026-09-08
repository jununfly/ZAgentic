---
doc-kind: design
authority: primary
authority-id: design.cross-stage-checkpoints
---

# Cross-stage checkpoints

## Question

Which focused skills add a distinct checkpoint around a ticketed delivery flow,
without duplicating planning, implementation, or documentation governance?

## Scope

This design defines the boundaries among `zj-steelman`, `zj-dry-run`, and
`zj-debrief`. It applies when a Human uses a plan or ticketed flow; it does not
make any checkpoint automatic.

## Boundaries

- `zj-steelman` tests whether a proposal has a defensible floor. It is a
  one-shot, inline pre-planning check, not a multi-round critique or a record.
- `zj-dry-run` rehearses an ordered ticket set after ticket creation and before
  implementation. It reports friction but never edits a spec or tickets.
- `zj-debrief` closes a finished task by recording drift, concepts, and actions
  in process material. It does not extract durable authority or delete retros;
  a later Human-invoked `zj-docs-ontology` pass governs those actions.

These checkpoints are neither a replacement for `zj-grilling`,
`zj-to-tickets`, or `zj-implement`, nor a generic lifecycle hook. A Human
selects each one for the phase where its question is useful.

## Design

| Checkpoint | Phase | Distinct question | Outcome and route |
| --- | --- | --- | --- |
| `zj-steelman` | Before grilling or detailed review | Does the strongest case for each core assumption hold? | Any weak assumption routes to `zj-grilling`; otherwise the proposal may proceed. |
| `zj-dry-run` | After `zj-to-tickets`, before `zj-implement` | Can these concrete tickets run in order without boundary, dependency, or decision friction? | Recut through `zj-to-tickets` or `zj-to-spec`, or route unresolved decisions to `zj-grilling`. |
| `zj-debrief` | After a task | What drift, concepts, and next actions deserve process capture? | Writes a retro and updates the root context index; durable extraction remains pending governance. |

The checkpoints are complementary because they use different mental models:
defend an idea, rehearse an execution path, then inspect what actually happened.
Keeping those models separate avoids role conflicts and keeps each output small.

## Source map

- [zj-steelman](../../skills/engineering/zj-steelman/SKILL.md) — assumptions,
  strongest-case test, and route to grilling.
- [zj-dry-run](../../skills/engineering/zj-dry-run/SKILL.md) — ticket rehearsal,
  friction classification, and non-mutating routes.
- [zj-debrief](../../skills/codebase-docs/zj-debrief/SKILL.md) — process closeout
  writes and concept extraction.
- [documentation governance contract](../../skills/codebase-docs/zj-docs-ontology/references/governance-contract.md)
  — process-material extraction and deletion boundary.

## Related authority

- [ZAgentic documentation map](../README.md) — category and lifecycle routing.
- [Codebase Docs capability spec](../prds/codebase-docs-capability.md) —
  process-material lifecycle.
- [ADR 0002](../zj-adr/0002-1-stage-skill-pair-key-decisions.md) — historical
  record of the original checkpoint decision.
