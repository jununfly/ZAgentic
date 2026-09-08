# Documentation Entry Points

How skills should enter the documentation system selected by
`/zj-docs-ontology`.

## Before exploring

Read the selected document map — normally `docs/README.md`, unless an active
rule or root README points to a compatible map. Follow its registered root
context entry (`ZJ-CONTEXT.md` or `ZJ-CONTEXT-MAP.md`) and accepted ADRs when
they apply to the work.

The map and its categories are governed by `/zj-docs-ontology`; this agreement
does not prescribe or create a layout.

## Use the glossary's vocabulary

When output names a domain concept, use the term defined in the relevant
`ZJ-CONTEXT.md`. A missing term is either an avoided synonym or a gap to record
for `/zj-domain-modeling`.

## Flag ADR conflicts

Surface a conflict explicitly rather than silently overriding it:

> _Contradicts ADR-0007 (event-sourced orders) — but worth reopening because…_
