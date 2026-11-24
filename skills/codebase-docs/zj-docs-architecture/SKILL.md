---
name: zj-docs-architecture
description: "Maintains and validates a codebase's multi-view architecture handbook: map, layers, subsystems, flows, and cross-cutting rules. Use when creating, reviewing, migrating, or validating architecture documentation and its source maps."
source: zagentic

---

# Architecture Handbook

Keep one architecture map that routes readers to complementary views; never use
the map to repeat those views. This skill owns handbook shape, not domain
terminology (`/zj-domain-modeling`), hard-to-reverse decisions
(`/zj-grilling` and ADR work), or a repository's whole documentation
governance (`/zj-docs-ontology`).

## Shared Conventions

```json
{
  "rule_source": "docs/skill-conventions/skill-conventions.json",
  "authority_id": "reference.skill-conventions",
  "consumes": ["naming-syntax-core", "doc-kind", "authority"],
  "extensions": ["page-prefix:ta-/ba-/pa-", "page-prefix:tacm-"]
}
```

This is a human-authored build-time declaration, not a runtime load. `consumes`
selects which shared core keys the release generator inlines into this skill;
`extensions` lists private terms that must never leak into the shared source or an
inlined block. The generated `BASE_RULES_*` block is a separate, generated section.

## Workflow

1. **Discover, read-only.** Run the discovery command below. Follow an explicit
   `docs-map: <repo-relative Markdown path>` pointer in root `AGENTS.md`,
   `CLAUDE.md`, or `README.md`; otherwise use `docs/README.md`; otherwise
   report one compatible candidate or an ambiguity. Do not create a second map.
2. **Classify the gap.** Route readers to a system overview, layers, subsystem,
   flow, or cross-cutting page. A rule or explanation has one durable owner;
   link from other views rather than copying it.
3. **Propose before mutation.** For greenfield, propose the smallest map and
   only needed pages. For existing material, inventory paths, contracts,
   authority conflicts, moves, link repairs, and synthesis decisions. Wait for
   explicit Human confirmation before creating, moving, rewriting, or deleting.
4. **Write the confirmed slice.** Apply the page contract and source-map
   evidence. Label each statement as target architecture, implemented behavior,
   inference, or explicit unknown; do not turn inference into fact.
5. **Validate.** Run the validator and resolve mechanical failures. Present
   duplicate/ambiguous ownership as a Human-review signal, never an automatic
   winner.

```sh
python3 skills/codebase-docs/zj-docs-architecture/scripts/validate_architecture_docs.py .
python3 skills/codebase-docs/zj-docs-architecture/scripts/validate_architecture_docs.py . --discover
```

Read [architecture-contract.md](references/architecture-contract.md) before
proposing pages or migration. Read
[validator-contract.md](references/validator-contract.md) when interpreting a
diagnostic, changing the validator, or adding a fixture.

## Maintenance triggers

After a code change, check the handbook when any signal below appears. A hit
means going back to workflow step 3 — propose the handbook change and wait for
confirmation, rather than editing pages in passing. The list is authoritative in
`architecture-contract.md`, which carries the same items and their rationale.
Because these names seed the concept vocabulary, changing an item here or in the
contract also means updating `CONCEPT_KINDS` in `scripts/concept_map.py` (its slug
form) — `ConceptVocabularyTest` fails if the two drift.

- **Extension seam** — a new plugin, registry, hook, or callback entry exists, or
  an existing one changes signature: the handbook must say where outside code
  attaches and what it has to obey.
- **Durable owner** — a rule or explanation moves, or now appears on two pages:
  ownership changed, so the page that lost it becomes a link.
- **Cross-process contract** — the message, schema, or call convention between
  two processes changes: every page describing either side has to agree.
- **Effect policy** — retry, idempotency, write path, or failure compensation
  changes: a flow page's failure behavior is stale until it is re-checked.
- **Replay boundary** — what can be replayed, from which point, and against what
  stored input changes: the flow page's state and evidence claims move with it.
- **Lifecycle rule** — a state machine, or when something is created, migrated,
  or destroyed, changes: those transitions are documented behavior, not code
  detail.
- **Accepted ADR** — an ADR moves to `accepted` or `superseded`: accepted ADRs
  may support a claim and proposed ones may not, so a supersession withdraws
  support from every page citing it.
- **Source-map target** — a path under `## Source map` moves, is renamed, or is
  deleted: the validator reports it as `SOURCE_*`, and the claim it supported
  needs re-checking, not just the link.

## Completion

Finish a handbook slice only when its selected map routes to the intended
views with an explicit `role: primary` declaration per primary entry (map
entry level is the only legal declaration position; `role: supporting` exempts
derived views from the primary contract), each primary view has one mapped
`authority-id`, source-map targets exist, and the validator exits successfully.
A migration stays a proposal until the Human confirms its named moves, rewrites,
and deletions.

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
