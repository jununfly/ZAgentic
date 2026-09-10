# Architecture validator contract

`validate_architecture_docs.py` is read-only. It reads the selected map, the
architecture pages linked by that map, and ADR files only when a page names one
as an accepted authority. It checks source-map targets by path existence, not
content. `--audit-json` exposes the read set for tests and review.

Mechanical diagnostics have stable codes: `MAP_*`, `PAGE_*`, `AUTHORITY_*`,
`SOURCE_*`, and `ADR_*`. `SIGNAL_*` diagnostics are Human-review signals and do
not make the command fail. The command exits nonzero only for mechanical
diagnostics.

Page-name stability is mechanical too, reported under `PAGE_NAME_*`:
`PAGE_NAME_PREFIX` (missing or unknown `ta-` / `ba-` / `pa-` prefix),
`PAGE_NAME_SHAPE` (not lowercase and hyphen-separated), `PAGE_NAME_DATE` (date,
bare year, or commit sha), and `PAGE_NAME_VERSION_OR_STATUS` (version number or
temporary-status word). A name is reported once per cause, and a date suppresses
the version report for the same name.

A map may defer the architecture category until the repository has a concrete
architecture page. With no `docs/architecture/` Markdown page, no architecture
link is required. Once such a page exists, the map must link it; an empty
architecture map is then a mechanical failure.

Run the fixture suite with:

```sh
python3 skills/codebase-docs/zj-docs-architecture/tests/test_validator.py
```

Fixtures prove valid minimal and multi-view handbooks, missing contract fields,
duplicate authority, source-map drift, unaccepted ADR use, unstable page naming,
the no-read boundary for process/evidence files, and a repository laid out
unlike this one.

### The external-layout fixture

`tests/fixtures/valid-external-layout` is a synthetic repository, not a copy of a
real one — its `SOURCE.md` records which conventions it borrows and why. It has
no `docs/` tree at all, keeps its map at `handbook/map.md` (reachable only
through the root `docs-map:` pointer), nests architecture pages under
`handbook/architecture/subsystems/`, and mixes `ta-` / `pa-` / `ba-` prefixes.

It exists because seven same-shaped fixtures can only prove self-consistency.
Its value is entirely in *not* firing: a difference in layout is not a defect.
Two guards keep that from degrading into a fixture that passes by being
invisible:

- the mapped pages must actually appear in the read set, so a validator that
  silently stops recognising this layout fails instead of reporting nothing;
- `handbook/architecture/drafts/ta-checkout-v2.md` is a deliberate negative
  control. Its name is unstable, but nothing maps it, so it must produce no
  diagnostic. `ExternalLayoutTest` maps it in a throwaway copy and asserts the
  naming diagnostic appears — the rule fires on the map claiming the page, not
  on the file existing.

Two seams are under test: `validate()` in-process for diagnostic codes, and the
command itself for exit codes — including a run against this repository, which
is the control for "the naming rule is not so strict that today's handbook
fails". The control locates that repository by walking up for an ancestor that
has both `.git` and `docs/`; an installed copy under `~/.codex/skills/…` has
neither, so the control skips there instead of pointing the validator at a home
directory.
