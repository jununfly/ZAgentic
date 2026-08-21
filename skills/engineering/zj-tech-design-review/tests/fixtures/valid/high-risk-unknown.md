# Model-generated transform review

Mode: review
Decision: defer

## One-page overview

### Summary
Evaluate a service that lets a model propose and run a data transformation in a sandbox.

### Platforms and scope
The worker service and audit trail are in scope; production enablement is not yet in scope.

### Ownership and tracking
Data tools owns the decision; Security owns the threat-model sign-off.

## Problem and goals

Goals: reduce manual transform setup while preserving human approval.
Non-goals: unattended access to production credentials or arbitrary network access.

## Design

Alternatives considered: no execution, a fixed transform catalog, or an isolated worker. The isolated worker remains unproven.
Risk owner: Data tools. Credentials are short-lived, approvals are explicit, and the sandbox denies dangerous operations.
Evidence: [E3](https://example.com/sandbox-threat-model) is a threat-model draft.
Unknown: whether the sandbox contains every filesystem escape path; this is not treated as absent.
Provenance records the prompt, generated code, approval, and output hash. Recovery destroys the worker and revokes credentials.

## Metrics and experiments

Baseline: manual setup takes 20 minutes. Unit: minutes and escaped-operation count. Method: replay 50 red-team fixtures.
Target: zero credential leaks. Threshold: zero sandbox escapes in the experiment cohort.

## Rollout, recovery, and lifecycle

Rollout: prototype only, with a hard pause gate. Rollback revokes all credentials and deletes worker state.

## Principle considerations

Performance is secondary to isolation. Simplicity requires a visible approval step.
Security covers credentials, approvals, isolation, dangerous operations, provenance, and recovery.
Privacy limits retained prompts and outputs.

## Testing and validation

Scenario: malicious prompt, path traversal, network exfiltration, and approval cancellation fixtures.
Expected observation: every dangerous operation is denied or requires an approval record.
Threshold: zero escapes and zero unapproved side effects.

## Open decisions

Question: which sandbox implementation gets a second independent review? Owner: Security.

## Review record

Blocking findings: sandbox escape coverage is unknown. Owner: Security.
Non-blocking findings: operator dashboard is deferred.
