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

`architecture-map` owns routing only.

## Page naming

A page name answers **what the page is about** and nothing else. A name that
encodes when it was written, which revision it is, or how current it is becomes
wrong the first time the page is revised — and every link to it goes stale with
it.

- **Prefix by architecture family**: `ta-` for technical, `ba-` for business,
  `pa-` for product architecture.
- **Lowercase and hyphen-separated**: `ta-checkout-flow.md`, never
  `ta-Checkout_Flow.md` or `ta checkout flow.md`.
- **No unstable tokens**: dates (`2026-09-10`, `20260910`, a bare year), commit
  shas, versions (`v2`, `1.0`, a trailing number), or temporary-status words
  (`draft`, `wip`, `tmp`, `latest`, `final`, `current`, `deprecated`, `copy`, …).

Renaming an existing unstable page is a migration: propose it, do not do it
silently — the map and every inbound link change with it. The validator reports
violations as `PAGE_NAME_PREFIX`, `PAGE_NAME_SHAPE`, `PAGE_NAME_DATE`, and
`PAGE_NAME_VERSION_OR_STATUS`.

## Maintenance triggers

A handbook change is in scope when any signal below appears. Signals, not
intent: the question is not "is this architectural" but "did one of these
change". This section is authoritative for the list; the copy in `SKILL.md`
must stay item-for-item identical, and `tests/test_docs_consistency.py`
compares the two.

- **Extension seam** — a new plugin, registry, hook, or callback entry exists, or
  an existing one changes signature: the handbook must say where outside code
  attaches and what it has to obey.
- **Durable owner** — a rule or explanation moves, or now appears on two pages:
  ownership changed, so the page that lost it becomes a link.
- **Cross-process contract** — the message, schema, or call convention between
  two processes changes: every page describing either side has to agree.
- **Effect policy** — retry, idempotency, write path, or failure compensation
  changes: a flow page's failure behavior is stale until it is re-checked.
- **Replay boundary** — what can be replayed, from which point, and against what
  stored input changes: the flow page's state and evidence claims move with it.
- **Lifecycle rule** — a state machine, or when something is created, migrated,
  or destroyed, changes: those transitions are documented behavior, not code
  detail.
- **Accepted ADR** — an ADR moves to `accepted` or `superseded`: accepted ADRs
  may support a claim and proposed ones may not, so a supersession withdraws
  support from every page citing it.
- **Source-map target** — a path under `## Source map` moves, is renamed, or is
  deleted: the validator reports it as `SOURCE_*`, and the claim it supported
  needs re-checking, not just the link.

## Source map and authority

Use links or repository-relative inline-code paths under `## Source map` for
code, tests, fixtures, accepted ADRs, or stable external references. Distinguish
target architecture, implemented behavior, inference, and unknowns in prose.
An accepted or superseded ADR may support a claim; a proposed ADR cannot.

Those paths resolve from the **directory holding the page**, the same base a
Markdown link uses: a page at
`handbook/architecture/subsystems/ta-billing-engine.md` cites
`../../src/billing/engine.rs`. Repository-root spelling — `src/billing/engine.rs`
— resolves to a path *under the page* and is reported as
`SOURCE_TARGET_MISSING`; a path that climbs past the repository root is reported
as `SOURCE_TARGET_OUTSIDE`. Map links and Source map entries therefore share one
base; there is no second rule to learn.

Process pages, plans, retros, raw evaluations, research ledgers, runtime traces,
and fixture payloads are evidence surfaces or process material, never pages the
validator reads as handbook content.
