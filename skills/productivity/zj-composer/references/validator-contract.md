# Plan validator contract

`scripts/validate_plan.py` is the Composer output seam. It accepts an external
Markdown Plan and returns a deterministic JSON object with `valid`, `summary`,
Plan metadata, handoff eligibility with blocker reasons, and sorted diagnostics.
It never executes a capability named by the Plan.

## Invocation

```bash
python skills/productivity/zj-composer/scripts/validate_plan.py PLAN.md \
  [--root ROOT_OR_INSTALLATION_WRAPPER] [--snapshot SNAPSHOT.json]
```

The root is resolved with the same Issue #177 precedence as discovery:
explicit `--root`, then `ZAGENTIC_ROOT`, then the validator script's location.
The resolver accepts a monorepo root, a flat catalog root, or a user-level
installation wrapper such as `~/.workbuddy` and normalizes it to the directory
that owns the installed skill packages. The snapshot path defaults to
`skills-outputs/zj-composer/catalog-snapshots/<snapshot_id>.json` under that
resolved catalog root, where the identifier comes from the Plan's
`skill_index_snapshot` field.

## Hard gates

- all nine v1 headings and required fields are present;
- when `template-versions.json` is bundled, `template_version` is registered,
  its package-relative template matches the pinned SHA-256, and identity fields
  are valid; a missing optional registry is retained as a visible warning and
  does not by itself block a valid Plan;
- each capability step has a skill/workflow, role, selection reason, inputs,
  outputs, prerequisite assessment, dependencies, and excluded alternatives;
- the referenced snapshot exists, its content digest matches its manifest, and
  selected skill source files match the pinned SHA-256 entries;
- selected, excluded, suggested, and gap-related capabilities use class-scoped
  `capability -> source` mappings in `source_references`; mapping subjects are
  compared as complete tokens, never as substrings;
- gap lines use the exact Unicode form `required skill：...`;
- unresolved prerequisites, contradictory step dependencies, authority bypass,
  undeclared or unapproved side effects, and secret-shaped values are rejected;
- Human approval and side-effect authorization checkpoints remain explicit, and
  the handoff states that Composer has no execution authority.

A malformed registry, invalid schema, path escape, missing registered template,
or template digest mismatch remains a hard validation error. A changed or
missing selected source produces `provenance_stale` and blocks handoff. An
approved Human may preserve an explicit
`stale source reviewed: <source path>` marker in `unknowns`; the validator then
keeps a `provenance_stale_reviewed` warning and allows eligibility only when
status, Human review, and Plan acceptance are all approved/passed. A rejected
Plan must preserve a concrete `because`/`reason` in `rejection_path`.
A valid Plan containing only `required skill：...` gaps and no capability step
remains preserved for review but is ineligible for handoff with
`no_matching_capability`.

Diagnostics use stable categories such as `missing_section`,
`missing_capability_field`, `provenance_stale`, `template_version_mismatch`,
`provenance_incomplete_excluded`, `provenance_incomplete_suggested`,
`provenance_incomplete_gap`, `malformed_gap`,
`dependency_contradiction`, `unresolved_conflict`, `authority_bypass`,
`unapproved_side_effect`, and `secret-shaped-output`. An explicit conflict
marker in a step's `excluded_alternatives` is rejected until a Human chooses
among the retained alternatives. Errors produce exit code 1; a valid Plan
produces exit code 0. Warnings remain visible in JSON and do not silently
disappear.

## Fixture oracle

`evaluate_fixture.py FIXTURE_DIR` composes the validator with a checked-in
`input.json` and `oracle.json`. The result records the fixture id, Plan id,
template version, pinned source revision, validator output, and scenario-oracle
diagnostics. A fixture passes only when both the generic validator and the
scenario oracle pass; the evaluator never makes a live repository request.
