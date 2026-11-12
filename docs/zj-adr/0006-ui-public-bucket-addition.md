---
doc-kind: adr
authority: historical
status: accepted
---
> 时点说明：本页为历史决策记录，所述数量、路径与状态陈述截至 2026-10-23；现行规则以 `AGENTS.md` 与 `docs/architecture/` 为准。

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
  row (11 skills: S0 + S1..S10) and, as of 2026-10-23, the `productivity` (13) and `research` (5) counts
  were refreshed to match the then-live tree (historical snapshot, not a live count;
  see the Amendment below).
- A per-bucket subsystem page `ta-skill-bucket-ui.md` is added to the architecture map
  so the `ui` bucket has the same routing surface as the other five public buckets.
- Reorganising or splitting `ui` (e.g. promoting a stage to its own bucket) stays
  ADR-bearing; this ADR is the recorded provenance for the bucket's existence.
- The validator's `rule.bucket-reorg-is-adr-bearing` now resolves: the `ui` bucket is
  both declared in the overview and referenced by this ADR.

## Amendment (2026-11-12)

事实治理复核（review finding #6）：Consequences 中的 `productivity` (13) 与 `research` (5)
是 **2026-10-23 的历史快照**，不是活树计数；顶部时点说明已声明本页为历史决策记录，
正文原句的现在时被上面的限定语更正。此后 `research` 桶增加一项，活树为 `research` (6)
（由架构总览桶表与 skills 目录双向核对，根守卫机械钉住）。

本 Amendment 只澄清事实口径，**不改写上文的历史数字、不推翻 ADR 判决**。现行桶计数以
架构总览的桶表为唯一事实源，本 ADR 不再维护活数；将来桶计数变化也不回填本页。
