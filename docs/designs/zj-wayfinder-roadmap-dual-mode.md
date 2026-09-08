---
doc-kind: design
authority: primary
authority-id: design.wayfinder-roadmap-carrier-seam
---

# Wayfinder and roadmap carrier seam

## Question

How do `zj-wayfinder` and `zj-roadmap-driven` preserve a planning-to-tracking
handoff while keeping their different physical sources of truth explicit?

## Scope

This design covers the seam among `zj-wayfinder`, `zj-to-tickets`, and
`zj-roadmap-driven`. It describes carrier selection, phase handoff, and source
of truth; it does not define a shared carrier API, an external coordination
service, or automatic migration between carriers.

## Boundaries

- `zj-wayfinder` plans: it resolves decision tickets until the route is clear.
  It does not own delivery tracking by default.
- `zj-roadmap-driven` tracks a defined route in local JSON or an explicit
  roadmap bundle. It does not plan a route on an issue tracker.
- `zj-to-tickets` converts a plan or resolved decision map into
  blocking-aware local or tracker tickets. It does not create a roadmap JSON.
- A Human chooses the carrier and phase transition. No skill silently moves a
  map, tickets, or decisions between physical stores.

## Carrier design

| Phase | Carrier | Fact source | Use when |
| --- | --- | --- | --- |
| Wayfinding | Issue tracker | One map issue and its decision-ticket issues, native blocking edges, and claims | Teamwork needs shared visibility and concurrent ticket ownership. |
| Wayfinding | Local Markdown | One map file with numbered decision-ticket sections, `🔒` claims, and textual blocking | A self-contained, offline, single-writer planning view is preferable. This is the fallback without tracker configuration. |
| Tracking | Local roadmap JSON | One roadmap JSON, edited through the roadmap CLI | The route is clear and execution needs a compact source of truth. |
| Tracking | Roadmap bundle | Manifest, node/decision shards, and append-only history, edited through the CLI | A large roadmap exceeds the single-file operating envelope. |

Tracker configuration comes from `zj-repo-init` when tracker mode is selected.
Local wayfinding requires no tracker configuration. Storage advice is explicit:
`zj-roadmap-driven` may recommend a bundle but never migrates one implicitly.

## Seam

1. Use `zj-wayfinder` while the path is foggy and decisions, rather than build
   slices, are the active work.
2. When the route is clear, use `zj-to-tickets` to publish ordered,
   blocking-aware tracer-bullet tickets in the selected ticket carrier.
3. Create or update the execution roadmap through `roadmap_cli.py`; its JSON
   or bundle becomes the tracking fact source.
4. Use `zj-roadmap-driven` to navigate the agreed route. Do not re-chart the
   wayfinding decisions by hand in the roadmap.

The seam preserves decisions by conversion, not by treating tracker issues,
local Markdown, and roadmap JSON as interchangeable stores.

## Source map

- [zj-wayfinder](../../skills/codebase-docs/zj-wayfinder/SKILL.md) — planning
  phases and tracker/local carrier rules.
- [zj-to-tickets](../../skills/engineering/zj-to-tickets/SKILL.md) —
  blocking-aware ticket publication.
- [zj-roadmap-driven](../../skills/codebase-docs/zj-roadmap-driven/SKILL.md) —
  JSON/bundle fact source and CLI-only writes.
- [dual-mode reference](../../skills/codebase-docs/zj-roadmap-driven/references/dual-mode.md)
  — detailed carrier and handoff guidance.

## Related authority

- [ZAgentic documentation map](../README.md) — document routing and lifecycle.
- [Codebase Docs capability spec](../prds/codebase-docs-capability.md) —
  repository documentation boundaries.
