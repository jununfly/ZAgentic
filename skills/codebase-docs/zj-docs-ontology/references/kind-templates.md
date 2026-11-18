# doc-kind templates

One row per `doc-kind` in the governance vocabulary, and nothing outside it.
A row is the *placement contract* for that kind: `Job` says which facts have
their home here, `Does NOT belong there` says which facts do not. The second
column is not decoration — a kind that only states what it holds will slowly
absorb whatever lands next to it, which is the main way a documentation system
drifts into duplicates.

`Must-write sections` is a default skeleton; a target repository may override
it for its own kinds. `Page form` picks the shape from
[tutorial or reference](governance-contract.md#page-form-tutorial-or-reference).
`Focused check` is the one audit action that catches this kind's characteristic
rot — it is a checklist item, not a gate, and it introduces no diagnostic code.

## Placement rows

The authoritative per-kind placement rows are a single machine-readable
source: see `canonical-preset.json#/kinds` in this skill's `references/`
directory. Each entry there carries `job`, `does_not_belong`,
`must_write_sections`, `page_form`, and `focused_check` for one `doc-kind`.
This file intentionally holds no copy of those rows — a second human mirror
is the drift this preset removes. The prose above still defines what each
field means; the JSON holds the values.
