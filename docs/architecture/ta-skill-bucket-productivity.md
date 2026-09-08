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
The bucket holds daily non-code-work skills: language switches, grilling
sessions, hand-offs, teaching state, question formulation, and skill-
writing helpers. It does **not** own repository-governance skills
(codebase-docs has those) or code-change skills (engineering has those).

## Boundaries

The productivity bucket holds daily non-code-work skills — language
switches, grilling sessions, hand-offs, teaching state, question
formulation, and skill-writing helpers. It does **not** own
repository-governance skills (codebase-docs has those) or code-change
skills (engineering has those).

## Responsibility

Daily Human- and Agent-facing workflow skills that operate on a single
session's communication, decisions, and craft rather than on a repository.
The bucket covers:

- language and tone switches (`zj-caveman`, `zj-grilling`,
  `zj-wait-what`),
- session transfer and continuation (`zj-handoff`),
- multi-session teaching state (`zj-teach`),
- decision capture and routing (`zj-to-questionnaire`),
- skill-creation discipline (`zj-write-a-skill`,
  `zj-writing-for-agents`).

## Owned state

- The skill folders under `skills/productivity/` (8 entries) plus their
  per-skill `references/`, `scripts/`, and `tests/` directories.
- The local `README.md` index for the bucket.
- No state outside the bucket: these skills operate on session-local
  context and on produced artefacts, never on durable repository state
  without explicit Human consent.

## Interface

| Direction | Interface |
| --- | --- |
| Inbound | Human prompts that ask for a grilling session, a handoff, a teaching arrangement, a questionnaire, or a skill-writing task. |
| Outbound | Reformatted language, drilling questions, handoff documents, teaching plans, questionnaires, and skill drafts — all session-scoped outputs. |
| Cross-bucket | May cite `ZJ-CONTEXT.md` for vocabulary; `zj-grilling` may consult `zj-grill-with-docs` from the codebase-docs bucket for repository-aware drilling. Reads but does not modify other buckets. |
| External | Reads `ZJ-CONTEXT.md` for vocabulary; produces skill drafts into `skills/` or `personal/` only with explicit Human confirmation. |

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

## Source map

- [Bucket README](../../skills/productivity/README.md) — local index.
- [ZJ-CONTEXT.md](../../ZJ-CONTEXT.md) — vocabulary consulted by
  `skills/productivity/zj-to-questionnaire/SKILL.md` and
  `skills/productivity/zj-grilling/SKILL.md`.
- [zj-grilling](../../skills/productivity/zj-grilling/SKILL.md) — the
  stress-test interview loop.
- [zj-handoff](../../skills/productivity/zj-handoff/SKILL.md) —
  forward session transfer.
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
