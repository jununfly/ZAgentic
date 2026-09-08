---
doc-kind: architecture-subsystem
authority: primary
authority-id: architecture.subsystem.bucket.engineering
---

# Engineering bucket

## Question

What does the `skills/engineering/` subsystem own, what does it expose, and
how does it fail?

## Scope

This page describes the engineering bucket as an architecture subsystem.
It identifies the responsibility, the owned state, the external interface,
and the failure behaviour that the bucket's skills provide. It is **not** a
skill-by-skill summary; each `SKILL.md` is the source of truth for its own
workflow.

## Boundaries

The bucket covers code-change work in an existing repository: diagnosis,
design, implementation, validation, and release preparation. It is **not**
the planning or documentation-governance subsystem (`codebase-docs` owns
that), not the daily-communication subsystem (`productivity` owns that),
and not the evidence-production subsystem (`research` owns that). Each
`SKILL.md` remains the source of truth for its own workflow; this page
owns only the bucket-level boundary.

## Responsibility

Daily code work — diagnostic, design, implementation, validation, and
release-prep skills an agent invokes when changing, restructuring, or
shipping source code in an existing repository. The bucket owns the
tactical seam between upstream planning (codebase-docs, productivity) and
the actual code change. It also owns the repository-collaboration bootstrap
(`zj-repo-init`) and the Git safety wrapper (`zj-git-bypass-safe-delete`)
that no other bucket may depend on for its core safety.

## Owned state

- The skill folders under `skills/engineering/` (21 entries) plus their
  per-skill `references/`, `scripts/`, and `tests/` directories.
- The local `README.md` index for the bucket and the matching registration
  entries in the top-level `README.md`.
- No state outside the bucket: bucket-owned skills do not write into
  `docs/`, do not modify `scripts/` outside their own bundle, and do not
  mutate other buckets' skills.

## Interface

| Direction | Interface |
| --- | --- |
| Inbound | Human prompts reaching for diagnostic, design, implementation, validation, or release-prep skills, plus delegation from upstream planning skills (for example `zj-to-tickets` handing off to `zj-implement`). |
| Outbound | Code edits the agent applies; tickets the Human reviews; `zj-docs-architecture` validator runs triggered from terminal; ADR drafts and process material created through cross-stage checkpoints. |
| Cross-bucket | Reads `docs/`, `docs/designs/`, `docs/zj-adr/`, `ZJ-CONTEXT.md`, and `AGENTS.md`. May cite any layer-3 reference under any bucket. Does not modify other buckets' source. |
| External | Invokes `scripts/` shell tools (`scripts/zj-git`, `scripts/validate-plugin.sh`) through terminal; uses the supported Agent platform's standard tool surface. |

## Failure behavior

- A `zj-git-bypass-safe-delete` invocation returns non-zero because Git
  itself recovered; the skill reports recovery steps rather than silent
  success.
- A ticketed implementation (`zj-implement`) halts when tests fail or a
  review checkpoint (`zj-code-review`, `zj-dry-run`) reports an unresolved
  boundary; it never amends a commit silently.
- A diagnostic skill (`zj-diagnosing-bugs`) reports the smallest defensible
  fix path plus the evidence the Human asked for; it never silently retries.
- A repository-init (`zj-repo-init`) refuses to bootstrap when a docs
  system is missing; it explicitly points to `zj-docs-ontology` rather
  than replacing its role.

## Source map

- [Bucket README](../../skills/engineering/README.md) — local index.
- The top-level [README.md](../../README.md) registration column for
  engineering skills.
- [AGENTS.md](../../AGENTS.md) — bucket policy this bucket relies on.
- [scripts/zj-git](../../scripts/zj-git) — the Git safety wrapper used by
  every skill in this bucket that performs a Git operation.
- [Codebase Docs capability spec](../prds/codebase-docs-capability.md) —
  the link boundary this bucket cross-references.
- [zj-guide](../../skills/engineering/zj-guide/SKILL.md) — routing entry
  point that dispatches into this bucket.
- [zj-to-spec](../../skills/engineering/zj-to-spec/SKILL.md) →
  [zj-to-tickets](../../skills/engineering/zj-to-tickets/SKILL.md) →
  [zj-implement](../../skills/engineering/zj-implement/SKILL.md) — the
  ticketed delivery spine.
- [zj-steelman](../../skills/engineering/zj-steelman/SKILL.md) and
  [zj-dry-run](../../skills/engineering/zj-dry-run/SKILL.md) — the
  pre-plan and pre-implementation checkpoints.
- [zj-repo-init](../../skills/engineering/zj-repo-init/SKILL.md) —
  repository collaboration bootstrap.
- [zj-git-bypass-safe-delete](../../skills/engineering/zj-git-bypass-safe-delete/SKILL.md) —
  the WorkBuddy safe-delete recovery path.

## Related authority

- [Architecture map](README.md) — primary routing surface.
- [Bucket discipline](ta-skill-bucket-boundary.md) — the cross-cutting
  rule this subsystem consumes.
- [Layers](ta-zagentic-layers.md) — layer-2 to layer-6 boundary this
  subsystem obeys.
