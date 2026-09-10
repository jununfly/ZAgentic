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
precedence: two pages that answer the same question *differently* are a
Human-review signal, because settling conflicting normative claims needs
judgment about content. A binding is different in kind — which page the map gave
an id to is a fact, not a reading — so its conflicts are mechanical.

The two layers have separate owners:

| Layer | Question | Owner | Codes |
| --- | --- | --- | --- |
| Binding | Does the map give one id to more than one page? | this skill | `MAP_AUTHORITY_CONFLICT` |
| Declaration | Do two pages claim the same id, and do map and page agree? | `zj-docs-architecture` | `AUTHORITY_ID_DUPLICATE`, `AUTHORITY_ID_MISSING`, `AUTHORITY_MAP_BINDING` |

Both can fire on one id, and that is two defects rather than one reported twice:
the map bound it to two pages *and* the pages declared it. Neither tool claims
the other's layer, and neither suppresses the other.

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

### What overlaps with `zj-docs-architecture`, and who owns it

Both skills run against the same repository, and both have to select a map
before they can do anything else. Three codes therefore exist under the same
name in both: `MAP_POINTER_BROKEN`, `MAP_AMBIGUOUS`, and `MAP_LINK_BROKEN`.
When the two run together they are one condition seen twice, not two defects —
de-duplicate on `(code, path)`. They are owned here: this skill governs the
whole map, while `zj-docs-architecture` re-derives them only to reach the
architecture pages it is responsible for. Everything that needs a page's
contents (`PAGE_*`, `AUTHORITY_ID_*`, `SOURCE_*`, `ADR_*`) is its alone.

The duplication is tolerated on purpose. Removing it would mean a shared
module, and a skill is installed by copying its directory — a cross-skill import
breaks at install time, while carrying a private copy just moves the same code
and adds a rule that the two must be kept in step.
