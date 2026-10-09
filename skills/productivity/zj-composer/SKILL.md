---
name: zj-composer
description: Generate a reviewable, versioned task Plan from a goal, constraints, evidence needs, and permission boundaries. Use when a Human invokes /zj-composer to assemble ZAgentic capabilities, expose gaps, or prepare a bounded handoff to an existing execution chain.
disable-model-invocation: true
argument-hint: "目标、约束和期望产物"
---

# zj-composer

`/zj-composer` is a Human-invoked intent-to-Plan workflow. It explains a
candidate capability composition and stops at a reviewable Plan. It does not
approve or execute work, own skill semantics, or create a second runtime.

## Workflow

1. Capture the goal, scope, constraints, desired output, evidence needs,
   permission boundary, and exclusions.
2. Read the current recursive public-skill catalog with the bundled read-only
   helper: `python skills/productivity/zj-composer/scripts/discover_catalog.py`.
   Generate a provenance artifact with
   `python skills/productivity/zj-composer/scripts/generate_snapshot.py`.
   Record its source revision or content digest, discovery time, source paths,
   and metadata warnings. See [the snapshot contract](references/snapshot-contract.md).
   Treat the existing catalog as the authority.
3. Compose ordered capability steps. For every selected skill, record its role,
   selection reason, inputs, outputs, prerequisites, dependencies, and excluded
   alternatives. Keep conflicts visible and route unresolved choices to a Human.
4. Report bounded external or future suggestions with their source and fit
   caveats. When no reliable suggestion exists, write one exact line per gap:
   `required skill：简短地描述缺失skill的形状`
5. Fill [the Plan template](references/plan-template.md) and apply
   [the v1 contract](references/plan-contract.md). Store generated Plans and
   their snapshots under `skills-outputs/zj-composer/`.
6. Validate an external Plan at the output seam with
   `python skills/productivity/zj-composer/scripts/validate_plan.py PLAN.md`.
   For a frozen fixture, compose that check with
   `python skills/productivity/zj-composer/scripts/evaluate_fixture.py FIXTURE_DIR`
   to produce the scenario oracle result. See
   [the validator contract](references/validator-contract.md). A rejected Plan
   stays preserved with its reason; only
   an approved Plan may hand off to the consuming execution chain.

## Output boundary

Every Plan pins `template_version: 1` and a stable `plan_id`. Composer-owned
statuses are `planned`, `approved`, `rejected`, `superseded`, and `cancelled`.
After approval, the consuming execution chain owns `running`, `blocked`,
`failed`, `verified`, `recorded`, and `rolled_back`.

Keep verification, failure exits, rollback, Human checkpoints, provenance, and
side-effect boundaries in the Plan. Do not perform writes, network publication,
Git release, credential use, or other irreversible actions as part of composing.

## Completion

The workflow is complete when the Plan has an auditable capability composition,
explicit gaps or bounded suggestions, a provenance snapshot, a fixed oracle or
observable verification check, safe failure and rollback instructions, and a
clear Human approval handoff.
