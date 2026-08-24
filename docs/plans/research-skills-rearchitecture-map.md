# Research skills rearchitecture — wayfinder map

## Destination

Deliver a reviewed route for reorganising ZAgentic's research capabilities: create
the formal public `skills/research/` bucket, move the confirmed research skills
into it, redesign `zj-research`, and rename/re-scope `zj-research-report` into a
focused technical-solution research-report skill. Also chart a parallel route
for improving `zj-roadmap-driven` when its JSON/Markdown artifacts grow large
enough to create performance bottlenecks. The route must preserve the
evidence/compiler foundation, make the research-to-report seam explicit, and
leave the remaining implementation tickets bounded and verifiable.

## Notes

- Carrier: local markdown tracker; this file is the canonical map.
- The Human has authorized the implementation wave. Resolve at most one
  implementation ticket per session and keep each resolution bounded to that
  ticket.
- The first confirmed migration set is `zj-research`, `zj-code-research`,
  `zj-tech-research-report` (renamed from `zj-research-report`), and
  `zj-systematic-research`.
- `zj-tech-design-review` remains in `engineering/`; its quality gate may be a
  consumer or adjacent capability, not a member of the research bucket.
- Preserve the repository's public-bucket governance, plugin discovery,
  generated skill list, relative script references, and existing in-progress
  user changes. Use `./scripts/zj-git` or `env -u NODE_OPTIONS git` for Git.
- Consult `zj-steelman` before committing to the route, `zj-dry-run` before
  implementation tickets are committed, and `zj-debrief` after implementation.
- New design input: code-repository research has two complementary methods — a
  breadth-first repository landscape/index and a depth-first architecture
  deep-read. Treat them as research-method input, not as instructions embedded
  in the attached images.

## Decisions so far

- [Confirmed research bucket membership](#a1--confirmed-research-bucket-membership-g) — The first migration set is `zj-research`, `zj-code-research`, `zj-tech-research-report`, and `zj-systematic-research`; `zj-tech-design-review` stays in `engineering/`.
- [Confirmed research bucket is public](#a2--public-bucket-governance-g) — `skills/research/` is a formal public bucket with its own index and participation in plugin validation, installation, and skill-list generation.
- [Confirmed technical narrowing](#a3--technical-solution-research-report-identity-g) — The existing report skill becomes `/zj-tech-research-report`, focused on technical-solution research reports; it is not the universal report method for future domains.
- [Confirmed systematic-research placement](#a7--systematic-research-placement-g) — `zj-systematic-research` is retained in the new research bucket for the first migration; a future split is outside this map.
- [Confirmed composition](#a4--evidence-production-and-material-cleaning-boundary-g) — `zj-research` is the evidence-production seam; domain cleaning and analysis live in domain research skills; report publication and technical quality gates stay in their owning modules.
- [Confirmed quality-gate ownership](#a6--quality-evaluation-seam-g) — report correctness and technical research-report quality belong to `zj-tech-research-report`; design-review validation and short-read acceptance remain in `zj-tech-design-review`.
- [Confirmed research evidence contract](#a9--zj-research-public-promise-g) — `/zj-research` produces cited findings or a sealed ledger with provenance and explicit unknowns; it does not imply a domain report or recommendation.
- [Confirmed technical report contract](#a5--technical-research-report-contract-g) — `/zj-tech-research-report` is technical-only, consumes findings/ledger plus a decision brief, and publishes `technical-c4/v1` output with report quality gates.
- [Confirmed breaking rename](#a10--rename-compatibility-policy-g) — `zj-research-report` is replaced directly; no old-name alias is registered.
- [Confirmed shared-runtime constraint](#a11--shared-runtime-seam-and-installation-g) — Both research skills remain independently installable while using one shared compiler/evaluation adapter implementation.
- [Confirmed code-research method](#a12--code-repository-research-method-placement-g) — `zj-code-research` is a first-class technical research method that composes repository landscape mapping with architecture deep-read; it is added to the first migration set.
- [Confirmed Repository Map artifact model](#a13--repository-landscape-contract-g) — A map is an immutable snapshot artifact bundle: a small manifest plus deterministic shards and generated Markdown/HTML views; it is not one ever-growing JSON file.
- [Confirmed Architecture Study contract](#a14--architecture-deep-read-contract-g) — Architecture Study is an evidence-linked, descriptive depth-pass bundle bound to a Repository Map snapshot; it separates observed, inferred, unknown, and decision records and does not make the final solution recommendation.
- [Confirmed code-research quality evaluation](#a15--code-research-quality-evaluation-g) — Code research uses independent `landscape/v1` and `deep-read/v1` rubrics with mechanical hard gates plus calibrated semantic evaluation and separate controlled fixtures.
- [Confirmed roadmap large-artifact direction](#a16--large-roadmap-artifact-performance-g) — Large roadmaps use an optional sharded bundle with append-only history, materialized snapshots, current pointers, lazy reads, bounded views, explicit migration, and three-axis benchmarks while preserving the small single-file mode.
- [Confirmed roadmap CLI compatibility](#a17--roadmap-cli-contract-parity-g) — The implementation and tests are authoritative; Markdown import is not supported, `migrate --to bundle` is the explicit storage migration, decision removal becomes traceable retraction, and full sections are opt-in.
- [Confirmed implementation route](#a8--migration-and-governance-route-t) — The migration is split into structural identity/governance, shared evidence runtime, Repository Map, Architecture Study, technical report, code-research evaluation, roadmap bundle, and final verification tickets.
- [Completed structural migration](#a18--public-research-bucket-and-direct-skill-identity-migration-t) — The four confirmed research skills now live under `skills/research/`, the report identity is `zj-tech-research-report`, and governance, output paths, runtime references, and generated discovery lists are synchronized.
- [Completed shared runtime seam](#a19--shared-research-runtime-and-evidence-seam-implementation-t) — `zj-research` is the evidence-only seam; the technical report publisher resolves its canonical adapters from a sibling runtime or explicit `ZJ_RESEARCH_RUNTIME`, with an independent-install setup failure covered by the golden contract.
- [Completed Repository Map implementation](#a20--repository-map-implementation-t) — `zj-code-research` now emits immutable commit/worktree-pinned bundles with fact shards, deterministic targets, generated views, bounded reads, and mechanical validation.
- [Completed Architecture Study implementation](#a21--architecture-study-implementation-t) — `zj-code-research` now emits map-bound or explicitly direct-scoped evidence-linked study bundles with four record kinds, line-addressable claims, flows, risks, unknowns, diagrams, and follow-up targets.
- [Completed technical research-report implementation](#a22--technical-research-report-implementation-t) — `zj-tech-research-report` now validates a `technical-decision-brief/v1` plus sealed ledger and `technical-c4/v1` Report IR before compiler publication, producing Markdown, HTML, and a receipt with a versioned technical quality-gate result.
- [Completed code-research quality implementation](#a23--code-research-quality-fixtures-and-evaluation-t) — `zj-code-research` now owns separate `landscape/v1` / `deep-read/v1` hard gates, controlled fixture cases, dimensional semantic scoring, and calibrated Judge checks.
- [Completed roadmap bundle implementation](#a24--roadmap-bundle-storage-and-performance-implementation-t) — `zj-roadmap-driven` now supports explicit sharded bundle storage, bounded cross-mode CLI views, append-only decision retractions, safe legacy migration, and reproducible small/medium/large benchmarks.
- [Completed migration and verification closeout](#a25--research-migration-and-roadmap-verification-closeout-t) — The real planning corpus, research contracts, roadmap bundle, public discovery, and documentation surfaces have been verified together; no active legacy skill alias remains.
- [Completed storage adoption advisory](#a26--read-only-roadmap-storage-advisory-t) — `recommend-storage` reports explainable single-file versus bundle signals without repairing, migrating, or rewriting the roadmap.
- [Completed storage-advisor threshold calibration](#a27--storage-advisor-threshold-calibration-t) — Real roadmap corpora now distinguish structural pressure from measured performance and reject non-execution Registry JSON.
- [Completed implementation release](#a28--researchroadmap-implementation-release-t) — The research/roadmap implementation wave was published from `main`, with release closeout kept separate from implementation changes and no deployment claim added.
- [Completed research-chain dogfood](#a29--real-research-chain-dogfood-t) — A real `zj-code-research → zj-research → zj-tech-research-report` chain passed its quality gates; failed fresh collection remained explicitly distinct from reuse of an older sealed ledger.
- [Completed research runtime hardening](#a30--research-collection-runtime-hardening-t) — `zj-research` now performs GitHub quota/auth preflight, emits structured diagnostics, and records fresh, explicit-reuse, and blocked collection states.
- [Completed authenticated live collection acceptance](#a31--authenticated-live-collection-acceptance-t) — A real authenticated fresh collection completed against the fixed three-repository brief; the live path also exposed and fixed the standard-library timeout invocation bug.
- [Completed fresh-ledger technical report republish](#a32--fresh-ledger-technical-report-republish-t) — The A31 sealed ledger was rebuilt into a new technical-c4 report and published healthy without the A29 ledger or fingerprint.
- [Completed roadmap-driven handoff](#a33--roadmap-driven-handoff-for-langgraph-checkpoint-probe-t) — The settled LangGraph checkpoint/resume validation route now has a separate execution roadmap in ZAgenticLoop, with a native-baseline focus and no migration of Wayfinder history.
- [Completed second real research-combination acceptance](#a34--second-real-research-combination-acceptance-t) — A second `zj-code-research → zj-research → zj-tech-research-report` run passed on a dirty-but-pinned ZAgenticLoop checkpoint slice, with two authenticated fresh ledgers, explicit semantic gaps, and a healthy technical-c4 report.

## Not yet specified

- None for this implementation wave. The A26 thresholds are initial advisory
  starting points and may be tuned by real usage; they are not automatic
  migration rules.

## Out of scope

- Designing financial, legal, or other future domain research skills in this map.
- Moving `zj-tech-design-review` into `skills/research/`.
- Changing the ZHarness research/evaluation protocol or compiler artifact in the
  first redesign pass unless a later decision proves a protocol gap.

## A1 — Confirmed research bucket membership [G] ✅

### Question

Which existing skills belong in the first `skills/research/` migration set?

### Resolution

The first set is:

- `zj-research`
- `zj-code-research`
- `zj-tech-research-report`
- `zj-systematic-research`

`zj-tech-design-review` remains in `skills/engineering/` because it is a
technical design review and quality-gate skill, not a research-method skill.

## A2 — Public bucket governance [G] ✅

### Question

Should `skills/research/` be a formal public bucket rather than an informal
directory?

### Resolution

Yes. It gets a bucket `README.md` and participates in top-level README links,
`.codex-plugin/plugin.json` discovery, plugin/layout validation, installation,
and generated skill-list workflows.

## A3 — Technical-solution research-report identity [G] ✅

### Question

What exact name should replace `zj-research-report`, and what must the name
promise to the user? The name must distinguish technical-solution research from
generic evidence collection and from technical design review.

### Resolution

The skill is renamed to `zj-tech-research-report`. Its directory name,
frontmatter `name:`, invocation name, README links, plugin-facing references,
and all internal path references must move together. It is focused on
technical-solution research reports, while `zj-research` remains the evidence
creation seam and `zj-tech-design-review` remains the review/quality-gate seam.

## A4 — Evidence-production and material-cleaning boundary [G] ✅

### Question

After redesign, what does `zj-research` own for technical work, and what must
remain a domain-specific research skill rather than a universal cleaning method?

### Resolution

The accepted composition is:

- `zj-research` owns domain-neutral evidence production: primary-source
  collection, provenance, canonical evidence, sealed ledgers, and unknowns.
- Domain research skills own material cleaning, domain taxonomies, analysis
  methods, and domain-specific quality criteria.
- `zj-tech-research-report` owns technical synthesis, Report IR, publication,
  and technical research-report quality.
- `zj-tech-design-review` owns technical design review, its mechanical gate,
  and short-read acceptance.
- Shared compiler/runtime adapters are infrastructure, not user-facing research
  methods.

`zj-research` keeps its name. The name describes the evidence-production entry
point and does not promise a universal domain-analysis method; its description
and body must make that narrower promise explicit.

## A9 — `zj-research` public promise [G] ✅

### Question

What exact user-facing description and output contract should make it clear that
`zj-research` produces evidence rather than a finished domain report?

➡️ Recommended promise: submit a research question or evidence brief and receive
cited findings or a sealed ledger with canonical evidence, provenance, and
explicit unknowns. No domain recommendation or final report is implied.

### Resolution

Adopt the recommended promise. `zj-research` keeps the invocation name but its
description and workflow explicitly stop at evidence production.

## A5 — Technical research-report contract [G] ✅

### Question

What is the minimum end-to-end contract of the renamed skill: input findings and
sealed ledger, decision frame, technical analysis, Report IR, publication, and
explicit unknowns? Which existing `zj-research-report` behaviour is removed,
retained, or moved to another skill?

### Resolution

`zj-tech-research-report` is technical-only. It consumes cited findings or a
sealed ledger plus a technical decision brief, performs technical material
cleaning and synthesis, and emits `technical-c4/v1` Report IR followed by
compiler-derived Markdown, HTML, and a publication receipt. The generic
`zj-draft/v1` path is removed from this skill. Technical design review remains a
separate follow-on route.

## A6 — Quality-evaluation seam [G] ✅

### Question

How should the technical solution research report connect to the existing
quality capabilities: compiler `evaluate`, `zj-tech-design-review`'s mechanical
validator, and human short-read acceptance? Decide which skill orchestrates each
gate without making research-report a universal review skill.

### Resolution

- Compiler correctness, publication consistency, and the report's technical
  research quality belong to `zj-tech-research-report`.
- `zj-tech-design-review` remains responsible for design-review structure,
  blocking/non-blocking findings, owners, and human short-read acceptance.
- A research report may feed a design review, but the report skill does not
  become a universal design-review skill.

## A10 — Rename compatibility policy [G] ✅

### Question

When `zj-research-report` becomes `zj-tech-research-report`, is this an
immediate breaking rename, or should the repository temporarily ship a
compatibility alias/redirect for the old invocation?

### Resolution

Use an immediate breaking rename. Do not register a `zj-research-report` alias;
update all references and publish the new invocation name.

## A11 — Shared runtime seam and installation [G] ✅

### Question

Where should the compiler/evaluation adapter and artifact-lock logic live so
that `zj-research` and `zj-tech-research-report` have one implementation, while
each skill can still be installed independently by the current flattened skill
installer?

### Resolution

Both `zj-research` and `zj-tech-research-report` must remain independently
installable while sharing one authoritative compiler/evaluation adapter
implementation. The physical packaging seam is part of A8's migration route;
duplicating the adapter is ruled out.

## A7 — Systematic-research placement [G] ✅

### Question

Does `zj-systematic-research` remain in the new research bucket for the first
migration?

### Resolution

Yes. It is part of the first migration set. Any future split between this
cross-domain method and narrower domain methods is outside the current map.

## A8 — Migration and governance route [T] ✅

### Question

What exact file operations and validation updates are required to create the
bucket and rename the report skill without breaking links, plugin discovery,
relative paths, compiler adapters, tests, generated skill lists, or the user's
uncommitted work?

### Resolution

The implementation route is split into ordered, bounded tickets. The current
working tree changes in `zj-research-report/SKILL.md`, its new exemplar, this
map, and `ZJ-CONTEXT.md` are preserved and must be included deliberately rather
than overwritten.

#### Structural identity and content operations

- Create the formal `skills/research/` bucket and its README.
- Move `zj-research` and `zj-systematic-research` from `skills/engineering/`.
- Move and directly rename `zj-research-report` to
  `zj-tech-research-report`, updating frontmatter, agent metadata, prompts,
  README links, guide routes, and active references. Do not register an alias.
- Create the new `zj-code-research` skill in the research bucket from the
  accepted Repository Map → Architecture Study contract.
- Keep `zj-tech-design-review` in engineering.
- Relocate the active `skills-outputs/zj-research-report/` output directory to
  `skills-outputs/zj-tech-research-report/` and update the user-facing link and
  application-owned receipt paths while preserving report hashes and evidence.

#### Shared runtime and relative-path operations

- Keep `research_cli.py`, `research_eval_cli.py`, the compiler lock, and the
  bundled artifact under the canonical `zj-research` implementation; do not
  duplicate them in the report skill.
- Update the report publisher and its tests to resolve the sibling runtime
  through an explicit setup pointer. A report skill installed without the
  runtime remains discoverable/installable but fails loudly with the setup
  instruction when compiler-backed publication is requested.
- Update hard-coded source paths in the compiler-artifact updater and golden
  contract test. Preserve the stable protocol/schema names, especially
  `zj-research-cli/v1`, `zj-research-report-ir/v1`, and the compiler lock.

#### Governance and discovery operations

- Add `research` to the repository validator and private-naming bucket lists.
- Add `research` to the generated skill-list scanner and regenerate
  `scripts/zagentic-skills-list`, removing the old report skill name.
- Update the top-level README, `skills/engineering/README.md`, and create
  `skills/research/README.md` so every public skill has one linked entry.
- Update `zj-guide` routing and all active old-name/path references.
- No direct `.codex-plugin/plugin.json` skill-array edit is required because
  this manifest points to the recursive `./skills/` root; plugin/layout
  validation must still pass after the bucket is added. `link-skills.sh` has no
  hard-coded bucket list, but its dry-run must cover the new bucket.

#### Verification and safety operations

Before moving anything, capture status and run the current research golden
contract. Execute moves with `git mv` through the repository-safe Git wrapper,
never reset or overwrite the user's edits. Afterward run old identity/path
searches with explicit exemptions for stable schemas/protocols and immutable
history, plugin/layout/frontmatter validation, skill-list regeneration check,
adapter golden tests, output receipt checks, and `git diff --check`.

## A12 — Code-repository research method placement [G] ✅

### Question

How should the two newly identified, complementary code-repository methods be
combined with the research skill redesign?

The methods are:

1. **Repository landscape / index** — breadth-first inventory of files,
   directories, languages, packages/crates, workflows, integration layers, and
   top-level structure. Its output is a navigable map, not a conclusion.
2. **Architecture deep-read** — depth-first analysis of selected layers or
   flows: module relationships, interfaces, runtime interactions, persistence,
   execution, sandbox/security, extension points, design choices, and risks.

### Recommended direction

Make them a two-pass technical code-research workflow:

```text
repository landscape
  → choose target layer / flow
  → architecture deep-read
  → path-pinned evidence, claims, unknowns, and diagrams
  → optional technical decision report
```

Keep the evidence/provenance machinery in `zj-research`; keep technical
solution synthesis in `zj-tech-research-report`. Prefer a distinct
code-research method skill if the two passes need their own prompts, artifacts,
and quality rubric; do not hide architecture interpretation inside the generic
evidence collector or the final report publisher.

### Resolution

Add `zj-code-research` as a first-class skill in the `research` bucket. It owns
the technical code-research method and composes two passes:

```text
repository landscape
  → choose target layer / flow
  → architecture deep-read
  → path-pinned evidence, claims, unknowns, and diagrams
  → optional technical decision report
```

`zj-research` remains the evidence/provenance seam, and
`zj-tech-research-report` remains the technical decision-report seam. The two
passes are one skill with a staged workflow, not two separate user-facing
skills. The first migration set is therefore four skills:
`zj-research`, `zj-code-research`, `zj-tech-research-report`, and
`zj-systematic-research`.

## A13 — Repository landscape contract [G] ✅

### Question

What is the minimum useful `Repository Map` artifact produced by the breadth
pass, and which facts must be commit-scoped, mechanically measured, or marked
unknown?

### Resolution

`Repository Map` is a snapshot artifact bundle, not a single ever-growing JSON
file. Each snapshot is immutable and identified by repository/ref or explicit
working-tree fingerprint, generator/schema/tool/config metadata, and coverage.
The bundle uses a small `manifest.json` entrypoint plus deterministic shards:
summary, tree/inventory, navigation targets, and unknowns. Markdown and HTML are
generated views; caches and query indexes are disposable derived artifacts.

The map records scan scope, exclusions, skipped/failed paths, and stable node
identities. It separates generated facts from human research judgments and hands
explicit navigation targets to `Architecture Study`.

The accepted lifecycle is:

```text
scan → write immutable snapshot → update current pointer/index → render views
```

It does not mutate one historical map in place or accumulate all history in the
current artifact.

## A14 — Architecture deep-read contract [G] ✅

### Question

What is the minimum useful `Architecture Study` artifact produced by the depth
pass, and how must it separate observed source facts, inferences, unknowns,
design choices, runtime flows, ownership, and risks?

### Resolution

`Architecture Study` is a descriptive, evidence-linked depth-pass artifact. It
does not select the final technical solution; `zj-tech-research-report` owns
solution comparison and recommendation.

The standard `zj-code-research` flow must bind the study to one immutable
`Repository Map` snapshot and its `navigation/targets.json`. A direct study is
allowed only when an explicit scope is converted into equivalent navigation
targets and the absence of a map is recorded.

The study is an immutable `architecture-study` snapshot artifact bundle rather
than one Markdown file or one ever-growing JSON document. Its small manifest
references independently readable shards for scope, evidence, relationships,
runtime flows, claims, unknowns, and risks; Markdown/HTML are generated views
and indexes are disposable.

Every record uses exactly one of these kinds:

- `observed` — directly read from the pinned source;
- `inferred` — derived from one or more observed evidence records;
- `unknown` — not established by the current evidence;
- `decision` — a research-scope or follow-up choice, not a source fact.

The minimum study covers scope and exclusions, source snapshot and commit,
module relationships, interfaces, runtime/data flows, persistence, execution
and sandbox/security, extensions and external dependencies, ownership, design
choices, risks, unknowns, at least one structure or flow diagram, and follow-up
navigation targets. Every critical claim must carry an evidence ID, commit,
source path, and line range; missing evidence cannot be promoted to a critical
architecture claim.

## A15 — Code-research quality evaluation [G] ✅

### Question

How should code-research quality be evaluated? Reuse the existing `deep-read/v1`
criteria where applicable, and decide whether a new `landscape/v1` rubric is
needed for coverage, navigability, target selection, and usefulness to the
deep-read pass.

### Resolution

Code-research quality uses two layers:

1. Mechanical hard gates validate snapshot pinning, scope/exclusion accounting,
   shard and reference integrity, target binding, evidence links, explicit
   unknowns, and reproducible output.
2. Calibrated semantic evaluation measures coverage, navigability, evidence
   fidelity, architecture interpretation, and downstream usefulness.

The quality contract has two independent versioned rubrics:

- `landscape/v1` for Repository Map coverage, measurements, stable navigation,
  target selection, and usefulness to deep-read;
- `deep-read/v1` for Architecture Study target adherence, module/flow coverage,
  evidence-backed claims, certainty separation, ownership, risks, unknowns, and
  follow-up validation targets.

The result is dimensional rather than one aggregate score. Code research gets
its own controlled-quality fixture corpus, separate from technical-report
fixtures, and may reuse the shared evaluator adapter, rubric loading, and Judge
calibration machinery. `zj-code-research` orchestrates these checks;
`zj-tech-research-report` and `zj-tech-design-review` retain their existing
quality responsibilities.

## A16 — Large roadmap artifact performance [G] ✅

### Question

How should `zj-roadmap-driven` evolve when its JSON source of truth and rendered
Markdown view grow large enough to cause noticeable performance bottlenecks,
while preserving its current CLI interface, deterministic human view, safe
writes/locks, and decision history?

The route should investigate at least:

- separating the small active index/control plane from large node, decision, and
  history data;
- lazy/depth-bounded reads and renders rather than loading the whole artifact;
- immutable snapshots or append-only history versus in-place rewrites;
- generated Markdown view size limits and focused views;
- migration, compatibility, atomicity, locking, and recovery for existing
  roadmap files;
- benchmark fixtures based on a realistically large roadmap, not only tiny demo
  files.

This is a parallel design route. It may reuse the Repository Map artifact
lessons, but it must not silently change the research-skill migration contract.

### Resolution

Keep a small single-file mode for ordinary roadmaps and add an explicit large
roadmap bundle mode:

```text
roadmap.bundle/
├── manifest.json
├── nodes/
├── decisions/
├── history/
├── views/
└── indexes/       # disposable derived data
```

The manifest is a small control plane. Current node state, decisions, and
history are independently readable; views and indexes are derived artifacts.
History is append-only, while periodically materialized snapshots prevent
reads from replaying an unbounded log. A `current pointer` selects the active
immutable snapshot/state without rewriting historical artifacts.

The existing CLI names remain, but default operations become lazy and bounded:
`tree`, `get`, `focus`, node-scoped `decisions`, and light `render` read only
the needed shards. `section` becomes bounded by default; full expansion is an
explicit operation and may accept a byte limit. Focused node/subtree/decision
views are first-class outputs.

Migration is explicit: validate the legacy JSON, write and validate a temporary
bundle, then atomically cut over under a bundle-level lock. The source remains
unchanged until cutover; failures retain the source and temporary recovery
artifacts. Ordinary writes do not silently trigger migration.

Acceptance uses separate dimensions for correctness, performance, and
usability. Benchmarks cover cold reads, bounded queries, writes, rendering,
concurrency, lock recovery, interrupted writes, memory, and growth across
small/medium/large fixtures. Full export may remain expensive; it is not used
to define the bounded-operation target.

## A17 — Roadmap CLI contract parity [G] ✅

### Question

Which commands and compatibility promises are actually supported by
`zj-roadmap-driven`? In particular, should the documented `import` command be
implemented, removed from the reference, or replaced by an explicit migration
command before the large-artifact storage change?

### Resolution

The implemented CLI and its tests are the authoritative command contract;
reference documentation must not promise commands that do not exist.

`import <json> <md>` is removed from the documented contract and is never
implemented: Markdown is a generated view, not a fact source. Large-storage
conversion uses an explicit `migrate <roadmap> --to bundle` command with
validation, temporary output, atomic cutover, and recovery preservation.

The existing creation, mutation, navigation, validation, recovery, and view
capabilities remain useful across both storage modes. Three semantics change:

- `remove-decision` no longer physically deletes append-only history; its
  canonical replacement is a traceable decision retraction, with the old name
  retained only as a deprecated compatibility alias if needed;
- `section` remains an export capability but is bounded by default, with full
  expansion requiring an explicit option such as `section --all`;
- `link` may later be grouped under a view command, but custom view binding is
  still a useful capability.

`import` is the only listed command ruled out as merely erroneous/legacy. The
other commands express real capabilities and should not be removed solely to
reduce the interface.

The resulting implementation tickets are listed below; this map remains
planning-only until the Human starts that implementation wave.

## A18 — Public research bucket and direct skill identity migration [T] ✅

### Question

How should the confirmed research skills be moved into `skills/research/`, the
report skill be directly renamed, active output paths and references updated,
and existing user edits preserved in one structural migration?

### Resolution

Completed the structural migration without overwriting the pre-existing user
changes in the report skill, its exemplar, the map, or the glossary:

- Moved `zj-research`, `zj-systematic-research`, and the directly renamed
  `zj-tech-research-report` into the formal public `skills/research/` bucket.
- Added the new `zj-code-research` skill entry with the accepted two-pass
  Repository Map → Architecture Study contract; implementation details remain
  in A20/A21.
- Updated frontmatter, agent metadata, top-level/bucket indexes, guide routes,
  AGENTS/CLAUDE bucket policy, validator bucket lists, private naming checks,
  and generated uninstall inventory. The recursive plugin manifest remains the
  discovery root; no old-name alias was added.
- Moved active generated outputs to
  `skills-outputs/zj-tech-research-report/` and updated the linked receipt and
  global landscape path. Stable protocol/schema names such as
  `zj-research-report-ir/v1` were intentionally preserved.
- Updated the compiler-artifact updater and golden-contract publisher path for
  the new sibling layout. Also replaced unsupported `zip(..., strict=True)` in
  the existing evaluation adapter with the already length-checked compatible
  form so the contract runs on the repository's Python runtime.

Verification passed: recursive plugin validation (48 skills), frontmatter
validation, private naming, Codex installation dry-run, research golden
contract (7 compiler cases and 10 evaluation cases), and `git diff --check`.

## A19 — Shared research runtime and evidence seam implementation [T] ✅

### Question

How should `zj-research` be narrowed to evidence production while retaining one
canonical compiler/evaluation adapter and an explicit setup pointer for an
independently installed `zj-tech-research-report`?

### Resolution

Implemented the shared runtime seam without duplicating the compiler or
evaluation adapters:

- Narrowed `zj-research` to primary-source findings, provenance, sealed ledgers,
  and explicit unknowns; report synthesis, ranking, and recommendations remain
  in consuming domain skills.
- Kept `research_cli.py`, `research_eval_cli.py`, the compiler lock, and the
  bundled artifact under `skills/research/zj-research/` as the canonical
  runtime.
- Updated the technical report publisher to resolve a sibling `zj-research`
  first, then an independently configured `ZJ_RESEARCH_RUNTIME` skill root.
  Missing runtime fails with the exact setup pointer instead of using a
  Markdown-only fallback.
- Documented the seam in the runtime reference, technical report skill, and
  `ZJ-CONTEXT.md`; added an independent-install test for both missing and
  explicitly configured runtime cases.

Verification passed: the research golden contract (7 compiler cases and 10
evaluation cases), independent publisher runtime checks, recursive plugin
validation (48 skills), private naming validation, Python compilation, and
`git diff --check`.

## A20 — Repository Map implementation [T] ✅

### Question

How should `zj-code-research` implement the commit-scoped Repository Map
snapshot bundle, deterministic scanner, navigation targets, and bounded views?

### Resolution

Implemented the Repository Map as a deep CLI seam in
`skills/research/zj-code-research/scripts/repository_map.py`:

- `scan` reads the checked-out `HEAD` (or a matching `--ref`) and records the
  commit, clean/dirty state, content fingerprint, scope, exclusions, unknowns,
  measured inventory, packages, integrations, workflows, and stable IDs.
- Each scan writes a new immutable bundle with a small manifest, independently
  readable JSON/JSONL fact shards, `navigation/targets.json`, and generated
  Markdown/HTML views. Existing bundles are rejected rather than overwritten.
- `view` reads only the requested shard and a positive record limit; `validate`
  checks all manifest-declared hashes, snapshot identity, summary, and target
  document before Architecture Study consumes the bundle.
- The scanner never follows symlinks, excludes `.git` and an in-repository
  output bundle, and preserves unreadable paths as explicit unknowns. It does
  not infer architecture or capability absence.
- Added the implementation reference and a generated temporary-repository
  contract covering commit pinning, dirty-tree fingerprints, target discovery,
  bounded views, validation, and write-once behavior.

Verification passed: Repository Map contract, research golden contract,
recursive plugin validation (48 skills), private naming validation, Python
compilation, and `git diff --check`.

## A21 — Architecture Study implementation [T] ✅

### Question

How should `zj-code-research` implement the evidence-linked Architecture Study
bundle, four record kinds, runtime/ownership/risk coverage, and Map-target
binding?

### Resolution

Implemented the Architecture Study as a separate deep CLI seam in
`skills/research/zj-code-research/scripts/architecture_study.py`:

- `study` accepts map target IDs or explicit repository-relative paths. A
  map-bound study validates the Repository Map first and refuses a changed
  commit or working-tree fingerprint; a direct study records the absence of a
  map as a `decision`.
- The immutable bundle has independent shards for scope, line-addressable
  evidence, relationships, runtime flows, claims, unknowns, risks, diagrams,
  and follow-up targets, with generated Markdown/HTML views.
- Evidence records carry source path, commit or working-tree fingerprint,
  SHA-256, and line ranges. `observed`, `inferred`, `unknown`, and `decision`
  are validated as the only record kinds; critical claims cannot pass without
  evidence IDs.
- The bounded pass records unresolved ownership and behavior as unknowns,
  derives only evidence-linked relationships/flows/risks, and keeps solution
  selection outside the study for `zj-tech-research-report`.
- Added the Architecture Study reference and a temporary-repository contract
  covering map binding, direct scope, four record kinds, evidence links,
  bounded views, validation, and stale-map rejection.

Verification passed: Architecture Study contract, Repository Map contract,
research golden contract, real ZAgentic map→study smoke test, recursive plugin
validation (48 skills), private naming validation, Python compilation, and
`git diff --check`.

## A22 — Technical research-report implementation [T] ✅

### Question

How should `zj-tech-research-report` implement the technical-only decision brief,
`technical-c4/v1` Report IR, compiler publication, and report quality gates
after the direct rename?

### Resolution

Implemented the technical report seam in
`skills/research/zj-tech-research-report/`:

- Added the `technical-decision-brief/v1` reference and a mechanical
  `technical-research-quality-gate/v1` validator. It checks the decision frame,
  sealed-ledger fingerprint, exact candidate `stars`/`topicMatch`, Evidence ID
  links, critical claims, cards, comparisons, recommendations, metrics,
  required C4 diagrams, and explicit follow-ups for sealed unknowns.
- Made `publish_report.py` require `--brief` for `technical-c4/v1` and run the
  quality gate before invoking the shared compiler. The receipt records the
  quality gate beside compiler evaluation; publication targets remain
  write-once.
- Kept the validator as a lazy technical-only import so an independently
  installed publisher can retain the existing low-level `zj-draft/v1` compiler
  contract while the public skill remains focused on technical-solution
  reports.
- Added a real-fixture contract covering successful publication and rejection
  of an invalid brief or broken evidence link without Markdown, HTML, or
  receipt artifacts. Updated the skill instructions and glossary vocabulary.

Verification passed: technical research-report contract, research golden
contract, Repository Map contract, Architecture Study contract, recursive
plugin validation (48 skills), private naming validation, Python compilation,
and `git diff --check`.

## A23 — Code-research quality fixtures and evaluation [T] ✅

### Question

How should the `landscape/v1` and `deep-read/v1` rubrics, mechanical hard gates,
controlled-quality fixtures, and calibrated semantic evaluation be implemented
for Repository Map and Architecture Study?

### Resolution

Implemented the code-research quality seam in
`skills/research/zj-code-research/`:

- Added `scripts/code_research_quality.py` with separate asset validation,
  Repository Map and Architecture Study mechanical hard gates, dimensional
  `landscape/v1` / `deep-read/v1` scoring, and calibrated Judge agreement
  reporting. The gate checks source pinning, scope/exclusions, shard hashes,
  inventory/tree consistency, target binding, line-addressable evidence,
  record kinds, unique IDs, critical-claim evidence, risks, diagrams, flows,
  and follow-up navigation.
- Added the independent controlled corpus under
  `research/evaluation/code-research-quality-v1/`: balanced and sparse
  landscape fixtures plus runtime and insufficient-evidence deep-read
  fixtures, human-coded required properties, rubric definitions, and four
  calibration samples. It does not reuse technical-report `reportFamily`
  assets, because the existing ZHarness evaluation protocol intentionally
  accepts only `technical-c4/v1` / `zj-draft/v1`; the protocol remains unchanged.
- Added a contract test that materializes each fixture into a temporary Git
  repository, runs map→study→quality evaluation, checks calibration
  (`scoreMeanAbsoluteError=2.0833`, tolerance/agreement `1.0`), and proves a
  tampered immutable shard is rejected.
- Fixed Architecture Study claim assembly so secondary ownership claims are
  not appended twice; duplicate record IDs are now a quality hard failure.

Verification passed: code-research quality contract, Repository Map contract,
Architecture Study contract, research golden contract, recursive plugin
validation, private naming validation, Python compilation, and `git diff --check`.

## A24 — Roadmap bundle storage and performance implementation [T] ✅

### Question

How should `zj-roadmap-driven` implement the optional sharded bundle, append-only
history, materialized snapshots, explicit migration, bounded views, and
small/medium/large benchmark fixtures while preserving the current mode?

### Resolution

Implemented the optional large-roadmap carrier in
`skills/engineering/zj-roadmap-driven/`:

- Added `roadmap_bundle.py` with a small manifest/current pointer, independently
  readable node and decision shards, append-only `history/events.jsonl`,
  interval-based materialized snapshot metadata, disposable status/focus/stats
  indexes, atomic writes, and validation/rebuild support. Single-file JSON mode
  remains unchanged for ordinary roadmaps.
- Unified `roadmap_cli.py` around a storage adapter: existing files use the
  legacy adapter, existing bundle directories use the bundle adapter, and
  `init --storage bundle` creates a bundle directly. `migrate <json> --to bundle`
  validates the source, writes/validates a temporary bundle, locks source and
  destination, then atomically renames the result; failures leave the source
  unchanged and do not implement Markdown import.
- Preserved the useful command compatibility surface across both modes. Bundle
  reads for `tree`, `get`, `focus`, node-scoped `decisions`, and light `render`
  stay shard-local; `section` is bounded by default and `section --all` is the
  explicit full export. Bundle `remove-decision` records a traceable retraction
  instead of deleting the original decision record.
- Added 14 bundle/single-file contract tests covering migration/source
  preservation, parent-status cascade, snapshot intervals, bounded reads,
  corruption/stale-index rejection, invalid migration recovery, concurrent
  writes, lock-compatible history sequencing, and existing CLI behavior. Added
  a standard-library benchmark generator for 100/1,000/5,000-node fixtures;
  observed large-fixture bounded operations stayed near constant-time while
  full export remained explicitly expensive (`full_section_ms=406.686` on the
  local 5,000-node run).
- Updated the skill, CLI reference, data-model wording, and wayfinder/roadmap
  dual-mode design so Markdown is a generated view and the fact source is
  single-file JSON or bundle canonical shards according to the selected mode.

Verification passed: roadmap single-file and bundle contract tests (14 tests),
Python compilation, small/medium/large benchmark generation, and `git diff
--check`.

## A25 — Research migration and roadmap verification closeout [T] ✅

### Question

How should the completed implementation wave be verified across public-bucket
governance, skill discovery, compiler contracts, artifact paths, code-research
quality, roadmap migration, and user-facing documentation before closeout?

### Resolution

Completed the implementation-wave closeout without modifying the external
`ZBrainForStudy` repository:

- Added `skills/engineering/zj-roadmap-driven/tests/verify_real_plan_corpus.py`.
  It reads the real `ZBrainForStudy/docs/plans/` corpus as a read-only input,
  builds an equivalent legacy JSON fixture only in a temporary directory, and
  exercises the public `migrate --to bundle`, `validate`, `tree`, `get`,
  bounded `section`, `section --all`, `link`, `render`, and rejected `import`
  paths. The corpus contains 12 Markdown files and 66,305 bytes; migration
  produced 14 temporary nodes and 12 decision shards, preserved source bytes,
  and proved a depth-1 tree reads only `1` and `1-1` shards.
- Re-ran the research golden contract, Repository Map contract, Architecture
  Study contract, code-research quality contract, technical research-report
  contract, 14 roadmap single/bundle tests, Python compilation, frontmatter,
  private naming, plugin validation, and skill discovery/link dry-run. The
  generated 48-skill list is unchanged and includes all four research skills.
- The official plugin validator still reports the known four bucket-root
  `SKILL.md` warnings (`engineering`, `misc`, `productivity`, `research`);
  repository recursive validation passes all 48 skills. This is retained as a
  transparent warning rather than adding fake bucket frontmatter files.
- The old `zj-research-report` name appears only in historical wayfinder
  decisions and migration narrative; stable protocol/schema identifiers such
  as `zj-research-report-ir/v1` are retained intentionally. No active old-name
  alias, old output path, or old discovery entry remains.
- The implementation wave is represented by commit `817e218`; the A25
  verification script and this closeout documentation are the remaining
  closeout delta to commit. No external repository, branch, worktree, or user
  planning file was cleaned or deleted.

Verification status: knowledge and workspace closeout complete for the local
implementation wave; deployment/live verification is not applicable because
these are installable local skills and no deployment was performed.

## A26 — Read-only roadmap storage advisory [T] ✅

### Question

How should users choose between ordinary single-file JSON and an explicit
sharded roadmap bundle without introducing automatic format switching or
read-time repair side effects?

### Resolution

Implemented a read-only storage advisor in
`skills/engineering/zj-roadmap-driven/storage_advisor.py` and exposed it as:

```bash
python roadmap_cli.py recommend-storage <roadmap_path> [--measure]
```

- The versioned `zj-roadmap-storage-recommendation/v1` output reports node and
  decision counts, maximum depth, canonical bytes, view bytes, bundle shard
  counts, history bytes, and total artifact bytes.
- The default policy returns `keep-single`, `consider-bundle`, or
  `recommend-bundle`; an already selected bundle returns `keep-bundle`.
  Starting signals are 1,000 nodes, 500 decisions, or 256 KiB of canonical
  data; severe signals are 5,000 nodes, 2,000 decisions, or 1 MiB. `--measure`
  adds bounded-tree and full-section timings, with 100/300 ms advisory lines.
- The command never calls bundle index rebuild, never migrates, never writes
  Markdown, and never changes the selected carrier. A missing derived bundle
  index remains missing after the recommendation, preserving the strict
  read-only contract.
- Added five contract tests covering small single-file keep, medium
  single-file consideration, large single-file recommendation, bundle
  measurement/read-only behavior, and missing-index non-repair. Existing
  explicit `migrate --to bundle` remains the only storage conversion path.

Verification passed: storage-advisor contract tests, existing roadmap
single-file/bundle tests, Python compilation, and `git diff --check`.

## A27 — Storage-advisor threshold calibration [T] ✅

### Question

How should `recommend-storage` interpret real roadmap corpora when structural
size signals are present but local measurements do not show a current
performance bottleneck, and how should it distinguish execution roadmaps from
the global Initiative Registry index?

### Resolution

Calibrated the A26 policy against real read-only JSON corpora and tightened the
input boundary:

- A single starting signal still returns `consider-bundle`. Multiple starting
  signals now remain `consider-bundle`; they explain structural pressure but do
  not assert a performance failure. `recommend-bundle` requires a severe
  structural signal or an explicit `--measure` result at the severe
  `full_section_ms` line.
- `recommend-storage` now validates single-file execution roadmaps and rejects
  inputs without the execution root node `1`. Bundle reports likewise reject a
  bundle without root shard `nodes/1.json`, preventing the fixed three-level
  global Initiative Registry schema from being treated as an execution route.
- Read-only dogfood covered: `ZBrain/docs/plans/big-map-roadmap.json` (18
  nodes, 4.9 KB, `keep-single`),
  `ZAgenticLoop/docs/plans/opn-real-agent-dogfood-next-milestone-roadmap.json`
  (20 nodes, 465 decisions, 245.9 KB, `keep-single`), and
  `ZAgenticLoop/docs/plans/loop-graph-engineering-integration-roadmap.json`
  (23 nodes, 694 decisions, 411.4 KB, `consider-bundle`; measured bounded tree
  0.767 ms and full section 0.956 ms). Source hashes were unchanged.
- Added two contract tests for the calibrated two-signal result and rejection
  of a non-execution Registry JSON; the full storage-advisor contract now has
  seven tests.

Verification passed: seven storage-advisor tests, the complete roadmap test
suite, Python compilation, recursive plugin validation, and `git diff --check`.

## A28 — Research/roadmap implementation release [T] ✅

### Question

How should the completed research and roadmap implementation wave be published
without mixing release closeout documents into the implementation commits or
claiming deployment that did not happen?

### Resolution

Published the completed implementation wave from `main` after refreshing the
remote and confirming the fast-forward path. The release closeout remained a
separate knowledge-governance step, and the repository records the result as a
published GitHub repository state rather than a deployed or live-verified
runtime. The closeout also retained the known bucket-root validator warnings
and the bundled compiler artifact used by contract tests.

## A29 — Real research-chain dogfood [T] ✅

### Question

Does the composed research route work on a real technical decision from
commit-pinned code research through evidence collection, technical report
publication, and quality evaluation, including failure boundaries?

### Resolution

Ran the real `zj-code-research → zj-research → zj-tech-research-report` chain:

- Repository Map snapshot `map-c8ade72a1d1d9640c164106c` and Architecture Study
  snapshot `study-bec314dee3c9f2e9f604c52b` passed their hard gates after the
  study generator made each entrypoint flow ID include its line-scoped evidence
  identity, preventing duplicate IDs for one source file.
- The requested three-repository fresh collection was blocked by exhausted
  unauthenticated GitHub API quota. No fresh ledger was fabricated; the report
  explicitly reused a previously successful sealed ledger and kept its broader
  evidence boundary visible. A31 later replaced that historical reuse with an
  authenticated fresh collection, and A32 republished the report from it.
- The technical `Report IR`, Markdown, HTML, receipt, and technical quality
  gate passed. The evidence supported adapter-only capability probes, while the
  native core remained the recommended semantic owner.

## A30 — Research collection runtime hardening [T] ✅

### Question

How should `zj-research` prevent an avoidable GitHub auth/quota failure from
consuming a multi-repository run, and how should it distinguish a new
collection from an explicitly reused sealed ledger or a blocked attempt?

### Resolution

Hardened the shared research runtime without changing the
`zj-research-cli/v1` protocol:

- A GitHub `/rate_limit` preflight records authentication mode and core quota
  before fresh collection. Anonymous collection remains possible when quota is
  available; invalid credentials, exhausted quota, forbidden responses, and
  network failures fail with structured diagnostics.
- Compiler stderr and malformed responses are classified into stable, actionable
  error codes. Uncontextualized failures such as `undefined.map` retain the
  original compiler detail but are no longer exposed as the only explanation.
- `--status-output` records the current brief and one of
  `fresh-collection`, `reused-sealed-ledger`, or `collection-blocked`.
  `--reuse-ledger` is explicit and requires a matching brief fingerprint; a
  blocked fresh run never silently falls back to an older ledger.
- Runtime contract tests cover auth/quota/network failures, compiler error
  classification, brief matching, status serialization, explicit reuse, and
  fresh/blocked state transitions. The existing golden compiler/evaluation
  contract remains green.

The implementation was published as commit `fb71652` on `main`; live fresh
collection with an authenticated GitHub token remains the next operational
acceptance step, not an unverified claim of A30.

## A31 — Authenticated live collection acceptance [T] ✅

### Question

Can the hardened `zj-research` runtime complete a real authenticated fresh
collection against the fixed three-repository technical brief, preserving
status, provenance, commit-pinned evidence, and explicit unknowns rather than
silently reusing the older sealed ledger?

### Resolution

Completed a live fresh collection with the authenticated GitHub CLI credential
injected only into the child process. The run used the existing
`research-brief.json` for the Graph Coordinator framework selection and wrote
new A31 artifacts beside it:

- `skills-outputs/zj-research/zjloop-graph-coordinator-framework-selection/a31-live-collection-status.json`
  records `state: fresh-collection`, authenticated preflight, a core quota of
  `5000` with `4996` remaining, `canCollect: true`, and no automatic fallback.
- `skills-outputs/zj-research/zjloop-graph-coordinator-framework-selection/a31-live-ledger-response.json`
  records a `zj-verified-evidence-ledger/v1` with the matching brief
  fingerprint, 22 Evidence IDs, 36 files read, 175,177 source bytes, a
  non-cache collection, and three commit-pinned repositories:
  LangGraph `f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`, AutoGen
  `027ecf0a379bcc1d09956d46d12d44a3ad9cee14`, and CrewAI
  `f4731f5025f861c78e3af0487cc80bf5e7c64782`.
- The sealed ledger retains explicit candidate stars/topic matches and two
  `unknownCriteria` entries; neither was converted into a negative claim.

The first live attempt exposed a real runtime bug in A30's preflight: passing
`timeout` as the second positional argument to Python 3.13's `urlopen` treated
the float as an HTTP body. Changed the call to `timeout=timeout` and added a
regression assertion in `verify_runtime_contract.py`. The runtime contract,
golden contract (7 compiler cases and 10 evaluation cases), Python compilation,
and diff check all passed before the successful rerun.

Verification status: A31 live fresh collection accepted. The generated status
sidecar proves the authenticated fresh state; the generated ledger is the only
source for the collected GitHub facts. No old ledger was used.

## A32 — Fresh-ledger technical report republish [T] ✅

### Question

Can the A31 fresh sealed ledger feed a new technical-solution research report
without reusing A29's older brief, evidence boundary, fingerprint, or empty
unknown set?

### Resolution

Rebuilt the technical report inputs from the A31 ledger instead of swapping a
fingerprint into the older Report IR:

- Wrote fresh cited findings at
  `skills-outputs/zj-tech-research-report/zjloop-graph-coordinator-framework-selection/a32-fresh-findings.md`.
- Wrote a new `technical-c4/v1` Report IR at
  `skills-outputs/zj-tech-research-report/zjloop-graph-coordinator-framework-selection/a32-report-ir.json`
  with three candidates, eight claims, five comparisons, seven
  recommendations, seven metrics, 22 ledger Evidence IDs, and two explicit
  unknown follow-ups.
- Reused the existing technical decision brief only as the unchanged decision
  frame. The Report IR uses A31 fingerprint
  `5fbef253ed7642b64eeb69af673a2e458fa2ed04b9aaabfde8fb09c6f2128a36`; the old
  A29 fingerprint is absent from all A32 artifacts.
- Published new Markdown, HTML, and receipt artifacts with report hash
  `bfb31a765e8e2df6896083ee0c0244451e530aed846394d0dcfe9a08ac937334`.
  Compiler evaluation and the technical research quality gate both report
  `healthy: true`, with `publishExactlyOnce`, revision pinning, provenance,
  critical-claim evidence, and unknown surfacing all passing.

The fresh evidence supports the same bounded direction — keep the native core,
then test LangGraph checkpoint, AutoGen event/delegation, and CrewAI
role/task/persistence as removable adapter capabilities — while keeping
LangGraph observability and AutoGen security/sandbox as unresolved follow-ups.

Verification passed: technical Report IR quality gate, technical research-report
contract, publication consistency (fresh fingerprint, receipt hash, no old
ledger), and `git diff --check`.

## A33 — Roadmap-driven handoff for LangGraph checkpoint probe [T] ✅

### Question

How should the settled A32 recommendation move from Wayfinder planning into
roadmap-driven execution without migrating the historical decision map or
turning the LangGraph adapter into a new product authority?

### Resolution

Created a separate small single-file execution roadmap in the target product
repository:

`ZAgenticLoop/docs/plans/opn-langgraph-checkpoint-adapter-probe-roadmap.json`

with generated view:

`ZAgenticLoop/docs/plans/opn-langgraph-checkpoint-adapter-probe-roadmap.md`

The roadmap is valid and contains 16 nodes, four persisted decisions, 14
pending nodes, and two in-progress nodes. Its route is bounded to:

- native baseline and `Conformance fixture`;
- provider-neutral checkpoint adapter contract;
- isolated LangGraph checkpoint/resume probe;
- authority, Evidence, failure-gate, and Human acceptance conformance;
- adapter removal and continue/defer/stop closeout.

The root decision explicitly keeps the native Graph/OPN core, Evidence,
Human acceptance, security, and lifecycle authority in ZAgenticLoop. AutoGen
and CrewAI are deferred. The current roadmap focus is
`1-1-1 Define native checkpoint fixture and resume oracle`; `roadmap_cli
validate`, `stats`, `tree`, `focus`, and bounded `section` all passed.

Wayfinder remains the historical decision map; the new roadmap is the sole
execution tracker for the probe. Existing unrelated `ZAgenticLoop` changes in
`tools/zj-loop-mcp-server/package-lock.json`, `.tmp/`, and
`tools/zj-loop-core/.tmp/` were preserved.

## A34 — Second real research combination acceptance [T] ✅

### Question

Can the composed `zj-code-research → zj-research → zj-tech-research-report`
route complete a second real acceptance on the A33 LangGraph checkpoint/resume
decision, while keeping a dirty consumer snapshot pinned, collecting fresh
external evidence, and refusing to overstate mechanically matched gaps?

### Resolution

Completed a second real research-combination run against the current
`ZAgenticLoop` consumer repository and the explicit `langchain-ai/langgraph`
repository:

- `zj-code-research` produced and validated Repository Map
  `map-107165ed1ab7a867791fc300` at commit
  `88cdfb86218022d98119f05e940cfb6068b25959`, explicitly recording a dirty
  working tree, 2,340 files, 547 directories, 71,572,479 source bytes, and one
  unreadable socket path as an unknown. Its map-bound Architecture Study
  `study-55b124aa9d5fcfa0e67cc114` selected nine checkpoint/graph/runtime
  targets and passed with 461 line-addressable Evidence records, one unknown,
  three risks, and unique record IDs.
- `zj-research` completed two authenticated fresh collections, retaining both
  status sidecars and sealed ledgers. The first pass recorded 13 files and
  33,109 source bytes; the discriminating v2 pass is the report source, with
  fingerprint `c012ac5ea04d673fb1e7c7f6f317c62dc822d34727f78ef39889c61f5d544250`,
  LangGraph commit `f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`, 24 files,
  41,617 source bytes, and five canonical Evidence IDs. Both statuses are
  `fresh-collection`, authenticated, and non-cache.
- The v2 evidence supports LangGraph's `BaseCheckpointSaver` storage and
  conformance seam plus a Postgres persistence boundary. It does not directly
  establish `thread_id`/interrupt resume identity, a native TypeScript/Node.js
  checkpointer seam, or host security/approval ownership. These remain explicit
  unknown follow-ups even though the compiler's `unknownCriteria` is empty.
- `zj-tech-research-report` published a new `technical-c4/v1` report from the
  v2 ledger, with five ledger Evidence links, seven claims, four comparisons,
  six recommendations, and seven metrics. The receipt reports compiler and
  technical quality gates `healthy: true`, `publishExactlyOnce: true`, and
  report hash `49ef31bb98927dc89313a010c9228b8a89fc17146fefae72ff2b41bcb9ebbea3`.

The decision is bounded: keep the ZAgenticLoop native Graph/OPN core and use
LangGraph only for an isolated, removable checkpoint adapter probe. Native
execution identity, duplicate delivery, Evidence, verification, Human
acceptance, security, and lifecycle remain the conformance authority; identity
drift, digest drift, second execution authority, authority bypass, or failed
adapter removal are hard stops.

Verification passed: repository-map and architecture-study contracts,
code-research quality assets/map/study gates, research runtime and golden
contracts, technical report quality gate, compiler publication consistency,
recursive plugin validation, and `git diff --check`. Existing uncommitted
changes in `ZAgenticLoop` were not modified.
