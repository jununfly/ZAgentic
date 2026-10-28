# Health Contract

This file is the single definition of what `scripts/doc_health.py` measures,
what it refuses to do, and what its output means. Read it before changing the
tool or interpreting a report.

## Status in the skill chain

`/zj-docs-ontology` owns map correctness (`MAP_*`, `RETIRE_*`);
`/zj-docs-architecture` owns structure correctness (`PAGE_*`, `SOURCE_*`,
`ADR_*`). This skill owns **measurement**, a different axis: it fires no
correctness diagnostics, borrows no gating authority, and its verdicts are
advisory outliers for the Human. "The map is correct", "the structure is
valid", and "the pages are healthy" are three different claims.

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

- Default location `docs/doc-health.json`; `--config` overrides.
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
the page's directory — the architecture layer's one base, no second syntax)
compared against the page's modification time. Drift when the gap exceeds
`max_age_days`. A page with no `## Source map` section is skipped — freshness
cannot be asserted without a declared source.

Time source: git commit time when the target is a git work tree; file mtime
otherwise (plain directories, test fixtures). Git time is preferred because
checkouts and rebases do not reset content age.

### ORPHAN_PAGE / ZERO_INDEGREE

Link graph over living pages (evidence surfaces and process material are
excluded from both endpoints — they are frozen or transient, not living
references). The docs map is tracked separately from ordinary citations:

- `ORPHAN_PAGE` — no inbound link from any living page **including the map**:
  nothing knows the page exists.
- `ZERO_INDEGREE` — the map links it but no living page does: indexed but
  uncited. Common and often fine for entry points; it is an advisory signal
  for the Human, which is why it is metered only when `orphans: true`.

## Output and exit codes

JSON with `status` (`opt-in` / `config-error` / `measured`), `config`,
`outliers` (each: `code`, `path`, `detail`). Exit 1 when `outliers` is
non-empty, 0 when clean or unconfigured. `config-error` also exits 1: an
unreadable parameterization must not masquerade as a clean bill of health.

## What a clean run does not mean

A zero-outlier run says the Human's parameterized thresholds are currently
satisfied. It does not say the pages are good, complete, or correct — those
belong to the other two skills and to the Human reading them.
