---
doc-kind: architecture-cross-cutting
authority: primary
authority-id: architecture.cross-cutting.bucket-discipline
---

# Bucket discipline

## Question

What single rule governs the boundary between the public skill buckets, the
root-level `personal/` tree, the documentation authorities, and the scripts/
pipeline — a rule that every other view in this architecture handbook
consumes?

## Scope

This page owns the bucket-discipline rule as a cross-cutting concern. Every
overview, layer, subsystem, and flow view links here when it needs to refer
to that rule. The page states the rule, names the views that consume it,
and points at the durable authorities that establish it. It does not define
per-bucket responsibilities (the bucket subsystem pages own those) and does
not restate the capability spec (the Codebase Docs capability spec owns
that).

## Boundaries

- This rule is one rule. It is the rule of **bucket ingress, tree
  separation, and authority non-duplication**. Distinct concerns, such as
  frontmatter validation or the wayfinder-roadmap seam, are owned by their
  respective design authorities and are not part of this page.
- The rule applies to every cross-bucket or cross-tree edge in the
  repository. If a view claims an exception, the exception must reference
  this page and name its specific scope.

## Shared rule

A skill's discoverability, installation, and governance depend on exactly
three things:

1. **Its bucket is the entry.** A public skill is indexed by its bucket's
   `README.md` and by the top-level `README.md`. A personal skill is indexed
   only by `personal/README.md`. No other index may list it. Adding or
   removing a bucket or moving a skill across buckets is an ADR-bearing
   change recorded under `docs/zj-adr/`.
2. **The personal tree is a parallel path, not a duplicate path.** The
   `personal/` tree installs through the same link script, and its skills
   follow the same layer stack internally, but it is excluded from plugin
   discovery, from the top-level index, and from the bucket indexes. Its
   governance and vocabulary still route through root-level context entries
   (`ZJ-CONTEXT.md`, `AGENTS.md`).
3. **No architecture page duplicates a design or ADR authority.** An
   architecture view links to a `docs/designs/` page or a `docs/zj-adr/`
   page for a normative answer; it does not restate that answer in
   architecture prose. The map routes, the design explains, the ADR
   records the hard-to-reverse decision.

These three statements together form the bucket-discipline rule.

## Consumers

Every other view in this handbook is meant to consume this rule. A view
that ignores the rule either encodes a hidden assumption or duplicates an
authority elsewhere (both are mechanical failures the validator surfaces).

| Consumer view | What it consumes |
| --- | --- |
| [Overview](ta-zagentic-overview.md) | 5 + 1 enumeration, the parallel-path note, the reader routing that links (not copies) into `docs/`. |
| [Layers](ta-zagentic-layers.md) | Layer 1 (index) write boundary, layer 7 (authority) write confirmation, layer 2 (skill) read scope including the personal-tree specialisation. |
| [Pipelines](ta-zagentic-pipelines.md) | Flow 1 step 2 iterates public buckets and `personal/` separately; Flow 2 stages 3 and 4 require explicit Human confirmation before any cross-bucket or cross-tree move. |
| Each bucket subsystem page | Owns its skill set, points to this page for the discovery and installation boundary. |
| [Personal tree subsystem page](ta-zagentic-personal-tree.md) | Restates the "parallel path" clause. |

The bucket discipline is a cross-cutting concern because every view either
applies it or restates it; no view can ignore it. A view that ignores it
either encodes a hidden assumption or duplicates an authority elsewhere
(both are mechanical failures the validator surfaces).

## Exceptions and additions

The rule admits no inheritance-based exceptions and no implicit additions.
A new bucket, a new top-level tree, or a new pattern (for example, a
runtime-only sidecar tree) becomes valid only by amending this page and
referencing the ADR that approved the change. The rule does not itself
*prevent* such an addition; it makes the addition discoverable and
reversible by recording the source of the rule and the authority that
amended it.

## Source map

- [AGENTS.md](../../AGENTS.md) — bucket policy and public registration
  rule that establish points 1 and 2.
- [CLAUDE.md](../../CLAUDE.md) — Claude-side companion to the same rules.
- [ZJ-CONTEXT.md](../../ZJ-CONTEXT.md) — vocabulary (`Skill bucket`,
  `Personal skill tree`, `Document contract`, `Authority ID`) that the rule
  relies on.
- [Codebase Docs capability spec](../prds/codebase-docs-capability.md) —
  point 3 (the "one primary page per durable rule" authority model).

## Related authority

- [Architecture map](README.md) — where this page is routed from.
- [System overview](ta-zagentic-overview.md) — restates the 5 + 1 model
  derived from this rule.
- [Layers](ta-zagentic-layers.md) — restates the boundary as a write
  boundary in the layer table.
- [Pipelines](ta-zagentic-pipelines.md) — restates the boundary as a
  flow confirmation step.
- [Cross-stage checkpoints](../designs/zj-cross-stage-skills.md) — design
  page that complements, not replaces, this rule.
- [Skill frontmatter validation boundary](../designs/zj-skill-frontmatter-schema.md) —
  design page that establishes the discoverability contract this rule
  depends on.
- [ADR 0002](../zj-adr/0002-stage-skill-pair-key-decisions.md) —
  historical record of the A-only PR three-rule decision that parallels
  point 1.
