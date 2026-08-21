# Search index migration review

Mode: review
Decision: revise

## One-page overview

### Summary
Review a proposal to move the search index from process memory to a shared local store.

### Platforms and scope
Desktop Linux and macOS; migration and rollback are in scope.

### Ownership and tracking
Search platform owns the decision, migration, and support queue.

## Problem and goals

Goals: reduce restart latency and bound memory use.
Non-goals: changing ranking semantics or adding a remote index.

## Design

Alternatives considered: keep memory-only, use SQLite, or use a hosted service. SQLite is preferred for local ownership.
Risk owner: Search platform. The adapter translates old records and preserves document identity.
Evidence: [E2](https://example.com/index-migration) covers a representative corpus.

## Metrics and experiments

Baseline: 4.2 s cold start. Unit: seconds and MiB. Method: replay 1000 queries five times.
Target: cold start below 2 s with no p95 memory increase. Threshold: migration error rate below 0.5%.

## Rollout, recovery, and lifecycle

Rollout: opt-in flag, dogfood, then staged release. Rollback restores the old reader and keeps the old store until the exit gate.
Version-skew test covers one-version-old writers.

## Principle considerations

Performance and power improve after warm-up. Security limits the store to the user profile.
Privacy retains no query text beyond the local retention window.

## Testing and validation

Scenario: migrate empty, large, corrupted, and interrupted stores. Expected observation: either an equivalent index or a clean rollback.
Threshold: query result parity is at least 99.9% on the golden corpus.

## Open decisions

Question: when can the old store be deleted? Owner: Search platform.
Next validation: migrate empty, large, corrupted, and interrupted stores, then verify equivalent results or a clean rollback. Threshold: at least 99.9% query-result parity on the golden corpus. Owner: Search platform.

## Review record

Blocking findings: migration rollback needs an explicit operator signal. Owner: Search platform.
Non-blocking findings: benchmark documentation can be clearer.
