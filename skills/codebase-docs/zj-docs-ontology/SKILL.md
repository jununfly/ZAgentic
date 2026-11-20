---
name: zj-docs-ontology
description: "Governance and ontology design for a codebase's documentation system, run as four layers. L1 health check and the governance layer: doc-kind vocabulary, authority bindings, lifecycle, map integrity, drift validation, safe migration proposals; L3 adds a map-derived graph_snapshot (a read-only navigation projection, not a reasoning knowledge graph). Ontology design layer (Module D, L4): entity/attribute/relation/rule modelling with decomposition and recomposition of the docs system — a lightweight JSON schema, not a formal OWL/RDF ontology. L1–L3 run in docs_governance.py; Module D validates in a separate process, validate_ontology_model.py. Use when proposing or executing a documentation-map pass, classifying page kinds, resolving authority conflicts, or decomposing/recomposing long-lived docs against the model. Does not cover ontologies whose object is not a documentation system (a database schema or runtime data model) — use a domain-specific capability for those."
disable-model-invocation: true
source: zagentic

---

# Govern a Codebase Documentation System

One explicit, Human-owned governance pass over a codebase's document map, authorities,
process material, and evidence boundaries — not a publisher or an automatic closeout handler.

## Workflow

Four layers, named the same as the design spine
`docs/designs/zj-docs-ontology-skill-design.md` (L1 health check → L2 governance →
L3 graph projection → L4 ontology design). L1–L3 run in `docs_governance.py`; L4
validates in a separate process, `validate_ontology_model.py`. Preserve meaning by default
throughout.

1. **L1 · Health check, read-only.** Follow a `docs-map:` pointer, then
   `docs/README.md`, then one compatible candidate; classify long-lived docs,
   process material, external references, fixture documentation, and evidence
   surfaces (an unfamiliar target-repo category is target-defined, not an error).
   Diagnose broken links, `UNMAPPED_PAGE` coverage gaps, duplicate-fact and
   parallel-ontology signals, and closed-vocabulary compliance. A conflict or
   greenfield repo stays a proposal until the Human confirms the map and category set.
2. **L2 · Propose governance.** List each map addition, `git mv`, link repair,
   authority synthesis, and deletion candidate with its reason; name each
   confirmation and never write while proposing (`mutations: []`).
3. **L2 · Execute the confirmed scope.** Moves, rewrites, merges, and process deletion
   are separately named actions; use `git mv` for an approved move. A page leaving
   service retires and tombstones while inbound links remain — drain them, only then
   is deletion a candidate. Deletion is never a default and never fires on a signal.
4. **L3 · Graph projection.** The `graph_snapshot` is derived from the map alone — a
   read-only navigation projection (no TBox, no inference: traverse `supersedes` /
   `derived-from`, never derive new facts). Enrich, refresh, or create long-lived
   docs here; a rotten page is routed back to L2 retirement, not deleted in place.
5. **L4 · Ontology design + validate.** Decompose and recompose long-lived docs
   against a lightweight entity/attribute/relation/rule schema (not a formal OWL/RDF
   ontology) with `validate_ontology_model.py`, then run `docs_governance.py
   --validate` plus `/zj-docs-architecture`. One `authority-id` on two pages is a
   mechanical failure (non-zero); `UNMAPPED_PAGE` is the pre-flight a green run must
   settle first. A green run proves the checks were consistent, not that content is
   right. L4 findings are Human-queued back into the next L2 proposal — the tool does
   not auto-loop across the two processes. Compose `/zj-domain-modeling`,
   `/zj-debrief`, `/zj-neat-freak` only as needed.

```sh
python3 skills/codebase-docs/zj-docs-ontology/scripts/docs_governance.py . --proposal
python3 skills/codebase-docs/zj-docs-ontology/scripts/docs_governance.py . --validate
# L4 model validation runs in a separate process; <repo> positional + --model are required
python3 skills/codebase-docs/zj-docs-ontology/scripts/validate_ontology_model.py . --model <path/to/model.json>
```

## Shared conventions

```json
{
  "rule_source": "docs/skill-conventions/skill-conventions.json",
  "authority_id": "reference.skill-conventions",
  "consumes": ["naming-syntax-core", "doc-kind", "authority"],
  "extensions": ["topic-batch-token"]
}
```

Build-time declaration, not runtime load: `consumes` picks keys the generator inlines
into the `BASE_RULES_*` block below; `extensions` must never leak into the shared source.

## Report fields and boundaries

`--object <declaration>` states what the pass governs (a repo-relative directory or
the Human's text); with no flag the report derives `docs` under the repo root as
`source: "derived"`, never silent. Every report carries a `capability_boundary` block
with two covered layers (governance, Module D) and one residual class — ontologies
whose object is not a documentation system. The old `CAPABILITY_NOT_COVERED` signal
for docs-system decomposition is **retracted**: that work is this skill's own job, so
mis-scoping defense is the `--object` declaration. See
[proposal-tool-contract.md](references/proposal-tool-contract.md).

## Ontology design (Module D) and relations

Module D (L4) treats the docs system as one scoped object: decompose each page into
entity/attribute/relation/rule elements (bootstrap or incremental), then recompose
the docs so claims trace to a model element validated against
`references/ontology-meta-schema.json` by the separate `validate_ontology_model.py`
process — a lightweight JSON schema, not a formal OWL/RDF ontology. Map entries are
the L3 declaration surface: a closed `relations:` set and a `graph_snapshot` derived
from the map alone (a read-only projection, not a reasoning knowledge graph). Both
layers are audits, not verdicts; green is a floor.
To gate a merge, pipe the report to `check_gate.py`, which applies
`references/gate-rules.json` (ERRORs gate; signals pass unless escalated); the skill
never auto-installs workflows (see `references/ci-snippet.yml`).

Read [governance-contract.md](references/governance-contract.md) and
[proposal-tool-contract.md](references/proposal-tool-contract.md) before proposing,
interpreting a report, or wiring a gate; [kind-templates.md](references/kind-templates.md)
when classifying a page and [doc-slop-checklist.md](references/doc-slop-checklist.md)
when auditing page health.

## Completion

Complete when the Human sees the map, categories, mechanical failures, review signals,
mutation confirmations, and material awaiting extraction or deletion approval. Authority
conflicts are mechanical failures (exit non-zero); conflicting normative claims stay a
review signal. Never claim a lifecycle loop closed merely because a plan or issue ended.

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
