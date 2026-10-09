# Composer regression evidence

`regression-result.json` is produced by the local regression runner:

```bash
python skills/productivity/zj-composer/scripts/run_regressions.py
```

The runner evaluates both checked-in Composer fixtures, then applies these
mutations only to temporary Plan copies:

- malformed Unicode gap → `malformed_gap`
- missing prerequisite → `unresolved_prerequisite`
- stale snapshot digest → `provenance_digest_mismatch`
- authority bypass → `authority_bypass`
- second durable authority and automatic irreversible request → `authority_bypass`
- secret-shaped output → `secret-shaped-output`
- unapproved write → `unapproved_side_effect`
- conflicting alternatives → `unresolved_conflict`
- missing excluded/suggested/gap provenance → stable class-specific diagnostics
- rejected Plan → preserved with `status=rejected` and
  `human_review=rejected`, a concrete rejection reason, and no handoff eligibility

The runner actively attempts an out-of-allowlist write, credential read, network
connection, Git publication, and irreversible deletion. Every attempt must be
blocked and counted while actual effects remain zero. It also checks recursive
catalog metadata and snapshot digests, no-match stopping, stale-source review,
template-version pinning, and removal. The removal regression runs the original
catalog path before and after deleting the isolated Composer layer, compares the
outputs byte-for-byte by digest, and verifies that historical artifacts remain.
The real repository is read-only except for the allowlisted regression result.
