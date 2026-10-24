---
doc-kind: adr
authority: historical
status: accepted
---

# Composer authority and Plan contract

## Context

The pstack-claude comparison showed the value of connecting discovery, staged execution, acceptance, evidence, and review. Its host-specific router and runtime assumptions do not fit ZAgentic's existing skill ownership, Human authority, evidence protocol, and documentation governance. A product decision is needed before adding more skills or introducing orchestration.

## Decision

ZAgentic adopts a thin **Composer + Plan** product form.

- Composer is an intent-to-Plan capability that discovers available skills, explains candidate combinations, reports bounded suggestions, and emits explicit missing-capability lines when no reliable suggestion exists.
- Plan is a versioned, reviewable task contract generated from a template owned by the Composer skill.
- Existing skills and workflows own capability semantics and execution behavior.
- Existing evidence and decision protocols own provenance, verification facts, and Human decisions.
- Existing execution chains own approved execution and side effects.
- Documentation governance owns durable rules and authority pages.

The first validation slice is limited to external repository research and tool-combination design. It produces versioned Markdown Plans under `skills-outputs/`, requires Human review before execution, and has no automatic irreversible actions.

## Missing-capability protocol

When an existing skill covers the need, Composer proposes it with reasons and constraints. When a credible future or external capability is identifiable, Composer gives a bounded suggestion with source and fit caveats. When no reliable suggestion exists, Composer emits one line per gap:

```text
required skill：简短地描述缺失skill的形状
```

## Plan template ownership

The Composer skill owns the Plan template as a versioned resource. Every Plan records the template version. A template change requires an explicit version change and cannot silently change the meaning of an existing Plan.

## Consequences

- Stage-based workflow, acceptance contracts, evidence packages, and debrief records can be reused as method mechanisms.
- A global router, hooks, transcript/model-sheet state, host runtime state, and shipping glue remain outside the default product boundary.
- The PoC uses fixed fixtures, scenario oracles, contract checks, security hard gates, and removal regression. Manual-assembly timing and success rates are descriptive observations rather than causal acceptance baselines.
- A future thin orchestration layer requires a separate decision and evidence; it is not implied by this ADR.

## Evidence

The pstack investigation produced three evidence packages under
`skills-outputs/` (the agreed home for skill-produced artifacts, per
`AGENTS.md`): primary findings under `skills-outputs/zj-research/`, the
capability-fit decision record under
`skills-outputs/zj-open-source-capability-fit/`, and the technical research
report under `skills-outputs/zj-tech-research-report/`. Those three trees were
removed by the 2026-10-22 governance sweep that cleared `skills-outputs/` of
temporary session content, so the paths above no longer resolve — the supporting
material survives only in git history. The durable output of that investigation
is the product-form decision below, which is what this ADR records:

- [Composer and Plan product form](../designs/zj-composer-plan-product-form.md)
