---
doc-kind: adr
authority: historical
status: accepted
supersedes: 0008 (Decision 3, "discussion record is kept")
---

# UI Agent Skills discussion record retirement (decoupling zj-ui-core from discussions/)

## Context

ADR 0008 (Decision 3) retained the discussion record
`discussions/ui-agent-skills-complete-solution/` as process material after the
derived governance page `docs/designs/ui-agent-skills/` was retired. At that
time the record was the only home of two content blocks that the frozen
`zj-ui-core` contracts (`golden-fixtures-spec.md`, `ui-flow-v1-contract.md`,
`skill-capability-manifest.md`) cited as their `引用源` / `权威来源`.

A later decision (2026-10-24) established that **tracing "why the solution was
decided" is not required**. With that constraint, the discussion record's only
remaining value — provenance for the contracts — is no longer needed, and the
three contracts' outward citations to `discussions/` became pure coupling (no
closure relevance, but still a hard dependency if the folder is ever deleted).

The two content blocks that legitimately belonged in durable authority were:
1. the **Remaining-risks 控制矩阵** (11 risks) and its "明确无法解决的事项" list;
2. the **Experience Version Wave 0–3** responsibility cards and **graduation
   预注册指标**.

These have now been distilled (de-sourced, no `discussions/` link) into two new
frozen contracts under `skills/ui/zj-ui-core/contracts/`:
- `guarantee-boundary.md` — guarantee boundary & risk-control matrix (v0.1, frozen);
- `graduation-gates.md` — graduation waves & pre-registered acceptance metrics (v0.1, frozen).

The three original contracts had their `引用源` / `权威来源` lines replaced with
pointers to these two in-repo files.

## Decision

1. **The discussion record `discussions/ui-agent-skills-complete-solution/` is
   retired**, superseding ADR 0008 Decision 3 ("is kept"). Its durable content
   now lives in `skills/ui/zj-ui-core/contracts/guarantee-boundary.md` and
   `graduation-gates.md`; the 35 briefings, 31 viewpoints and 6 sub-doc
   discussion drafts were pure process and are not migrated.
2. **`zj-ui-core` is fully decoupled from `discussions/`**: no skill file under
   `skills/` references the retired folder. `zj-discuss` / `zj-doc-collab`
   still reference `discussions/<slug>/` by design (they create/carry it) and
   are out of scope for this decoupling.
3. The frozen contracts keep their v0.1 freeze; the two new files are likewise
   frozen v0.1, so the "contract-before-graduation" gate is unchanged.

## Consequences

- The folder `discussions/ui-agent-skills-complete-solution/` may be deleted
  (no in-repo consumer remains). Deletion is a mechanical step gated by this
  ADR, not a separate decision.
- `scripts/check-skill-runtime-closure.py` continues to exclude `discussions/`
  (still relevant for future `discussions/<slug>/` folders created by
  `zj-discuss`); this ADR does not change that exclusion.
- `scripts/check-docs-dangling-refs.py` should report zero dangling links after
  deletion; any remaining `discussions/ui-agent-skills-complete-solution/`
  mention is historical prose and must be updated or marked retired.
- ADR 0008 Decision 3 is reversed by this ADR but ADR 0008's other decisions
  (CONDITIONAL_ADOPTION verdict, 1-10 retirement) are unaffected.
