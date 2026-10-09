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
- secret-shaped output → `secret-shaped-output`
- unapproved write → `unapproved_side_effect`
- conflicting alternatives → `unresolved_conflict`
- rejected Plan → preserved with `status=rejected` and
  `human_review=rejected`, and not eligible for handoff

The runner also records source and fixture path integrity, zero network/Git or
credential side effects, and a temporary removal simulation in which the
Composer experiment layer is removed while a historical artifact and a
non-Composer capability path remain available. It never executes capability
steps or performs a real deletion.
