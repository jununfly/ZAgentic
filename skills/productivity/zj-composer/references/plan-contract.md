# Composer Plan v1 contract

This reference is the operational checklist for the bundled template. The
buildable specification and the Composer design remain the durable sources for
the product boundary:

- [buildable spec](../../../../docs/plans/zj-composer-buildable-spec.md)
- [product form](../../../../docs/designs/zj-composer-plan-product-form.md)
- [authority ADR](../../../../docs/zj-adr/0005-composer-authority-and-plan-contract.md)
- [snapshot contract](snapshot-contract.md)

## Required shape

Every emitted Plan has the nine headings in `plan-template.md` and an Identity
block containing `plan_id`, `status`, `template_version: 1`, `generated_at`,
Composer version, and Human review state.

Each capability step declares a selected skill or workflow, role, one reason,
inputs, outputs, prerequisites, dependencies, and excluded alternatives.

## Provenance

The Plan names the capability-index snapshot, its source revision or content
digest, generation time, and source references for selected, excluded,
suggested, or gap-related capabilities. Missing or stale metadata stays visible
as a warning or blocks approval when it changes a capability's meaning.
The snapshot's immutable file format and reuse rule are defined in
`snapshot-contract.md`.

## Gaps and states

Use one exact line per unresolved gap:

required skill：简短地描述缺失skill的形状

Do not number, merge, or rewrite that line with an ASCII colon. A gap never
creates or installs a skill. Composer owns only `planned`, `approved`,
`rejected`, `superseded`, and `cancelled`; the consuming execution chain owns
post-approval execution and verification states.

## Authority and side effects

The Plan is process material. Existing skills own their semantics, evidence
protocols own facts and provenance, execution chains own approved side effects,
and documentation governance owns durable rules. Composition may inspect and
write Plan evidence, but it must stop before unapproved writes, network calls,
Git publication, credentials, or irreversible actions.
