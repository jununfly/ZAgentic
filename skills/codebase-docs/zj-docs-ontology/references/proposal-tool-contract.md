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

## Architecture witness (Step 5 composition)

`--validate --arch-witness PATH [--arch-fingerprint SHA256]` records a witness
for the Step 5 `/zj-docs-architecture` composition. The artifact is a
caller-supplied path to saved architecture-validator output; this tool never
imports or invokes that skill, and it hashes the file's bytes without opening,
parsing, or adding the path to `read_paths`. The report gains an
`architecture_witness` field with `status` (`not-declared` / `declared`),
`artifact`, `exists`, `fingerprint`, and `expected_fingerprint`.

The two checks keep different strengths (P0 ruling 3):

| Condition | Diagnostic | Exit |
| --- | --- | --- |
| Declared artifact does not exist | `EXEC_STEP5_ARTIFACT_MISSING` | non-zero (mechanical fact) |
| Artifact exists, fingerprint differs from expected | `EXEC_STEP5_FINGERPRINT_MISMATCH` | zero (in-pass self-certification) |

No declaration → `not-declared`, no diagnostic: the tool cannot tell a
full-governance pass from a shape-only check. Scope boundary: the declaration
is a caller-supplied CLI value, **not** yet P0 ruling 4's tool-derived checklist
(`tmp/skills-outputs/zj-docs-ontology/<topic>/`, whose topic convention is still
open). A caller that omits `--arch-witness` is therefore not mechanically
caught; that gap closes when the checklist lands. A green witness means the
declared file existed and matched, never that the architecture content is
correct — that stays Human review.

`--proposal` never runs the witness check; it is a `--validate` concern, like
the other mechanical diagnostics.

## Exit codes

ERROR codes are an explicit allowlist in `main()` (`ERROR_CODES`), with the
current `MAP_*` / `RETIRE_*` families kept alongside it until the four P0
rulings land in full. A new gate must be added by name or it will silently exit
zero — the fake-green pattern this allowlist exists to prevent. Signal codes
(`SIGNAL_CODES`) stay exit zero.

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
