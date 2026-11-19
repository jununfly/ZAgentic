---
name: zj-docs-ontology
description: "Governance of the documentation governance layer: doc-kind vocabulary, authority bindings, lifecycle categories, map integrity, drift validation, and safe migration proposals. Does NOT cover product-domain ontology modelling or decomposing/recomposing the docs system into entity/attribute/relation/rule models — use zj-codebase-design or a dedicated ontology-design capability for that."
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

This skill owns the **governance layer** of a documentation system: the
`doc-kind` vocabulary, `authority` levels, lifecycle categories, and the
`docMapBinds` 1:1 rule that drives `MAP_AUTHORITY_CONFLICT`. That contract is
fully contained here (this file, `references/`, and `scripts/docs_governance.py`),
so the skill installs and runs unchanged in any target repository.

A consuming repository may layer a **product-domain model** on top of this
governance layer (for example platform / bucket / skill / pipeline entities
specific to that repo). Such a model is *that repository's* concern and is
**not** shipped with this skill — it lives wherever that repo keeps its own
documentation ontologies, not inside the installed skill. The two layers share
one vocabulary, so there is no naming collision; this skill only ever owns the
governance layer.

**Capability boundary (declared, not implied).** Every report carries a
`capability_boundary` block: this pass covers the governance layer only;
product-domain ontology modelling and decomposing/recomposing the docs system
into entity/attribute/relation/rule models are **not** covered by this skill.
When the declared object's text requests that uncovered class, the report
emits `CAPABILITY_NOT_COVERED` — a signal (exit stays zero) that names the
alternatives (`zj-codebase-design` or a dedicated ontology-design skill). A
green governance run is never evidence that such a request was served; the
signal exists so the governance layer cannot mask it.

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
