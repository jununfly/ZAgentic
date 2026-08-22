# Skill-pair forms and strategies

Use this reference during candidate comparison and roadmap planning.

## Pair forms

Compare each source skill against `base-skills-list` using name and description similarity. Represent each candidate in one of these forms:

| form | example | meaning |
|---|---|---|
| `pair(base, source)` | `pair(zj-triage, triage)` | same intent, different name → absorb/采纳/micro/严格对齐 |
| `pair(null, source)` | `pair(null, code-review)` | new to base → adopt-as-is or adopt-with-modifications |
| `pair(base, null)` | `pair(zj-grill-with-docs, null)` | base-only → flag for deprecation if redundant |
| `unrelated(source)` | `unrelated(wait-what)` | source has no matching base concept → evaluate as B-unique |

## Strategy enum

Record one of these strategies as the roadmap decision for each pair. The enum mirrors what 1-3 actually used:

- `strict-align` — copy B source files verbatim, only zj- prefix the `name` field
- `absorb` — keep A as base, cherry-pick specific B features (Redact, scope-before-scan, seam...)
- `adopt` — rename A to B's name, body is B verbatim
- `replace` — delete A, install B (body is B verbatim)
- `reject` — no merge (decision: keep A unchanged)
