# Plan validator contract

`scripts/validate_plan.py` is the Composer output seam. It accepts an external
Markdown Plan and returns a deterministic JSON object with `valid`, `summary`,
Plan metadata, and sorted diagnostics. It never executes a capability named by
the Plan.

## Invocation

```bash
python skills/productivity/zj-composer/scripts/validate_plan.py PLAN.md \
  [--root REPOSITORY] [--snapshot SNAPSHOT.json]
```

The repository root defaults to this checkout. The snapshot path defaults to
`skills-outputs/zj-composer/catalog-snapshots/<snapshot_id>.json`, where the
identifier comes from the Plan's `skill_index_snapshot` field.

## Hard gates

- all nine v1 headings and required fields are present;
- `template_version: 1`, an allowed Composer status, a stable Plan id, and an
  ISO-8601 generation time are present;
- each capability step has a skill/workflow, role, selection reason, inputs,
  outputs, prerequisite assessment, dependencies, and excluded alternatives;
- the referenced snapshot exists, its content digest matches its manifest, and
  selected skill source files match the pinned SHA-256 entries;
- every selected capability is named in the source references;
- gap lines use the exact Unicode form `required skill：...`;
- unresolved prerequisites, contradictory step dependencies, authority bypass,
  undeclared or unapproved side effects, and secret-shaped values are rejected;
- Human approval and side-effect authorization checkpoints remain explicit, and
  the handoff states that Composer has no execution authority.

Diagnostics use stable categories such as `missing_section`,
`missing_capability_field`, `provenance_stale`, `malformed_gap`,
`dependency_contradiction`, `authority_bypass`, `unapproved_side_effect`, and
`secret-shaped-output`. Errors produce exit code 1; a valid Plan produces exit
code 0. Warnings remain visible in JSON and do not silently disappear.
