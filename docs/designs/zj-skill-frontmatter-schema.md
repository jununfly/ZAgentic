---
doc-kind: design
authority: primary
authority-id: design.skill-frontmatter-schema
---

# Skill frontmatter validation boundary

## Question

What frontmatter and sidecar rules make an active ZAgentic skill mechanically
discoverable without rewriting its instructions?

## Scope

This page explains the contract enforced by
[`scripts/validate-skill-frontmatter.py`](../../scripts/validate-skill-frontmatter.py).
It covers public skills under `skills/<bucket>/` and root-level `personal/`
skills, not plugin registration, README indexing, or instruction quality.

## Boundaries

- Passing validation proves only mechanical conformance. It does not certify a
  skill's workflow, factual accuracy, or semantic completeness.
- The validator reports invalid fields; it never rewrites skill sources.
- Source-body preservation during a skill merge is a separate maintenance
  decision. Mechanical YAML, naming, and registration fixes do not authorize a
  semantic rewrite of an adopted skill.

## Contract

Every active `SKILL.md` has these required string fields:

| Field | Rule |
| --- | --- |
| `name` | Matches its directory and starts with `zj-`. |
| `description` | Non-empty, at most 1024 characters, and contains no angle brackets. |

The validator accepts these common optional fields when they have the required
type: `license`, `compatibility`, `metadata`, and `allowed-tools`. Invocation
metadata is limited to `disable-model-invocation` (boolean) and `argument-hint`
(string). Unknown top-level fields fail validation.

`zj-roadmap-driven` is the sole registered exception: its `title` string and
non-empty `triggers` string list remain top-level compatibility fields. No
other skill may introduce them without a new schema decision.

When `agents/openai.yaml` exists, its `policy.allow_implicit_invocation` value
must be boolean. A sidecar cannot enable implicit invocation when the matching
frontmatter sets `disable-model-invocation: true`.

## Source map

- [frontmatter validator](../../scripts/validate-skill-frontmatter.py) —
  executable field, type, namespace, and sidecar checks.
- [recursive plugin validator](../../scripts/validate-zagentic-plugin.py) —
  catalog discovery and the caller for frontmatter validation.
- [zj-roadmap-driven frontmatter](../../skills/codebase-docs/zj-roadmap-driven/SKILL.md)
  — registered compatibility extension.

## Related authority

- [ZAgentic documentation map](../README.md) — documentation and catalog entry
  points.
- [AGENTS.md](../../AGENTS.md) — public registration and Git safety rules.
