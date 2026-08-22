# ZAgentic skill frontmatter schema

This document defines the repository's frontmatter boundary. It is a validation
contract, not a reason to rewrite skill instructions.

## Layers

Every active `SKILL.md` has the two required core fields:

| Field | Type | Rule |
|---|---|---|
| `name` | string | Must match the skill directory name and use the `zj-` namespace. |
| `description` | string | The capability and trigger pointer; at most 1024 characters and no angle brackets. |

These standard optional fields are accepted when used:

- `license` — string
- `compatibility` — string
- `metadata` — mapping of skill-owned metadata
- `allowed-tools` — a string or list of strings

ZAgentic also supports these invocation extensions:

- `disable-model-invocation` — boolean; `true` marks a user-invoked skill.
- `argument-hint` — string shown as an argument hint by runtimes that support it.

The Codex-specific `agents/openai.yaml` file is a separate layer. When present,
its `policy.allow_implicit_invocation` value must be boolean. If the skill's
frontmatter sets `disable-model-invocation: true`, that sidecar must not enable
implicit invocation.

## Registered repository extension

`zj-roadmap-driven` currently uses two top-level fields from its original
frontmatter:

- `title` — string
- `triggers` — a non-empty list of strings

They remain top-level until every consumer is checked. Moving them into
`metadata` before that check could silently change trigger behavior. No other
skill may introduce these fields without a new schema decision.

## Unknown fields and source provenance

Unknown top-level fields fail validation. The validator reports the field and
the skill; it never deletes or rewrites it.

For skills merged from an open-source collection, preserve the source body by
default so later merge updates remain practical and previously validated
behavior remains available. Mechanical fixes — valid YAML quoting/block style,
name/path coupling, indexes, and registrations — are allowed. A proposed
change to the source skill's logic or semantics requires a separate Human grill
and an explicit decision before editing.

This boundary deliberately separates mechanical conformance from semantic
review. Passing the validator does not certify that a skill's instructions are
complete or correct.
