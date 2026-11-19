---
name: zj-docs-ontology
description: "Governance and ontology design for a codebase's documentation system. Governance layer: doc-kind vocabulary, authority bindings, lifecycle categories, map integrity, drift validation, safe migration proposals. Ontology design layer (Module D): entity/attribute/relation/rule modelling with decomposition and recomposition of the docs system. Does NOT cover ontologies whose object is not a documentation system — use a domain-specific capability for those."
disable-model-invocation: true
source: zagentic

---

# Govern a Codebase Documentation System

Run one explicit governance pass. This is the Human-owned entry point for a
codebase's document map, long-lived authorities, process material, and evidence
boundaries. It is not a shared-knowledge publisher or an automatic closeout
handler.

## Shared Conventions

```json
{
  "rule_source": "docs/skill-conventions/skill-conventions.json",
  "authority_id": "reference.skill-conventions",
  "consumes": ["naming-syntax-core", "doc-kind", "authority"],
  "extensions": ["topic-batch-token"]
}
```

This is a human-authored build-time declaration, not a runtime load. `consumes`
selects which shared core keys the release generator inlines into this skill
(`<topic>` naming plus doc-kind/authority classification and the map-binding layer);
`extensions` lists private terms that must never leak into the shared source or an
inlined block. The generated `BASE_RULES_*` block is a separate, generated section.

## Workflow

1. **Discover, read-only.** Run the proposal tool. It follows an explicit root
   `docs-map:` pointer, then `docs/README.md`, then one compatible candidate.
   A conflict or greenfield repository stays a proposal until the Human confirms
   the selected map and minimal category set.
2. **Classify.** Separate long-lived documentation, process material, external
   references/runbooks, fixture documentation, and evidence surfaces. Treat an
   unfamiliar target-repository category as target-defined, not as an error.
3. **Propose governance.** List each proposed map addition, `git mv`, link
   repair, authority synthesis, and deletion candidate with its reason. Name
   the confirmation required for every mutation; do not write while proposing.
4. **Execute the confirmed scope.** Preserve meaning by default. Moves, rewrites,
   authority merges, and process deletion are separately named actions. Use
   `git mv` for an approved tracked move. A page leaving service retires first
   and tombstones while inbound links remain; deletion is the last stage, never
   a default. A `git mv` stages git-native rename evidence: the validator
   reports it as `RENAME_AWAITING_CONFIRMATION` (a signal, exit zero) until
   the confirmed proposal's `moves` names it — a rename needs no tombstone
   stub, and a deletion without rename evidence still errors
   (`UNDECLARED_RETIREMENT`).
5. **Validate and report.** Run map, link, and authority-binding checks and
   `/zj-docs-architecture` for the architecture layer. One `authority-id` bound
   to two pages is a mechanical failure, not a signal: it exits non-zero and the
   Human settles it. A green run means these checks were confirmed consistent
   on this content, not that the content is right — semantic correctness stays
   with review. Compose `/zj-domain-modeling`, `/zj-debrief`, and
   `/zj-neat-freak` only when the Human's governance request needs their
   specialist work. Report pending durable extraction and deletion proposals.

```sh
python3 skills/codebase-docs/zj-docs-ontology/scripts/docs_governance.py . --proposal
python3 skills/codebase-docs/zj-docs-ontology/scripts/docs_governance.py . --validate
```

**Declare the governed object.** `--object <declaration>` is the first-class
statement of what this pass governs — a directory relative to the repo root
or the Human's declaration text. With no flag the tool reports
`object_of_governance` with `source: "derived"` (default `docs` under the
repo root); a declared directory is recorded with `source: "declared"`. The
report always answers "what is the governed object?": `object_of_governance`
(the boundary) and `pass_topic` (the checklist output key) are two separate
fields — `scope` no longer means both.

```sh
python3 skills/codebase-docs/zj-docs-ontology/scripts/docs_governance.py . --validate \
  --object docs --topic docs-redesign
```

A bare `--validate` (no `--topic`) is a shape-only check: the report emits
`EXEC_CHECKLIST_NOT_DECLARED` (exit zero) and states that a green run is not
evidence a full pass ran or that content is correct. It is a signal for a CI
rule or step-gated authorization to escalate — the tool cannot tell a shape-only
check from a skipped pass, and an executor that never calls `--validate` at all
is outside its observation boundary. Use a topic below for a full pass.

For a full governance pass, use a **pass topic** and an execution checklist.
The topic is lowercase-hyphen with no date/sha/version/status token (e.g.
`docs-redesign`). Emit the checklist from the read-only proposal, then run the
architecture validator and save its output at the declared Step 5 path:

```sh
python3 skills/codebase-docs/zj-docs-ontology/scripts/docs_governance.py . --proposal \
  --topic docs-redesign --emit-checklist
python3 skills/codebase-docs/zj-docs-architecture/scripts/validate_architecture_docs.py . \
  > tmp/skills-outputs/zj-docs-ontology/docs-redesign/architecture-validator.txt
python3 skills/codebase-docs/zj-docs-ontology/scripts/docs_governance.py . --validate \
  --topic docs-redesign
```

The checklist is emitted to `<repo-root>/tmp/skills-outputs/zj-docs-ontology/<topic>/`
(gitignored, pass-scoped). The output zone anchors to the governed repo root —
the default and any relative `--out` resolve against it, never against the
directory the CLI was launched from. Its `confirmation_id` is the tool-computed hash of
the confirmed proposal — never an agent-supplied "I confirmed" claim. Steps
marked done must be backed by an existing artifact; a missing one is
`EXEC_CHECKLIST_STEP_UNBACKED` (non-zero). Step 5's artifact path is declared
by the tool, so a `skipped` status still fires `EXEC_STEP5_ARTIFACT_MISSING`.
A fingerprint mismatch is a signal (`EXEC_STEP5_FINGERPRINT_MISMATCH`, exit
zero) — it never proves the architecture content is right.

`--arch-witness` / `--arch-fingerprint` remain as a compatibility fallback
for callers with no checklist; when `--topic` is supplied the checklist is the
sole witness source and CLI witness values are ignored. See
[proposal-tool-contract.md](references/proposal-tool-contract.md).

### Relations layer and graph snapshot (issue #275 Fix 7)

The map is the ontology declaration surface: each entry is a graph node
(`role` / `authority-id` are node attributes), and an entry may declare typed
edges with an optional `relations:` clause — `derived-from`, `supersedes`,
`supports` (a closed set, so the map never becomes an unmaintained decoration),
each target being another entry's `authority-id` or a repo-relative page path:

```markdown
- [Overview](designs/overview.md) — what the subsystem is; role: primary; authority-id: `a.b`; relations: supports: c.d, derived-from: designs/detail.md
```

Validation is two-tier: a declared edge that resolves to neither a map
authority-id nor an existing page is `MAP_RELATION_DANGLING` (ERROR — an
explicit declaration that does not match reality); an unknown relation type is
`MAP_RELATION_TYPE_INVALID` (ERROR). A map entry declaring a non-primary role
with no inbound edge is `ORPHAN_PAGE` (signal — the remedy is declaring an
edge, not deleting the page; undeclared-role entries stay the architecture
layer's `PAGE_ROLE_UNDECLARED` concern). Every report also carries a
`graph_snapshot` block: nodes = map entries, edges = declared relations,
constraints as a separate block, `schema_version: graph-snapshot/v1`. The
snapshot is derived from the map alone — never a second declaration source —
and is machine-loadable for AI navigation (follow `supersedes` to the current
authority, `derived-from` to sources); Human-side rendering is a consumer
concern.

## Ontology design (Module D): decompose and recompose the docs system

The request this skill exists for: treat the whole docs system as one scoped
object, decompose every long-lived page's content into entity / attribute /
relation / rule elements, and recompose the long-lived docs so each one is
traceable to the model. Two layers share the work: the meta-schema
(`references/ontology-meta-schema.json`) is owned here; the model instance —
concrete entity types and vocabulary — is the repository's own.

### Modes

- **bootstrap** — first decomposition of the scoped object: build the model
  draft from the map inventory, then decompose page by page.
- **incremental** — an existing model instance plus target pages (a new page,
  or a page whose content changed): decompose the target against the model,
  extending it only by declared, confirmed elements.

### Workflow (Human-owned gates in bold)

1. Declare the object (`--object`) — the whole docs system, a directory, or
   the Human's declaration text. Mis-scoping has no silent path.
2. Inventory and classify (proposal tool, read-only).
3. Draft or extend the model instance (AI work). Every unclear detail goes
   into the **open-questions ledger** first — batch the questions to the
   Human and wait; never silently assume.
4. **Human settles the open questions and confirms the model.**
5. Decompose: write a per-page receipt (page → model elements) for every
   map-covered page.
6. **Human confirms the recomposition plan per page** before any page is
   rewritten.
7. Recompose: rewrite the long-lived pages so their claims trace to model
   elements; meaning is preserved by default.
8. Validate both layers: `validate_ontology_model.py` (meta-schema +
   coverage) and `docs_governance.py --validate` (map/authority/lifecycle).
   Green is a floor, not a verdict; semantic correctness stays with review.

### Artifacts

- Model instance, receipts, and the open-questions ledger live in the
  pass-scoped output zone (`tmp/skills-outputs/zj-docs-ontology/<topic>/`,
  gitignored, ADR 0010). Whether the model instance is also checked into the
  repository (for example a `docs/ontology/` home) is the repository's own
  decision — the skill recommends, never forces.
- Recomposed pages are the docs tree itself (tracked).

### Mechanical face

`scripts/validate_ontology_model.py <repo> --model <path>` validates an
instance against the meta-schema: required fields (read from the meta-schema
file — never hard-coded a second time), id uniqueness across classes,
attribute owners, relation endpoints, rule traces, receipt integrity — all
ERRORs, because they are explicit declarations that do not match the model's
own facts — plus the coverage invariant: every map-covered page needs a
receipt, and a missing one is `CONTENT_UNCOVERED` (signal; declare the
receipt, never delete the page on this signal).

To turn a report into a merge gate in **any** target repository, pipe it into
the consumer-side gate. The tool emits facts; the repository decides which
signals block a merge:

```sh
python3 skills/codebase-docs/zj-docs-ontology/scripts/docs_governance.py . --validate \
  --topic docs-redesign | \
  python3 skills/codebase-docs/zj-docs-ontology/scripts/check_gate.py \
  --escalate EXEC_CHECKLIST_NOT_DECLARED
```

`check_gate.py` applies `references/gate-rules.json` (which travels with the
skill): ERRORs always gate, signals pass unless escalated, and never-gate
signals are rejected even if requested. See `references/ci-snippet.yml` for a
copyable workflow job — it must trigger unconditionally (no `paths:` on a
required check) and parse the JSON rather than trust the validator's exit code.
The skill never auto-installs workflows; each repository wires its own gate.

Read [governance-contract.md](references/governance-contract.md) before a
proposal or confirmed execution. Read
[proposal-tool-contract.md](references/proposal-tool-contract.md) before
interpreting a report, changing the tool, adding a fixture, or wiring a gate.
Read [kind-templates.md](references/kind-templates.md) when classifying a page
or deciding where a fact belongs, and
[doc-slop-checklist.md](references/doc-slop-checklist.md) when auditing page
health — both are audit material, neither adds a diagnostic to the tool.

## Portability boundary

This skill owns two layers of a documentation system, both fully contained
here (this file, `references/`, and `scripts/`), so the skill installs and
runs unchanged in any target repository:

- **Governance layer (Module G)**: the `doc-kind` vocabulary, `authority`
  levels, lifecycle categories, and the `docMapBinds` 1:1 rule that drives
  `MAP_AUTHORITY_CONFLICT`.
- **Ontology design layer (Module D)**: the *meta*-schema for entity /
  attribute / relation / rule models and the methodology that decomposes and
  recomposes a docs system against it. The skill owns the meta-schema and its
  validator only.

A consuming repository instantiates **its own model** — the concrete entity
types (for example platform / bucket / skill / pipeline) and their instances
are *that repository's* concern and are **not** shipped with this skill; they
live wherever the repo keeps its documentation ontology (instance layer). The
meta-schema and the instance share one vocabulary, so there is no naming
collision; this skill never carries a repo's instance model.

**Capability boundary (declared, not implied; amended 2026-11-20).** Every
report carries a `capability_boundary` block. It declares two covered layers —
the governance layer and the ontology design layer (Module D: entity /
attribute / relation / rule modelling with decomposition and recomposition of
a docs system) — and one residual uncovered class: ontologies whose declared
object is not a documentation system (a database schema, a runtime data
model), which domain-specific capabilities own. The original
`CAPABILITY_NOT_COVERED` signal for decomposition/recomposition requests is
**retracted**: that request class is this skill's own job, so flagging it as
uncovered would be false; mis-scoping defense is the explicit `--object`
declaration itself. The retraction is recorded here and in the tests so the
history stays readable.

## Completion

Complete the pass when the Human can see the selected map, categories,
mechanical failures, Human-review signals, explicit mutation confirmations, and
any process material awaiting durable extraction or deletion approval. Authority
conflicts count as mechanical failures: a binding is a fact, so it exits
non-zero, while conflicting *normative claims* between pages stay a
Human-review signal because settling them needs judgment. Do not claim that a
lifecycle loop closed merely because a plan or issue ended.

<!-- BASE_RULES_START -->
<!-- GENERATED from docs/skill-conventions/skill-conventions.json -- do not edit by hand; re-run the generator. -->
```json
{
  "$generated": {
    "source": "docs/skill-conventions/skill-conventions.json",
    "schema_version": "skill-conventions/v1",
    "consumes": [
      "naming-syntax-core",
      "doc-kind",
      "authority"
    ]
  },
  "core": {
    "naming-syntax-core": {
      "summary": "Lowercase, hyphen-separated names that encode what a thing is — never when it was written, which revision it is, or how current it is.",
      "applies_to": "any skill-owned artifact name that a second skill constrains (architecture view page stems, ontology <topic> keys, kebab-case audits)",
      "rules": [
        {
          "id": "shape",
          "statement": "name must be lowercase and hyphen-separated (alphanumeric segments joined by single hyphens)",
          "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$",
          "match": "full-string"
        },
        {
          "id": "no-date",
          "statement": "name must not encode a date, bare year, or commit sha",
          "pattern": "(?:^|[-.])(?:\\d{4}-\\d{1,2}-\\d{1,2}|\\d{4}-\\d{2}|\\d{8}|(?:19|20)\\d{2})(?:[-.]|$)",
          "sha-segment-pattern": "^[0-9a-f]{7,40}$"
        },
        {
          "id": "no-version",
          "statement": "name must not encode a version number or trailing bare revision number",
          "pattern": "^(?:v\\d+(?:\\.\\d+)*|\\d+(?:\\.\\d+)+|r\\d+)$",
          "trailing-bare-number": true
        },
        {
          "id": "no-status",
          "statement": "name must not encode a temporary-status token",
          "tokens": [
            "draft",
            "wip",
            "todo",
            "tmp",
            "temp",
            "temporary",
            "new",
            "old",
            "latest",
            "final",
            "current",
            "deprecated",
            "scratch",
            "backup",
            "copy",
            "obsolete",
            "stale"
          ],
          "match": "whole-segment"
        }
      ],
      "notes": "Prefix families and topic-scoped private tokens are consumer-private extensions declared per skill; they must not be injected into this shared source (closed-schema check 1). One cause per name; a date finding suppresses the version finding for that name."
    },
    "doc-kind": {
      "summary": "The closed vocabulary of frontmatter doc-kind values.",
      "closed": true,
      "values": [
        "method",
        "prd",
        "architecture-map",
        "architecture-overview",
        "architecture-layers",
        "architecture-subsystem",
        "architecture-flow",
        "architecture-cross-cutting",
        "agreement",
        "design",
        "testing",
        "benchmark",
        "reference",
        "adr",
        "plan",
        "retro",
        "fixture-documentation"
      ]
    },
    "authority": {
      "summary": "The closed vocabulary of frontmatter authority values and its primary binding semantics.",
      "closed": true,
      "values": [
        "primary",
        "supporting",
        "historical",
        "process",
        "external"
      ],
      "binding": {
        "id": "primary-has-exactly-one-authority-id",
        "statement": "a page declaring authority: primary must declare exactly one authority-id, and the doc-map must bind that id to exactly one page",
        "layers": [
          {
            "layer": "map-binding",
            "owner": "zj-docs-ontology",
            "checks": "one authority-id bound to one page (MAP layer)"
          },
          {
            "layer": "page-declaration",
            "owner": "zj-docs-architecture",
            "checks": "no duplicate id across pages; primary carries an id; map and page agree"
          }
        ],
        "notes": "These two layers can both fire on one id as two distinct defects. Diagnostic codes stay in the owning skill; only the binding semantics are shared."
      }
    }
  }
}
```
<!-- BASE_RULES_END -->
