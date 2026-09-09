---
doc-kind: architecture-map
authority: primary
authority-id: architecture.map.zagentic
---

# ZAgentic architecture map

This map routes readers to the maintained architecture views for this
repository. Navigation order does not establish global truth precedence; each
view answers one bounded question and points to its durable authorities
without restating them. The five complementary views follow the
`zj-docs-architecture` contract.

## Question

What is the current technical architecture of `jununfly/ZAgentic`, and which
view answers which question about it?

## Scope

This map covers the ZAgentic skills collection, its installer and validator
pipelines, the documentation governance system, and the boundary between the
public `skills/` tree and the root-level `personal/` tree. It does not cover
the runtime behavior of any individual skill (owned by each `SKILL.md`), the
historical decisions behind bucket boundaries (owned by `docs/zj-adr/`), or the
maintenance rules for a single skill's frontmatter (owned by
`docs/designs/zj-skill-frontmatter-schema.md`).

## Boundaries

- One durable rule has exactly one owner. This map links to that owner; the
  linked view further links to the design, capability, or ADR document that
  holds the normative answer.
- Process material (`docs/zj-retros/`), research evidence (`research/`), and
  per-session artifacts (`skills-outputs/`) are evidence surfaces and are not
  routed from this map.
- Personal-skill-tree questions route through the standalone
  `architecture-subsystem` page rather than being absorbed by the public-bucket
  views.
- A new primary view must add a stable `authority-id` here before it is
  shipped; renames preserve authority IDs to keep validator readings stable.

## Map

### Overview

- [System overview](ta-zagentic-overview.md) — purpose, exterior boundary,
  the 5 + 1 skill-tree model, and reader entry points; owner:
  `architecture.overview.zagentic`; authority-id: `architecture.overview.zagentic`.

### Layers and allowed dependencies

- [Layers](ta-zagentic-layers.md) — what each layer is responsible for, what
  it may depend on, and what it must not touch; authority-id:
  `architecture.layers.zagentic`.

### Subsystems (per bucket, plus the personal tree)

- [Engineering bucket](ta-skill-bucket-engineering.md) — daily code-work
  skills; authority-id: `architecture.subsystem.bucket.engineering`.
- [Codebase-docs bucket](ta-skill-bucket-codebase-docs.md) — one-codebase
  documentation governance skills; authority-id:
  `architecture.subsystem.bucket.codebase-docs`.
- [Productivity bucket](ta-skill-bucket-productivity.md) — daily
  non-code-work skills; authority-id:
  `architecture.subsystem.bucket.productivity`.
- [Misc bucket](ta-skill-bucket-misc.md) — kept-around, infrequently used
  skills; authority-id: `architecture.subsystem.bucket.misc`.
- [Research bucket](ta-skill-bucket-research.md) — evidence-production and
  domain-study skills; authority-id:
  `architecture.subsystem.bucket.research`.
- [Personal skill tree](ta-zagentic-personal-tree.md) — root-level
  `personal/` tree as its own subsystem with a separate installation path;
  authority-id: `architecture.subsystem.personal-tree`.

### Flow

- [Pipelines](ta-zagentic-pipelines.md) — install and validate flow plus
  documentation-governance flow; authority-id:
  `architecture.flow.install-and-docs-governance`.

### Cross-cutting

- [Bucket discipline](ta-skill-bucket-boundary.md) — the single shared rule
  every other view consumes (a bucket is the public entry, the personal tree
  is a parallel path, design and ADR authorities do not move into the
  architecture handbook); authority-id:
  `architecture.cross-cutting.bucket-discipline`.

## Source map

- [docs/README.md](../README.md) — the repository-wide documentation map.
- [AGENTS.md](../../AGENTS.md) — repository rules referenced by every view.
- [ZJ-CONTEXT.md](../../ZJ-CONTEXT.md) — domain vocabulary referenced by
  every view.
- [Codebase Docs capability spec](../prds/codebase-docs-capability.md) —
  governance contract that the documentation-governance flow page leans on.

## Related authority

- [Cross-stage checkpoints](../designs/zj-cross-stage-skills.md) — design
  authority for which skills act as which checkpoints.
- [Skill frontmatter validation boundary](../designs/zj-skill-frontmatter-schema.md) —
  design authority for the skill-discoverability contract.
- [Wayfinder and roadmap carrier seam](../designs/zj-wayfinder-roadmap-dual-mode.md) —
  design authority for the wayfinder/roadmap hand-off boundary.
- [ADR 0001](../zj-adr/0001-explicit-setup-pointer-only-for-hard-dependencies.md)
  — pointer-only setup decision.
- [ADR 0002](../zj-adr/0002-stage-skill-pair-key-decisions.md) — A-only PR
  three-rule decision and the cross-stage skill meta-rule.
- [ADR 0003](../zj-adr/0003-khazix-wave-absorb-key-decisions.md) — historical
  absorb-wave decision.
- [ADR 0004](../zj-adr/0004-research-report-improvement-scope.md) — research
  scope decision.
