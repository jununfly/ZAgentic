# ZJ-CONTEXT.md

Project domain glossary for `jununfly/ZAgentic`. Owned by `zj-domain-modeling`.
Updated inline as decisions crystallise, per the format in
`skills/codebase-docs/zj-domain-modeling/CONTEXT-FORMAT.md`.

## Language

### Skills meta

**Skill bucket**:
A public purpose-based directory under `skills/` — `engineering/`,
`codebase-docs/`, `productivity/`, `ui/`, `misc/`, or `research/`. Each bucket
has its own `README.md` listing its skills with a one-line description. See
`AGENTS.md` for the bucket policy.
_Avoid_: category, folder, group

**Installed-copy drift**:
已装副本漂移。`~/.workbuddy/skills/<name>/`（扁平安装桶）里的副本与仓库源码
`skills/<bucket>/<name>/` 长期不同步的状态。更新只能走「删-重装」——scanner
启动即扫并内存缓存、无 fs.watch，所以改了源码不重装就不会生效；而跳过重装时
WorkBuddy **不报错**，技能照常出现在发现列表里，漂移因此是静默的。判据：对比
已装 `SKILL.md` 的字节数与 `scripts/` 清单。
_Avoid_: sync, update, refresh（这些暗示存在增量机制，实际没有）

**Pair Decision entry**:
The `## Decision` record in a merge wave pair task's context-md (zj-dp-driven
corpus), holding the strategy (`strict-align` / `absorb` / `adopt` / `replace` /
`reject`), the source path, and the base path. `zj-merge-skill-pair` consumes
exactly this record; a strategy not written here did not happen.
_Avoid_: roadmap decision, node decisions, decision note

**Seam**:
A point where work passes between actors or stages — a place the test must
cover, the spec must declare, and the commit message must call out. Seams are
"the only thing TDD should aim for" (per 1-3-1's absorption of B's `tdd`).
_Avoid_: boundary, interface, contract (in this specific engineering sense)


### Codebase documentation

**Codebase docs**:
The documentation system belonging to one codebase: its document map,
long-lived authorities, process material, evidence-surface boundaries and
governance loop. It is not a cross-project knowledge store.
_Avoid_: documentation dump, shared evidence repository

**Document map**:
The reader-facing routing page that names a codebase's documentation categories,
their primary questions, authority boundaries, lifecycle and entry points.
_Avoid_: document manifest, duplicate README, site map

**Long-lived document**:
A maintained authority that states a stable entity, connection, fact or rule for
a codebase. It excludes execution status and other temporary process context.
_Avoid_: permanent note, process log, current task record

**Process material**:
Documentation that carries dynamic planning, execution focus, decisions or
observability while work is active. Durable value is extracted before the
material is proposed for deletion.
_Avoid_: long-lived authority, disposable scratch by default

**Evidence surface**:
Code, tests, fixtures, traces, research packages or evaluation output that can
support a document claim without becoming a long-lived documentation page.
_Avoid_: documentation category, authoritative prose

**Authority boundary**:
The bounded question for which one documentation page or category is the
maintained answer. Contradictory normative answers are a Human-review signal,
not an automatic precedence decision.
_Avoid_: global document hierarchy, newest-file-wins

**Authority ID**:
A stable identifier that the document map binds to exactly one primary page and
the bounded question it answers. It gives documentation validation a mechanical
ownership seam without making prose similarity the source of truth.
_Avoid_: page title, path-derived status, heuristic duplicate detector

**Document contract**:
The minimal machine-checkable header and category-specific readable sections a
governed documentation page supplies. It identifies kind and authority while
the body answers the page's bounded question.
_Avoid_: metadata-only document, prose-only implicit contract

**Architecture handbook**:
The architecture layer of a codebase documentation system: one routing map and
complementary overview, layer, subsystem, flow, and cross-cutting views with
explicit source maps.
_Avoid_: duplicated architecture essay, code inventory

**Architecture map**:
The reader-facing routing page of an architecture handbook. It links each
architecture view once and states that view's bounded question; for a primary
view the same list item also carries its `authority-id`. The map routes; it does
not restate the views it points at.
_Avoid_: parallel manifest, duplicated architecture essay, site map

**Architecture view**:
One of the five complementary page kinds an architecture handbook uses:
`architecture-overview`, `architecture-layers`, `architecture-subsystem`,
`architecture-flow`, and `architecture-cross-cutting`. Each view answers one
bounded question and is named with a `ta-`, `ba-`, or `pa-` file prefix.
_Avoid_: architecture page, generic document, diagram

**View contract**:
The view-specific headings one architecture view must supply in addition to the
common `Question` / `Scope` / `Boundaries` / `Source map` / `Related authority`
sections. Example: a flow view must supply trigger, sequence, state and effects,
failure or exit behavior, and observable evidence.
_Avoid_: page template, optional heading list

**Source map target**:
A path named under a page's `## Source map` heading — code, tests, fixtures, an
accepted ADR, or a stable external reference. The validator checks that the
target resolves from the repository root, so source-map entries use
root-relative paths rather than paths relative to the owning skill.
_Avoid_: bare skill name, unresolvable path, evidence payload

**Concept map (face A / B / C)**:
`zj-docs-architecture`'s own three-view model of its concepts. Face **A** is the
code side: `@concept:` markers embedded in source that declare a concept exists.
Face **B** is the concept-map artifact — the single machine block generated from
A and the authority `--consistency` reads. Face **C** is the architecture content
pages that document a concept in prose. The three are solved against one another
to surface drift. B is architecture's OWN artifact, distinct from the repo
**Document map** / **Architecture map** it consumes (that one is owned by ontology).
_Avoid_: concept index, the repo doc-map, document map

**Concept kind**:
The closed vocabulary of a concept on face B — the slug of each entry under
`## Maintenance triggers` in `references/architecture-contract.md`, mirrored by
`CONCEPT_KINDS`. A concept carries exactly one kind; an unknown kind is rejected
rather than invented. It is enforced against drift by `ConceptVocabularyTest`.
_Avoid_: doc-kind, Architecture view (the page-kind vocabulary is a separate enum)

**Consistency signal**:
One of the four advisories `--consistency` emits while joining faces A/B/C:
`CONSIST_UNDOC` (a B concept anchored in code that no architecture page cites in
its Source map), `CONSIST_ORPHAN_DOC_CLAIM` (a page claims a concept absent from
code-derived B), `CONSIST_OWNER_MISMATCH` (a declared owner page does not
externalize the concept), and `CONCEPT_CYCLE` (a part-of decomposition that is not
a DAG — B-internal well-formedness, needs no page). All four are signal-only: they
never enter the ERROR set and never gate the exit code. A status token written after
a page's concept claim (`:target`, `:implemented`, …) is echoed as context only — it
is never validated against a fixed set and never exempts a signal. A B that cannot be
parsed (unclosed fence, absent block, or invalid JSON) surfaces separately as
`CONCEPT_MAP_MALFORMED` — an input-integrity precondition that suppresses the four
drift checks rather than joining them, so it never rides alongside them.
_Avoid_: consistency error, a gate, a status enum to validate against, a drift signal

**`@concept:` marker**:
The face-A grammar that declares a concept in source:
`@concept: <kind> <id> [--anchor=<loc>] [--owner=<authority-id>] [--part-of=<id>[,<id>…]]`,
one marker per concept (several may share a line). The attributes are order-fixed —
a flag written out of position is silently dropped, not an error. `format_concepts`
(formatter, A→B) scans the whole repo for these markers to regenerate B deterministically.
_Avoid_: free-form tag, order-independent attributes

**`tacm-` page-prefix**:
The prefix reserved for the concept-map **B** artifact
(`docs/architecture/tacm-map.md`, the skill's `CONCEPT_MAP_FILE`). It names a model
artifact, not a content view: `tacm-` is deliberately outside the `ta-` / `ba-` /
`pa-` content-page family, so a `tacm-` file never runs through the content-page
naming gate and is reached only by `--consistency`. Declared in this skill's
`extensions`, and — by design — kept out of the shared `core` so it cannot leak into
the BASE_RULES block.
_Avoid_: content page, a fourth view prefix (ta-/ba-/pa- are the only content prefixes)

**Bucket discipline**:
The cross-cutting rule that a skill's discoverability depends on exactly three
things: its bucket is its public entry, the root-level `personal/` tree is a
parallel path rather than a seventh bucket, and no architecture page duplicates a
design or ADR authority. Every architecture view consumes this rule.
_Avoid_: bucket policy, folder convention

**6 + 1 model**:
The shape of the ZAgentic skills collection: six public purpose-based buckets
under `skills/` plus one root-level `personal/` tree that is installable but
outside plugin discovery and public indexes.
_Avoid_: five buckets, personal bucket

**Repository collaboration setup**:
The tracker, triage-vocabulary, and Agent-entrypoint configuration established
by `zj-repo-init` after a documentation map has been selected.
_Avoid_: documentation-system bootstrap, implicit docs migration

**Personal skill tree**:
The root-level `personal/` directory for skills tied to the user's own setup.
It remains installable through the local scripts but is outside plugin discovery
and public README indexes.
_Avoid_: personal bucket, public skill

**Composer / 组合器**:
The thin intent-to-Plan capability approved for ZAgentic. It reads a user's goal,
constraints, available skill/workflow metadata, evidence requirements, and
permission boundary; it returns a reasoned candidate composition, bounded
suggestions, or one `required skill：...` line per missing capability. It does
not own approved execution, irreversible side effects, or durable governance.
_Avoid_: global router, executor, session runtime

**Task Plan / Plan**:
A versioned, reviewable task contract generated from the Composer skill's
built-in template. It records selected capabilities, reasons, order,
dependencies, Human checkpoints, verification, failure exits, rollback, and
provenance. It does not own execution or
long-term authority.
_Avoid_: executor, runtime state

**Plan validator seam**:
The deterministic artifact boundary that checks an external Composer Plan's
v1 schema, capability reasons, snapshot provenance, gap syntax, dependency
assessment, Human approval, authority, and side-effect gates. It emits stable
diagnostic categories and never executes the Plan.
_Avoid_: Composer executor, second runtime, narrative-only review

**Capability snapshot**:
The immutable, content-addressed Composer view of the recursively discovered
public skill catalog. It preserves each capability's source reference, declared
inputs/outputs/dependencies/boundaries, declaration checks, and metadata warnings.
_Avoid_: second registry, rewritten skill contract

**Class-scoped provenance mapping**:
A `source_references` entry that binds one represented capability class to its
source: selected, excluded, suggested, or gap. The mapping makes provenance
coverage mechanically checkable instead of relying on an unstructured source list.
_Avoid_: generic references, selected-only provenance

**Template version binding**:
The registry entry that binds a Composer `template_version` to the exact
SHA-256 of its bundled Plan template. Template content changes require a new
version rather than silently changing the meaning of an existing Plan.
_Avoid_: template label, mutable v1 template

**Handoff eligibility**:
The validator-derived result that a Plan has no hard errors, is approved by the
Human, and has passed Plan acceptance. A stale selected source remains
ineligible until regeneration or an explicit stale-source review marker.
_Avoid_: Plan validity, automatic execution, dispatch

**Skill**:
A single unit of agent capability under
`skills/<bucket>/zj-<name>/SKILL.md` or `personal/zj-<name>/SKILL.md`.
A skill is the smallest thing this repo ships, but a single **merge wave** can
touch many of them at once.
_Avoid_: command, plugin, tool

**Skill-pair**:
The (base, source) tuple that one merge action operates on — a `Skill` in this
repo matched with one or more `Skill`s in a source skills collection. Multiple
sources per base are allowed; the merge result is decided by `zj-merge-skill-pair`
on a per-pair basis.
_Avoid_: bundle, package, group

**Merge wave**:
A whole planned set of skill-pairs, generated by `zj-merge-skills-wave`, laid
out as zj-dp-driven tasks (one task per skill-pair, one `## Decision` entry per strategy).
A wave is the unit of planning; a single skill-pair is the unit of execution.
_Avoid_: batch, run, sweep

**zj- naming**:
The `zj-` prefix applied to every skill name in this repo. Prevents collision
with upstream skills collections (e.g. `upstream/skills`) that share names.
_Avoid_: underscore, hyphen-separated, namespace

**Name-field coupling**:
A skill's directory name, its frontmatter `name:` field, and its invocation
name `/zj-<name>` must stay identical — the WorkBuddy scanner routes by the
frontmatter `name:`. Renaming a skill is therefore a three-way coordinated
change (mv the dir, update frontmatter, update all references), verified by grepping the old
name down to zero repo-wide (append-only history logs exempt).
_Avoid_: rename-in-place, dir-only rename
- **Runtime alias exception (board-approved, retired 2026-09-09)**: installed copies
  under `~/.codex/skills/` and `~/.workbuddy/skills/` were once allowed to keep a
  legacy directory name (`zj-research-report`) while SKILL.md `name:` stayed canonical
  (`zj-tech-research-report`); each copy carried an `ALIAS.md`, and the exception was
  ratified in `docs/zj-adr/0004-research-report-improvement-scope.md`. On 2026-09-09 the
  alias copies were deleted — no remaining path referenced them, and the copies had
  drifted from canonical — so the exception is **retired**: installed copies now use the
  canonical directory name, and Name-field coupling holds without exception.
  _Avoid_: reintroducing a directory/name divergence for path compatibility

**Evidence Compiler**:
The versioned research component that accepts one shared comparison brief, fixes every repository to a commit, performs bounded source reads, and returns a **Sealed ledger**. `zj-research` reaches it through the **Research CLI protocol** rather than reproducing collection logic in a prompt.
_Avoid_: research agent, GitHub scraper, report generator

**Shared research runtime seam**:
The canonical `zj-research/scripts/` adapters used by research consumers. They
own the protocols and validation, but carry no compiler: the executable comes
from the caller's **External compiler pointer**. A sibling `zj-research` skill is
the default adapter runtime; an independently installed consumer resolves the
same implementation through `ZJ_RESEARCH_RUNTIME` rather than copying adapters.
_Avoid_: duplicated adapter, report-local compiler, prompt-only fallback, bundled compiler

**Sealed ledger**:
An immutable `zj-verified-evidence-ledger/v1` result containing **Canonical evidence**, uncovered repository/criterion pairs, navigation diagnostics, and the normalized brief fingerprint. Reports may cite it but cannot add evidence to it.
_Avoid_: notes, findings file, source dump

**Canonical evidence**:
A source excerpt read from a repository at a fixed commit, identified by repository, commit, path, URL, and Evidence ID. It can support a report claim; **Derived navigation** cannot.
_Avoid_: search result, hint, summary

**Derived navigation**:
Non-authoritative candidate paths produced by DeepWiki or deterministic heuristics. It controls where the Evidence Compiler reads next but never becomes report evidence.
_Avoid_: evidence, citation, source

**Report IR**:
The versioned `zj-research-report-ir/v1` graph linking Evidence IDs to claims, comparisons, metrics, diagrams, and recommendations. The compiler validates references before producing the Markdown fact source.
_Avoid_: Markdown template, report outline, prose draft

**Technical Decision Brief**:
The `technical-decision-brief/v1` alignment input that fixes the user/job,
baseline, target outcome, goals, non-goals, constraints, assumptions, lifecycle
stage, decision scope, and serious options before a technical Report IR ranks
solutions.
_Avoid_: report summary, implementation plan, candidate ranking

**Technical Research Quality Gate**:
The `technical-research-quality-gate/v1` mechanical check owned by
`zj-tech-research-report`. It validates a Technical Decision Brief against a
sealed ledger and `technical-c4/v1` Report IR before compiler publication,
including evidence links, candidate score copying, critical claims, diagrams,
comparisons, metrics, the **Risk Register**, and explicit unknown follow-ups.
_Avoid_: design review, human sign-off, semantic quality score

**Risk Register**:
The `riskRegister` field of a `technical-c4/v1` Report IR: a non-empty list of
the risks that survive the recommendation, each carrying `risk`, `trigger`,
`impact`, `mitigation`, `residualRisk`, and `owner` — all six required and
non-empty. A mitigation that restates the risk is rejected; the gate compares
content only, so punctuation, spacing, and case cannot buy a pass. Placeholders
such as `TBD` or `待定` in any field are also rejected. Paraphrase that names no
mechanism escapes the gate and is a review responsibility, not a gate check.
This is KEP-753 step 4, kept separate from the validation plan so residual
ownership stays explicit. The externally supplied compiler does not render it — see
**Risk-register coverage**.
_Avoid_: risk prose, risk section, recommendation follow-up, risk table

**Risk-register coverage**:
The `riskRegisterCoverage` check inside the Technical Research Quality Gate. It
passes only when the Report IR carries a fully populated Risk Register, and
reports the entry count as `counts.riskRegister`. It is a contract check, not a
render: the compiler that produces Markdown is supplied by the caller through
`ZJ_RESEARCH_CLI`, outside this repository, and it does not render
`riskRegister`. Passing the check therefore does not make the
register visible to a reader; the rendered surface is `recommendations`.
_Avoid_: risk review, human risk sign-off, rendered risk table

### Agent coordination

**Activation**:
A bounded, task-agnostic request carrying a fresh `activation_id`, stable Agent
profile, and explicit project scope through one discovery and at most one claim.
It is routing context; it does not select a Work Item by name or imply that
execution succeeded.
_Avoid_: task prompt, retry, execution attempt

**Agent profile**:
The stable identity and capability/permission set an Agent supplies to one
activation, including its `agent_id`, `device_id`, capabilities, permissions,
and review ability.
_Avoid_: model identity, repository owner, Work Item assignment

**Work Item**:
The coordination-plane unit an activation may discover and claim, carrying an
objective, acceptance conditions, and the lifecycle state needed for one
bounded handoff. It is separate from the Issue
tracker Issue.
_Avoid_: ticket, execution attempt

**Activation receipt**:
The structured result returned by the activation runner. It is the source for
activation status, handoff, next action, evidence, and event-recording state;
only a `claimed` receipt authorizes continuation of its handoff.
_Avoid_: repository summary, inferred claim, completion report

### Research architecture

**Graph Coordinator**:
The responsibility unit that coordinates graph execution and delegates work;
it does not automatically own product authority, evidence truth, Human
acceptance, or lifecycle closeout.
_Avoid_: framework core, agent platform

**Unit capability**:
A narrow, independently testable capability that can be composed behind a
seam without importing the source project's whole product semantics or
ownership model.
_Avoid_: feature copy, platform adoption

**Native semantic owner**:
The system that remains authoritative for the product's durable facts,
responsibility boundaries, and lifecycle decisions after an external
capability is composed.
_Avoid_: host framework, integration wrapper

**Adapter-only reuse**:
An adoption mode in which an external project is used behind a reversible
adapter and conformance fixture while the native semantic owner remains the
source of truth.
_Avoid_: framework-core adoption, embedded platform

**Research CLI protocol**:
The `zj-research-cli/v1` stdin/stdout JSON protocol between ZAgentic skills and any externally supplied compiler implementation. A missing or incompatible executable fails loudly; there is no bundled fallback or prompt-only path for technical comparisons.
_Avoid_: shell wrapper, internal API, compatibility mode

**GitHub quota preflight**:
A read-only check of GitHub authentication mode and API core quota before a
fresh multi-repository collection. It may permit anonymous collection when
quota is available, but it blocks a run when the observed quota or credential
state cannot support collection.
_Avoid_: best-effort probe, implicit retry

**Collection run status**:
The durable boundary record for one research collection attempt. It names a
fresh collection, an explicitly reused matching sealed ledger, or a blocked
collection, and keeps the current brief separate from any older ledger.
_Avoid_: ledger, compiler result, fallback result

**External compiler pointer**:
The `ZJ_RESEARCH_CLI` / `ZJ_RESEARCH_EVAL_CLI` environment variables through which the caller supplies a `zj-research-cli/v1` / `zj-research-eval-cli/v1` implementation. `zj-research` bundles no compiler, pins no upstream version, and refuses to run when a pointer is unset; choosing and upgrading the compiler belongs to the caller.
_Avoid_: compiler artifact lock, bundled tarball, PATH fallback, vendored source

**Research evaluation assets**:
The immutable rubric set, per-case human annotation set, and blind-Judge calibration set resolved by one versioned keyless corpus. Every quality case resolves to human truth, and only a calibrated Judge configuration contributes results to a quality baseline.
_Avoid_: mutable benchmark, Judge-only truth, unique recommendation answer

**Code-repository research**:
A technical research method that first builds a commit-scoped repository landscape, then performs a targeted architecture deep-read before optionally feeding a technical decision report.
_Avoid_: code tour, repository summary

**Repository Map**:
The breadth-first, commit-scoped orientation artifact for a code repository: structure, packages, integration layers, workflows, measured inventory, and navigable research targets. It is a map, not an analytical conclusion.
_Avoid_: directory dump, architecture report

**Repository Map target**:
A deterministic, bounded navigation record naming one repository path or
surface worth reading next, with a stable ID, target kind, and reason. It
guides Architecture Study scope but is not evidence of a capability or design.
_Avoid_: architecture claim, capability score, search hint

**Architecture Study**:
The depth-first, evidence-linked study of selected repository layers or flows, explaining module relationships, interfaces, runtime interactions, ownership, design choices, risks, and unknowns.
_Avoid_: code walkthrough, architecture essay

**Architecture Study bundle**:
An immutable `architecture-study` snapshot artifact whose manifest points to
independently readable scope, evidence, relationship, flow, claim, unknown,
and risk shards; Markdown/HTML are generated views rather than the fact source.
_Avoid_: architecture Markdown, monolithic architecture JSON

**Study record kind**:
The required certainty classification for an Architecture Study record:
`observed` (directly read source fact), `inferred` (evidence-backed deduction),
`unknown` (not established by the current evidence), or `decision` (a research
scope/follow-up choice, not a source fact).
_Avoid_: confidence-only label, unqualified architecture claim

**Code-research quality rubric**:
The versioned evaluation contract for code-repository research. `landscape/v1`
evaluates Repository Map coverage and navigation; `deep-read/v1` evaluates
Architecture Study fidelity and evidence-linked interpretation. The two results
remain dimensional rather than collapsing into one quality score.
_Avoid_: code-research score, report-quality rubric

**Code-research quality fixture corpus**:
The separate `code-research-quality/v1` controlled cases for `zj-code-research`:
balanced and sparse Repository Maps plus runtime and insufficient-evidence
Architecture Studies. Each case supplies a fixture source tree and human-coded
required properties; it is not a golden prose answer and is independent from
technical-report evaluation assets.
_Avoid_: technical-report fixture, demo repository, golden Markdown

**Real plan corpus**:
A read-only collection of existing Markdown planning documents used to verify a
planning workflow without treating Markdown as a fact source. Validation
may derive a temporary fixture from the corpus, but migration never
writes back to the source documents.
_Avoid_: Markdown-import source

**Code-research semantic baseline**:
The calibrated Judge agreement result for the code-research fixture corpus. It
records score mean absolute error, within-tolerance rate, recommendation
agreement, and risk-count error before semantic quality results are trusted.
It is a calibration gate, not an aggregate quality score.
_Avoid_: code-research score, Judge-only truth, pass rate

**Mechanical hard gate**:
An automated validity condition that must pass before semantic quality results
are considered: source pinning, scope accounting, artifact references, target
binding, evidence links, explicit unknowns, and reproducible output.
_Avoid_: quality impression, Judge-only approval

**Controlled-quality fixture**:
An immutable repository snapshot plus expected structural and semantic
annotations used to calibrate and evaluate a research-quality rubric. It tests
quality dimensions and invariants, not identical generated prose.
_Avoid_: demo repository, golden Markdown

**Conformance fixture**:
A shared, bounded scenario set with expected native facts used to compare a
native execution path and an adapter path. It checks semantic identity,
recovery, Evidence binding, authority boundaries, and removal behavior rather
than rewarding framework-specific output.
_Avoid_: framework demo, feature checklist, adapter-only test

**Resume oracle**:
The native identity and invariant set that defines what a resumed execution
must preserve — work item, attempt, state digest, Evidence linkage, and Human
acceptance boundary — so an external checkpoint implementation cannot redefine
product semantics.
_Avoid_: framework checkpoint, latest state copy, restart heuristic

**Snapshot artifact bundle**:
An immutable, versioned set of generated research facts split into a small manifest and independently readable shards, with derived human views and disposable indexes kept separate from the canonical facts.
_Avoid_: monolithic JSON, mutable report file

**Current pointer**:
A small reference that identifies which immutable snapshot is the active one for a research artifact; it can change without rewriting historical snapshots.
_Avoid_: latest copy, in-place history

**Technical design review**:
A decision-focused design document that traces a user problem and target outcome through constraints, alternatives, architecture, ownership, risks, validation gates, rollout, and follow-up. It is a review artifact; it does not authorize implementation by itself.
_Avoid_: implementation plan, feature checklist, architecture essay

**Review gate**:
An explicit observable threshold or decision condition that determines whether a design can proceed, pause, roll back, or be revised. A gate names evidence, owner, and exit action.
_Avoid_: vague confidence, sign-off, success hope

**Short-read acceptance**:
A human review gate where a reviewer reads a design briefly, without validator output, and recovers the decision, blocking finding and owner, and next validation action with threshold and owner. It tests whether the document makes its critical path legible, not whether the prose is stylistically polished.
_Avoid_: skimming, automated approval, prose review

### UI delivery

**UI delivery chain**:
The ten-stage route `S1 brief → S2 discover → S3 direction → S4 design system →
S5 flow → S6 prototype → S7 visual review → S8 break → S9 verify → S10 handoff`,
implemented as one skill per stage in the `ui/` bucket. It is a chain, not a
menu: each stage consumes the previous stage's artifact revision.
_Avoid_: UI pipeline, design workflow, frontend process

**Experience Version**:
The single form/approval sample flow that the chain is validated against. It
bounds scope: the skills are proven on one path before any cross-framework
generalisation is claimed.
_Avoid_: pilot project, demo app, template

**Canonical UI artifact**:
One of the six ZAgentic-owned artifacts the chain writes — `UI-BRIEF.md`,
`UI-DESIGN.md`, `ui-flow/v1`, `review record`, `verification receipt`,
`handoff`. Each has exactly one write owner per field; an adapter may only
submit a projection carrying its source revision.
_Avoid_: output file, generated doc, external schema

**Capability manifest**:
The 16-field block at `## Capability Manifest` in every `ui/` SKILL.md
(`skill_id`, `manifest_version`, `stage`, `owner_scope`, `writes`, `reads`,
`input`, `output`, `forbidden`, `dependencies`, `required_capabilities`,
`stop_conditions`, `owner`, `precedence`, `failure_fixtures`, `human_gate`).
It is machine-read JSON, not prose: a missing field means the skill is not
loadable.
_Avoid_: skill metadata, config, frontmatter

**Write owner**:
The single skill allowed to write a given `(stage, artifact_kind)` pair. Zero or
two owners is `BLOCKED_OWNER_CONFLICT` — no plan is generated and nothing is
written; ownership is never resolved by precedence or by discovery order.
_Avoid_: primary writer, default owner, best-effort owner

**Direction card**:
A comparable visual-direction candidate (colour, type, density, motion, fit,
trade-offs, provenance) that a Human chooses between. Selection is a Human
gate because taste is not formalisable; the skill never defaults to the first
card.
_Avoid_: theme preset, style option, template

**ui-flow/v1**:
The semantic flow artifact whose six meanings — `screen`, `component`, `state`,
`action`, `intent`, `acceptance` — must stay distinct and survive a semantic
round-trip. Merging any two is a hard fail, and no external protocol may own it.
_Avoid_: wireframe, prototype spec, canvas model

**Unknown quartet**:
The four fields that keep a gap honest — `path`, `raw`, `reason`, `source`. A
missing value is recorded, never filled with a guess and never collapsed to
empty.
_Avoid_: empty value, TBD, default

**Verification receipt**:
The replayable record that binds claim, threshold, command, commit, fixture and
environment hash, artifact and status. A receipt missing any link field is not a
successful receipt, and stale evidence is marked `revalidation_required` rather
than reused.
_Avoid_: test report, screenshot proof, pass log

**Human gate**:
The single gate the orchestrator emits once per decision, accepting only
`APPROVE(plan_id)`, `REJECT(reason)` or `CHOOSE(candidate_id)`. A skill may not
open a second gate, and timeout is never approval.
_Avoid_: confirmation prompt, sign-off, approval step

**Failure fixture**:
A named normal / conflict / failure case (`FF-<SKILL>-01..03`, plus `FF-ORCH-*`
for cross-skill conflicts) that resolves to exactly one responsible owner. A
fixture that cannot name its owner is not acceptance evidence.
_Avoid_: test case, edge case, smoke test

**Contract skeleton**:
A skill directory whose manifest, inputs, outputs, forbidden actions, stop
conditions and fixture ids are frozen while its executable implementation is
still pending a later node. Marked `metadata.status=contract-skeleton` and by a
status block in the body, so a skeleton is never mistaken for a working skill.
_Avoid_: stub, draft skill, placeholder

**Base skill**:
A skill directory that carries shared executable machinery instead of owning a
stage: `metadata.status=implemented`, `owner_scope=read`, an empty `writes` list,
and `precedence` below the first stage. It exists because the bucket layout
forbids a shared `_lib/` (every immediate child of `skills/<bucket>/` must hold a
`SKILL.md`), and because two implementations of "unknown" is how the quartet
silently becomes a nullable string. Today: `zj-ui-core` (UI contract base) and
`zj-doc-collab` (document-collaboration substrate); both are consumed by runtime
import and stay bucket-installed.
_Avoid_: helper skill, lib skill, utility folder

**AdapterBoundary**:
The thin orchestration layer (S1/S7 seam) that maps an external design tool's
native objects (e.g. a Storybook active session) onto the chain's canonical
artifact shape, and back. It owns only translation, never the artifact's
authoritative content — any claim it emits carries its source revision so the
write owner can revalidate.
_Avoid_: adapter, connector, plugin

**Dual Lane Runner**:
The deterministic verifier (R-HAR-1) that runs every UI gate twice — once on the
baseline lane, once on a degraded/offline lane — under a fixed virtual clock,
fixed RNG seed, replayed network and frozen config_hash, then asserts the two
runs produce identical `manifest_hash` / `env_hash` / `matrix_key`
(`rerun_idempotent`). Its selfcheck exits non-zero when the two lanes disagree.
_Avoid_: test runner, dual check, replay harness

**Resolver**:
The stage-engine component that, given a `(stage, artifact_kind)` pair, returns
the single write owner and the contract skeleton that the request must satisfy,
so ownership is never resolved by precedence or discovery order.
_Avoid_: dispatcher, router, lookup

**M3E**:
The PoC at node 1-7-4-3 whose verdict was recorded as `out-of-core` — the
capability (e.g. a model's multi-modal embed) is intentionally out of the Wave 0
harness and gated for a later wave rather than faked into a pass.
_Avoid_: model plugin, embedding step

**Golden fixture**:
An immutable observation or receipt fixture that the contract tests pin as the
expected output of a gate/adapter version. It lives under
`skills/research/zj-research/tests/golden/controlled-quality-v1`,
`skills/research/zj-code-research/tests/golden/code-research-quality-v1`, and
`skills/research/zj-tech-research-report/tests/golden/multi-device-agent-context`
(refactored out of the repo-root `research/` store on 2026-10-28), is referenced by
`research-compiler-contract.yml`, and must never be silently deleted.
_Avoid_: sample, seed data, example

**Drift harness**:
The shared golden-diff / version-drift detector (1-7-4-4) that compares two
versions of a golden fixture and reports a non-zero exit when they diverge, so a
replay regression cannot read as green. It is wired into the ui gate.
_Avoid_: diff tool, comparator

### DP-driven

A `zj-dp-driven` run treats one complex task as a dynamic-programming pass over a
partially observable, two-layer state graph. Governed by `zj-dp-driven`; design baseline
`docs/designs/zj-dp-driven-skill-design.md`.

**DP run / 动态规划运行**:
One end-to-end solve of a `destination` through the orchestration loop — expand states,
discover (findings → new states), execute (tickets → terminal), until every task is
terminal. Process state is a throwaway SQLite carrier; the durable output is the `.md`
corpus it references.
_Avoid_: roadmap, plan file, project

**Available pool / 可用池**:
The derived set `{s | s.status = 未完成 ∧ s is claimed by no in-flight plan}` over tickets and
findings — the input to each orchestration decision. A view, never a stored entity.
_Avoid_: backlog, todo list, work queue (it is computed, not a queue)

**Finding / 发现**:
An atomic, non-coupled observation (a conclusion, an idea, a new problem, a new or
previously-missed detail) — raw material, not necessarily already-actionable. May belong to
0..n task-plans (multi-owner = the overlapping-subproblem landing point). `已完成` means
**dispositioned once**, not "turned into a ticket".
_Avoid_: issue, insight, conclusion-only; ticket (a finding is not an action)

**Ticket / 工单**:
An atomic action node bound to a github/gitlab issue or a local md. Single-owner (one task-plan
at a time; `task_id = NULL` means it is in the pool); globally unique, so its completion
radiates over `blocks` edges to every downstream. A "shared ticket" is a modeling smell — it
should be a shared **finding**.
_Avoid_: finding, subtask, card

**Task / Task-plan / 任务 / 任务规划**:
A `task` is a layer-1 (coarse) state node; its 1:1 `task-plan` is a region of the single global
layer-2 graph. **Task status is always derived from the task-plan** (single source); the plan
stores lifecycle status. Do not double-write task and plan status.
_Avoid_: epic, milestone; storing task.status

**Single source of status / 状态单一源**:
Three tiers, each stored in exactly one place, more-derived going up: ticket/finding store their
own status; task-plan stores the task↔plan lifecycle; task status is a query projection. The
consistency root of the whole skill.
_Avoid_: cached status field, mirrored state

**Derived blocked / 派生被阻塞**:
`被阻塞` is computed on read from `blocks` edges and never stored, on both layers. Parent-child
never blocks. When unblocked, the `blocked`/`blocked_reason` fields are absent, not `False`. An
off-graph wait is `external_hold` (orthogonal), never written into `status`.
_Avoid_: stored blocked flag, `status=被阻塞` write

**Disposition / 处置 (§3.5)**:
Marking a finding terminal AND removing it from every plan that holds it, so it is never
re-processed; its downstream (tickets / new findings / new task / scoped detail) is dispatched
per its form. The memo step that makes "解一次、处处命中" hold.
_Avoid_: closing, deleting, converting-to-ticket (those are only some forms)

**DP carrier / 动态规划载体**:
The SQLite file holding only process state (tasks / plans / tickets / findings / edges /
memberships / claims). Deleted at closeout together with its process-zone siblings — the writer
lock sidecar, the event log, and the regenerable view artifacts — none of which may be referenced
by a long-lived doc; only the `.md` corpus persists. Lives in a Human-specified directory
(default `docs/plans/dp-driven/<topic>/`), never `~/`/repo-root/cwd.
_Avoid_: database of record, archive, roadmap.json

**Claim / 占用声明 (§4.4)**:
A session-scoped statement that some agent is working one layer-1 plan or one ticket. The two
layers are independent: a plan claim gates only that plan's status writes, a ticket claim only
that ticket's. Disposing a finding, hotplugging an item into a plan, or adding a `blocks` edge is
deliberately claim-free — announcing ownership is not the same as freezing arrangement.
_Avoid_: lock, mutex, assignment, ownership transfer

**Claim lease / heartbeat (§4.4)**:
The bounded life of a claim: it records when the holder was last seen and how long that sighting
stays valid, and liveness is answered on read. An expired claim is inert, so any other agent may
take it over and a crashed holder gives up its grip without a sweeper; a heartbeat renews the
lease, which is what separates "still thinking" from "dead". Expiry is never a stored flag.
_Avoid_: stored expired boolean, background reaper, indefinite claim

**Settlement round / 结算轮 (§4.5)**:
The catch-all orchestration round that sweeps the available pool into a single plan when no
cohesive subset is worth proposing, so a run can always converge instead of stalling on leftovers.
Its plan-level claim degrades to a sentinel, letting any agent pick the swept items back up. A
high settlement share is evidence the grouping pass underperformed, not that the run is healthy.
_Avoid_: mop-up task, backlog drain, failed run

**Two-stage closeout / 两段式收摊 (§5.2)**:
The ordered teardown of a finished run: export the structural snapshot while the carrier is still
readable, let the Human govern that markdown corpus and attest it, and only then delete the
carrier. The order is load-bearing — governing documents that still point into a live process
store inverts the authority boundary between durable output and throwaway state.
_Avoid_: archiving the carrier, backup-before-mutate, delete first and reconcile later

**Cohesion suggestion / 内聚建议 (§3.6 F3 / §4.2)**:
A token-cheap greedy proposal for which pool items are worth grouping into the next plan, scored
on how interconnected the candidate set is, how clean its cut is, and how much it unlocks —
reference values for Human confirmation, not a verdict. It never enumerates subsets, never claims
optimality, and is never persisted: a stored suggestion would be a second source of truth.
_Avoid_: authoritative ranking, autonomous scheduler, stored score

**Derived view artifact / 视图产物 (§6)**:
A renderable projection of the state graph — Mermaid text, a self-contained interactive viewer, or
the node snapshot behind their click-to-card behavior — built on demand from the same derived
reads the CLI exposes. It is a generation-time snapshot: never written back, never trusted as
state, and refreshed by re-running the view command rather than by any background sync.
_Avoid_: visualization state, canvas of record, live model

**Event log / 事件日志 (§9)**:
The append-only observation channel beside the carrier that records what happened across rounds —
orchestrations, settlements, terminal transitions, manual reassignments, Human verdicts, and
externally reported token cost. It is history, not state: no derivation may read it, and its
absence or corruption must never change the graph. It dies with the carrier at closeout, after its
numbers have been exported into the durable corpus.
_Avoid_: audit table as truth source, second state store, achieved baseline

### Issue / Triage

**Issue tracker**:
The tool that hosts a repo's issues — GitHub Issues, GitLab Issues, Linear,
or a local `.scratch/` markdown convention. Skills like `zj-to-tickets`,
`zj-to-spec`, and `zj-triage` read from and write to it.
_Avoid_: backlog manager, backlog backend, issue host

**Issue**:
A single tracked unit of work inside an **Issue tracker** — a bug, task,
spec, or slice. The domain-internal abstract noun. Stays an Issue in the
agent's reasoning even after it becomes a **Ticket** in the tracker.
_Avoid_: backlog item, story, work item

**Ticket**:
The concrete record of an **Issue** in an external **Issue tracker** — a
GitHub issue, a Linear ticket, a Jira ticket. `zj-to-tickets` is the act of
writing an **Issue** out to a tracker so it becomes a **Ticket**.
_Avoid_: issue record, issue row (these are the same thing, just less specific)

**Triage role**:
A canonical state-machine label applied to an **Issue** during triage
(e.g. `needs-triage`, `ready-for-agent`, `ready-for-human`, `needs-info`,
`wontfix`). Each role maps to a real label string in the **Issue tracker**
configured by `zj-repo-init`.
_Avoid_: status label, workflow state, kanban column

**Hard dependency**:
A skill whose correctness depends on per-repo collaboration config (issue
tracker and triage labels). Without `zj-repo-init` output, the skill's output
is **wrong, not just fuzzy**. Such skills include an explicit one-liner:
"_… should have been provided to you — run `/zj-repo-init` if not._"
_Avoid_: required dependency, mandatory module

**Soft dependency**:
A skill that consumes per-repo config to sharpen output but **degrades
gracefully** without it. References "the project's domain glossary" and
"ADRs in the area you're touching" in vague prose only.
_Avoid_: optional dependency, nice-to-have

**Setup pointer**:
The explicit one-liner inside a **hard dependency** skill's body that
tells the agent to run `/zj-repo-init` if the per-repo config is missing.
See ADR `0001` for the rationale.
_Avoid_: setup hint, setup reminder, bootstrap call

### Local file persistence

**Local file persistence / 落盘**:
A skill writing a durable artifact to local disk. Governed by ADR `0010`.
_Avoid_: temp, cache (when ephemeral)

**Durable artifact / 持久化产物**:
A file a skill writes that survives across sessions and may be referenced later
(excludes pure `/tmp` ephemeral state and caches). The scope of ADR `0010`.
_Avoid_: log, scratch

**Project-output scenario / 项目输出场景**:
A skill run inside a project whose artifact semantically belongs to that project
(roadmap, briefings, a report about a target codebase). Lands in
`<project-root>/tmp/skills-outputs/<skill>/<topic>/`.
_Avoid_: project file (the user-edited deliverable)

**Non-project-output scenario / 非项目输出场景**:
An artifact that belongs to no specific project (one-off viewing report, cache, a
skill's own dev artifact). The skill must ask the Human for a path — never default
to `~/`, `~/Desktop`, `cwd`, or repo root.
_Avoid_: ad-hoc output

**Project root / 项目根**:
The nearest ancestor of the carrier/cwd containing `.git`; falls back to cwd.
_Avoid_: workspace, repo

**Project-isolated zone / 项目隔离区**:
`<project-root>/tmp/skills-outputs/<skill>/<topic>/` — gitignored generated
artifacts, never committed.
_Avoid_: output dir

**Process zone / 过程暂存区 (`docs/plans/`)**:
The repo's tracked staging area for transient plans and DP-driven process material (defined
in `docs/prds/codebase-docs-capability.md` as "Process"). Lives while a plan is
active; considered for deletion after close-out. NOT a citation target for durable
docs/code (ADR `0010` one-directional coupling).
_Avoid_: plans dir, drafts

**One-directional coupling / 单向耦合**:
Plans (`docs/plans/`) are transient; decisions (ADRs) are the durable
anchor. Dependency direction is only `plan → decision → code`; durable docs/code
must never cite a plan as evidence.
_Avoid_: bidirectional reference

**Relative-path baseline / 相对路径基准**:
The directory a stored relative path is resolved against — the carrier file's
directory or the skill directory (normpath). Absolute paths are never stored.
_Avoid_: absolute base

**Doc metrics / 文档度量**:
A measurement axis, distinct from map correctness (`MAP_*`/`RETIRE_*`) and
structure correctness (`PAGE_*`/`SOURCE_*`/`ADR_*`). Metered only by
`zj-docs-metrics`, only against a committed opt-in config
(`docs/docs-metrics.json`): line budgets, Source-map freshness, navigation-orphan
and map-only pages. Report-only; a mechanical health-score gate by default
is a rejected design (see governance-contract `Rejected defaults`).
_Avoid_: health-score gate（作为默认门禁）, uninvited metering

**Retired page / 退役页**:
A page past its service life, declared on the docs map with
`retired-to: <path-or-URL>`. Lifecycle: retire → tombstone → drain → propose
and confirm deletion. Mechanically checked by `zj-docs-ontology`
(`RETIRE_TARGET_MISSING`, `RETIRE_DRAIN_INCOMPLETE`,
`RETIRE_DECLARATION_INCOMPLETE`); deletion is a candidate only at zero
inbound references with a valid destination, and still needs Human
confirmation.
_Avoid_: silent deletion, deletion as a default

**Bucket inventory source of truth / 桶计数真相源**:
The live skill tree is the only fact source for how many skills a public bucket holds; a document either links to that count or has a deterministic check verify it, and never restates the number in a second place. A copied count drifts the moment a skill is added or removed.
_Avoid_: 桶页自报 entries 数, 多处手写计数表, 以文档数字反推活树, generated region 之外的手工清单

## Relationships

- A **Skill bucket** holds many **Skills**
- A **Merge wave** contains many **Skill-pairs**
- A **Skill-pair** is one **Task** in a **DP run**
- A **Task** carries one **Decision** entry at a time
- A **Skill** may have a **Hard dependency** or a **Soft dependency** on
  per-repo config
- A **Hard dependency** skill contains a **Setup pointer**
- An **Issue tracker** holds many **Issues**
- An **Issue** becomes a **Ticket** when written to a tracker via `zj-to-tickets`
- An **Issue** carries one **Triage role** at a time
- A **Seam** is a point a **Skill-pair** merge must explicitly resolve

## Cross-stage skills

Vocabulary for the three skills that span multiple workflow stages — not bound to A↔B processing, but to any skill-pair work.

**Debrief**:
The post-task close-out. Walks drift between the planned path and the actual
path, surfaces new domain terms, and captures 1-3 "do differently next time"
actions in `docs/zj-retros/YYYY-MM-DD-retro.md`. The record is process
material; a separate Human-invoked `zj-docs-ontology` pass decides durable
extraction and deletion.
_Avoid_: post-mortem, retrospective (overloaded with agile ceremony meaning), notes dump

**Steelman**:
The pre-plan reality check. Assumes the plan is worth defending, finds its strongest case, and judges whether the case actually holds. Routes to `zj-grilling` only if a case is weak. One-shot, in-place, no file written.
_Avoid_: pre-mortem, argue both sides (mixes attack and defense roles), devil's advocate

**Dry-run**:
The pre-commit rehearsal. Walks each ticket, flags friction as blocker / ambiguity / dependency, and produces a per-ticket table plus a decision-bottleneck list. Routes friction to `zj-to-spec` / `zj-to-tickets` (suggestions only, no auto-edit) and bottlenecks to `zj-grilling`. In-place output, no file written.
_Avoid_: trace through, simulate (too general), risk analysis (different goal)

**Complementarity check**:
The rule for adding a new skill: it must name a specific existing skill it complements, and the complement must be on a clear axis — time (before/after/during), direction (defense/attack), or scope (micro/macro). A skill that doesn't name its complement is rejected as duplicating existing capability.
_Avoid_: useful in principle, fills a gap, nice to have

### Discussion methodology

Vocabulary for the `zj-discuss` / `zj-discuss-view` discussion-methodology skill pair under `skills/productivity/` — decompose a hard problem into a master + independent sub-documents, run multi-role independent discussion, synthesize, and hand off to `zj-docs-ontology`.

**zj-discuss / zj-discuss-view**:
The discussion-methodology skill pair. `zj-discuss` owns the lifecycle (decompose, prepare roles, generate briefings, orchestrate the fixed+dynamic agenda, synthesize, point to phase-2 deposition); `zj-discuss-view` is its companion, loaded in a **separate independent Agent session** to take one role on one sub-document. One skill, one role, one session — never a same-session roleplay.
_Avoid_: discussion tool, chat, meeting skill, multi-role-in-one-session

**过程性质权威依据 (process-nature authority basis)**:
The `discussions/<slug>/` folder during the solve phase. It is the authoritative record of the multi-role discussion *process*, but it is process material, not a long-lived authority. After the problem is solved it is proposed for deletion by `zj-docs-ontology`.
_Avoid_: durable doc, permanent record, knowledge-base entry, always-keep

**两阶段生命周期 (two-stage lifecycle)**:
zj-discuss's folder lifecycle: phase 1 keep-during-solving (the folder is the process authority) and phase 2 ontology-deposit-and-delete (after solving, `zj-docs-ontology` extracts durable value, then the folder is deleted). The keeper and the deleter are different stages, never conflated.
_Avoid_: always-keep, permanent archive, delete-while-solving

**声明必需集 (declared required role set)**:
The variable set of roles locked in the preparation phase for a discussion or sub-document — any subset of the candidate pool (default base {B,C,A}), drives viewpoint generation and convergence. Role count and the role→agent mapping are **never** hardcoded.
_Avoid_: role list, B/C/A-only, fixed-three-role-set, hardcoded mapping

**角色候选池 (role candidate pool)**:
The SSOT set of structurally-different role stances in `references/role-matrix.md` — base {B,C,A} plus optional T/S/O/D/L/F/U/R/P/E, each with a one-line intro and trigger signal. The preparation phase recommends a subset; the Human adjusts.
_Avoid_: fixed roles, persona list, role matrix (overloaded)

**固定议程 / 动态议程 (fixed / dynamic agenda)**:
F1–F5 bottom-line invariants every discussion must complete (define problem / confirm+dispatch roles / independent effective viewpoints / human round-by-round decision / synthesize+deposit), plus a state-driven dynamic loop that only adds focused rounds or reorders *within* F1–F5 — it never skips a fixed stage.
_Avoid_: agenda template, meeting agenda, phases, optional stages

**跨会话独立 Agent (cross-session independent Agent)**:
A separate Agent session (different model/provider preferred) that loads `zj-discuss-view --role X <sub-doc>` and writes one structurally-different viewpoint — the only trustworthy isolation. Same-session SubAgent previews are low-weight and **never** authority. Corollary: one session carries exactly one viewpoint, which is why the `--role X,Y` comma syntax was **formally closed** rather than implemented (see R1 in `docs/designs/zj-discuss/design.md`); `--all` emits separate launch lines instead.
_Avoid_: roleplay, same-session agent, subagent-as-isolation, multi-role-in-one-session

**启动包 (launch pack)**:
The one ready-to-paste Markdown file written per declared role by `scripts/launch_pack.py`, under `<讨论文件夹>/briefings/<sub-slug>-launchpack-<role>.md`. It carries the role's structural stance, the mandatory "Read the original" order, and the exact `zj-discuss-view --role X <path>` command, replacing hand-written per-role copies.
_Avoid_: briefing, prompt template, handoff packet (that is `zj-handoff`'s term)

**静态生成器 (static generator)**:
`scripts/launch_pack.py`'s mandated shape: it reads Markdown and writes Markdown, and never starts, orchestrates, or contacts a session. A regression guard (`NoRuntimeInvariant`) mechanically forbids runtime primitives, because a session runtime would reclassify the approach under the capability-fit decision model.
_Avoid_: launcher service, orchestrator, runtime, session spawner

**状态协议 (status protocol)**:
The machine-checkable enum on a sub-document conclusion — `DONE` / `DONE_WITH_CONCERNS` / `BLOCKED` / `NEEDS_CONTEXT` — replacing a vague ✅. `BLOCKED` and `NEEDS_CONTEXT` are deliberately distinct: cannot-be-done versus not-enough-information.
_Avoid_: done flag, ✅ status, completed marker, open/closed

**结构性闸门 (structural gate)**:
`scripts/check_subdoc.py` — the mechanical enforcer of source-marker, preview-label, and conclusion invariants (exit 0 clean / 1 violation / 2 unreadable). Named as a gate precisely because the previous round proved that stating these rules in prose does not make them happen.
_Avoid_: convention, guideline, best practice, self-discipline

**独立性阶梯 (independence ladder)**:
The ordered isolation strengths a viewpoint can come from — cross-provider session > same-provider cross-session > same-session SubAgent preview. The method only ever moves *up* it, never down: same-session is a floor you pass through, not a place to settle. Operational form is the **非降级自检项** — a conclusion claiming `DONE` / `DONE_WITH_CONCERNS` must rest on at least one cross-session viewpoint, enforced by the structural gate. A doc honestly reporting `BLOCKED` makes no such claim and is exempt.
_Avoid_: optional isolation, roleplay, "cross-session when convenient", provider choice as mere style

**度量注册表 / 复盘度量 (metric registry)**:
R4 — `scripts/metrics.py`, a read-only recomputable metric computer. Given a `discussions/<slug>/` folder (or one sub-doc path) it recomputes the §9 schema: `roles_used`, `viewpoint_count` (valid cross-session only), `raw_volume_chars` (all viewpoint blocks), `solution_volume_chars` (MASTER 解决思路 / sub-doc conclusion), `compression_ratio`, and closure (sub-doc-level: total=1, closed iff conclusion ∈ {DONE, DONE_WITH_CONCERNS}; discussion-level aggregates sub-docs). `recomputable` is always `true` — no hidden state. It reads disk and never writes or injects digest/learnings, so it is orthogonal to the §8 structural-digest decision and needs no PoC to activate.
_Avoid_: dashboard, metrics server, runtime analytics, injected digest

**digest 注入 / 围栏感知解析 (digest injection / fence-aware parsing)**:
§8 — digest is **voice-only** (inject zj's ethos/voice, NOT auto-inject discussion-state digest); the optional `## AI 上下文 digest` block in the subdoc / MASTER templates is a *landing spot* a Human/agent may fill, not an auto-injection mechanism. The minimum PoC (`tests/test_digest_poc.py`) proved digest injection is **semantically compatible** — `check_subdoc.py` and `metrics.py` treat the block as inert (no phantom viewpoint, no inflated raw/solution volume, no gate violation). The PoC surfaced and fixed a general parsing bug: `split_sections` in both scripts is now **fence-aware** (code-fence ``` / ~~~ lines never split as headings), so any digest that echoes `### 视角：X` inside a fence is inert. Decision reaffirmed: remain voice-only; structural (state) digest stays off, but the parsing door is open if ever wanted.
_Avoid_: auto-injected discussion-state digest, bare `#` headings inside a digest block, runtime digest server

### Decision methodology (open-source capability fit)

Vocabulary for the `zj-open-source-capability-fit` decision instrument under `skills/research/` — applying the ZAgentic open-source capability-fit model to decide whether to ingest / merge an external OSS capability.

**开源能力拟合决策模型 (open-source capability-fit decision model)**:
开源能力拟合决策模型（SSOT：`docs/agreements/open-source-capability-fit-decision-model.md`）。以目标需求 `R` 与候选项目 `O` 为单位能力，算 `有效拟合度 = 覆盖×语义匹配×可组合性` 与 `总所有权成本 E`，判 A/B/C/D。
_Avoid_: 自创选型框架, 通用评分卡, 主观打分

**zj-open-source-capability-fit**:
把上述模型操作化成**带机械闸门**的决策仪器（`skills/research/zj-open-source-capability-fit/`）；计算与判定由 `scripts/capability_fit.py` 确定性执行，闸门(G1–G4)不过就拒绝自信分类。与 `zj-tech-research-report` 的边界：本技能只产 R×O 矩阵 + A/B/C/D 判定，report 写完整选型报告并引用本技能结论，二者不重做判定逻辑。
_Avoid_: 薄 prompt 角色, 通用研究报告技能, 选型报告(那是 tech-research-report)

**A/B/C/D 分类 (fit classification)**:
A 直接采用(关键完整、G 与 E 可忽略) / B 扩展采用(缺口小且可控、开源为母体、自有是薄适配层，细分 B1 adapter·B2 upstream-contrib·B3 fork) / C 选择性复用(自有架构为主体、只复用组件) / D 继续搜索(关键缺失、拟合低、成本非线性或 E 超范围)。默认优先 A>B1>B2>C>B3，非强制，偏离须记录理由。
_Avoid_: 简单打分排序, 终态否决(误读 D), 忽略可控 B 边界

**可控 B 边界 (controlled-B boundary)**:
扩展采用要求自有部分是可移除薄层（身份映射 / 查询适配 / 状态转换 / claim·lease 协调语义 / 来源可追溯适配）；若适配层开始拥有主体数据模型或业务状态（存储同步 / 完整检索记忆 / ACL 权限 / 完整工作流平台），须降为 C 或 D。这是 zj-discuss 红线"适配层不得拥有主体方法状态"的同源依据。
_Avoid_: 把适配层做成主体, 误判为 A, 忽视红线

**D = 继续搜索 (D is continue-searching, not terminal veto)**:
canonical 语义：`D` 是搜索循环的**回环态**——该候选不满足、引入新候选后回到拆解重评，不是"永不采用"的终态否决。单候选评估时功能接近"不选"，但语义不同；zj-discuss design.md §2 曾误读为"否决/拒绝"，已在 SSOT 标注偏离。
_Avoid_: 把 D 当否决, 在单候选下混用两语义

**观察包 (observation bundle)**:
采集端（浏览器/adapter）产出的**结构化证据**，按 `<fixture_id>/<viewport>.json` 落盘，契约 R-OBS-1 见 `skills/ui/zj-ui-core/contracts/hard-gates.md` §1。门禁只吃观察包、不做采集：DOM 节点（含 computed accessible name / ARIA / tabindex）、焦点序列与可见样式、对比度采样、布局盒模型、动效描述、状态机 trace。**"没有观察包"是一种结论（证据缺失），不是"没问题"**。
_Avoid_: 把浏览器截图当观察包, 让门禁自己抓 DOM, 用空段代表零缺陷

**硬门禁 (hard gate)**:
对观察包做确定性判定的纯函数（`skills/ui/zj-ui-core/scripts/hard_gates.py`，R-HAR-2），产出 `FAIL / HUMAN_REVIEW_REQUIRED / QUARANTINED / WARNING / PASS`。核心语义是 **fail-closed**：证据缺失一律 `HUMAN_REVIEW_REQUIRED`，绝不落 `PASS`；`overflow`/`focus`/恢复类失败不得降级成 warning。与"评分/建议"的区别在于它没有"差不多"档。
_Avoid_: 把 hard gate 叫 lint, 用 warning 表示硬失败, 允许部分覆盖算通过

**收据 (verification receipt)**:
可归因、可重算、可过期的验证结论载体（R-RCP-1，`skills/ui/zj-ui-core/scripts/verification_receipt.py`；契约 `skills/ui/zj-ui-core/contracts/verification-receipt.md`）。14 个固定段 + 身份段，每个 cell 带 `status` / `observed` / 判据快照（threshold、oracle、command），使结论离线可复核；签发后 append-only，同 `receipt_id` 内容变化即失效。与"报告"的区别：报告给人读，收据给机器与复核人判。
_Avoid_: 把运行日志当收据, 用通过率代替覆盖率判 PASS, 签发后原地改状态

**stale / revalidation_required**:
收据的新鲜度判定（读取时重算，不信任存量值）。`STALE` = 漂移可精确收敛到部分 cell（fixture 内容/class、阈值/oracle）；`REVALIDATION_REQUIRED` = 无法收敛或代价等同全量（env 轴、维度集合/cell 门禁、schema 升版、过期、事实源不可读）。过期（TTL 默认 14 天）不因 hash 未变而豁免。
_Avoid_: 用 hash 未变当没过期, 把 STALE 当 FAIL, 拿"曾经通过"放行过期结论

**无法归因 (unattributable)**:
quarantine 的一个子类：证据无法映射到 fixture × dimension × viewport，或缺 evidence / release_condition。与 attributed 分开计数，两者都判 `QUARANTINED`；不得转成 `FAIL`（"不知道"不等于"已验证失败"），也不进通过率分母。解除须新 run_id + 复核人签署。
_Avoid_: 把"不知道"写成失败, 把 quarantine 计入分母, 原地把 quarantine 改成 PASS

### Graphical cross-comparison (product-project)

Vocabulary for the multi-project structural comparison agreement (SSOT:
`docs/agreements/product-project-graphical-cross-comparison-model.md`). It answers
"what differs between several product projects", not "should we adopt one candidate"
(that is the open-source capability-fit decision model above).

**产品项目图式横比模型 (product-project graphical cross-comparison model)**:
以固定场景集为公共坐标系，把多个产品项目各自独立的图对齐成**逐条可追溯的差异清单**；摘要指标只作展示、不参与结论。本文是方法论约定，纸面契约不等于已有实现体。
_Avoid_: 横比矩阵, 评分卡, 架构裁决, 采用结论

**固定场景集 (fixed scene set)**:
由 Human 独立给定、不来自任何 `Graph_i`、带版本 pin 与产品域一手材料证据的跨项目公共坐标系；只描述可观察场景（起点 / 终点 / 可观察结果），不规定节点、模块或实现划分。
_Avoid_: 从项目切片归纳, 项目划分模板, 架构蓝图, 候选池采纳

**可选场景集 (observed scene candidates)**:
Stage 2 逐项目原样摘录 `(project, slice, 场景原文, evidence-ref)` 得到的**过程材料**，仅供 Human 做盲区检查（核对遗漏、识别把项目特有场景误当通用），不得直接采纳为固定场景集；Agent 对它零语义操作。
_Avoid_: 场景归纳, 候选场景池(暗示可采纳), 自动去重, 语义等价提示

**场景锚定 (scene anchoring)**:
以固定场景集而非节点语义等价作为跨项目对齐单位；各 `Graph_i` 按自己的语义独立建成，只在 Stage 3 经场景映射发生对齐。这是 ADR 0012 的判决。
_Avoid_: 节点等价映射, 全局同义词表, 预先对齐, 同名即同义

**差异条目 (difference entry)**:
唯一的结论载体；一条 = `场景 × 项目 × 供给四态 × 支撑切片 / 节点集 × 证据 × 映射裁决`，`unknown` 另附最小验证计划。
_Avoid_: 差异分数, 项目排名, 汇总评分, 以摘要代替清单

**供给四态 (supply verdict)**:
`native / adapted / unsupported / unknown`，参照系是场景（不是我方架构）；复用母模型 `R × O` 的四态。`unsupported` 必须绑定一手材料中的显式否定陈述，`unknown` 是既无覆盖证据也无否定陈述。
_Avoid_: 三态(漏 unsupported), absent, 元素级 status, 把 unknown 写成不支持

**竖切片 (vertical slice)**:
一条超边 = 一个端到端可观察用户场景；`members` 列表是 SoT，Mermaid 中间节点只是投影。
_Avoid_: UI 页面, 模块, 横切路径, 从投影反推成员集

**横切路径 (cross-cutting path)**:
在 ≥2 条竖切片中重复出现的体验路径，带结构化 `appears_in`；不与竖切片并列、不参与成员下界检查、不计入共享度分子。
_Avoid_: 横切片超边, 共享节点计数来源, 并列 kind 枚举

**依赖边 (dependency edge)**:
语义恒为 `requires` 的有向边，是唯一可进入强连通分量 / 依赖闭包 / 扇入计算的关系；选择约束与时序约束另放 `relation-constraints`（记号 `RC`）。
_Avoid_: 耦合边(混类型), co-varies(需跨版本证据), 无向连通分量

**强连通分量 (strongly connected component, SCC)**:
本模型中只用于刻画「互相依赖、不可单独交付」，仅在环上非空；属摘要指标。忽略 `requires` 方向的无向连通分量会把可独立交付的依赖方与共享底座绑成一团。
_Avoid_: 无向连通分量, 把 SCC 当工作量估算, 把共享底座算进同一团

**传递依赖闭包 (transitive dependency closure)**:
按起点定义、可重叠的集合族，刻画单次交付的最小成本；不是划分。`closure(v) ∪ {v}` 是交付 `v` 的最小单元。
_Avoid_: 连通分量, 「耦合团」清单, 工作量估算值

**缩点 DAG (condensation DAG)**:
把每个 SCC 压成超节点后必然无环的依赖顺序结构；本模型分析实现顺序的落点。
_Avoid_: 按无向连通分量排实现顺序, 把扇入当拓扑序

**扇入 (fan-in)**:
依赖图上节点的入度，刻画变更波及面与共享底座的复用价值；是节点级标量，与共享度（超边成员计数）不是同一件事。
_Avoid_: 共享度, 场景出现次数, 出度 fan-out 混用

**共享度 (slice-sharing ratio)**:
出现在 ≥2 条竖切片中的节点数 / 全部节点数；只按 `S` 计数，横切路径 `X` 不计入，否则指标会被建模方式系统性抬高。
_Avoid_: 把横切路径计入分子, 当成扇入, 当成复用价值结论

**摘要指标 (summary metrics)**:
证据绑定覆盖率 / 竖切片覆盖率 / 共享度 / SCC 规模分布 / 最大依赖闭包 / 扇入分布 / 未决存量；只作差异清单的摘要展示。
_Avoid_: 判定量(暗示可裁决), 机械闸门, BLOCKED, 用于排序 / 回灌 / 优先级

**证据 / Human 裁决 / 假设 (evidence / ruling / assumption)**:
报告必须标注的三类来源；Human 裁决不得写成证据，假设不得写成裁决，「区分证据 vs 假设」的二分类不足以覆盖它们。
_Avoid_: 只分证据与假设两类, 把 Human 裁决伪装成客观数字

**上下文条目 (context entry)**:
非能力事实的**旁挂清单**，不进 `V`、不进 `S.members`、不进有向依赖图，也不计入任何摘要指标的分母；不给图记号、不属于 `Graph_i` 元组。`scope: domain` 归固定场景集所有（Human 给定，仍不规定实现划分），`scope: project` 归各自 `Graph_i`（Stage 2 登记）。母模型把同类事实放在 `C` 的兼容性验证项与 `E` 的成本分量里，本模型沿用这一分工。
_Avoid_: 节点类型, NFR 节点, 塞进 `T`, 扩 `V` 为多类型, 自由文本 notes

**上下文条目种类 (context entry kinds)**:
四类 `kind`：`constraint`（非功能约束，如数据不出域 / 响应门槛 / 许可合规，只有满足与违反、没有独立验收条件）、`data-contract`（数据契约，长期记忆对象 / 页级元数据 / schema 与生命周期，是被操作的事实载体）、`external-dep`（外部依赖，第三方 API / 模型服务 / provider 条款，供给来自外部）、`actor`（参与主体，Human operator / 审批人 / 执行 Agent，是场景角色不是交付单元）。节点上的 `semantic-owner` 与 `data-contract` 互补：前者答「谁拥有 durable facts」。
_Avoid_: 把约束写成能力, 把数据对象写成技术节点, 把角色当成可验收单元

**上下文判定三态 (context verdict)**:
`satisfied / violated / unknown`，由差异条目的 `context-verdicts` 逐条给出；`violated` 须绑定显式否定证据，`unknown` 须附最小验证计划。**与供给四态是两套枚举，不得混用**；它不改变差异条目的 `verdict`，只补「能力结构相同但上下文条件不同」这类差异（如两个项目都 `native`，一个数据不出域、一个依赖第三方模型服务）。
_Avoid_: 与 native/adapted/unsupported/unknown 混用, 压成单一标量, 一次裁决批量套用多个项目

## Flagged ambiguities

- "ticket" was previously `_Avoid_` in the issue-triage glossary — resolved:
  **Ticket** is now a distinct concept (the external-tracker carrier),
  not a synonym. The old `_Avoid_` rule is retired as of 1-4-5.
- "backlog" was previously used to mean both the *tool* hosting issues and
  the *body of work* inside it — resolved: the tool is the **Issue tracker**;
  "backlog" is no longer used as a domain term.
- "backlog backend" / "backlog manager" — resolved: collapsed into
  **Issue tracker**.
- A↔B relationship (this repo vs. any source skills collection) is
  intentionally **not defined** as a domain term here. It is a property of
  individual merge waves, not of the glossary.
- `orphan` — resolved by scope: in docs-metrics / `zj-docs-metrics` it means a
  **navigation orphan** (`NAV_ORPHAN`: no inbound link from any living page); in the graphical
  cross-comparison agreement it means an **orphan node** (a `V` member no
  `S` connects). Never use the bare word across these two contexts.
- `composability` / 可组合性 — resolved by scope: in the capability-fit model
  it is a **multiplier of 有效拟合度** (and a `matrix[O][R]` column in the
  skill-layer application guide), not a field the cross-comparison agreement
  can claim to write into. The agreement now only offers difference entries as
  optional input material and declares the mother-model interface undefined.
- `unknown` — three distinct enums, not one term: `Study record kind`
  (`observed / inferred / unknown / decision`), the capability-fit `R × O`
  matrix state, and the cross-comparison **supply verdict** four-state. Always
  name the enum when the context is not locally obvious.
- `G` — resolved by symbol avoidance: in the capability-fit model `G = R − C` is the
  **capability gap**. The cross-comparison graph is written `Graph_i`, never
  `G_i`, so the two never share a symbol domain.
- `constraint` / `C` — resolved by renaming (2026-11-08): the cross-comparison
  agreement's in-graph relation constraint was renamed to `RC` (field
  `relation-constraints`, ID `RC::`) and its review conditions to `CHK-01`…
  `CHK-10`, so the bare single-letter `C` now refers only to the capability-fit
  model's `C = Compose(...)`. `kind: constraint` on a **context entry** keeps
  its name (non-functional condition: data residency, latency, license) because
  `constraints` is an established field name in UI contracts. The ontology's
  `constrains` relation and `Contract.gate` attribute remain doc-artifact-layer
  senses; no scope-based disambiguation is needed inside the agreement anymore.

## Retros

🔄 判断 push 是否成功一律用 `git ls-remote`，不信客户端退出码 — durable lesson from the 2026-09-12 retro; the source is retained in git history (`5fd2d4a`).
🔄 Bash coreutils 可能整体不在 PATH（`ls`/`head`/`which` 缺失）→ 文件操作改 Python，删文件走 `[System.IO.File]::Delete` — durable lesson from the 2026-09-12 retro; the source is retained in git history (`5fd2d4a`).
- 补文档前先 grep 本地确认基线，别假设已合并 PR 的文档一定在本地 — durable lesson from the 2026-09-12 retro; the source is retained in git history (`5fd2d4a`).
- 更新 / 重装 skill 前先探测已装副本（SKILL.md 字节数 + `scripts/` 清单），防已装副本漂移 — durable lesson from the 2026-09-12 retro; the source is retained in git history (`5fd2d4a`).
