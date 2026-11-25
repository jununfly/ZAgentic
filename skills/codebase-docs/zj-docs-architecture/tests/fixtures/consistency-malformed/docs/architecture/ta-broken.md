---
doc-kind: architecture-subsystem
authority: primary
authority-id: architecture.subsystem.broken
---

# Broken concept map demo

## Question

What does this fixture demonstrate? That a malformed concept-map B degrades to
a signal instead of crashing the consistency command.

## Scope

The consistency command reading `docs/architecture/tacm-map.md`.

## Boundaries

The B block is unclosed; the page itself stays a valid primary view so the
command's exit code reflects only the B guard.

## Source map

`../../src/broken.rs`

## Related authority

None.

## Responsibility

Hold a valid primary architecture-subsystem contract.

## Owned state

Nothing durable; this is a test fixture.

## Interface

Read by `consistency()` via `CONCEPT_MAP_FILE`.

## Failure behavior

A malformed B yields a single `CONCEPT_MAP_MALFORMED` signal and exit 0.
