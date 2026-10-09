# Composer Plan

<!-- Composer template v1. Keep existing Plans pinned to their original version. -->

## Identity

- **plan_id:** `tool-combination-design-v1-plan`
- **title:** Compose a reviewed implementation path for a bounded product request
- **status:** `planned`
- **template_version:** `1`
- **generated_at:** 2026-10-09T17:30:00Z
- **composer_version:** `zj-composer/v1`
- **human_review:** `pending`

## Intent

- **goal:** Turn a bounded product request into a reviewable implementation brief, technical design review, and roadmap handoff.
- **scope:** Use existing ZAgentic capabilities to frame the request, review its design, and record a roadmap-ready handoff.
- **constraints:** Use the current local catalog and existing skill semantics; require Human approval; no automatic execution.
- **desired_output:** A versioned Plan with candidate capabilities, an explicit gap, verification, handoff, and rollback.
- **exclusions:** No global router, no second runtime, no automatic execution, and no publication or implementation side effect.
- **permission_boundary:** Read current local capability metadata and write only bounded Plan evidence; no automatic execution, unapproved writes, network publication, credentials, or irreversible actions.

## Capability composition

List steps in execution order. Each selected capability needs one reason tied to
an input or acceptance requirement.

### Step 1 — Frame the product request

- **skill_or_workflow:** `zj-leader`
- **role:** Turn the bounded product request into an agent-ready implementation brief.
- **reason:** It translates the goal and constraints into a brief with acceptance criteria for the design review.
- **inputs:** Bounded product request, constraints, desired output, and permission boundary.
- **outputs:** Implementation brief with goal, scope, constraints, non-goals, and acceptance criteria.
- **prerequisites:** The request and constraints are written in the fixture input.
- **dependencies:** none
- **excluded_alternatives:** Starting implementation before the goal and acceptance criteria are explicit.

### Step 2 — Review the technical design

- **skill_or_workflow:** `zj-tech-design-review`
- **role:** Review the brief for architecture choices, risks, metrics, rollout, testing, and rollback.
- **reason:** It supplies the architecture design review and risk analysis required by the acceptance requirements before a roadmap handoff.
- **inputs:** Step 1 implementation brief, constraints, and acceptance criteria.
- **outputs:** Technical design review with architecture, risk register, validation gates, and rollout boundaries.
- **prerequisites:** Step 1 has produced a complete brief and acceptance criteria.
- **dependencies:** Step 1
- **excluded_alternatives:** An informal architecture opinion without a risk or verification record.

### Step 3 — Record the roadmap handoff

- **skill_or_workflow:** `zj-roadmap-driven`
- **role:** Convert the reviewed design into a bounded roadmap node and handoff record.
- **reason:** It records roadmap progress, verification evidence, and handoff preconditions for Human review.
- **inputs:** Step 2 design review, decisions, dependencies, verification checks, and rollback boundaries.
- **outputs:** Roadmap node update and reviewable handoff record.
- **prerequisites:** Step 2 has a passing design review and explicit rollback boundary.
- **dependencies:** Step 2
- **excluded_alternatives:** A hidden task dispatch or unreviewed execution handoff.

## Gaps and suggestions

required skill：跨工具组合的统一执行能力

## Human checkpoints

- **approval_point:** Human approval is required after the design review and before any consuming execution chain handoff.
- **decisions_needed:** Human confirms the acceptance criteria, design risks, roadmap scope, and whether the explicit gap is acceptable.
- **rejection_path:** Preserve this Plan and record the rejection reason; do not execute.
- **side_effect_authorization:** Human approval is the only authorization for a consuming execution chain; this fixture permits only bounded local Plan evidence.

## Evidence and provenance

- **skill_index_snapshot:** `catalog-v1-0bbd5fc19b5cde54b2fcd9a89e0a97dd0b9bd5ff98c64919cad5b96dfbd0c776`
- **catalog_revision_or_digest:** `0bbd5fc19b5cde54b2fcd9a89e0a97dd0b9bd5ff98c64919cad5b96dfbd0c776`
- **source_references:** selected=[zj-leader -> skills/engineering/zj-leader/SKILL.md | zj-tech-design-review -> skills/engineering/zj-tech-design-review/SKILL.md | zj-roadmap-driven -> skills/codebase-docs/zj-roadmap-driven/SKILL.md]; excluded=[Step 1 -> skills-outputs/zj-composer/tool-combination-design/oracle.json | Step 2 -> skills-outputs/zj-composer/tool-combination-design/oracle.json | Step 3 -> skills-outputs/zj-composer/tool-combination-design/oracle.json]; suggested=[none declared]; gap=[required skill：跨工具组合的统一执行能力 -> skills-outputs/zj-composer/tool-combination-design/input.json]
- **evidence_requirements:** Each selected capability must be traceable to its current SKILL.md and each design claim must point to a review artifact.
- **generated_assertions:** The three selected capabilities cover framing, design review, and roadmap handoff; the cross-tool executor capability remains an explicit gap.
- **unknowns:** The missing cross-tool execution capability is not installed, and no consuming chain is authorized by this fixture.

## Verification

- **step_checks:** Perform observable checks confirming each selected skill has a role, reason, inputs, outputs, prerequisites, dependency, excluded alternatives, and source reference.
- **scenario_oracle:** The tool-combination-design oracle checks the fixed goal and constraints, three-step order, dependency direction, exact gap line, Human checkpoint, verification, handoff, rollback, and forbidden authority expansion.
- **plan_acceptance:** `pending`

## Failure and rollback

- **failure_exits:** Stop if the brief, design review, dependency, verification, or gap contract is incomplete.
- **safe_stop:** Safe stop: preserve the Plan and evidence, keep the gap visible, and request Human review.
- **rollback:** Rollback by reverting only the current roadmap evidence update; preserve the frozen fixture input and rejected Plan artifact.
- **undeclared_side_effect_response:** stop, preserve evidence, and escalate for Human review.

## Handoff

- **consuming_execution_chain:** Existing consuming execution chain is the roadmap-driven chain after Human approval.
- **handoff_preconditions:** Human approval, complete provenance, passing Plan validation, passing scenario oracle, and an accepted gap decision.
- **authority_statement:** Composer proposes and documents; it has no execution authority.
