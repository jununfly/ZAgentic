# Offline import design

Mode: draft
Decision: defer

## One-page overview

### Summary
Allow users to import a local archive and inspect it without uploading contents.

### Platforms and scope
Desktop clients; the importer and local index are in scope. Cloud sync is out of scope.

### Ownership and tracking
Importer team owns the decision and the issue tracker entry.

## Problem and goals

Goals: make the first import observable and recoverable.
Non-goals: cross-device sync, remote sharing, and automatic deletion.
Constraints: archives may be malformed and machines may be offline.

## Design

Alternatives considered: parse in the UI, use a worker process, or upload to a service. The worker process is chosen for isolation.
Risk owner: Importer team. State stays local; the UI receives progress events.
Evidence: [E1](https://example.com/import-benchmark) shows the worker keeps the UI responsive.

## Metrics and experiments

Baseline: 18 s median import. Unit: seconds per archive. Method: repeat 30 fixed fixtures.
Target: p95 below 25 s and zero UI hangs. Regression metric: worker crash rate.

## Rollout, recovery, and lifecycle

Rollout: hidden flag, then 10% and 100%. Rollback when crash rate exceeds 1%; recovery removes only the temporary index.

## Principle considerations

Performance is measured on low-end hardware. Simplicity keeps one import action. Security rejects path traversal.
Privacy: archive contents remain local and are deleted only by the user.

## Testing and validation

Scenario: import valid, malformed, and interrupted fixtures. Expected observation: progress resumes or reports a recoverable error.
Threshold: all malformed fixtures fail closed.

## Open decisions

Question: should a paused import resume after restart?
Next validation: interrupt 30 imports, restart, and verify recovery. Threshold: at least 99% resume successfully with no duplicate or lost files. Owner: Importer team.

## Review record

Blocking findings: the restart behavior is unresolved.
Non-blocking findings: progress copy needs UX review.
