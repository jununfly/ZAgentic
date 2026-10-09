# Composer Plan

<!-- Composer template v1. Keep existing Plans pinned to their original version. -->

## Identity

- **plan_id:** `{{plan_id}}`
- **title:** {{title}}
- **status:** `planned`
- **template_version:** `1`
- **generated_at:** {{generated_at}}
- **composer_version:** {{composer_version}}
- **human_review:** `pending`

## Intent

- **goal:** {{goal}}
- **scope:** {{scope}}
- **constraints:** {{constraints}}
- **desired_output:** {{desired_output}}
- **exclusions:** {{exclusions}}
- **permission_boundary:** {{permission_boundary}}

## Capability composition

List steps in execution order. Each selected capability needs one reason tied to
an input or acceptance requirement.

### Step {{step_number}} — {{step_name}}

- **skill_or_workflow:** {{skill_or_workflow}}
- **role:** {{role}}
- **reason:** {{selection_reason}}
- **inputs:** {{inputs}}
- **outputs:** {{outputs}}
- **prerequisites:** {{prerequisites}}
- **dependencies:** {{dependencies}}
- **excluded_alternatives:** {{excluded_alternatives}}

## Gaps and suggestions

Record bounded external or future suggestions with source, fit caveat, unknowns,
and the boundary that keeps them from being treated as installed. For an
unresolved gap with no reliable suggestion, emit one line per gap using exactly:

required skill：简短地描述缺失skill的形状

## Human checkpoints

- **approval_point:** {{approval_point}}
- **decisions_needed:** {{decisions_needed}}
- **rejection_path:** preserve this Plan and record the reason; do not execute.
- **side_effect_authorization:** {{side_effect_authorization}}

## Evidence and provenance

- **skill_index_snapshot:** {{snapshot_id}}
- **catalog_revision_or_digest:** {{catalog_revision_or_digest}}
- **source_references:** {{source_references}}
- **evidence_requirements:** {{evidence_requirements}}
- **generated_assertions:** {{generated_assertions}}
- **unknowns:** {{unknowns}}

## Verification

- **step_checks:** {{step_checks}}
- **scenario_oracle:** {{scenario_oracle}}
- **plan_acceptance:** `pending`

## Failure and rollback

- **failure_exits:** {{failure_exits}}
- **safe_stop:** {{safe_stop}}
- **rollback:** {{rollback}}
- **undeclared_side_effect_response:** stop, preserve evidence, and escalate for Human review.

## Handoff

- **consuming_execution_chain:** {{consuming_execution_chain}}
- **handoff_preconditions:** Human approval, complete provenance, and passing verification checks.
- **authority_statement:** Composer proposes and documents; it has no execution authority.
