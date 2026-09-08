---
doc-kind: architecture-subsystem
authority: primary
authority-id: architecture.subsystem.bucket.codebase-docs
---

# Codebase-docs bucket

## Question

What does the `skills/codebase-docs/` subsystem own, what does it expose,
and how does it fail?

## Scope

This page describes the codebase-docs bucket as an architecture subsystem.
The bucket is the **governance subsystem** of the repository: it owns the
documentation-system lifecycle, the architecture handbook, the domain
vocabulary maintenance, the cross-stage debrief, and the wayfinding /
roadmap tracking needed for large planning work. It is **not** a place to
ship user-facing productivity skills or runtime diagnostics.

## Boundaries

The codebase-docs bucket is the documentation-governance subsystem of the
repository. It owns the document map, the architecture handbook, the
domain vocabulary, the cross-stage debrief, and the wayfinder / roadmap
tracking needed for large planning work. It does **not** ship
user-facing productivity skills or runtime diagnostics; those belong to
other buckets.

## Responsibility

One-codebase documentation governance. The bucket owns:

- the document map and the long-lived-authority / process-material /
  evidence-surface classification,
- the architecture handbook (this architecture layer),
- the domain vocabulary and the glossary updates that flow from it,
- the debrief closeout that converts session drift into long-lived authority
  or evidence surfaces,
- the wayfinder and roadmap carrying of decisions for long-running work,
- the grilling loop that crystallises hard-to-reverse decisions before
  ADR creation.

The bucket accepts Human-invoked governance, never auto-triggers it.

## Owned state

- The skill folders under `skills/codebase-docs/` (8 entries) plus their
  per-skill `references/`, `scripts/`, and `tests/` directories.
- The local `README.md` index for the bucket.
- The architecture handbook under `docs/architecture/` (owned by
  `zj-docs-architecture`).
- No exclusive ownership of `docs/` itself — the bucket creates and
  governs documents under it, but the documents' durable authority is
  shared with their category's primary owners.

## Interface

| Direction | Interface |
| --- | --- |
| Inbound | Human prompts for documentation governance, architecture handbook work, domain-model updates, debrief closeouts, wayfinder or roadmap tracking, and repository-aware grilling. |
| Outbound | Document map updates, architecture page validations, glossary entries, retrospective records, wayfinder maps, and ADR drafts — all subject to explicit Human confirmation. |
| Cross-bucket | Reads every other bucket's `SKILL.md` to register it in the architecture map; may consume `research/` and `skills-outputs/` as evidence surfaces but never promotes them without a Human confirmation. |
| External | Validates the `docs/` tree through `validate_architecture_docs.py`; promotes hard-to-reverse decisions into ADRs. |

## Failure behavior

- The architecture handbook validator surfaces mechanical failures
  (`MAP_*`, `PAGE_*`, `AUTHORITY_*`, `SOURCE_*`, `ADR_*`) with non-zero
  exit; the bucket does not silently rewrite to clear them.
- `zj-docs-ontology` stops on authority conflicts and on Human-withheld
  consent; it never picks a winner between conflicting claims.
- `zj-debrief` writes process material only; durable value extraction is
  a later governance pass, not a side effect of the closeout.
- `zj-wayfinder` and `zj-roadmap-driven` carry decisions as carriers do;
  they do not silently drop or merge decision threads.

## Source map

- [Bucket README](../../skills/codebase-docs/README.md) — local index.
- [Codebase Docs capability spec](../prds/codebase-docs-capability.md) —
  the accepted capability boundary this subsystem implements.
- [Architecture handbook base map](README.md) — the architecture layer
  this bucket owns.
- [ZJ-CONTEXT.md](../../ZJ-CONTEXT.md) — domain vocabulary this bucket
  updates.
- [zj-docs-ontology](../../skills/codebase-docs/zj-docs-ontology/SKILL.md) —
  the Human-invoked governance entry point.
- [zj-docs-architecture](../../skills/codebase-docs/zj-docs-architecture/SKILL.md) —
  the architecture-handbook owner; its
  `skills/codebase-docs/zj-docs-architecture/scripts/validate_architecture_docs.py`
  is Flow 2's stage-6 validator.
- [zj-domain-modeling](../../skills/codebase-docs/zj-domain-modeling/SKILL.md) —
  glossary and domain-model maintenance.
- [zj-grill-with-docs](../../skills/codebase-docs/zj-grill-with-docs/SKILL.md) —
  repository-aware grilling that produces ADRs.
- [zj-debrief](../../skills/codebase-docs/zj-debrief/SKILL.md) — the
  process-material closeout.
- [zj-neat-freak](../../skills/codebase-docs/zj-neat-freak/SKILL.md) —
  drift reconciliation.
- [zj-wayfinder](../../skills/codebase-docs/zj-wayfinder/SKILL.md) and
  [zj-roadmap-driven](../../skills/codebase-docs/zj-roadmap-driven/SKILL.md) —
  the decision carriers whose seam is owned by
  [design.wayfinder-roadmap-carrier-seam](../designs/zj-wayfinder-roadmap-dual-mode.md).

## Related authority

- [Architecture map](README.md) — primary routing surface.
- [Bucket discipline](ta-skill-bucket-boundary.md) — the cross-cutting
  rule this subsystem consumes.
- [Layers](ta-zagentic-layers.md) — layer-7 write-confirmation boundary
  this subsystem depends on.
- [Pipelines](ta-zagentic-pipelines.md) — Flow 2 is this subsystem's main
  flow.
