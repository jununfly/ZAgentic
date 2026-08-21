# Invalid unknown handling

Decision: defer

## One-page overview
Summary: invalid fixture.
Platforms and scope: test only.
Ownership and tracking: Test owner.

## Problem and goals
Goals: test the validator. Non-goals: ship this design.

## Design
Alternatives considered: none. Risk owner: Test. Evidence: [E1](https://example.com/evidence).
Unknown is absent, so no follow-up is needed.

## Metrics and experiments
Baseline: 1. Unit: count. Method: fixture run. Target: pass.

## Rollout, recovery, and lifecycle
Rollout: never. Rollback: delete the fixture.

## Principle considerations
Security: test only.

## Testing and validation
Scenario: parse the fixture. Threshold: report the anti-pattern.

## Open decisions
Question: none.

## Review record
Blocking findings: invalid statement.
Non-blocking findings: none.
