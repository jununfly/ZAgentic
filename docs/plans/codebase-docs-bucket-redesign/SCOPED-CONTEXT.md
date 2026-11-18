---
doc-kind: plan
authority: process
---

# Scoped context: codebase-docs bucket redesign

> Status: **DRAFT — Human is actively refining this context.** Do not act on it
> yet. It is process material under ADR 0010 (`docs/plans/`, git-tracked,
> cleaned at close-out). At task close-out, its durable conclusions are to be
> archived into the long-lived authority docs by the updated `zj-docs-ontology`.
> Created 2026-11-18. Revision 2026-11-18 (zj, 2nd): the shared-rule authority
> is a **new** docs directory, freshly authored — reusing or seeding from the
> existing `docs/ontology/ontology.schema.json` is rejected as the case-2
> baseline error. Directory name closed 2026-11-18 (zj): `docs/skill-conventions/`
> — `docs/skill-components/` rejected for colliding with the repo's established
> `component` semantics (see Open sub-questions).
> Revision 2026-11-18 (zj, 3rd): Q4/Q5 closed — the dependency/extension
> declaration is a **fenced JSON block in the SKILL.md body** (not frontmatter),
> and the validator-binding check is a **canary mutation test built now**, not
> deferred. Revision 2026-11-18 (zj, 4th): Q6 re-sort analysis landed — nine
> skills classified into three tiers with per-skill keep/merge/decouple/move
> recommendations and evidence; awaiting zj's per-skill rulings (not applied).
> Revision 2026-11-18 (zj, 5th): Q6 RULED — 1 delete (`zj-grill-with-docs`),
> 2 no move (`zj-roadmap-driven` / `zj-wayfinder` stay), 3 no new skill.
> Revision 2026-11-18 (zj, 6th): Q7 opened — whether to merge
> `zj-docs-ontology` + `zj-docs-architecture`; analysis landed with
> recommendation **no merge** (the boundary is intentional; the real gap is an
> unmechanised composition step). Revision 2026-11-18 (zj, 7th): Q7 RULED —
> accept **no merge + witness field**; implementation reuses P0 Ruling 3's
> existing codes, no new diagnostic code.

## Question

How should the `codebase-docs/` bucket of skills be redesigned so that shared
naming rules live in exactly one authoritative place that is **visible at
runtime under single-skill installation**, while skills that do not need those
rules stay independent — and how should the existing skills be re-sorted by
division of labour (merge / decouple / delete / add)?

## Why this is now a complex task

This task originated as open item 5 of issue #264's P0 ruling
(`tmp/skills-outputs/zj-docs-ontology/p0-decisions/DECISIONS.md`):
where should the `<topic>` naming convention live. A proposal to embed a copy
of the rules in every consuming skill's `references/` was rejected by zj:
technically inelegant and a埋下的技术债. The scope escalated from "name one
topic" to "redesign the bucket's shared-rule architecture". It is being tracked
here as its own context because simple conversation is not sufficient to hold
it.

## Repo context (zj, verbatim intent — preserved)

ZAgentic is a project composed of a rich set of skills. Its evolution follows
zj's first-principles chain:

```
Human => [岗位 == Motivation + Skill + Knowledge]
      => [Role == Task + Skill + Knowledge]
      => Agent
```

Continuous accumulation of skills raises the working capability and efficiency
of both Human and Agent, and enables Agent to take on more independent work.
Some skills complete a class of task alone; others must compose with other
skills to do it well.

zj's preferred problem-solving method: **Occam's razor + dynamic programming →
progressive decision making**. SOP:

1. Apply **systems thinking** to abstract/simplify the target task. If one
   skill can solve it well, focus on making that one skill excellent.
2. If systems thinking is insufficient, refine one step: apply **structured
   thinking** against first principles / some pattern to split the task into
   scopes, build one skill per scope, then close the loop with systems
   thinking.
3. If systems + structured thinking are insufficient, partition the content:
   apply **model thinking** to model the special part (group one special class
   of problems into its own scope / small closed loop), build a skill for that
   scope, then close the loop with structured + systems thinking.

zj intends to keep using this method to design and maintain ZAgentic's skills.

## codebase-docs context (zj, verbatim intent — preserved)

The long-term task in any codebase project is to continuously maintain a
complete and fresh documentation system. The `codebase-docs/` bucket of skills
exists to help Human & Agent accomplish exactly that task.

## Task context (zj, verbatim intent — preserved)

Redesign the whole group's design; re-inventory the `codebase-docs/` skills:

1. The "embed the authoritative rule in every consuming skill's `references/`"
   approach is to be replaced: save shared rules **in one base skill inside the
   `codebase-docs/` bucket**.
2. Within the bucket, skills that depend on this base skill must **explicitly
   require the Agent to load the base skill first and follow its rules**.
   Skills with no dependency on it stay independent.
3. Re-sort the existing skills per the Repo-context method: merge what should
   be merged, set boundaries for what should be decoupled, delete what should
   be deleted, add what should be added.

## Hard constraints (取证 fact — not open for redesign)

These come from the repo's mechanics, not preference. Any design must satisfy
them or it breaks at install time / fails a gate.

| Constraint | Evidence | Implication |
| --- | --- | --- |
| Default: a bucket installs together; **a user may pick a single skill** to install. An external Agent Harness (Claude Code / Codex / WorkBuddy) executes them | zj, Q2 answer 2026-11-18 | Design must hold under **both** modes — a single-installed skill has no sibling and no `docs/designs/`, so runtime references to either are broken links |
| Installing by copy; cross-skill **import** breaks at install time; carrying a private copy merely relocates the code and adds a sync rule | `skills/codebase-docs/zj-docs-ontology/references/governance-contract.md:253-256` | Runtime must not import a base skill; base content must already be **inside** each installed skill |
| The closure gate allows a path-bearing reference to a sibling skill root (base 4) because install is bucket-flat | `scripts/check-skill-runtime-closure.py:28-33,137-165` | Base 4 is valid only in bucket-install mode; single-install mode is why Q2 chose publish-time inlining |
| `docs/plans/` is transient process material; durable decisions go to ADR/design; long-lived docs must not point *into* `docs/plans/` (plan-coupling ERROR) | ADR 0010; `check-docs-dangling-refs.py:162` | This context file is process-only; its conclusions must be extracted to authority docs at close-out |
| Rules on naming are currently scattered across 4+ skills | `zj-docs-architecture` (`architecture-contract.md:57-75`, `validator-contract.md:13-18`), `zj-neat-freak` (`governance.md:11`), `zj-triage` (`OUT-OF-SCOPE.md:58`), `zj-discuss` (`SKILL.md:81`) | Consolidation target is real; each current owner must be classified (define / consume / audit / unrelated) |
| A shared authority must be **freshly authored to a quality bar**, never derived from or seeded by an existing docs artifact | zj, 2026-11-18 2nd revision; P0 Ruling 1 v3 case 2 (a flawed prior state used as the baseline misleads the executor and propagates defects) | Reject `docs/ontology/ontology.schema.json` as the source or seed of shared rules; author from the verified Q3 consumer requirements, reconcile overlap deliberately |

## Bucket inventory (取证 — 9 skills)

Source: `skills/codebase-docs/README.md` + `git ls-tree main:skills/codebase-docs`.

| Skill | Stated role (from bucket README) | Naming-rule relation |
| --- | --- | --- |
| `zj-docs-architecture` | Maintain & validate architecture handbook views | Defines `PAGE_NAME_*` |
| `zj-docs-ontology` | Docs-system discovery, governance proposal, validation, lifecycle | Consumes `<topic>` (pending) |
| `zj-doc-health` | Opt-in report-only docs health metering | none found |
| `zj-debrief` | Close out task as process material; route durable conclusions | none found |
| `zj-domain-modeling` | Maintain project domain language & glossary | owns `ZJ-CONTEXT.md` format |
| `zj-grill-with-docs` | Repository-aware grilling with doc updates | co-owns `ZJ-CONTEXT.md` |
| `zj-neat-freak` | Reconcile codebase knowledge & governance drift | audits kebab-case (`governance.md:11`) |
| `zj-roadmap-driven` | Maintain decision-carrying execution roadmap | none found |
| `zj-wayfinder` | Maintain shared map of large-work planning decisions | none found |

Note: `zj-triage` / `zj-discuss` naming rules live in **other** buckets — out of
the "docs-system related" scope zj defined; ignore unless a dependency is
later proven.

## Re-sort analysis — Q6 (取证 landed 2026-11-18; per-skill rulings OPEN)

Per task item 3, each of the 9 skills is classified by the Repo-context method
(one skill solves it → keep; else split by scope). Source: each SKILL.md's own
stated boundaries + the cross-skill `/zj-*` references + `git log` + root tests.
Three tiers emerge. **Nothing here is applied** — these are evidence-backed
recommendations for zj to rule on.

### Tier A — docs-system core (keep; Q1–Q5 restructuring applies)

| Skill | Evidence of distinct scope | Recommendation |
| --- | --- | --- |
| `zj-docs-ontology` | Owns whole map + governance loop + lifecycle; SKILL.md explicitly says it is "not a shared-knowledge publisher or automatic closeout handler". Cross-refs to architecture/debrief/domain-modeling/neat-freak are **compositions it invokes on Human request**, not overlap. | **Keep** as base (Q1) + governance entry. |
| `zj-docs-architecture` | SKILL.md declares it owns "handbook shape, not domain terminology (`/zj-domain-modeling`), hard-to-reverse decisions (`/zj-grill-with-docs` and ADR work), or whole documentation governance (`/zj-docs-ontology`)". Clean mutual boundary with ontology. | **Keep**. Value domain becomes shared (Q3 option A); validator reads inlined copy. |
| `zj-doc-health` | "Health is a different axis from correctness" — meters aliveness (budgets/freshness/orphan/indegree), report-only, opt-in config. No overlap with map/structure correctness. | **Keep**. No dependency on the shared rules (naming/value domains) → generator does not touch it. |

### Tier B — process / domain layer (keep; boundaries locked by ADR 0011)

| Skill | Evidence | Recommendation |
| --- | --- | --- |
| `zj-debrief` | Task closeout → `docs/zj-retros/`; Step 2 invokes `/zj-domain-modeling`. ADR 0011:74 — "zj-neat-freak (drift reconcile) and zj-debrief (retro) still own the process layer; this ADR does not change their boundary." | **Keep**. Consumes domain-modeling; not a docs-governance duplicate. |
| `zj-neat-freak` | Six-fact-surface closeout (code/runtime/docs/rules/memory/workspace); governance.md:11 audits kebab-case. ADR 0003:46 records it was *deliberately* moved engineering → codebase-docs by later governance. ADR 0011:74 locks its process-layer role. | **Keep**. Its kebab-case audit becomes a **consumer** of the shared naming syntax core (Q3); it is not the rule owner. |
| `zj-domain-modeling` | Owns `ZJ-CONTEXT.md` + `docs/zj-adr/` format; SKILL.md stresses it is the *active* discipline (changing the model), distinct from merely reading vocabulary. Composed by debrief, grill-with-docs, wayfinder. | **Keep**. Glossary/ADR format stays its own private authority — do **not** fold into the shared naming source. |
| `zj-grill-with-docs` | SKILL.md body is **one line**: "Run a `/zj-grilling` session, using the `/zj-domain-modeling` skill." `/zj-grilling` lives in `productivity/`. No tests/gates pin it (only a `scripts/zagentic-skills-list:28` entry). | **Merge candidate → delete**: it is a pure wrapper composing two existing skills. Cost: remove the list entry; no test/CI rewrites. Alternative: keep as a discoverable alias if zj values the named entry point. **zj to rule.** |

### Tier C — planning / tracking (归属存疑; move cost proven high)

| Skill | Evidence | Recommendation |
| --- | --- | --- |
| `zj-roadmap-driven` | Owns decision-carrying execution roadmap (tracking); carrier in `docs/plans/` by ADR 0010. Domain is **execution-context**, not documentation-system governance. But **7+ root tests hardcode its `skills/codebase-docs/` path** (`test_zj_roadmap_driven_layout.py:21`, `_frontmatter.py:22`, `_landing.py:20`, `test_skill_install_smoke.py:31`, `test_process_authority_boundary.py:22`, …) and CI runs it from that path (`skill-closure-lint.yml:36,84`). | **Keep in bucket** by default — moving to `engineering/` (ADR 0003's "methodology → engineering" precedent) is a high-cost path rewrite with no functional gain. If zj wants semantic purity, isolate as an explicit future slice. |
| `zj-wayfinder` | Owns large-work planning (decision tickets), dual carrier; pairs with roadmap-driven (`plan → track`), `zj-to-tickets` seam in `engineering/`. Same domain argument as roadmap-driven, but **no test/CI path pins it**. | **Keep** (pairs with roadmap-driven); a move is cheap but would split the pair unless both move together. |

### Precedents outside the bucket (from the earlier base-skill section)

`zj-ui-core` (`skills/ui/`) and `zj-doc-collab` (`skills/productivity/`) consume
their base via **runtime import of code**, which the inline-rules generator
(Q2) does not cover. Rule needed: **leave as-is** (they are bucket-install
precedents with their own CI gate), and bound this redesign to *rules*, not
shared executable code. Document the portability caveat rather than migrate.

### Summary of recommendations — RULED 2026-11-18 (zj)

| # | Skill | Rec | zj ruling | Consequence |
| --- | --- | --- | --- | --- |
| 1 | zj-docs-ontology | Keep (base) | **Keep** | Q1–Q5 changes only |
| 2 | zj-docs-architecture | Keep | **Keep** (Q7 merge question still open) | validator enum → inlined read (Q3) + canary (Q5) |
| 3 | zj-doc-health | Keep | **Keep** | none |
| 4 | zj-debrief | Keep | **Keep** | none |
| 5 | zj-neat-freak | Keep | **Keep** | kebab-case rule → shared syntax consumer |
| 6 | zj-domain-modeling | Keep | **Keep** | glossary/ADR format stays private |
| 7 | zj-grill-with-docs | Delete | **DELETE** (zj: "1 删") | remove 1 skills-list line; no test impact |
| 8 | zj-roadmap-driven | Keep | **KEEP, do not move** (zj: "2 不移") | no test/CI path rewrite |
| 9 | zj-wayfinder | Keep | **KEEP, do not move** (zj: "2 不移") | pair with #8 preserved |

zj's shorthand "1 删、2 不移、3 不增" maps to the three open questions above:
(a) delete `zj-grill-with-docs`; (b) **no new skill** (the docs-bootstrap case
stays covered by ontology's proposal flow — Occam); (c) the two outside-bucket
bases (`zj-ui-core`, `zj-doc-collab`) stay as-is with a documented caveat —
"不移" read as **no relocation of any skill in this redesign**. Nothing in Q6
is applied yet; these are rulings to be executed in the red-green slice.

## Merge question — `zj-docs-ontology` ↔ `zj-docs-architecture` — Q7 (RESOLVED: NO MERGE)

zj's usage report: in practice a full governance pass is invoked as
`/zj-docs-ontology` with the prompt "做一次全面的文档治理"; the architecture
handbook is never driven as a standalone task. Question: should the two be
merged into one skill?

**Recommendation: NO MERGE.** The observed usage is already the designed
composition, not evidence of a duplicate boundary. Three 取证 reasons:

1. **The boundary is deliberate and documented on both sides**, not an
   accidental split. `zj-docs-architecture/SKILL.md:11-14` explicitly disclaims
   "a repository's whole documentation governance (`/zj-docs-ontology`)";
   `zj-docs-ontology/SKILL.md:13` says it "is not a shared-knowledge publisher
   or an automatic closeout handler". `governance-contract.md:242-256` has a
   dedicated section "What overlaps with `zj-docs-architecture`, and who owns
   it": the three shared `MAP_*` codes are "one condition seen twice",
   de-duplicated on `(code, path)`, owned by ontology; everything needing page
   contents (`PAGE_*`, `AUTHORITY_ID_*`, `SOURCE_*`, `ADR_*`) is architecture
   alone. The duplication is **tolerated on purpose** because a skill is
   installed by copying its directory and a cross-skill import breaks at
   install time — the exact constraint Q2 re-solved for *rules*. Merging the
   skills does not remove that constraint for other consumers and does remove
   the installability boundary.
2. **The PRD fixes the relationship as orchestration, not absorption.**
   `docs/prds/codebase-docs-capability.md:142`: "when a Human asks for a full
   governance pass, selectively orchestrate `zj-domain-modeling`,
   `zj-docs-architecture`, `zj-debrief` and `zj-neat-freak` **without absorbing
   their specialist workflows**." The PRD also sequences them as separate
   deliveries (`#20–#23` architecture, `#24` ontology built *over* the proven
   seam). Merging is a direct reversal of an accepted delivery contract;
   it would need an ADR, not a filing decision.
3. **Different owned questions and different consumers.** ontology owns the
   whole map + classification + lifecycle + proposal/execution, and reports
   Human-review signals; architecture owns the five complementary handbook
   views + view contracts + source-map target existence, and is the **only
   code consumer** of the shared `doc-kind`/`authority` domain (Q4/Q5 canary
   wiring depends on it). The composition is already written into ontology's
   workflow (`SKILL.md:33-40`: "Run map, link, and authority-binding checks
   and `/zj-docs-architecture` for the architecture layer"), and into the
   pipeline doc (`ta-zagentic-pipelines.md:112-113` stage 5 ontology
   orchestrating architecture, stage 6 its validator). One Human entry point
   already exists; merging skills and merging entry points are different
   moves.

**The real gap the usage report exposes — and the fix to land instead.**
The composition at `SKILL.md:33-40` is prose: nothing mechanically requires
the architecture validator to have run, or records its result in ontology's
report. That is the same class of defect as issue #264's "Step 5 skipped;
green run misread as content correct" — here at the cross-skill seam.
Per the P0 rulings' evidence-strength rule, add an explicit witness field to
ontology's report contract:

- absence of the architecture-validator result in a full-governance report →
  `EXEC_ARCH_VALIDATION_MISSING` (ERROR, mechanical fact — a named step did not
  produce its artifact), mirroring `EXEC_STEP5_ARTIFACT_MISSING`;
- validator ran but with an unexpected scope/version fingerprint → signal,
  mirroring `EXEC_STEP5_FINGERPRINT_MISMATCH` (the validator's own green is
  still not proof the architecture content is right — that stays Human review).

This keeps one Human entry point (what zj actually wants), makes the composition
mechanically observable, and avoids reversing the PRD/ADR boundary. Cost is one
report field + one fixture; far below a skill merge (which would touch the
validator path, the shared-rule canary, 7+ root tests, CI, the bucket README,
`docs/README.md`, the pipeline doc, three install copies, and re-litigate
ADR 0003/0011).

**Implementation correction + status (2026-11-18, landed in working tree):**
the analysis above proposed a new code `EXEC_ARCH_VALIDATION_MISSING`; that was
wrong — P0 Ruling 3's **Step 5 is `/zj-docs-architecture`**, so its existing
`EXEC_STEP5_ARTIFACT_MISSING` (ERROR) + `EXEC_STEP5_FINGERPRINT_MISMATCH`
(signal) already name this exact fact. A second code would recreate the
duplicate-ruler defect this task exists to remove. Implementation therefore
**reuses the two P0 codes, adds no new diagnostic code**. Landed as a red-green
slice in `docs_governance.py`: `--validate --arch-witness PATH
[--arch-fingerprint SHA256]`, an `architecture_witness` report field, and an
explicit `ERROR_CODES` allowlist. 29 governance tests + 18 quality tests + 34
root `test_*zj*` tests green; closure gate 0 ERROR / 0 WARN. Scope boundary
recorded in `proposal-tool-contract.md`: the declaration is a caller-supplied
CLI value, **not** P0 Ruling 4's tool-derived checklist (topic convention still
open at `DECISIONS.md` open item 1); a caller that omits `--arch-witness` is not
mechanically caught yet. Changes are uncommitted, in the skill's own files,
pending the bucket-redesign landing slice.

**If zj still prefers a merge despite this:** it must be filed as an ADR that
overrides the PRD's "without absorbing" clause and the governance-contract's
"tolerated on purpose" section, and must decide which owner keeps the value
-domain canary. Do not execute it as part of this bucket filing.

## Base-skill precedents in the repo (取证 — may need adjustment)

zj noted the project already has base-skill designs that may need to be brought
into alignment. Two exist, with **different** mechanisms; neither is the
publish-time inline mechanism Q2 chose.

| Precedent | What it is | Consumption mechanism | Gap vs Q2 |
| --- | --- | --- | --- |
| `zj-ui-core` (`skills/ui/`) | S0 base skill of the UI chain; owns shared **executable machinery** (`ui_skill_core.py`, `hard_gates.py`, …), `writes: []`, `precedence` below stage 1. Glossary term `Base skill` is defined from it (`ZJ-CONTEXT.md:620`). | Stage skills import/call its scripts at runtime. Contract pinned by root `tests/test_ui_agent_skills_layout.py` + `scripts/run_ui_skills_gate.sh` (required CI). | Assumes **bucket-installed together**; runtime import breaks if single-installed. No publish-time inlining. |
| `zj-doc-collab` (`skills/productivity/`) | Generic substrate for document-backed multi-agent collaboration; `zj-discuss` is a specialization. Owns parameterized engines `gate_core.py` / `launch_pack_core.py`. | Consumer `zj-discuss` **imports base scripts** at runtime (`skills/productivity/zj-discuss/SKILL.md:276-277`); base file says consumers specialise it. | Exactly the cross-skill import `governance-contract.md:253-256` warns breaks at install time under single install. No inlining. |

Implication: the new design must decide whether to (a) introduce publish-time
inlining as a **third** mechanism and leave these two alone, or (b) migrate
them to it too. zj flagged "可能需要一并调整" — this is an open sub-question,
not yet a ruling. Note that UI's base is a *contract-governed* precedent with a
required CI gate; whatever is built here should learn from its gate discipline
(assert generated artifacts actually contain the rules; fail loud when a
dependency is missing) rather than from its runtime import.

## Publish-time inline action (mechanism for Q1 + Q2 — ANALYSIS, not landed)

zj asked concretely: with the base fixed as `zj-docs-ontology`, how is the
"fixed publish action that inlines rules into each skill" handled? The answer
is constrained by two 取证 facts and has one consequence that changes how task
item 2 must be worded.

### The two facts that decide where the action runs

1. `scripts/link-skills.sh:101-136` is a **pure copy installer** — it finds
   each `SKILL.md` and `cp -r`s the folder to the three platform dirs. It has
   **no build step**, and installs from the **checked-in `skills/` tree**.
2. Under single-skill install, the device has **only that one skill folder** —
   no base skill, no generator, no sibling.

Therefore the inline action **cannot run at install time on the user's device**
(nothing to read the base from), and cannot be a runtime import. It must run
**once, on the repo side, before install**, and its output must be **checked in
as part of the skill source** so `link-skills.sh` keeps working unchanged.

### The mechanism (three pieces)

| Piece | What it is | Reused precedent |
| --- | --- | --- |
| **Rule source** | **REVISED 2026-11-18 (zj, 2nd revision): a NEW dedicated directory under `docs/` — **`docs/skill-conventions/` (zj confirmed 2026-11-18)** — freshly authored to a quality bar.** Three exclusions: (1) NOT inside any skill — avoids a shared rule hiding in an ontology-private file, "one file two owners" hidden debt; (2) NOT `canonical-preset.json` (that stays ontology-private semantic payload); (3) **NOT derived from or seeded by the existing `docs/ontology/ontology.schema.json`** — that file is an artifact of the very docs system under governance and may carry its defects; inheriting it repeats the case-2 baseline error (a flawed prior state becomes the bar and propagates). Content is authored from the Q3 取证 facts (actual consumer obligations) and judged against the preset, never copied from a prior artifact. The generator reads it at release time; humans maintain it as a long-lived authority. `docs/` is never a runtime dependency — the installed skill carries the inline block, so single-skill install still works. Directory name CLOSED (`docs/skill-conventions/`); doc-map registration still to confirm (see Open sub-questions). | `canonical-preset.json` decision (Option B) for the private half; P0 Ruling 1 v3 two-reference split — canonical preset (normative, authored) vs HEAD snapshot (observed, never the quality bar) |
| **Generator** | A repo-side script that renders the rule source into a **delimited GENERATED block** in each consuming skill's `SKILL.md` (or a sibling reference), using explicit `<!-- BASE_RULES_START/END -->` markers; replacement is idempotent. | `skills/codebase-docs/zj-roadmap-driven/scripts/roadmap.py:4503-4531` marker replacement |
| **Consistency gate** | A required CI check that re-renders from the rule source and asserts each committed block matches byte-for-byte; mismatch / missing marker / missing dependency declaration → non-zero. | `tests/test_ui_agent_skills_layout.py` manifest contract + `scripts/run_ui_skills_gate.sh` |

The publish flow becomes: edit base rule source → run generator (writes blocks
into checked-in skills) → CI gate confirms no drift → `link-skills.sh` copies
as before. A base edit that is not regenerated **fails CI**, which is the
mechanical form of zj's "result consistency" guarantee. Skills without a
dependency declaration are never touched by the generator.

### Consequence for task item 2 — wording must change

Task item 2 says dependent skills "must explicitly require the Agent to load
the base skill first and follow its rules." Read literally on a
single-installed device that is impossible: the base is not there. The
mechanism re-interprets it, and the context should carry the corrected form:

- **Declaration is build-time metadata**, not a runtime load instruction. A
  consuming skill declares a dependency (a fenced JSON block in the SKILL.md
  body — Q4/Q5 ruling below) so the **generator** knows to inline and the
  **gate** knows to verify.
- **At runtime the skill carries the rules itself** (the inlined block), so it
  is self-contained and never reaches for a base at execution time. The
  "explicit requirement" visible to the executing Agent is: follow the inlined
  rules in this skill, not "go load another skill".
- This is exactly the Q2 guarantee (runtime independence from Harness and from
  siblings) while keeping one authoritative source at development time.

### Open sub-questions introduced by this mechanism

- **Block location**: inline into `SKILL.md` directly, or into a sibling
  `references/` file that SKILL.md points at? `SKILL.md` guarantees visibility
  to the Harness; a reference file keeps SKILL.md short. **Still open** — Q4/Q5
  closed the *declaration* location (fenced JSON in SKILL.md body) but not this
  generated-block location.
- **Rule source directory + doc-map registration (zj ruling 2026-11-18,
  2nd revision)**: RESOLVED in principle — a **new dedicated directory**, never
  a reuse of `docs/ontology/`. Rejected: seeding the authority from the existing
  `docs/ontology/ontology.schema.json`. Reason (zj): that is exactly the case-2
  baseline error — if the previous docs system has quality defects, using it as
  the source and inheriting forward manufactures more defects. The new authority
  is authored from verified consumer requirements (Q3 取证), not derived from any
  existing docs artifact; any overlap with the old schema is reconciled
  deliberately, not inherited. **Directory name CLOSED 2026-11-18 (zj):
  `docs/skill-conventions/`.** Rejected `docs/skill-components/` (zj's first
  pick): `component` already means UI component catalog / `COMPONENT_REGISTRY`
  in `zj-ui-design-system` and `zj-ui-core/contracts/`, and `ZJ-CONTEXT.md:620`
  defines base skill as carrying "shared executable machinery" — the name would
  misread as reusable *code*, the exact runtime-import mechanism Q2 rejects.
  Also rejected bare `docs/conventions/` as too vague about whose conventions.
  Still open: the format (JSON machine-first vs Markdown-with-markers
  human-first — choose on merit, not to match a legacy schema). It is a
  long-lived authority needing a doc-map `authority-id` and an ontology
  `doc-kind`; never under `docs/plans/` (plan-coupling ERROR).
- **ADR 0007 / ontology.schema.json conflict (introduced by the zj revision;
  sharpened in the 2nd revision)**: `docs/ontology/ontology.schema.json:8-13`
  G_governance states the G-layer *vocabulary* is modelled there but the
  *constraint rules* are owned solely by the portable skill `zj-docs-ontology`
  — the schema deliberately has no rules, to avoid double-headed drift
  (ADR 0007). Putting the shared rules in a fresh `docs/` authority still
  reverses the "rules owned solely by the skill" half, so ADR 0007 and the
  schema's `G_governance` note must be amended: rules now have a repo-side
  authority (`docs/skill-conventions/`), the skill carries an inlined
  copy, and the schema's vocabulary model should become a pointer to that
  authority — **not** its seed (seeding from it is the rejected case-2 error).
  Take the opportunity to reconcile the model with the Q3 取证 facts explicitly
  rather than inheriting its current content. Do not leave the two representations
  to drift.
- **Generator ownership**: repo root `scripts/` (dev-time tool, not shipped in
  any skill) vs inside the base skill. Runtime closure only scans installed
  skills, so a repo-root dev tool is legitimate — confirm before building.
- **Gate placement**: add to `skill-closure-lint` (has a required job) or a new
  required workflow? Must be **unconditionally triggered** (path-filtered
  required checks caused past BLOCKED PRs).
- **Relationship to Q3**: RESOLVED below — the rule source carries the naming
  **syntax core** plus the `doc-kind` / `authority` **value domains + binding
  semantics**; it does not carry semantic payload or lifecycle/diagnostic codes.

## Shared scope — Q3 (RESOLVED 2026-11-18, zj: 取证矩阵 + option A)

Decision: the shared rule source contains exactly two layers; the boundary is
**"a value a second skill uses to constrain its own output → shared; a value
only the owner consumes → private."**

| Layer | Content | Ruling | 取证 |
| --- | --- | --- | --- |
| Naming syntax core | lowercase-hyphen, no date/sha/version/status tokens | **Shared** | `zj-docs-architecture` defines `PAGE_NAME_*`; `zj-neat-freak` audits kebab-case; `zj-docs-ontology` `<topic>` pending — three real consumers |
| Value domains + binding | 17 `doc-kind` values, 5 `authority` values, primary-has-exactly-1 `authority-id` | **Shared** | `architecture-contract.md:16,33,40` + `validator-contract.md:100-103` — architecture **consumes** the domain (its own pages declare these values and its validator enforces the binding), so it is a genuine second party, not merely "looks global" |
| Semantic payload | per-kind `Job` / `Does NOT belong` / `Must-write sections` (`kind-templates.md`, `canonical-preset.json`) | **Private** | only ontology's classify/quality flow reads it; architecture has its own "View \| doc-kind \| Must answer" table (`architecture-contract.md:47`) — different semantics; forcing one ruler onto both is the rejected "self-made ruler" trap |
| Process + diagnostics | category set (`methods`/`prds`/…), lifecycle, tombstone, `MAP_*` codes | **Private** | `zj-doc-health` only *reports retirement candidates* to ontology's path; neat-freak `retire` hits are eval-fixture noise |

Why not "naming only" (the Occam-minimal answer): the `doc-kind`/`authority`
domain is **already** a real cross-skill dependency in the repo (取证 above).
Leaving it out of the base would abandon an existing drift source — the
opposite of Q3's purpose.

**Boundary detail — option A (zj confirmed 2026-11-18, location revised same
day):** the value domain lives in **one** place. `zj-docs-architecture`'s
validator stops carrying its own hardcoded `doc-kind` enumeration and reads the
inlined copy instead — a single source of truth end-to-end. Rejected option B
(validator keeps its own enum, CI only checks the source block) was ruled out
because it relocates #264's drift to the implementation layer rather than
removing it. **Location revision (zj, 2nd revision same day):** that one place
is a **new** dedicated directory under `docs/` (zj-confirmed `docs/skill-conventions/`),
freshly authored — not `canonical-preset.json` inside the ontology skill, and
**not derived from the existing `docs/ontology/ontology.schema.json`**. Two
rationales: (1) a cross-skill shared rule in an ontology-private file has two
owners in name and one in practice — the hidden debt this redesign exists to
remove; (2) the existing schema is an artifact of the docs system under
governance and may carry its defects — seeding from it repeats the case-2
baseline error (a flawed prior state becomes the bar and propagates). Content
comes from the Q3 取证 facts; overlap with the old schema is reconciled
deliberately, not inherited. `canonical-preset.json` remains ontology-private
(the Q3 "semantic payload" layer); only the shared layers live in the new `docs/`
authority. Does not affect Q2: `docs/` is the repo-side source read at release
time, never at runtime.

## Declaration & machine checks — Q4 + Q5 (RESOLVED 2026-11-18, zj)

Two rulings close Q4 and Q5 together: they are one problem — how a per-skill
extension and a dependency declaration stay machine-verifiable.

**Ruling 1 — declaration location: a fenced JSON block in the SKILL.md body,
not frontmatter.** Frontmatter carries Harness scheduling fields (`name`,
`description`, `source`); adding contract keys there risks semantic pollution.
The repo already has a parsed, gate-pinned precedent: UI's `## Capability
Manifest` fenced JSON block, parsed key-by-key by
`tests/test_ui_agent_skills_layout.py:95-104`. The declaration has two classes
because they feed different machines:

| Key | Feeds | Meaning |
| --- | --- | --- |
| `consumes` | generator + gate | which shared core keys this skill inlines; drives which block to render and which block to verify. Must be a subset of the shared core's fixed key set. |
| `extensions` | gate ban-list | this skill's private terms — architecture's `ta-/ba-/pa-` prefix, `<topic>`'s batch token. Any of them found in the shared source or an inlined block → non-zero. This is the core/extension split's authoritative form (Q4). |

**Ruling 2 — check 3 strength: canary mutation test, built now (zj: "once and
for all"), not deferred to implementation.**

### The three machine checks

| # | Check | Method | Failure it catches |
| --- | --- | --- | --- |
| 1 | Closed schema | shared core key set is fixed; `consumes` ⊆ core; any `extensions` term appearing in the shared source or an inlined block → non-zero | extension leaking into shared (Q4's core fear) |
| 2 | Byte-equal re-render | re-render each consuming skill's `<!-- BASE_RULES_START/END -->` block from the rule source; compare byte-for-byte to the committed block (Q1 mechanism) | block drift, missed generation |
| 3 | Validator binding — **canary mutation** | temporarily inject a fake `doc-kind` into the rule source, re-render the architecture block, then run the validator against a fixture page declaring that fake value; require the validator to **accept** it (only possible if it read the mutated block). If it still rejects, the hardcoded enum is still in force → non-zero. Restore after. | hardcoded enum "deleted but reader never wired" — a fake green |

### Why check 3 must be a canary, not a grep

取证:
`skills/codebase-docs/zj-docs-architecture/scripts/validate_architecture_docs.py:20-33,274`
hardcodes the `doc-kind` / authority enums. Q3 option A requires deleting these
and reading the inlined value domain instead. If the gate only asserted "the
enum literals no longer appear in the script", deleting the enum while
forgetting to wire the reader would pass — the `checked==0` / "ERROR text +
exit 0" fake-green pattern already recorded in project memory. The canary tests
**causality**: mutate the shared source → validator behaviour must follow. That
is the only mechanical evidence the reader is genuinely connected.

Cost (accepted by zj): the canary needs generator + validator to run together
inside the test, so both must be independently callable; slower than a static
grep. Architecture is the only code consumer of the value domain
(`zj-neat-freak` only audits kebab-case), so only one binding needs wiring.

### Minimal schema (subject to implementation-time refinement)

```json
{
  "consumes": ["naming-syntax-core", "doc-kind", "authority"],
  "extensions": ["page-prefix:ta-/ba-/pa-", "topic-batch-token"]
}
```

Declaration and generated block are distinct: the declaration is
human-authored metadata; `BASE_RULES_*` is generated content. Both live in the
installed skill (declaration in SKILL.md body), so runtime stays self-contained.

## Design questions to resolve (open — this is what "refine the context" means)

These are unresolved. The document is not ready to act on until they have
answers. Ordered by dependency.

1. ~~**Base skill identity.**~~ **RESOLVED 2026-11-18 (zj): designate
   `zj-docs-ontology`.** It already owns the whole map, the governance loop,
   and `canonical-preset.json`; under the Repo-context method one skill
   suffices — no new skill. It becomes the **authoritative rule source**
   during development only. See "Publish-time inline action" below for why the
   base need not exist on a user's device at runtime. The two existing bases
   (`zj-ui-core`, `zj-doc-collab`) are handled separately in Q6.
2. ~~**Runtime loading mechanism.**~~ **RESOLVED 2026-11-18 (zj).**
   **Publish-time inline generation.** Add a fixed publish action that inlines
   the base skill's rules into each dependent skill's published artifact.
   Guarantees, in zj's words:
   - at runtime on the user's device, the repo's skills are **mutually
     independent and do not depend on Harness behaviour**;
   - during development, any base-skill edit syncs into every published
     artifact, keeping **result consistency**.
   This rejects both runtime import (breaks on single install) and prose "load
   base first" (invisible on single install). The generated copy, not a path to
   the base, is what each installed skill carries. See the base-skill precedents
   section below — neither existing precedent uses this mechanism; it must be
   built.
3. ~~**What exactly is shared.**~~ **RESOLVED 2026-11-18 (zj): shared =
   naming syntax core + `doc-kind`/`authority` value domains and binding;
   private = semantic payload (`kind-templates.md`, `canonical-preset.json`
   per-kind fields) + category/lifecycle/tombstone/`MAP_*`.** Boundary option A
   confirmed: value domain lives once; the architecture validator reads the
   inlined copy, dropping its own hardcoded enumeration. **Location revised
   (zj, same day, 2nd revision): the single source is a NEW dedicated `docs/`
   directory (zj-confirmed `docs/skill-conventions/`), freshly authored — neither the
   ontology-private `canonical-preset.json` nor derived from the existing
   `docs/ontology/ontology.schema.json`.** Rationale: the existing schema may
   carry the very quality defects this bucket exists to fix; inheriting it as a
   baseline manufactures more defects (case 2 of the P0 baseline ruling). See
   "Shared scope — Q3" above. Does **not** re-litigate Option B —
   `canonical-preset.json` stays ontology-private; only the shared layers live
   in the new docs authority. Conflict to resolve: ADR 0007 /
   `ontology.schema.json` G_governance says rules are skill-owned and the schema
   only models vocabulary — amend it, and make the schema point to the new
   authority rather than seed it.
4. ~~**Rule granularity — shape largely settled by Q3; mechanism still open.**~~
   **RESOLVED 2026-11-18 (zj): the core/extension split is enforced by check 1
   (closed schema).** `consumes` must be a subset of the shared core's fixed key
   set; any `extensions` term (architecture's `ta-/ba-/pa-` prefix, `<topic>`'s
   batch token) found in the shared source or an inlined block → non-zero.
   See "Declaration & machine checks — Q4 + Q5" above.
5. ~~**Dependency declaration format.**~~ **RESOLVED 2026-11-18 (zj): a fenced
   JSON block in the SKILL.md body** (UI `## Capability Manifest` precedent,
   `tests/test_ui_agent_skills_layout.py:95-104`), not frontmatter. Declares
   `consumes` (which core keys — drives generator + gate) and `extensions`
   (ban list — drives check 1). Build-time metadata, not the impossible runtime
   "load base first". Validator binding is pinned by the check-3 canary. See
   "Declaration & machine checks — Q4 + Q5" above.
6. ~~**Re-sort decisions.**~~ **RESOLVED 2026-11-18 (zj): 1 delete
   (`zj-grill-with-docs`), 2 no move (all nine stay in place), 3 no new skill
   (outside-bucket bases unchanged with a caveat).** See "Re-sort analysis —
   Q6" above for the per-skill rulings table. Not yet applied to the repo.
7. ~~**Merge question — ontology ↔ architecture (Q7).**~~ **RESOLVED 2026-11-18
   (zj): NO MERGE + add a witness field.** The two skills stay separate; the
   composition gap is fixed inside ontology's report contract, not by moving
   skill boundaries. See "Merge question" section below.
8. **Relationship to issue #264 P0.** The `<topic>` naming open item becomes a
   dependency of this task, not an independent ruling. Decide whether to close
   that item as "deferred to bucket redesign" and how to cross-link without
   creating a durable-doc → plan-coupling ERROR.

## Close-out plan (not now)

1. Human refines this context until design questions are answered.
2. Red-green landing of the chosen design in the repo (TDD, small slices).
3. Apply the updated `zj-docs-ontology` to archive durable conclusions here
   into: `docs/zj-adr/` (architecture decision), bucket README, affected SKILL.md
   / reference files, and `ZJ-CONTEXT.md` for any new terms.
4. Clean up this `docs/plans/` file per ADR 0010 once its content is absorbed.

## Source map

- Issue #264: `gh issue view 264 --repo jununfly/ZAgentic`
- P0 rulings (process material): `tmp/skills-outputs/zj-docs-ontology/p0-decisions/DECISIONS.md`
- Bucket index: `skills/codebase-docs/README.md`
- Naming rules: `skills/codebase-docs/zj-docs-architecture/references/architecture-contract.md`
- Cross-skill install rule: `skills/codebase-docs/zj-docs-ontology/references/governance-contract.md`
- Closure gate bases: `scripts/check-skill-runtime-closure.py`
- Persistence/plan discipline: `docs/zj-adr/0010-local-file-persistence-convention.md`
- Install mechanism (pure copy, no build step): `scripts/link-skills.sh:101-136`
- Idempotent generated-section precedent: `skills/codebase-docs/zj-roadmap-driven/scripts/roadmap.py:4503-4531`
- Manifest consistency gate precedent (fenced JSON parse): `tests/test_ui_agent_skills_layout.py:95-104` + `scripts/run_ui_skills_gate.sh`
- Architecture validator hardcoded value domains (to be replaced by inlined read): `skills/codebase-docs/zj-docs-architecture/scripts/validate_architecture_docs.py:20-33,274`
- Q7 merge evidence: `scripts/zagentic-skills-list:25`; `docs/prds/codebase-docs-capability.md:142-156,233-234,291`; `skills/codebase-docs/zj-docs-ontology/references/governance-contract.md:242-256`; `skills/codebase-docs/zj-docs-architecture/SKILL.md:11-14`; `docs/architecture/ta-zagentic-pipelines.md:112-113`
