# Architecture handbook contract

## Discovery

The active root `AGENTS.md`, `CLAUDE.md`, or `README.md` may declare one
explicit pointer as `docs-map: path/to/map.md`. Resolve it relative to the
repository root. Multiple distinct valid pointers are an ambiguity. Without a
pointer, an existing `docs/README.md` wins. When neither exists, exactly one
Markdown candidate ending in `-map.md` under `docs/` is proposed; several
candidates or no candidate requires a Human-confirmed proposal before writes.

## Map

The map is reader-facing Markdown. It links each architecture page once and
states the page's bounded question. For a primary page, the same list item must
also contain `authority-id: <id>`. The map therefore binds that ID to its one
primary path without a parallel manifest.

```markdown
- [Checkout flow](architecture/ta-checkout-flow.md) — trigger-to-effect path;
  authority-id: architecture.flow.checkout
```

Root `ZJ-CONTEXT.md` and `ZJ-CONTEXT-MAP.md` are external entries that a map may
register; do not relocate them.

## Page header and shared sections

New or normalised pages begin with:

```yaml
---
doc-kind: architecture-subsystem
authority: primary
authority-id: architecture.subsystem.catalog
---
```

`authority` is `primary`, `supporting`, `historical`, `process`, or `external`.
Only `primary` requires `authority-id`. Every primary architecture page has
`Question`, `Scope`, `Boundaries`, `Source map`, and `Related authority`
headings. Existing pages are reported as incomplete during a migration proposal;
they are not normalised without confirmation.

## Five complementary views

| View | `doc-kind` | Must answer |
| --- | --- | --- |
| System overview | `architecture-overview` | System purpose, exterior boundary, major parts, and reader routing. |
| Layers | `architecture-layers` | Allowed dependencies and layer responsibility. |
| Subsystem | `architecture-subsystem` | Responsibility, owned state, interface, and failure behavior. |
| Flow | `architecture-flow` | Trigger, sequence, state/effects, failure or exit behavior, and observable evidence. |
| Cross-cutting | `architecture-cross-cutting` | One shared rule and every view that consumes it. |

`architecture-map` owns routing only. Prefix technical pages `ta-`; use `ba-`
or `pa-` when the page instead belongs to business or product architecture.

## Source map and authority

Use links or repository-relative inline-code paths under `## Source map` for
code, tests, fixtures, accepted ADRs, or stable external references. Distinguish
target architecture, implemented behavior, inference, and unknowns in prose.
An accepted or superseded ADR may support a claim; a proposed ADR cannot.

Process pages, plans, retros, raw evaluations, research ledgers, runtime traces,
and fixture payloads are evidence surfaces or process material, never pages the
validator reads as handbook content.
