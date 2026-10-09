---
doc-kind: architecture-subsystem
authority: primary
authority-id: architecture.subsystem.bucket.productivity
---

# Productivity bucket

## Question

What does the `skills/productivity/` subsystem own, what does it expose,
and how does it fail?

## Scope

This page describes the productivity bucket as an architecture subsystem.
The bucket holds daily non-code-work skills: communication modes, capability
composition, structured discussion, hand-offs, teaching state, question
formulation, and skill-writing helpers. It does **not** own repository
governance (codebase-docs has that) or code-change execution (engineering has
that).

## Boundaries

The productivity bucket owns Human-facing workflow methods and their bounded
process or evidence artifacts. Composer Plans remain review artifacts under
`skills-outputs/`; zj-discuss document groups remain process material until a
Human invokes documentation governance. Neither artifact becomes durable
repository authority by being produced here.

## Responsibility

Daily Human- and Agent-facing workflow skills that operate on a single
session's communication, decisions, and craft rather than on a repository.
The bucket covers:

- language and tone switches (`zj-caveman`, `zj-grilling`,
  `zj-wait-what`),
- reviewable capability composition (`zj-composer`),
- structured complex-problem discussion (`zj-discuss`,
  `zj-discuss-view`),
- session transfer and continuation (`zj-handoff`),
- multi-session teaching state (`zj-teach`),
- decision capture and routing (`zj-to-questionnaire`),
- skill-creation discipline (`zj-write-a-skill`,
  `zj-writing-for-agents`).

## Owned state

- The skill folders under `skills/productivity/` (11 entries) plus their
  per-skill `references/`, `scripts/`, and `tests/` directories.
- The local `README.md` index for the bucket.
- Workflow-owned process and evidence artifacts such as Composer Plans under
  `skills-outputs/zj-composer/` and zj-discuss groups under
  `discussions/<slug>/`. These are not durable documentation authority and
  remain subject to their own Human review or governance lifecycle.

## Interface

| Direction | Interface |
| --- | --- |
| Inbound | Human prompts for communication help, capability composition, structured discussion, handoff, teaching, questionnaires, or skill writing. |
| Outbound | Session responses, reviewable Composer Plans, zj-discuss process-document groups, handoff documents, teaching plans, questionnaires, and skill drafts. |
| Cross-bucket | Composer reads the recursive public-skill catalog without taking semantic ownership; zj-discuss hands completed process material to `zj-docs-ontology`; repository-aware grilling may route to `zj-grill-with-docs`. |
| External | Reads `ZJ-CONTEXT.md` for vocabulary. Writes skill drafts into `skills/` or `personal/`, or promotes process material into durable docs, only through the applicable Human-confirmed workflow. |

## Failure behavior

- `zj-write-a-skill` and `zj-writing-for-agents` reject skill drafts that
  do not satisfy frontmatter, naming, or progressive-disclosure rules;
  they prompt the Human for the missing fields rather than guessing.
- `zj-grilling` and `zj-to-questionnaire` halt on ambiguous scope; they
  do not invent answers.
- `zj-handoff` refuses to truncate the live session's context; it produces
  a handoff document and lets the receiving agent resume explicitly.
- `zj-teach` does not advance without an explicit "continue" from the
  Human; it treats the teaching workspace as stateful.
- `zj-composer` stops at a reviewable Plan, preserves unresolved gaps, and
  cannot hand off until its validator reports eligibility.
- `zj-discuss` preserves unresolved viewpoints and hands its process material
  to documentation governance instead of promoting it automatically.

## Source map

- [Bucket README](../../skills/productivity/README.md) — local index.
- [ZJ-CONTEXT.md](../../ZJ-CONTEXT.md) — vocabulary consulted by
  `../../skills/productivity/zj-to-questionnaire/SKILL.md` and
  `../../skills/productivity/zj-grilling/SKILL.md`.
- [zj-grilling](../../skills/productivity/zj-grilling/SKILL.md) — the
  stress-test interview loop.
- [zj-handoff](../../skills/productivity/zj-handoff/SKILL.md) —
  forward session transfer.
- [zj-composer](../../skills/productivity/zj-composer/SKILL.md) — the
  intent-to-Plan composition boundary.
- [zj-discuss](../../skills/productivity/zj-discuss/SKILL.md) and
  [zj-discuss-view](../../skills/productivity/zj-discuss-view/SKILL.md) —
  the structured discussion lifecycle and independent-view companion.
- [zj-teach](../../skills/productivity/zj-teach/SKILL.md) — stateful
  multi-session teaching.
- [zj-write-a-skill](../../skills/productivity/zj-write-a-skill/SKILL.md)
  and
  [zj-writing-for-agents](../../skills/productivity/zj-writing-for-agents/SKILL.md) —
  the skill-creation discipline pair.

## Related authority

- [Architecture map](README.md) — primary routing surface.
- [Bucket discipline](ta-skill-bucket-boundary.md) — the cross-cutting
  rule this subsystem consumes.
- [Layers](ta-zagentic-layers.md) — layer-2 read scope with no write
  authority beyond layer 1.
