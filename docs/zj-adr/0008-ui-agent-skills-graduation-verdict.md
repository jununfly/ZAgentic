---
doc-kind: adr
authority: historical
status: accepted
---

# UI agent-skills graduation verdict (CONDITIONAL_ADOPTION) and governance-page retirement

## Context

The `ui-agent-skills` subsystem was governed through a repository-level page at
`docs/designs/ui-agent-skills/README.md` (deleted 2026-10-24; its relocated
records are listed under Decision). Through 2026-10-23 that page was
progressively slimmed: seven runtime contracts and nine specification documents
moved into `skills/ui/zj-ui-core/contracts/` (skill runtime closure: an installed
skill must not read files outside its own directory), twelve legacy twin / evidence
were deleted, and the page itself was reduced from an "authoritative hub (INDEX)"
to a "decision-convergence and governance status page", with contract and skill
navigation moved to `skills/ui/README.md`.

What survived that slimming was not a description of current behaviour but three
records: (1) the graduation verdict — **CONDITIONAL_ADOPTION**, signed by zj on
2026-10-22; (2) the page's last record of the 1-10 governance/rollout line; (3)
the cleanup log of the migration itself. Record (1) existed nowhere else: the
verdict's only other mention in the repository is a code comment in
`skills/ui/zj-ui-core/scripts/ui_stages.py`. Record (2) was recoverable, but only
by archaeology — the `ui-agent-skills-roadmap.*` carriers had already been
deleted, so no roadmap carried the 1-10 state, and the page was never re-synced
after items landed later the same day. Deleting the page without writing record
(1) down would have deleted the decision, not the file.

## Decision

1. **The graduation verdict is ADR-bearing and is recorded here.** The
   `ui-agent-skills` subsystem is adopted as **CONDITIONAL_ADOPTION** (signed by
   zj, 2026-10-22): the S0 contract base `zj-ui-core` plus the S1..S10 stage
   skills ship as the `ui` public bucket, conditional on the graduation gates
   continuing to hold (contracts satisfied before graduation —
   `rule.contract-before-graduation`). This ADR is the durable record of that
   verdict; the page that previously carried it is deleted.
2. **The 1-10 governance/rollout line is retired, and its state is recorded as it
   actually was.** The retired page described 1-10-2 / 1-10-3 / 1-10-4 as a chain
   in which each item blocks the next. That reading was stale: the page was
   written before 1-10-2 and 1-10-3 landed, and was never re-synced afterwards.
   The verified state, taken from the commits themselves, is:

   | item | scope | state | evidence |
   | --- | --- | --- | --- |
   | 1-10-1 | authoritative-page migration (index hub plus decision/risk summary; both pages since removed) | **completed** 2026-10-22 | `1176412` |
   | 1-10-2 | recursive discovery / index sync — the eight registration points, verified by `scripts/validate-zagentic-plugin.py` (66 skills, exit 0) | **completed** 2026-10-22 | `fbc5521` |
   | 1-10-3 | ownership, maintenance budget, RTO/RPO, re-evaluation cadence, WIP policy | **completed** 2026-10-22 | `8c9bbdb` |
   | 1-10-4 | rollout / pilot / kill-switch / adapter removal / revalidation decisions | **never started**; released to *ready* by 1-10-3 | no commit exists |

   Retirement therefore covers exactly one unfinished item — 1-10-4 — plus the
   ongoing maintenance of what 1-10-1 to 1-10-3 already produced. The reason to
   retire is the absence of a living owner, a roadmap carrier and a budget
   decision, **not** a blocking dependency: nothing was blocking 1-10-4 at
   retirement time. Each item's substance stays in its own commit; copying it here
   would create a second artefact to keep fresh. Item **1-9-5 (persistence replay
   gates G-19..G-25) stays separately scoped** — it was split out of the 1-9 line
   and is not part of this retirement.
3. **The governance status page is deleted.** `docs/designs/ui-agent-skills/` is
   removed; it held only that page.

   > **Reversed by [ADR 0009](./0009-ui-agent-skills-discussion-retirement.md)
   > (2026-10-24).** At the time this ADR was written, the discussion record
   > `discussions/ui-agent-skills-complete-solution/` was *kept* as process
   > material. That decision was later reversed: the record was retired and its
   > two durable content blocks distilled (de-sourced) into
   > `skills/ui/zj-ui-core/contracts/guarantee-boundary.md` and
   > `graduation-gates.md`. The remainder of this decision — the
   > CONDITIONAL_ADOPTION verdict and the 1-10 retirement — is unchanged.
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
- Re-opening 1-10 means re-opening **1-10-4** alone: rollout, pilot, kill-switch,
  adapter removal and revalidation decisions. Ownership, maintenance budget and
  RTO/RPO were settled by 1-10-3 (`8c9bbdb`) — the budget placed on the user side
  as a trade-off with no pre-set allowance on the development side, and RTO/RPO
  reduced to the two guarantees the design actually provides (near-zero RTO on
  degradation, RPO = 0 by construction) — so re-opening those would mean
  contradicting a completed item and needs an explicit rationale. Any re-open
  requires a new ADR superseding or extending this one, not a resurrection of the
  retired page.

## Amendment (2026-10-24)

An earlier revision of this ADR carried the retired page's wording unchanged and
described 1-10-2 / 1-10-3 / 1-10-4 as still mutually blocked. That was wrong.
`1176412`, `fbc5521` and `8c9bbdb` (all 2026-10-22) completed 1-10-1, 1-10-2 and
1-10-3, and 1-10-3 released 1-10-4 to ready — no dependency was blocking it. The
Context paragraph and Decision 2 above were corrected to match those commits; the
graduation verdict, the retirement decision and every other consequence are
unchanged. This ADR is `status: accepted` throughout — nothing was re-decided.

The failure mode is worth naming for any future derived page: a status page
decays silently once its source keeps moving, and the decay is invisible because
nothing fails. Before a derived page's last recorded state is promoted into an
ADR fact, reconcile it against the source's commit history — `git log -S` plus
`git merge-base --is-ancestor` settled this case in minutes. Otherwise a stale
artefact becomes an authority, and the next reader pays for it.

## Amendment (2026-10-24, superseded by ADR 0009)

Decision 3's "the discussion record `discussions/ui-agent-skills-complete-solution/`
is kept" is **reversed** by [ADR 0009](./0009-ui-agent-skills-discussion-retirement.md).
With the later decision that tracing "why the solution was decided" is not
required, the record's only remaining value (provenance for the frozen
`zj-ui-core` contracts) is no longer needed. Its two durable content blocks
(Remaining-risks 控制矩阵; Experience Version Wave/graduation 预注册指标) were
distilled, de-sourced, into `skills/ui/zj-ui-core/contracts/guarantee-boundary.md`
and `graduation-gates.md`. The three contracts' `引用源`/`权威来源` lines now
point to those in-repo files, so `zj-ui-core` is fully decoupled from
`discussions/`. Decision 3 is therefore obsolete; this ADR's other decisions
(CONDITIONAL_ADOPTION verdict, 1-10 retirement) are unchanged.
