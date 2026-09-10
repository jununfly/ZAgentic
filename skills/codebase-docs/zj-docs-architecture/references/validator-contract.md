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
and the no-read boundary for process/evidence files.

Two seams are under test: `validate()` in-process for diagnostic codes, and the
command itself for exit codes — including a run against this repository, which
is the control for "the naming rule is not so strict that today's handbook
fails". The control locates that repository by walking up for an ancestor that
has both `.git` and `docs/`; an installed copy under `~/.codex/skills/…` has
neither, so the control skips there instead of pointing the validator at a home
directory.
