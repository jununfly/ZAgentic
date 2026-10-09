# Capability snapshot contract

`generate_snapshot.py` turns the read-only discovery view into an immutable
provenance artifact. It is a derived evidence surface, not a second catalog or
registry.

## Required fields

- `schema`: `zj-composer/catalog-snapshot/v1`
- `snapshot_id`: `catalog-v1-<source content digest>`
- `generated_at`: UTC timestamp for this artifact
- `source.content_digest`: SHA-256 over the sorted source-file manifest
- `source.files`: every catalog input path, existence flag, byte size, and SHA-256
- `catalog`: the exact discovery output consumed from 1-3-1
- `metadata_warnings`: structured discovery, skill metadata, and declaration warnings

The digest covers the five bucket READMEs, the root README, `zj-guide`, the
install list, and every discovered public skill `SKILL.md`. A missing input is
retained in the manifest with `exists: false` so the provenance record remains
honest.

## Persistence and reuse

Snapshots are written to
`skills-outputs/zj-composer/catalog-snapshots/<snapshot_id>.json`. The generator
does not overwrite an existing matching snapshot; rerunning it reports the
existing immutable artifact. A conflicting file fails instead of silently
changing provenance.

`snapshot_id` is independent of `generated_at`, so the same catalog content
maps to the same identity even in a dirty or detached checkout. A changed
catalog produces a new digest and a new artifact.

Warnings remain attached to the snapshot. Missing or malformed metadata is
never replaced with invented capability semantics; downstream Plan selection or
validation decides whether a warning blocks approval.
