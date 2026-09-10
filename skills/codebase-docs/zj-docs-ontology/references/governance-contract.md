# Documentation governance contract

## Discovery and map choice

Read root `AGENTS.md`, `CLAUDE.md`, and `README.md` for an exact
`docs-map: <repo-relative Markdown path>` pointer. One valid pointer wins.
Without it, use existing `docs/README.md`. With neither, one `*-map.md`
candidate under `docs/` is a proposal; several candidates are an ambiguity;
no candidate is a greenfield proposal. Compatibility discovered in a target
repository wins over this convention.

## Categories

| Lifecycle | Categories |
| --- | --- |
| Long-lived | `methods`, `prds`, `architecture`, `agreements`, `designs`, `testing`, `benchmarks`, `references`, `zj-adr` |
| Process | `plans`, `zj-retros` |

Fixture documentation can live beside its fixture and is registered by the
map. Code, tests, fixtures, raw benchmark profiles, logs, research packages,
and evaluations are evidence surfaces rather than durable documentation pages.
`ZJ-CONTEXT.md` and `ZJ-CONTEXT-MAP.md` remain root-level external entries.

## Page and authority contract

`doc-kind` is one of `method`, `prd`, `architecture-map`,
`architecture-overview`, `architecture-layers`, `architecture-subsystem`,
`architecture-flow`, `architecture-cross-cutting`, `agreement`, `design`,
`testing`, `benchmark`, `reference`, `adr`, `plan`, `retro`, or
`fixture-documentation`. `authority` is `primary`, `supporting`, `historical`,
`process`, or `external`; a primary page has one `authority-id`, which the map
binds to one page and bounded question. Navigation order is not global truth
precedence: conflicting normative claims are a Human-review signal.

The binding is what the governance tool checks. One `authority-id` appearing on
two map entries is `MAP_AUTHORITY_CONFLICT`, reported against the map and
reflected in a non-zero exit — two pages answering the same bounded question is
a decision the Human has to make, and a report that exits zero would present it
as settled. The tool reads the map only; a page's own `authority` front matter
is `zj-docs-architecture`'s contract to enforce.

## Migration and lifecycle

Every migration has two stages:

1. A read-only inventory and proposal identifies classification, conventions,
   moves, broken links, authority synthesis, and deletion candidates.
2. The Human confirms each named mutation. Preserve meaning by default; use
   `git mv` for a tracked move. Rewrites, merges, and deletion need their own
   confirmation.

The lifecycle is `process material → durable extraction → authority audit →
deletion proposal → Human confirmation → deletion`. `/zj-debrief` produces
process material, and `/zj-neat-freak` governs drift; neither is an event hook.

## Composition

`zj-docs-architecture` maintains the handbook layer. `zj-domain-modeling`
resolves terminology, `zj-debrief` captures process closeout, and
`zj-neat-freak` reconciles broader knowledge drift. `zj-repo-init` configures
tracker/triage entrypoints only after a selected map exists; it never invokes
this skill.
