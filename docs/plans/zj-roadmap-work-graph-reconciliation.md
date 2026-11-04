# Roadmap reconciliation and work-graph design review

## One-page overview

### Decision

Decision: revise.

The architectural direction is accepted for further design: keep the tree as the
primary Human outline, but stop using ordered tree placement as work identity or
execution order. Add a reconciliation seam and atomic ChangeSet before considering
a full canonical work-graph migration.

Blocking findings:

- The semantic identity/obligation key used for deterministic duplicate detection
  is not yet specified.
- The migration boundary between the current `parent`/`children` carrier shape and
  future Placement/decomposition facts is not yet proven on real roadmap corpora.
- Duplicate, overlap, and replan baselines are unknown and must be measured before
  implementation is approved.
- Every rollout stage is blocked until generated views retain the process-state
  authority envelope and `authority-check .` reports zero durable Roadmap citations.

Non-blocking findings:

- The final Markdown notation for reference Placements (`↪` or another marker)
  needs Human review.
- A separate non-causal `precedes` constraint may be useful, but `priority` plus
  `blocks` should be tried first to avoid expanding the relation vocabulary.

### Summary

Execution findings currently move from the Trace layer into new plan Nodes without
Roadmap-wide reconciliation. This design introduces `Trace → Reconcile → ChangeSet
→ Work Graph → Outline projection`, so duplicate/overlapping work, dependency
changes, and topology changes are reviewed and committed atomically without making
the Human read a raw DAG.

### Platforms and scope

Supported environments are the existing local Python CLI, single-file JSON Roadmap
carrier, and SQLite Roadmap carrier. Affected surfaces are
`skills/codebase-docs/zj-roadmap-driven/roadmap.py`, `roadmap_sqlite.py`,
`roadmap_cli.py`, their tests and references, `ZJ-CONTEXT.md`, and the generated
Markdown view.

In scope:

- execution findings, reconciliation, duplicate/overlap detection;
- topology and Edge changes applied as one atomic ChangeSet;
- separation of work identity, decomposition, dependency, priority, and display;
- compatibility and migration for both carriers;
- Human outline and review projections.

Out of scope:

- replacing the Human outline with a graph UI;
- remote coordination, cloud storage, or a network service;
- autonomous model-driven merges of semantically similar Nodes;
- a general-purpose constraint language;
- immediate replacement of the current carrier with full event sourcing.

### Ownership and tracking

Decision owner: Human maintainer of `zj-roadmap-driven`.

Engineering owner: `zj-roadmap-driven` maintainer. Documentation owner:
`codebase-docs` documentation maintainer. Reviewers: Roadmap users who have observed
duplicate/overlapping Nodes, plus one carrier-contract reviewer.

Tracking item: this plan until an implementation issue or roadmap is created.

## Problem and goals

### User and job

A Human and one or more Agents use a Roadmap to execute long-running work while
retaining a compact shared view. During execution, newly discovered legacy work,
risks, or prerequisites must not be missed, duplicated, or allowed to corrupt the
atomicity of existing work.

### Current baseline

Observed:

- Plan Nodes are stored with `parent` and ordered `children`; display ids encode
  that position.
- Immutable `uid` already provides stable identity for durable references.
- `blocks` and other Edges are orthogonal to the tree and scheduling queries are
  derived from `blocks`.
- The Trace layer keeps execution-emergent findings out of the Human outline.
- `promote --accept` now acts as a compatibility adapter: it requires a reviewed
  reconciliation digest and delegates the topology write to the ChangeSet apply
  path; direct `Roadmap.promote(..., "accept")` is rejected.
- `add_node` validates parent, status, layer, and structural budget, but does not
  classify semantic overlap or duplicates.
- Parent Status is synchronized from `children`, so the tree remains both a display
  structure and an execution aggregation structure.

Evidence:

- [Roadmap execution graph](../designs/zj-roadmap-execution-graph.md)
- [Roadmap concurrency and dependency model](../designs/zj-roadmap-concurrency-model.md)
- [Roadmap data model](../../skills/codebase-docs/zj-roadmap-driven/references/roadmap-data-model.md)
- [Roadmap implementation](../../skills/codebase-docs/zj-roadmap-driven/roadmap.py)

Inferred:

- The recurring failure mode is not caused by trees alone. It is caused by
  conflating work identity, decomposition, display position, execution order,
  dependency, and completion aggregation in the same Node/children structure.
- Replacing the tree with a raw DAG would improve expressiveness but would not by
  itself prevent semantic duplicates.

Unknown:

- The duplicate and overlap rate in completed real-world Roadmaps.
- How often users need non-causal mandatory ordering beyond `priority` and `blocks`.
- Whether reference Placements are understandable in the bounded Markdown view.

### Goals

- Prevent a finding from becoming a new plan Node until it has been reconciled
  against the whole active Roadmap.
- Distinguish `covered`, `refine`, `reshape`, `novel`, and `dismiss` outcomes.
- Make dependency, priority, and Human display order independent concepts.
- Apply split, merge, move, Edge replacement, Decision append, and Trace disposition
  atomically.
- Preserve immutable `uid`, Trace layer isolation, derived scheduling facts, and
  byte-equivalent semantics across JSON and SQLite carriers.
- Keep the default Human view tree-shaped and bounded.

### Non-goals

- Perfect automatic semantic equivalence detection.
- Allowing an LLM similarity score to merge or discard work autonomously.
- Encoding all project scheduling theory in the Roadmap.
- Making display ids stable durable references.

### Assumptions and constraints

- The Roadmap Scope Gate remains mandatory before project edits or topology changes.
- Human authority remains required for topology-changing acceptance; self-reported
  actor flags are not authentication.
- All durable references use immutable `uid`; display ids are convenience addresses.
- Markdown remains a derived, non-importable view.
- Both carriers must expose identical semantic results and stable `E_*` errors.
- Runtime skill closure and ADR 0010 relative-path persistence rules remain intact.
- Roadmap status may select work but cannot substantiate product, architecture,
  release, or correctness claims; those claims promote through durable evidence.

### Success definition

The design succeeds when the same execution findings can be replayed against both
carriers and produce the same reconciliation proposal, accepted semantic state,
derived scheduling answers, and Markdown bytes; exact duplicates create no new
active WorkItem; ambiguous semantic matches require an explicit Human Decision;
and injected failure cannot expose a partially applied replan.

## Design

### Alternatives considered

1. **Keep the ordered tree and add more Edge types.** Small migration cost, but
   identity, overlap, direct promotion, and partial topology mutation remain
   unresolved. Rejected as insufficient.
2. **Replace the tree with a raw DAG.** Flexible scheduling and sharing, but poor
   Human orientation and no intrinsic duplicate prevention. Rejected as the default
   view and deferred as an internal representation choice.
3. **Use automatic model-assisted semantic deduplication.** Useful for ranking
   candidates, but false merges destroy work and provenance. Rejected as an
   authority; may later be an optional candidate-producing Adapter.
4. **Adopt immutable event sourcing and revision DAG immediately.** Strong audit and
   conflict semantics, but high migration/storage cost and inconsistent with the
   current choice to prefer SQLite over a custom event stream. Deferred.
5. **Chosen hybrid.** Add a deep Reconciliation Module and atomic ChangeSet first;
   then separate WorkItem identity from outline Placement if corpus validation
   demonstrates the need.

### Chosen model

```text
Trace finding
  -> Reconciliation Proposal
       covered | refine | reshape | novel | dismiss | unresolved
  -> Human review
  -> atomic ChangeSet
       WorkItem changes + Placement changes + Edge changes
       + Decisions + Trace disposition
  -> canonical semantic state
       -> Human outline projection
       -> ready / blocked / critical-path / impact
```

The canonical concepts are separated as follows:

| Concern | Representation |
|---|---|
| Work identity | `WorkItem(uid)` |
| Decomposition | membership/contains relation |
| Hard causal dependency | `blocks` Edge |
| Selection among ready work | `priority` |
| Human placement and order | primary/reference Placement plus outline rank |
| Execution evidence | Trace layer |
| Plan mutation | versioned atomic ChangeSet |

`precedes` is not part of the initial vocabulary. It may be introduced only if a
fixture proves a mandatory non-causal sequence that cannot be represented by
`blocks` or priority without corrupting `impact` semantics.

### Node and completion invariants

- `uid` is immutable and never reused.
- An executable `work` Node is atomic and has no decomposition children.
- A `group`/milestone is not directly executable; its completion is derived from its
  selected members.
- One accepted obligation has at most one active canonical owner. Ambiguity produces
  a review question, not an automatic Node.
- One WorkItem may appear in several outline contexts through reference Placements;
  references do not duplicate Status, Decision history, leases, or completion.
- Display order has no scheduling semantics.
- `blocked`, ready set, critical path, impact, group completion, and display ids are
  derived, not independently stored.

### Reconciliation Module and seam

The external Interface is intentionally small:

```text
reconcile(base_revision, trace_cut, write_scope, answers?) -> Proposal
apply(proposal_id, approved_digest, idempotency_key)       -> CommitReceipt
project(revision, outline | execution | review)            -> View
```

`reconcile` reads globally for duplicate detection but writes only within the
declared scope. Its proposal contains candidate matches, novelty evidence, intended
WorkItem/Placement/Edge changes, impact, and unresolved questions.

`apply` compares the proposal base revision with the current revision, validates the
final candidate graph, and commits all canonical changes or none. Markdown refresh
occurs after canonical commit; a refresh failure returns a committed revision plus a
stale-view signal, so retry cannot duplicate the mutation.

The Implementation hides obligation extraction, deterministic candidate matching,
duplicate clustering, split/merge/coalesce semantics, Edge rewiring, cycle and layer
validation, display-id remapping, carrier transactions, and derived queries.

### Reconciliation dispositions

| Result | Meaning | Plan effect |
|---|---|---|
| `covered` | Existing WorkItem already owns the obligation | Link provenance only |
| `refine` | Existing work needs criteria/scope clarification | Patch or explicitly reopen |
| `reshape` | Existing topology is wrong | Split, merge, move, or supersede in ChangeSet |
| `novel` | No active WorkItem covers the obligation | Create after novelty evidence |
| `dismiss` | Evidence does not require scheduling | Keep Trace and Decision |
| `unresolved` | Identity/scope is ambiguous | Block apply pending Human answer |

Creation requires evidence listing the candidates considered and why none covers the
obligation. Exact deterministic identity matches may be rejected mechanically;
semantic similarity only produces candidates.

### ChangeSet semantics

A ChangeSet has a stable id, base revision, Scope Gate classification, Trace
provenance, preconditions, and a closed list of changes. Initial change kinds:

- `work.create`, `work.patch`, `work.coalesce`, `work.supersede`;
- `placement.put`, `placement.move`, `placement.reference`;
- `edge.put`, `edge.remove`, `edge.replace`;
- `decision.append`, `trace.disposition`.

The Implementation applies all changes to a private candidate state, validates the
final state rather than intermediate operations, and then commits with compare-and-
swap against the base revision. The initial design does not require a full immutable
event store; current-revision hashes plus carrier-native atomic replacement/
transaction are sufficient.

### Failure handling

- `E_IDENTITY_AMBIGUOUS`: return candidate WorkItems and required Human question.
- `E_OVERLAP_UNRESOLVED`: obligations have multiple unresolved active owners.
- `E_CONFLICT`: base revision changed; rerun reconciliation.
- `E_APPROVAL_MISMATCH`: reviewed digest differs from the proposal being applied.
- `E_CYCLE`: final dependency/decomposition graph violates acyclicity.
- `E_LAYER_VIOLATION`: Trace/plan direction or Placement rules are violated.
- `E_SCOPE`: proposed write escapes the approved subtree/scope.
- `E_CHANGESET_INVALID`: final candidate violates a structural invariant.
- `E_VIEW_STALE`: canonical commit succeeded but Markdown publication needs repair.

Semantic uncertainty is a proposal state, not an exception. Existing retryable lock
and budget exit-code meanings remain unchanged.

### Compatibility and migration

1. Add read-only `reconcile` preview while all existing commands remain unchanged.
2. Route `promote` proposals through reconciliation; keep direct acceptance behind a
   compatibility Adapter during corpus validation.
3. Add ChangeSet preview/apply and route topology-changing commands through it.
4. Introduce typed `group`/`work` Nodes with a migration report; preserve all `uid`s.
5. Convert existing `parent`/`children` to primary Placements/decomposition facts;
   retain old child order only as an outline hint, never infer dependencies from it.
6. Disable direct topology mutation only after dual-carrier parity and real-corpus
   replay gates pass.

The source carrier remains recoverable during migration. No dual-write mode is
allowed: it would create two competing fact sources.

### Ownership boundaries

- Reconciliation policy, ChangeSet validation, and derived scheduling: Roadmap core
  Module owner.
- JSON/SQLite persistence primitives: carrier Adapter owner.
- CLI argument translation and Human-facing errors: CLI Adapter owner.
- Markdown layout and reference notation: projection owner.
- Decisions about ambiguous identity/scope: Human decision owner.

## Metrics and experiments

| Metric | Baseline | Unit | Method | Target/threshold | Owner |
|---|---|---|---|---|---|
| Exact duplicate creation | 0 in the labeled synthetic corpus | new active WorkItems per 100 duplicate findings | Replay a labeled corpus on both carriers | 0 | Roadmap core owner |
| False automatic merge | 0 in the near-duplicate fixtures | wrongly coalesced WorkItems per corpus | Adversarial near-duplicate fixtures | 0 | Roadmap core owner |
| Atomic replan integrity | 0 partial states in injected-failure fixtures | partial commits per 100 injected failures | Fault injection at every ChangeSet stage | 0 | Carrier Adapter owner |
| Cross-carrier semantic drift | 0 mismatches across 30 scenarios | mismatched outputs per fixture | Run identical corpus against JSON and SQLite | 0 | Carrier contract reviewer |
| Reconcile latency at 5,000 plan Nodes | JSON p95 10.19 ms; SQLite p95 7.26 ms | p95 milliseconds per proposal | Fixed local benchmark fixture, 30 runs | <= 1,000 ms | Roadmap core owner |
| Human outline growth from Trace-only writes | Existing design target is byte-stable | changed Markdown bytes | Add Trace records without plan acceptance | 0 bytes | Projection owner |
| Routine Human decisions | Unknown | questions per accepted finding batch | Replay labeled corpus and count unresolved outcomes | p95 <= 1 | Human workflow reviewer |

Experiment acceptance requires at least 30 labeled scenarios containing exact
duplicates, near-duplicates, cross-subtree overlap, completed-Node refinement,
dependency reversal, split, merge, cycle rejection, stale revision, and renderer
failure. Results must include raw fixture ids and both carrier outputs.

### Implementation evidence (2026-11-03)

The first implementation slices are now exercised through the public CLI for both
carriers. The evidence is reproducible from the repository (the JSON reports are
process artifacts under `tmp/skills-outputs/` and remain out of Git):

| Slice | Result | Reproduction / evidence |
|---|---|---|
| S0 deterministic reconciliation contract | 30/30 labeled scenarios; raw per-carrier outputs; `semantic_parity: true` | `skills/codebase-docs/zj-roadmap-driven/tests/reconciliation_corpus.py`; `tmp/skills-outputs/zj-roadmap-driven/reconciliation-corpus/report.json` |
| S1 preview and Human decisions | `covered`, `refine` (`reopen`/`supersede`/`noop`), `reshape`, `dismiss`, `novel`, `unresolved` covered by tests | `skills/codebase-docs/zj-roadmap-driven/tests/test_reconcile.py`, `skills/codebase-docs/zj-roadmap-driven/tests/test_reconciliation_corpus.py` |
| S2 atomic ChangeSet apply | topology, Placement, Decision and Trace operations; cycle/stale/fault paths leave no partial state | `skills/codebase-docs/zj-roadmap-driven/tests/test_changeset.py`, `skills/codebase-docs/zj-roadmap-driven/tests/test_reconcile.py` |
| Scoped ChangeSet writes | all operation reference classes rejected outside the inclusive subtree; legacy Placement ids and prompted-by Trace checked | `skills/codebase-docs/zj-roadmap-driven/tests/test_changeset.py::test_preview_scope_rejects_every_out_of_scope_topology_reference` |
| 5,000-node reconciliation capacity | 30 runs/carrier; JSON p95 10.19 ms; SQLite p95 7.26 ms; both under 1,000 ms | `skills/codebase-docs/zj-roadmap-driven/tests/benchmark_reconcile.py`; `tmp/skills-outputs/zj-roadmap-driven/reconciliation-benchmark/report.json` |
| Placement projection and typed migration | source-preserving primary/reference projection, radial Markdown coverage, group/work classification | `skills/codebase-docs/zj-roadmap-driven/tests/test_placement_projection.py`, `skills/codebase-docs/zj-roadmap-driven/tests/test_type_migration.py`, `skills/codebase-docs/zj-roadmap-driven/tests/test_placement_migration.py` |
| S3-1 default `promote --accept` routing | reviewed digest/idempotency adapter; JSON/SQLite receipts; stale/digest/legacy-override rejection; direct API bypass rejected | `skills/codebase-docs/zj-roadmap-driven/tests/test_promote.py`, `skills/codebase-docs/zj-roadmap-driven/tests/test_trace_prune_context.py`, `skills/codebase-docs/zj-roadmap-driven/roadmap.py`, `skills/codebase-docs/zj-roadmap-driven/roadmap_cli.py` |

This closes the synthetic S0–S2 implementation gate and implements S3-1. The
S3 rollout close-out, replay against three real Roadmaps, and Human review of the
reference notation remain open before the plan can be declared complete.

## Rollout, recovery, and lifecycle

### Rollout

1. **S0 — corpus and contract:** no runtime behavior change; establish baselines and
   expected dispositions; keep the authority envelope and `authority-check .` green.
2. **S1 — preview only:** add reconciliation output and review projection; direct
   promotion remains authoritative.
3. **S2 — opt-in ChangeSet apply:** selected fixtures and internal Roadmaps use the
   new path; old topology commands remain a compatibility Adapter.
4. **S3 — default reconciliation:** `promote --accept` routes through an accepted
   proposal digest; direct bypass emits a deprecation error. S3-1 implements this
   route; S3-2 still owns rollout parity, fault, governance, and review evidence.
5. **S4 — Placement migration:** only after real-corpus replay proves the projection
   and display-id migration.

### Monitoring and pause conditions

Pause progression on any false automatic merge, partial ChangeSet commit,
cross-carrier mismatch, lost Decision/provenance Edge, Trace leakage into Markdown,
or unexplained display-id retargeting.

### Rollback and recovery

- Before S4, disable the new command path and continue from the unchanged current
  carrier state.
- ChangeSet application is idempotent by id and proposal digest; retries return the
  original receipt.
- A stale Markdown view is repaired from the committed carrier revision and never
  treated as a failed canonical commit.
- Placement migration writes a new explicit target carrier/artifact and leaves the
  source byte-identical; rollback repoints to the source rather than reversing an
  in-place rewrite.

### Lifecycle and cleanup

After parity and migration gates pass, remove direct topology mutation paths and
their duplicate validation logic, update `ZJ-CONTEXT.md`, skill references, source
maps, and affected ADR factual statements, then close and remove this plan according
to ADR 0010. Compatibility Adapters must have an explicit deletion owner and release
gate.

## Principle considerations

### Performance

Reconciliation adds Roadmap-wide candidate matching and graph validation. The first
Implementation should use deterministic indexes over uid, normalized obligation key,
provenance, active Status, and Edge neighborhoods; optional model-assisted ranking is
not on the critical path. The 5,000-Node p95 threshold above is the initial capacity
gate. Memory and power impact is expected to remain bounded because the workflow is
local and batch-oriented; the expected cost is one in-process index per
reconciliation run, and benchmark evidence is still required before approval.

### Simplicity and accessibility

The Human continues to read a bounded tree. Added complexity is concentrated behind
the Reconciliation Module; callers review outcomes and a change projection rather
than manually sequencing low-level CRUD. Reference Placements must have text labels,
not color-only meaning, and the Markdown view must remain usable in plain text and
screen-reader navigation. The intentionally harder workflow is topology mutation:
it requires preview and acceptance because silent structural edits are expensive to
recover from.

### Security and privacy

The design adds no network access, credentials, or remote persistence. Trace bodies
and Decisions may contain sensitive local context and remain under existing carrier
access and retention rules. Model-assisted matching, if proposed later, is a new
trust boundary: it requires explicit data-handling review, opt-in, provenance, and a
rule that the model can only rank candidates, never commit a merge. Human approval
evidence is audit metadata, not authentication.

## Testing and validation

Required test matrix:

| Scenario | Expected observation | Threshold | Owner |
|---|---|---|---|
| Exact duplicate findings in one batch | One active WorkItem, both Trace sources linked | 100% fixtures | Roadmap core owner |
| Near-duplicate but different exit criteria | `unresolved` or two WorkItems; never auto-merge | 0 false merges | Roadmap core owner |
| Finding covered by another subtree | `covered` with reference Placement/provenance | 100% fixtures | Projection owner |
| Completed WorkItem refinement | Explicit reopen, supersede, or evidence-preserving no-op | No silent scope rewrite | Roadmap core owner |
| Dependency reversal | One atomic ChangeSet; no visible intermediate cycle | 0 partial states | Carrier owner |
| Combined changes form a cycle | Entire ChangeSet rejected with cycle witness | 100% rejection | Roadmap core owner |
| Base revision changes after preview | `E_CONFLICT`, no mutation | 100% rejection | Carrier owner |
| Failure during JSON/SQLite commit | Old or new full state, never partial | 0 partial commits | Carrier owner |
| Markdown publication failure | Commit receipt reports stale view; retry only repairs view | 100% idempotent repair | Projection owner |
| Trace-only additions | Plan hashes/views unchanged | 0 changed bytes | Projection owner |
| Legacy corpus migration | Uids, Decisions, Edges, Status meaning preserved | 100% labeled corpus | Migration owner |
| Scoped ChangeSet references | Every operation reference remains in the approved subtree | 100% rejection of out-of-scope fixtures | Roadmap core owner |
| Authority boundary | Envelope present on both views; durable source scan clean | 0 `E_PROCESS_AUTHORITY_LEAK` findings | Documentation owner |

Reproducible validation scenario:

1. Seed both carriers with the same Roadmap containing two cross-subtree Nodes with
   overlapping labels but different exit criteria.
2. Add three findings: one exact duplicate, one refinement, and one true new risk.
3. Reconcile the batch and assert `covered`, `refine`, and `novel` respectively.
4. Preview a ChangeSet that replaces a `blocks` Edge and adds a reference Placement.
5. Inject failure before and after carrier commit and before Markdown publication.
6. Compare proposal JSON, semantic revision, derived queries, and Markdown bytes
   across carriers.

Exit decision: move from `revise` to implementation approval only when every blocking
finding has an owner and resolution, the scenario passes on both carriers, all metric
thresholds pass, and a Human short-read confirms that the proposal makes duplicate,
reopen, and topology effects obvious.

## Open decisions

| Question | Evidence needed | Owner | Due/exit condition |
|---|---|---|---|
| What is the minimum deterministic obligation/work identity key? | Corpus comparison of label, exit criteria, artifact and provenance keys | Roadmap core owner | Blocking: before S1 schema freezes |
| Should `group`/`work` typing precede Placement separation? | Migration spike on three real Roadmaps | Migration owner | Blocking: before S2 implementation plan |
| Is `precedes` needed in addition to `priority` and `blocks`? | At least three real mandatory non-causal ordering cases | Decision owner | Non-blocking: default is no new Edge type |
| Should proposals persist in the carrier or an isolated process artifact? | Crash/retry and ADR 0010 path analysis | Carrier owner | Blocking: before preview persistence lands |
| How should reference Placements render in Markdown? | Plain-text and screen-reader review of two variants | Projection owner | Non-blocking: before S4 |
| Is full immutable revision history justified later? | Storage/latency measurements and recovery incidents | Decision owner | Non-blocking: after ChangeSet rollout |

## Review record

| Reviewer | Date | Concern | Response or decision | Remaining risk |
|---|---|---|---|---|
| Initial architecture analysis | 2026-11-02 | Ordered tree conflates identity, decomposition, order and dependency | Choose reconciliation + ChangeSet first; tree becomes a projection incrementally | Identity key and migration remain blocking |
| Pending Human review | TBD | Validate daily usability and reference notation | Open | Human review pending |

### Short-read acceptance

A reviewer should identify within a short read:

- Decision: `revise`.
- Blocking findings: identity key, migration boundary, and measured baselines.
- Next validation: build and replay the 30-scenario dual-carrier corpus.
- Threshold: zero false automatic merges, zero partial commits, and zero
  cross-carrier semantic mismatches.
- Owner: Roadmap core owner with carrier-contract and Human workflow reviewers.

## Remaining work and Issue mapping (2026-11-03)

S3-1 is implemented, but the plan remains open until the following four mapped
execution items are either completed or explicitly reviewed. These remain
separate so implementation, rollout evidence, carrier replay, and Human judgment
do not get reported as one indistinguishable task.

| Status | ID | Remaining item | Issue | Depends on | Completion evidence |
|---|---|---|---|---|---|
| [x] | S3-1 | Make `promote --accept` route through reviewed reconciliation and ChangeSet apply; remove the direct `add_node` bypass. | [#233](https://github.com/jununfly/ZAgentic/issues/233) | Current reconciliation/apply APIs | Single/SQLite accept receipts, stale/digest/idempotency rejection tests, legacy override rejection, and direct API bypass rejection. |
| [ ] | S3-2 | Close the S3 rollout: compatibility error, CLI/reference updates, parity/fault tests, governance gates, and Review record. | [#234](https://github.com/jununfly/ZAgentic/issues/234) | S3-1 | Explicit `reconcile + apply` and default accept produce the same semantic state; all gates pass. |
| [ ] | S4-1 | Replay migration and reconciliation against three supplied, read-only real Roadmap copies. | [#235](https://github.com/jununfly/ZAgentic/issues/235) | S2 implementation; three redacted Roadmap inputs | Source hashes unchanged; UIDs, Status, Decisions, Edges and leases preserved; JSON/SQLite parity and replay report pass. |
| [ ] | S4-2 | Human-review reference Placement notation in plain text and screen-reader-oriented Markdown views, then fix the final notation in tests/docs. | [#236](https://github.com/jununfly/ZAgentic/issues/236) | Placement projection fixture; Human reviewer | Dated review record with chosen notation, rationale, unresolved risks and synchronized tests/docs. |

Execution order and close-out gate:

```text
S3-1 (#233) → S3-2 (#234) ─┐
                            ├→ final plan close-out
S4-1 (#235) ────────────────┤
S4-2 (#236) ────────────────┘
```

The actual work must use the `zj-roadmap-driven` workflow. Real Roadmap
sources stay read-only; migration targets and replay reports go under
`tmp/skills-outputs/`. The plan may be closed only after all four Issues are
closed, the S3/S4 evidence is added above or in the linked review record, and
the final tests plus documentation/ADR/runtime/authority gates pass. Until
then, S3 rollout closure and S4 real-corpus/Human validation are explicitly
unfinished.
