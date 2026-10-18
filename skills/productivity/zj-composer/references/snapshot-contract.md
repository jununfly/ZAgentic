# Capability snapshot contract

`generate_snapshot.py` turns the read-only discovery view into an immutable
provenance artifact. It is a derived evidence surface, not a second catalog or
registry.

## Required fields

- `schema`: `zj-composer/catalog-snapshot/v1`
- `snapshot_id`: `catalog-v1-<source content digest>`
- `generated_at`: UTC timestamp for this artifact, formatted `YYYY-MM-DDThh:mm:ssZ`
- `source.content_digest`: SHA-256 over the sorted source-file manifest
- `source.files`: every discovered skill `SKILL.md` path, existence flag, byte
  size, and SHA-256
- `source.skills_root`: the absolute catalog root that was resolved
- `source.layout`: `installed-flat` or `monorepo-dev`
- `catalog`: the exact discovery output consumed from `discover_catalog`
- `metadata_warnings`: structured discovery and skill metadata warnings

## Discovery model (issue #177)

Discovery is deterministic and no longer hardcodes the ZAgentic bucket layout:

- The catalog root is resolved explicitly (`--root` / `ZAGENTIC_ROOT`) when
  provided, otherwise derived from the script's location. It is never assumed to
  be a fixed ancestor depth (`parents[N]`).
- Skills are enumerated generically: a flat install keeps packages directly
  under a `skills` directory (`<root>/<skill>/SKILL.md`); a monorepo checkout
  nests them under `<root>/skills/<bucket>/<skill>/SKILL.md`. The layout is
  detected, not assumed.
- Each skill declares its provenance in its SKILL.md frontmatter. A skill is a
  ZAgentic skill when `source: zagentic` is present. There is no central roster.
- The digest covers every discovered `SKILL.md` (relative to the catalog root). A
  missing input is retained in the manifest with `exists: false` so the
  provenance record remains honest.

## Honest failure

When the catalog root cannot be located, or contains no skill packages, discovery
reports `catalog_present: false` with a structured diagnostic instead of silently
returning an empty catalog. `generate_snapshot` refuses to write a snapshot in
that state and exits non-zero, so an Agent is never fed a "looks valid but empty"
capability index.

## Persistence and reuse

Snapshots are written to
`skills-outputs/zj-composer/catalog-snapshots/<snapshot_id>.json`. The generator
does not overwrite an existing matching snapshot; rerunning it reports the
existing immutable artifact. A conflicting file fails instead of silently
changing provenance.

`snapshot_id` is independent of `generated_at`, so the same catalog content maps
to the same identity even in a dirty or detached checkout. A changed catalog
produces a new digest and a new artifact.

Warnings remain attached to the snapshot. Missing or malformed metadata is never
replaced with invented capability semantics; downstream Plan selection or
validation decides whether a warning blocks approval.
