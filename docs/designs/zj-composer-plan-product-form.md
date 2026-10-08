---
doc-kind: design
authority: primary
authority-id: design.composer-plan-product-form
---

# Composer and Plan product form

## Question

What product form should reduce the cost of assembling ZAgentic capabilities while preserving one authority, auditable evidence, Human approval, and removable integration?

## Scope

This design defines the approved product boundary for the Composer capability and the Plan artifact. It covers discovery, recommendation, gap reporting, Plan generation, approval handoff, and the first reversible validation slice. It does not implement a session runtime, global router, automatic executor, or long-term governance store.

## Boundaries

- **Composer** is an intent-to-Plan capability. It reads the user's goal, constraints, available skill/workflow metadata, evidence requirements, and permission boundary; it returns a reasoned candidate composition.
- **Plan** is the versioned, reviewable task contract generated from the Composer skill's built-in template. It records selected capabilities, reasons, order, inputs/outputs, dependencies, Human checkpoints, verification, failure exits, rollback, and provenance.
- A skill or workflow remains the semantic owner of its capability and execution behavior.
- The evidence and decision protocol remains the owner of provenance, verification facts, and Human decisions.
- The existing execution chain owns approved execution, side effects, failure recovery, and verification.
- The documentation system owns durable governance rules. Composer output cannot silently become a long-lived rule.
- When an existing capability matches, Composer proposes it with reasons and constraints. When a credible external or future capability is identifiable, Composer gives a bounded suggestion with source and fit caveats. When no reliable suggestion exists, Composer emits one line per gap in the exact form `required skill：简短地描述缺失skill的形状`.
- Plan templates are versioned resources inside the Composer skill. A Plan records its template version; template changes require an explicit version change and cannot silently reinterpret an existing Plan.
- Composer may generate and explain a Plan. It does not own approved execution, irreversible writes, network actions, Git publication, or durable document authority.

## Contract

### Inputs

- User goal and task scope.
- Time, budget, repository, and output constraints.
- Available skill/workflow preferences.
- Permission and side-effect boundary.
- Acceptance criteria and evidence requirements.
- Current skill index and relevant provenance.

### Outputs

- Candidate skill/workflow composition.
- Selection reasons, exclusions, dependencies, and execution order.
- Expected inputs and outputs for each step.
- Human decision points and high-risk capability disclosures.
- Verification commands, scenario oracle, failure exits, and rollback steps.
- Provenance, template version, and unresolved risks.
- Suggestions or the required-skill gap list when coverage is incomplete.

### State handoff

Composer owns the generated Plan while it is `planned`. Human approval transfers the task to the existing execution chain, which owns `approved`, `running`, `blocked`, `failed`, `verified`, `recorded`, `cancelled`, and `rolled_back` transitions according to the consuming workflow.

## Reversible validation slice

The first PoC covers two task fixtures: external repository research and tool-combination design. It writes versioned Markdown Plans under `skills-outputs/`, does not edit skill definitions, and does not execute irreversible actions automatically. Human review is required before the Plan enters an existing execution chain.

Mechanical checks are:

- Plan schema and provenance are complete.
- Every selected capability has a reason.
- Missing capability lines use the required-skill form.
- The fixed scenario oracle passes.
- Authority bypass, undeclared side effects, unapproved writes or network calls, and secret leakage are zero.
- Removing the experiment restores the original path and historical artifacts.

Wall-clock time, interaction steps, manual edits, rejects, retries, recovery, and Plan adoption may be collected as descriptive observations. They are not treated as causal proof against an unstable manual-assembly baseline.

## Rejected default forms

- A global pstack-style router or suite runtime is not the default product path.
- Hooks, transcript/model-sheet state, host-specific runtime state, and shipping glue are not Composer responsibilities.
- A Plan does not become a second roadmap, executor, evidence authority, or governance database.

## Source map

- [ZAgentic guide](../../skills/engineering/zj-guide/SKILL.md)
- [Cross-stage checkpoints](zj-cross-stage-skills.md)
- [Open-source capability-fit decision model](../agreements/open-source-capability-fit-decision-model.md)
- [pstack primary findings](../../skills-outputs/zj-research/pstack-claude-capability-fit/primary-findings.md)
- [pstack capability-fit decision record](../../skills-outputs/zj-open-source-capability-fit/pstack-claude-skill-fit/decision_record.md)
- [pstack technical research report](../../skills-outputs/zj-tech-research-report/pstack-claude-skill-fit/2026-10-08-pstack-claude-report.md)

## Related authority

- [ZAgentic documentation map](../README.md)
- [ADR 0005](../zj-adr/0005-composer-authority-and-plan-contract.md)
- [ZJ-CONTEXT glossary](../../ZJ-CONTEXT.md)
