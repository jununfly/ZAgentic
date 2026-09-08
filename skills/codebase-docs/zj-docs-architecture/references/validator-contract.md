# Architecture validator contract

`validate_architecture_docs.py` is read-only. It reads the selected map, the
architecture pages linked by that map, and ADR files only when a page names one
as an accepted authority. It checks source-map targets by path existence, not
content. `--audit-json` exposes the read set for tests and review.

Mechanical diagnostics have stable codes: `MAP_*`, `PAGE_*`, `AUTHORITY_*`,
`SOURCE_*`, and `ADR_*`. `SIGNAL_*` diagnostics are Human-review signals and do
not make the command fail. The command exits nonzero only for mechanical
diagnostics.

A map may defer the architecture category until the repository has a concrete
architecture page. With no `docs/architecture/` Markdown page, no architecture
link is required. Once such a page exists, the map must link it; an empty
architecture map is then a mechanical failure.

Run the fixture suite with:

```sh
python3 skills/codebase-docs/zj-docs-architecture/tests/test_validator.py
```

Fixtures prove valid minimal and multi-view handbooks, missing contract fields,
duplicate authority, source-map drift, unaccepted ADR use, and the no-read
boundary for process/evidence files.
