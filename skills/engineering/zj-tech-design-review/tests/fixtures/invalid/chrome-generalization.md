# Invalid vendor generalization

Decision: revise

## One-page overview
Summary: a vendor-specific rule presented as universal.
Platforms and scope: test only.
Ownership and tracking: Test owner.

## Problem and goals
Goals: test the validator. Non-goals: ship this design.

## Design
Alternatives considered: none. Risk owner: Test. Evidence: [E1](https://example.com/evidence).
Finch is required for every rollout.

## Metrics and experiments
Baseline: 1. Unit: count. Method: fixture run. Target: pass.

## Rollout, recovery, and lifecycle
Rollout: staged. Rollback: disable the feature.

## Principle considerations
Security: test only.

## Testing and validation
Scenario: parse the fixture. Threshold: report vendor generalization.

## Open decisions
Question: should the vendor rule be optional?

## Review record
Blocking findings: vendor rule is overgeneralized.
Non-blocking findings: none.
