---
doc-kind: adr
authority: historical
status: accepted
---

# Unified ontology — Module G (governance) + Module P (product domain), deployment split

## Context

We first tried to rebuild `docs/` using the existing `zj-docs-ontology` skill
(`skills/codebase-docs/zj-docs-ontology`), but it did not meet the four engineering
goals we set for the documentation system: (1) unify semantics / remove ambiguity,
(2) support reasoning and constraint validation, (3) make the business easier to
understand for Agent and Human, (4) stay fresh under add/delete/modify.

That gap produced a separate "product-domain ontology + knowledge graph" under
`docs/ontology/` (entities like `Skill` / `SkillBucket` / `Platform`, plus
`ArchitectureView` / `Design` / `ADR` as documentation artifacts, with
`extract.py` and `validate.py`). A naming collision then surfaced: the skill's
"ontology" (a *documentation governance taxonomy*: `doc-kind` vocabulary,
`authority` levels, lifecycle categories, the doc-map binding contract) and the new
"ontology" (a *product-domain model*) were both called "ontology", which itself
violated goal (1).

On first-principles review, the two are not two ontologies at all: the skill's
governance taxonomy is just a set of entity types / attributes / relations inside
the same knowledge graph. They are two *concern modules* of one graph.

## Decision

1. **One ontology, not two.** A single source of truth —
   `docs/ontology/ontology.schema.json` — defines all entity types, attributes,
   relations, and rules, each tagged with a `module`:
   - **Module G (governance layer):** `DocMap` + `DocPage` and its subtypes, the
     `docMapBinds` relation, and rules `G1`/`G2`/`G3` (the `MAP_*` mechanical
     checks). Owner: the portable skill `zj-docs-ontology`.
   - **Module P (product-domain layer):** `Platform` / `SkillBucket` / `Skill` /
     `Pipeline` / `Validator`, plus the product rules. Owner: `docs/ontology/`
     (ZAgentic-local extraction + validation).
2. **Model unified, deployment split.** Module G ships with the portable skill
   (`scripts/docs_governance.py` + fixtures + tests) and can be installed into any
   codebase. Module P's extractor/validator live under `docs/ontology/` because they
   are ZAgentic-specific. The governance contract explicitly tolerates skill-local
   copies over cross-skill imports, so this split is intentional, not drift.
3. **One validator.** `docs/ontology/validate.py` executes Module P's native rules
   and *composes* the portable governance skill (`docs_governance.py --validate`)
   to cover Module G's `MAP_*` checks in the same run — one command, one report.
4. **Naming disambiguation resolved.** There is no "domain-graph vs ontology"
   sibling relationship. `docs/ontology/` is the unified ontology home; the product
   domain is simply Module P, and the governance layer is Module G.

## Consequences

- The `docs/README.md` doc-map must obey `rule.G1-docmap-binding`: each
  `authority-id` is bound to exactly one page via its own bullet, and descriptive
  text/tables between authority-id bullets carry no markdown links (otherwise the
  binding detector folds stray links into the preceding id).
- The portable skill keeps its own `MAP_*` logic; `validate.py` reuses it by
  composition rather than reimplementation. When the skill is absent (other
  repos), `validate.py` skips Module G with a warning.
- Graph is a derived fact; the live `skills/` + `docs/` trees are the source of
  truth. Freshness is preserved by regenerating the graph on every run.
- Goal (1) is now satisfied by the single vocabulary; the earlier naming collision
  is removed by design.
