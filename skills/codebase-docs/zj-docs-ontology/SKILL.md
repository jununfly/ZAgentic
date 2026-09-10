---
name: zj-docs-ontology
description: "Human-invoked governance of one codebase's documentation system: discover, classify, propose safe migration, validate drift, and report lifecycle work."
disable-model-invocation: true
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
   `git mv` for an approved tracked move.
5. **Validate and report.** Run map, link, and authority-binding checks and
   `/zj-docs-architecture` for the architecture layer. One `authority-id` bound
   to two pages is a mechanical failure, not a signal: it exits non-zero and the
   Human settles it. Compose `/zj-domain-modeling`, `/zj-debrief`, and
   `/zj-neat-freak` only when the Human's governance request needs their
   specialist work. Report pending durable extraction and deletion proposals.

```sh
python3 skills/codebase-docs/zj-docs-ontology/scripts/docs_governance.py . --proposal
python3 skills/codebase-docs/zj-docs-ontology/scripts/docs_governance.py . --validate
```

Read [governance-contract.md](references/governance-contract.md) before a
proposal or confirmed execution. Read
[proposal-tool-contract.md](references/proposal-tool-contract.md) before
interpreting a report, changing the tool, or adding a fixture.

## Completion

Complete the pass when the Human can see the selected map, categories,
mechanical failures, Human-review signals, explicit mutation confirmations, and
any process material awaiting durable extraction or deletion approval. Authority
conflicts count as mechanical failures: a binding is a fact, so it exits
non-zero, while conflicting *normative claims* between pages stay a
Human-review signal because settling them needs judgment. Do not claim that a
lifecycle loop closed merely because a plan or issue ended.
