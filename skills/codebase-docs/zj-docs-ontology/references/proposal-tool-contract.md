# Proposal tool contract

`docs_governance.py` is a read-only inventory. `--proposal` emits JSON with the
map decision, categories found by path, root context entries, process material,
evidence-surface paths, and an empty `mutations` list. It never creates,
moves, rewrites, or deletes a target.

`--validate` adds mechanical map-link diagnostics and authority-binding
conflicts. It reads only the selected map and root rule files needed for
discovery; category inventory uses path metadata, and the linked pages are
never opened. Architecture page contracts stay with `zj-docs-architecture`.

An `authority-id:` written next to a map entry binds that id to the linked page.
One id bound to two different pages is `MAP_AUTHORITY_CONFLICT` — reported
against the map, because the contract puts the binding on the map. Being a
`MAP_` code, it makes the command exit non-zero; a conflicting authority is a
failure to settle, not a signal to note and move on. Detection lives entirely in
the map text, so it costs no extra reads.

Run regression coverage with:

```sh
python3 skills/codebase-docs/zj-docs-ontology/tests/test_governance.py
```

The fixtures cover greenfield detection, an existing compatible map, map-link
drift, an unread process file, and one authority-id bound to two pages. The
report's `mutations` must remain empty in every case.

The conflicting-authority fixture proves the binding layer alone: its map binds
`payments.requirement` to two pages, and no page declares an `authority` at all.
That keeps it inside this tool's layer — a page that also declared the id would
put the sample in `zj-docs-architecture`'s layer too, and a page placed under
`docs/architecture/` would additionally have to satisfy that skill's page
contract, since both run against the same repository.

Exit codes live at the CLI seam, so `CommandLineTest` runs the script itself:
the conflicting-authority fixture must exit non-zero, and the other four must
keep their previous exit codes (greenfield, existing-map, and read-boundary
exit zero; broken-map does not).
