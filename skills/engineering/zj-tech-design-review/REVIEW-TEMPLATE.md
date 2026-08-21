# Technical design review template

> Mechanical gate: run `python scripts/validate_review.py <review.md>` from this skill directory. The gate checks structure and traceability; a human still decides whether the reasoning is sound.

## One-page overview

### Decision

Choose one: `approve`, `revise`, `reject`, or `defer`. State whether unresolved findings are `blocking` or `non-blocking`.

### Summary
What changes, for whom, and why now? (1–3 sentences.)

### Platforms and scope
Supported environments, affected code/data surfaces, dependencies, and explicit exclusions.

### Ownership and tracking
Decision owner, engineering/operations contacts, issue or launch tracker, and reviewers.

## Problem and goals

User/job, current workflow and baseline, pain or opportunity, goals, non-goals, assumptions, constraints, and success definition.

## Design

Alternatives considered; chosen design; major modules and seams; state/data/control flow; APIs and compatibility; failure handling; migration; ownership boundaries. Link diagrams, mocks, specs, and related work.

## Metrics and experiments

Success metrics and regression metrics with baseline, unit, method, target/threshold, and owner. Describe experiments, cohorts, guardrails, and acceptance criteria.

## Rollout, recovery, and lifecycle

Rollout stages or flag, monitoring, pause/rollback triggers, migration and version-skew plan, support burden, deprecation, cleanup, and follow-up work.

## Principle considerations

### Performance
Speed, memory, power, capacity, and benchmark or field measurement plan.

### Simplicity and accessibility
User-visible effects, new concepts or controls, switching costs, accessibility, and intentionally harder workflows.

### Security and privacy
Threat model, trust boundaries, untrusted inputs, credentials, approvals, sandbox/isolation, data collection, retention, access, and deletion.

## Testing and validation

Test matrix by behavior/platform/failure mode; fixtures and reproducible scenarios; expected observations; thresholds; owner; and exit decision.

## Open decisions

| Question | Evidence needed | Owner | Due/exit condition |
|---|---|---|---|

## Review record

Reviewer, date, concern, response or decision, and remaining risk.

### Short-read acceptance

Before publishing, a reviewer should be able to identify within a short read:

- the current decision (`approve`, `revise`, `reject`, or `defer`);
- every `blocking` finding and its owner;
- the next validation action, threshold, and owner.
