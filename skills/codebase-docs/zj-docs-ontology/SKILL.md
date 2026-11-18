---
name: zj-docs-ontology
description: "Human-invoked governance of one codebase's documentation system: discover, classify, propose safe migration, validate drift, and report lifecycle work."
disable-model-invocation: true
source: zagentic

---

# Govern a Codebase Documentation System

Run one explicit governance pass. This is the Human-owned entry point for a
codebase's document map, long-lived authorities, process material, and evidence
boundaries. It is not a shared-knowledge publisher or an automatic closeout
handler.

## Workflow

1. **Discover, read-only.** Run the proposal tool. It follows an explicit root
   `docs-map:` pointer, then `docs/README.md`, then one compatible candidate.
   A conflict or greenfield repository stays a proposal until the Human confirms
   the selected map and minimal category set.
2. **Classify.** Separate long-lived documentation, process material, external
   references/runbooks, fixture documentation, and evidence surfaces. Treat an
   unfamiliar target-repository category as target-defined, not as an error.
3. **Propose governance.** List each proposed map addition, `git mv`, link
   repair, authority synthesis, and deletion candidate with its reason. Name
   the confirmation required for every mutation; do not write while proposing.
4. **Execute the confirmed scope.** Preserve meaning by default. Moves, rewrites,
   authority merges, and process deletion are separately named actions. Use
   `git mv` for an approved tracked move. A page leaving service retires first
   and tombstones while inbound links remain; deletion is the last stage, never
   a default.
5. **Validate and report.** Run map, link, and authority-binding checks and
   `/zj-docs-architecture` for the architecture layer. One `authority-id` bound
   to two pages is a mechanical failure, not a signal: it exits non-zero and the
   Human settles it. A green run means these checks were confirmed consistent
   on this content, not that the content is right — semantic correctness stays
   with review. Compose `/zj-domain-modeling`, `/zj-debrief`, and
   `/zj-neat-freak` only when the Human's governance request needs their
   specialist work. Report pending durable extraction and deletion proposals.

```sh
python3 skills/codebase-docs/zj-docs-ontology/scripts/docs_governance.py . --proposal
python3 skills/codebase-docs/zj-docs-ontology/scripts/docs_governance.py . --validate
```

A bare `--validate` (no `--topic`) is a shape-only check: the report emits
`EXEC_CHECKLIST_NOT_DECLARED` (exit zero) and states that a green run is not
evidence a full pass ran or that content is correct. It is a signal for a CI
rule or step-gated authorization to escalate — the tool cannot tell a shape-only
check from a skipped pass, and an executor that never calls `--validate` at all
is outside its observation boundary. Use a topic below for a full pass.

For a full governance pass, use a **pass topic** and an execution checklist.
The topic is lowercase-hyphen with no date/sha/version/status token (e.g.
`docs-redesign`). Emit the checklist from the read-only proposal, then run the
architecture validator and save its output at the declared Step 5 path:

```sh
python3 skills/codebase-docs/zj-docs-ontology/scripts/docs_governance.py . --proposal \
  --topic docs-redesign --emit-checklist
python3 skills/codebase-docs/zj-docs-architecture/scripts/validate_architecture_docs.py . \
  > tmp/skills-outputs/zj-docs-ontology/docs-redesign/architecture-validator.txt
python3 skills/codebase-docs/zj-docs-ontology/scripts/docs_governance.py . --validate \
  --topic docs-redesign
```

The checklist is emitted to `tmp/skills-outputs/zj-docs-ontology/<topic>/`
(gitignored, pass-scoped). Its `confirmation_id` is the tool-computed hash of
the confirmed proposal — never an agent-supplied "I confirmed" claim. Steps
marked done must be backed by an existing artifact; a missing one is
`EXEC_CHECKLIST_STEP_UNBACKED` (non-zero). Step 5's artifact path is declared
by the tool, so a `skipped` status still fires `EXEC_STEP5_ARTIFACT_MISSING`.
A fingerprint mismatch is a signal (`EXEC_STEP5_FINGERPRINT_MISMATCH`, exit
zero) — it never proves the architecture content is right.

`--arch-witness` / `--arch-fingerprint` remain as a compatibility fallback
for callers with no checklist; when `--topic` is supplied the checklist is the
sole witness source and CLI witness values are ignored. See
[proposal-tool-contract.md](references/proposal-tool-contract.md).

To turn a report into a merge gate in **any** target repository, pipe it into
the consumer-side gate. The tool emits facts; the repository decides which
signals block a merge:

```sh
python3 skills/codebase-docs/zj-docs-ontology/scripts/docs_governance.py . --validate \
  --topic docs-redesign | \
  python3 skills/codebase-docs/zj-docs-ontology/scripts/check_gate.py \
  --escalate EXEC_CHECKLIST_NOT_DECLARED
```

`check_gate.py` applies `references/gate-rules.json` (which travels with the
skill): ERRORs always gate, signals pass unless escalated, and never-gate
signals are rejected even if requested. See `references/ci-snippet.yml` for a
copyable workflow job — it must trigger unconditionally (no `paths:` on a
required check) and parse the JSON rather than trust the validator's exit code.
The skill never auto-installs workflows; each repository wires its own gate.

Read [governance-contract.md](references/governance-contract.md) before a
proposal or confirmed execution. Read
[proposal-tool-contract.md](references/proposal-tool-contract.md) before
interpreting a report, changing the tool, adding a fixture, or wiring a gate.
Read [kind-templates.md](references/kind-templates.md) when classifying a page
or deciding where a fact belongs, and
[doc-slop-checklist.md](references/doc-slop-checklist.md) when auditing page
health — both are audit material, neither adds a diagnostic to the tool.

## Portability boundary

This skill owns the **governance layer** of a documentation system: the
`doc-kind` vocabulary, `authority` levels, lifecycle categories, and the
`docMapBinds` 1:1 rule that drives `MAP_AUTHORITY_CONFLICT`. That contract is
fully contained here (this file, `references/`, and `scripts/docs_governance.py`),
so the skill installs and runs unchanged in any target repository.

A consuming repository may layer a **product-domain model** on top of this
governance layer (for example platform / bucket / skill / pipeline entities
specific to that repo). Such a model is *that repository's* concern and is
**not** shipped with this skill — it lives wherever that repo keeps its own
documentation ontologies, not inside the installed skill. The two layers share
one vocabulary, so there is no naming collision; this skill only ever owns the
governance layer.

## Completion

Complete the pass when the Human can see the selected map, categories,
mechanical failures, Human-review signals, explicit mutation confirmations, and
any process material awaiting durable extraction or deletion approval. Authority
conflicts count as mechanical failures: a binding is a fact, so it exits
non-zero, while conflicting *normative claims* between pages stay a
Human-review signal because settling them needs judgment. Do not claim that a
lifecycle loop closed merely because a plan or issue ended.
