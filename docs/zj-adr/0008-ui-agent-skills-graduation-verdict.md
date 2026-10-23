---
doc-kind: adr
authority: historical
status: accepted
---

# UI agent-skills graduation verdict (CONDITIONAL_ADOPTION) and governance-page retirement

## Context

The `ui-agent-skills` subsystem was governed through a repository-level page at
`docs/designs/ui-agent-skills/README.md`. Through 2026-10-23 that page was
progressively slimmed: seven runtime contracts and nine specification documents
moved into `skills/ui/zj-ui-core/contracts/` (skill runtime closure: an installed
skill must not read files outside its own directory), twelve legacy twin / evidence
were deleted, and the page itself was reduced from an "authoritative hub (INDEX)"
to a "decision-convergence and governance status page", with contract and skill
navigation moved to `skills/ui/README.md`.

What survived that slimming was not a description of current behaviour but three
records: (1) the graduation verdict — **CONDITIONAL_ADOPTION**, signed by zj on
2026-10-22; (2) the 1-10 governance/rollout progress and its blocking chain
(1-10-2 blocked by 1-10-1, 1-10-3 by 1-10-2, 1-10-4 by 1-10-3); (3) the cleanup
log of the migration itself. Items (1) and (2) existed nowhere else: the
`ui-agent-skills-roadmap.*` carriers had already been deleted, so no roadmap
carried the 1-10 state, and the verdict's only other mention in the repository is
a code comment in `skills/ui/zj-ui-core/scripts/ui_stages.py`. Deleting the page
without relocating them would delete the decision, not the file.

## Decision

1. **The graduation verdict is ADR-bearing and is recorded here.** The
   `ui-agent-skills` subsystem is adopted as **CONDITIONAL_ADOPTION** (signed by
   zj, 2026-10-22): the S0 contract base `zj-ui-core` plus the S1..S10 stage
   skills ship as the `ui` public bucket, conditional on the graduation gates
   continuing to hold (contracts satisfied before graduation —
   `rule.contract-before-graduation`). This ADR is the durable record of that
   verdict; the page that previously carried it is deleted.
2. **Roadmap items 1-10-2 / 1-10-3 / 1-10-4 are retired, not migrated.** They form
   a blocked chain with no living owner, no roadmap carrier and no budget
   decision, while 1-1 through 1-9 are complete. Their state is archived here as
   historical fact and is not carried into a new tracker. Item **1-9-5
   (persistence replay gates G-19..G-25) stays separately scoped** — it was split
   out of the 1-9 line and is not part of this retirement.
3. **The governance status page is deleted.** `docs/designs/ui-agent-skills/` is
   removed; it held only that page. The discussion record
   `discussions/ui-agent-skills-complete-solution/` is kept — process material is
   preserved, only the derived conclusion page is retired.
4. **The cleanup log is not migrated.** The class 1/2/3 migration records are
   recoverable from git history; duplicating them into a long-lived page would
   create a second artefact to keep fresh.

## Consequences

- `rule.contract-before-graduation` in `docs/ontology/ONTOLOGY.md` and the
  human-review checklist now cite this ADR instead of the deleted page.
- The `Contract` section of `docs/README.md` routes the decision-convergence
  question to this ADR; the machine-readable contracts stay in
  `skills/ui/zj-ui-core/contracts/`.
- `docs/ontology/graph.json` is regenerated, so the `doc:designs/ui-agent-skills/*`
  nodes — including those left behind by earlier deletions because the graph was
  never re-extracted — disappear, and the graph stops asserting that deleted files
  exist.
- Nothing in CI depends on the deleted page: the `ui-contract` gate reads only
  `skills/ui/**` and `tests/`, so this deletion is CI-neutral by construction.
- Re-opening 1-10 governance (owner, maintenance budget, RTO/RPO, rollout,
  kill-switch) requires a new ADR superseding or extending this one, not a
  resurrection of the retired page.
