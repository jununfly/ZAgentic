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

## Execution checklist and confirmation ledger (Rulings 2 + 4)

A full governance pass is keyed by an explicit **topic**:
`lowercase-hyphen`, no date / sha / version / status token. The tool never
guesses one. An invalid topic exits 2 with `INVALID_TOPIC`.

`--proposal --topic T --emit-checklist [--out DIR]` writes two files to
`tmp/skills-outputs/zj-docs-ontology/<topic>/` (default base; `--out`
overrides). This is the gitignored ADR 0010 output zone, not a target-repo
mutation — `mutations` stays empty.

- `proposal.json` — the confirmed proposal, which **is** the ledger (Ruling 2).
- `checklist.json` — step list plus one entry per named `proposed_actions`
  item, each carrying `status`, `artifact`, and `confirmation_id`.
  `confirmation_id = sha256` of the canonical proposal JSON, computed by the
  tool. There is no `--confirm` flag: that would be agent self-certification.

`--validate --topic T [--out DIR]` cross-checks the checklist against the
stored proposal:

| Condition | Diagnostic | Exit |
| --- | --- | --- |
| proposal.json or checklist.json missing | `CONFIRMATION_BASELINE_LOST` | zero (signal; checklist claims are not made) |
| checklist `confirmation_id` ≠ hash of stored proposal | `UNCONFIRMED_MUTATION` | non-zero |
| a step marked `done` has no existing artifact | `EXEC_CHECKLIST_STEP_UNBACKED` | non-zero |
| Step 5's tool-declared artifact missing (any status, incl. `skipped`) | `EXEC_STEP5_ARTIFACT_MISSING` | non-zero |
| Step 5 artifact exists, fingerprint differs | `EXEC_STEP5_FINGERPRINT_MISMATCH` | zero (signal) |

The Step 5 artifact path is declared by the tool, so a step cannot escape the
existence gate by leaving the path blank or marking the step `skipped` — that
is issue #264's actual case. A green witness means the declared file existed
and matched, never that the architecture content is right; that stays Human
review.

**Sole source.** When `--topic` is supplied the checklist is the only witness
source. `--arch-witness` / `--arch-fingerprint` are a compatibility fallback
for callers with no checklist and are ignored when a checklist is present; two
live declarations for one fact is the drift this design removes. `--proposal`
never runs the validation checks.

**Bare-validate disclosure (platform-layer C, tool slice).** `--validate`
without `--topic` cannot check a checklist, so the report emits
`EXEC_CHECKLIST_NOT_DECLARED` and sets `checklist.status` to `not-declared`.
The message states that a green run is not evidence a full pass ran or that
content is correct (issue #264's report-required item). Strength stays
**signal** (exit zero), by Ruling 3's invariant: the tool cannot distinguish a
shape-only check from a full pass that skipped its checklist, so escalating
would punish legitimate checks. Raising this signal to a gate is the job of a
**consumer** (CI rule / WorkBuddy step-gated authorization) — the tool supplies
the machine-readable fact, the platform decides. An executor that never calls
`--validate` at all is outside the tool's observation boundary; only the
platform layer can close that last step.

When `--topic` is supplied the disclosure is suppressed and
`CONFIRMATION_BASELINE_LOST` owns the "declared but missing" case — the two
codes are mutually exclusive by the report's branch structure. The hash records
*which* proposal was confirmed, not that the Human was truthful.

## Exit codes

ERROR codes are an explicit allowlist in `main()` (`ERROR_CODES`), with the
current `MAP_*` / `RETIRE_*` families kept alongside it until the four P0
rulings land in full. A new gate must be added by name or it will silently exit
zero — the fake-green pattern this allowlist exists to prevent. Signal codes
(`SIGNAL_CODES`) stay exit zero.

## Consumer-side gate (wildcard / any target repository)

The validator's exit code is a *tool* decision and covers only mechanical
ERRORs. Whether a signal blocks a merge is a *consumer* decision and belongs to
the target repository. Two shipped artifacts make that decision portable:

- `references/gate-rules.json` — the closed criteria: `error_codes` +
  `error_prefixes` always gate; `escalatable_signals` may be opted into;
  `never_gate_signals` (self-certification / permitted divergence) are rejected
  even if requested. This file is locked to the tool's allowlists by tests.
- `scripts/check_gate.py` — reads the report JSON on stdin, applies the rules,
  and exits 0 (pass) / 1 (fail) / 2 (bad input). Consumers opt in per signal:

```sh
python3 <skill>/scripts/docs_governance.py . --validate --topic T | \
  python3 <skill>/scripts/check_gate.py --escalate EXEC_CHECKLIST_NOT_DECLARED
```

`references/ci-snippet.yml` is a copyable workflow job showing the required
constraints: unconditional trigger (no `paths:` on a required check — #211),
parse the JSON rather than trust the validator's exit code, and pipe the report
into `check_gate.py`. The skill does **not** auto-install workflows — copying a
skill directory never touches `.github/` — so each target repository wires its
own gate deliberately. That is correct: branch protection is repository-owned.

Regression: `tests/test_gate.py` pins rule↔tool allowlist consistency, default
pass for signals, opt-in escalation, and rejection of never-gate escalations.

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
