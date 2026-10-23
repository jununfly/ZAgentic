---
doc-kind: architecture-subsystem
authority: primary
authority-id: architecture.subsystem.bucket.ui
---

# UI bucket

## Question

What does the `skills/ui/` subsystem own, what does it expose, and how does
it fail?

## Scope

This page describes the `ui` bucket as an architecture subsystem. The bucket
holds the UI agent-skill chain: a deterministic contract base (`zj-ui-core`,
S0) and ten ordered stages (S1..S10) that take a UI request from intake to
handoff. It does **not** own documentation governance (codebase-docs owns
that), does **not** own code-change skills (engineering owns that), and does
**not** own evidence production (research owns that).

## Boundaries

The `ui` bucket owns the canonical artifact contracts and the deny-first /
unknown-quartet / atomic-commit discipline that the stages enforce. The
deterministic implementation lives in `zj-ui-core/scripts/`; the ten stage
skills declare contracts only. The bucket never writes outside its declared
canonical artifacts and never treats an external protocol (A2UI / M3E) as the
schema owner.

## Responsibility

UI agent-skill work used when a Human asks for a UI surface to be specified,
built, reviewed, broken, verified, and handed off. The bucket covers:

- contract base and fixture runner (`zj-ui-core`, S0),
- intake / brief drafting (`zj-ui-brief`, S1),
- discovery of gaps and evidence grading (`zj-ui-discover`, S2),
- direction cards and Human direction choice (`zj-ui-direction`, S3),
- design-system tokens and component catalog (`zj-ui-design-system`, S4),
- semantic flow authoring (`zj-ui-flow`, S5),
- local preview / implementation-slice build (`zj-ui-prototype`, S6),
- browser visual review and review record (`zj-ui-visual-review`, S7),
- extreme-data and viewport break testing (`zj-ui-break`, S8),
- accessibility / interaction / motion verification (`zj-ui-verify`, S9),
- handoff packaging (`zj-ui-handoff`, S10).

## Owned state

- The skill folders under `skills/ui/` (11 entries: S0 + S1..S10) plus their
  per-skill `scripts/`, `references/`, and `tests/` directories.
- The local `README.md` index for the bucket.
- The canonical artifacts (`UI-BRIEF.md`, `UI-DESIGN.md`, `ui-flow/v1`,
  `review record`, `verification receipt`, `handoff`) produced by the stages.
- The fixture set under `tests/ui-agent-skills/fixtures/` that gates the
  chain.

## Interface

| Direction | Interface |
| --- | --- |
| Inbound | Human prompts asking to design, build, review, break, verify, or hand off a UI surface. |
| Outbound | Canonical UI artifacts and a verification receipt written into the target project's chosen surface. |
| Cross-bucket | Reads `ZJ-CONTEXT.md` for vocabulary; reads `skills/ui/zj-ui-core/contracts/` and `docs/zj-adr/` for the contracts and decisions it must respect; reads but does not write into other buckets. |
| External | Connects to a Storybook active adapter (B1) for verification; relies on `zj-ui-core/scripts/` for the shared primitives. |

## Failure behavior

- A stage that hits an unregistered or type-mismatched field stops and
  reports it (`REJECTED`); it never silently drops or guesses a value.
- A required input that is missing or unverifiable is recorded as an
  `unknown` quartet; it is never collapsed to an empty string or a guess.
- A `verification receipt` that is missing its provenance chain, or that
  reuses a stale baseline, is not emitted as a success; downstream stages
  freeze.
- A Human gate (`required` on S3 / S6 / S7) that is unsigned blocks the next
  stage; the skill never substitutes a default choice.
- An artifact with a second write owner freezes and reports
  `BLOCKED_OWNER_CONFLICT`; it does not merge concurrent writes.

## Source map

- [Bucket README](../../skills/ui/README.md) — local index.
- [ZJ-CONTEXT.md](../../ZJ-CONTEXT.md) — vocabulary the bucket respects.
- [ADR 0008](../zj-adr/0008-ui-agent-skills-graduation-verdict.md) — the
  graduation verdict (CONDITIONAL_ADOPTION) for the chain; its retired
  decision-convergence page has no successor page.
- [zj-ui-core](../../skills/ui/zj-ui-core/SKILL.md) — the S0 contract base.
- [zj-ui-brief](../../skills/ui/zj-ui-brief/SKILL.md) — S1 intake.
- [zj-ui-discover](../../skills/ui/zj-ui-discover/SKILL.md) — S2 discovery.
- [zj-ui-direction](../../skills/ui/zj-ui-direction/SKILL.md) — S3 direction.
- [zj-ui-design-system](../../skills/ui/zj-ui-design-system/SKILL.md) — S4 design system.
- [zj-ui-flow](../../skills/ui/zj-ui-flow/SKILL.md) — S5 flow.
- [zj-ui-prototype](../../skills/ui/zj-ui-prototype/SKILL.md) — S6 build.
- [zj-ui-visual-review](../../skills/ui/zj-ui-visual-review/SKILL.md) — S7 review.
- [zj-ui-break](../../skills/ui/zj-ui-break/SKILL.md) — S8 break.
- [zj-ui-verify](../../skills/ui/zj-ui-verify/SKILL.md) — S9 verify.
- [zj-ui-handoff](../../skills/ui/zj-ui-handoff/SKILL.md) — S10 handoff.

## Related authority

- [Architecture map](README.md) — primary routing surface.
- [System overview](ta-zagentic-overview.md) — the 6 + 1 skill-tree model
  this bucket is part of; `architecture.overview.zagentic`.
- [Bucket discipline](ta-skill-bucket-boundary.md) — the cross-cutting
  rule this subsystem consumes.
- [ADR 0006](../zj-adr/0006-ui-public-bucket-addition.md) — the recorded
  provenance for adding the `ui` public bucket.
