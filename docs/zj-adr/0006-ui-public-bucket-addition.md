---
doc-kind: adr
authority: historical
status: accepted
---

# UI public bucket addition

## Context

The `skills/ui/` tree was introduced (carrying `zj-ui-core` — the S0 contract base
carrier — plus the S1..S10 stage skills `zj-ui-brief` / `zj-ui-discover` /
`zj-ui-direction` / `zj-ui-design-system` / `zj-ui-flow` / `zj-ui-prototype` /
`zj-ui-visual-review` / `zj-ui-break` / `zj-ui-verify` / `zj-ui-handoff`) as the
UI agent-skill chain. The architecture overview still described the repository as a
"5 + 1" model (five public buckets plus the root-level `personal/` tree) and omitted
`ui` entirely, so the documentation had drifted behind the live `skills/` tree. The
`ui` bucket is a public bucket: it installs to the same three Agent platforms
(`claude`, `codex`, `workbuddy`) and is not excluded from plugin discovery like
`personal/`.

## Decision

Ratify `skills/ui/` as a **sixth public skill bucket** (`ui`). Its responsibility is
the UI agent-skill chain: a deterministic contract base (`zj-ui-core`, S0) and ten
ordered stages (S1..S10) that take a UI request from intake to handoff under a
deny-first / unknown-quartet / atomic-commit discipline. The repository model is now
"6 + 1" (six public buckets plus the `personal/` tree). The `ui` bucket follows the
existing architecture-handbook governance: any future reorganisation of it remains an
ADR-bearing change, and any new primary view it requires must be registered with a
stable `authority-id` in the architecture map before shipping.

## Consequences

- The system overview's "5 + 1" model becomes "6 + 1"; its bucket table gains a `ui`
  row (11 skills: S0 + S1..S10) and the `productivity` (13) and `research` (5) counts
  are refreshed to match the live tree.
- A per-bucket subsystem page `ta-skill-bucket-ui.md` is added to the architecture map
  so the `ui` bucket has the same routing surface as the other five public buckets.
- Reorganising or splitting `ui` (e.g. promoting a stage to its own bucket) stays
  ADR-bearing; this ADR is the recorded provenance for the bucket's existence.
- The validator's `rule.bucket-reorg-is-adr-bearing` now resolves: the `ui` bucket is
  both declared in the overview and referenced by this ADR.
