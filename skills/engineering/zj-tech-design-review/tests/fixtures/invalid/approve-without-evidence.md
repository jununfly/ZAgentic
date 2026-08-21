# Invalid unsupported approval

Decision: approve

## One-page overview
Summary: an approval without a source.
Platforms and scope: test only.
Ownership and tracking: Test owner.

## Problem and goals
Goals: test the validator. Non-goals: ship this design.

## Design
Alternatives considered: none. Risk owner: Test.

## Metrics and experiments
Baseline: 1. Unit: count. Method: fixture run. Target: pass.

## Rollout, recovery, and lifecycle
Rollout: never. Rollback: delete the fixture.

## Principle considerations
Security: test only.

## Testing and validation
Scenario: parse the fixture. Threshold: report missing evidence.

## Open decisions
Question: why is this approved?

## Review record
Blocking findings: evidence is missing.
Non-blocking findings: none.
