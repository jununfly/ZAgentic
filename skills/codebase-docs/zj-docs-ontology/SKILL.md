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

Read [governance-contract.md](references/governance-contract.md) before a
proposal or confirmed execution. Read
[proposal-tool-contract.md](references/proposal-tool-contract.md) before
interpreting a report, changing the tool, or adding a fixture. Read
[kind-templates.md](references/kind-templates.md) when classifying a page or
deciding where a fact belongs, and
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
