# Metrics Contract

This file is the single definition of what `scripts/docs_metrics.py` measures,
what it refuses to do, and what its output means. Read it before changing the
tool or interpreting a report.

## Status in the skill chain

`/zj-docs-ontology` owns map correctness (`MAP_*`, `RETIRE_*`, `UNMAPPED_PAGE`,
typed relations, Module D); `/zj-docs-architecture` owns structure correctness
(`PAGE_*`, `SOURCE_TARGET_*`, `ADR_*`, concept-graph `CONSIST_*`). This skill owns **measurement**, a different axis: it fires no
correctness diagnostics, borrows no gating authority, and its verdicts are
advisory outliers for the Human. "The map is correct", "the structure is
valid", and "the pages are healthy" are three different claims.

**What this skill measures.** A read-only metering of a repository's *living
pages* by pure topology and physical properties only — deliberately no semantic
judgment, no gate, no cross-skill contract dependency. The admission test for any
meter here: can it be computed from the living pages plus the plain markdown-link
graph plus file physics alone? A metric that instead requires re-implementing a
sibling skill's contract syntax is a positioning conflict, not a meter. This rule
is both the scope and the gate for adding new meters.

**Authority: this serves a gap `/zj-docs-ontology` explicitly declined.**
The **Rejected defaults** section of the `/zj-docs-ontology` skill's own
`governance-contract.md` (that sibling skill is not shipped when this one is
installed standalone) lists "a mechanical health-score gate (page size
budget, freshness scoring, orphan scoring)" as a **rejected default**, because the
target repo has "no manifest and no uniform source-map timestamp, so any score
would be invented. It is carried as a capability gap rather than built on a
missing fact source." This skill serves that declined gap without contradicting
the reason: it is opt-in (the Human commits `docs/docs-metrics.json`, supplying
the manifest ontology says a repo lacks) and it borrows no gating authority
(advisory outliers only). The rejected thing was an automatic gate, not the
measurement itself — inviting a report is exactly what the gap left open.

**Living-page scope is deliberately independent of the other skills.** This
skill counts a *living page* as every `*.md` outside the
`artifacts|evidence|evaluations|fixtures|skills-outputs|test-results` and
`plans|zj-retros` path segments. That is **not** `/zj-docs-ontology`'s
map-coverage notion, and the two scopes may disagree on which pages count — by
design. Unifying them would couple this opt-in, zero-cross-skill-import tool to
the ontology's preset vocabulary and break its portability boundary. Every meter
here is only meaningful within this skill's own living-page scope; do not
"align" the two definitions, and do not assume a page this skill ignores is a
page the ontology ignores.

## Opt-in and portability

The engine is parameterized by a JSON config the target repository commits:

```json
{
  "budgets": [
    {"glob": "docs/prds/*.md", "max_lines": 120}
  ],
  "freshness": {"max_age_days": 30},
  "orphans": true
}
```

- Default location `docs/docs-metrics.json`; `--config` overrides.
- **No config file means no measurement**: the tool prints `status: opt-in`
  and exits zero. A repository that never adopted these skills is untouched —
  metering never crosses the portability boundary uninvited.
- Malformed config: `status: config-error`, exit 1. The tool never guesses
  parameters.

## Meters

### BUDGET_EXCEEDED

For each `budgets` rule, every `.md` file matching `glob` (relative to the
repository root) with more physical lines than `max_lines`. Physical lines,
not words: deterministic and linter-checkable later if the Human promotes it.

### FRESHNESS_DRIFT

For every living docs page that declares a `## Source map` section: the
newest existing target (markdown links and inline-code paths, resolved from
the page's directory) compared against the page's modification time. Drift when
the gap exceeds `max_age_days`. A page with no `## Source map` section is
skipped — freshness cannot be asserted without a declared source.

**The `## Source map` fact source belongs to `/zj-docs-architecture`; this meter
is only a best-effort consumer of it.** It re-derives targets with its own
link/inline scan rather than importing architecture's `source_paths()`, so its
target set can diverge from the authoritative one (inline-code regex, `/`-prefixed
paths, section detection). That divergence is accepted, not a bug to chase: every
verdict here is advisory, and the precision ceiling of this meter is set by the
"consumer + zero-cross-skill-import" positioning, not by how tightly it tracks
architecture. Where a *strict* source set matters, `/zj-docs-architecture` is the
authority — and its `SOURCE_*` covers only target existence/bounds
(`SOURCE_TARGET_MISSING`/`SOURCE_TARGET_OUTSIDE`), with no time concept. That
absence is exactly the gap this consumer fills.

Time source: git commit time when the target is a git work tree; file mtime
otherwise (plain directories, test fixtures). Git time is preferred because
checkouts and rebases do not reset content age.

### NAV_ORPHAN / MAP_ONLY

Link graph over living pages (evidence surfaces and process material are
excluded from both endpoints — they are frozen or transient, not living
references). The docs map is tracked separately from ordinary citations:

- `NAV_ORPHAN` — no inbound link from any living page **including the map**:
  nothing knows the page exists.
- `MAP_ONLY` — the map links it but no living page does: indexed but
  uncited. Common and often fine for entry points; it is an advisory signal
  for the Human, which is why it is metered only when `orphans: true`.

**`NAV_ORPHAN` (formerly `ORPHAN_PAGE`) is a different claim from
`/zj-docs-ontology`'s `ORPHAN_PAGE`, and the two coexist.** That skill's is a
graph-reachability defect over `## Source map` entries and their typed relation
edges (`derived-from`/`supersedes`/`supports`); this skill's is a navigation
island over the plain-markdown-link graph of living pages. Different graph,
different edge, no shared authority. A page can be reported by both at once
without either being wrong, and clearing one never clears the other. This skill
was renamed `ORPHAN_PAGE` → `NAV_ORPHAN` precisely to drop the inherited name
collision; the two codes never shared authority and still do not.

## Output and exit codes

JSON with `status` (`opt-in` / `config-error` / `measured`), `config`,
`outliers` (each: `code`, `path`, `detail`). Exit 1 when `outliers` is
non-empty, 0 when clean or unconfigured. `config-error` also exits 1: an
unreadable parameterization must not masquerade as a clean bill of health.

## What a clean run does not mean

A zero-outlier run says the Human's parameterized thresholds are currently
satisfied. It does not say the pages are good, complete, or correct — those
belong to the other two skills and to the Human reading them.
