---
doc-kind: adr
authority: historical
status: accepted
---
> 时点说明：本页为历史决策记录，所述数量、路径与状态陈述截至 2026-10-24；现行规则以 `AGENTS.md` 与 `docs/architecture/` 为准。

# Composer authority and Plan contract

## Context

Before adding skills or orchestration, a product decision was needed: the pstack comparison's router and runtime assumptions did not fit ZAgentic's ownership model. The problem statement belongs to [Composer and Plan product form](../designs/zj-composer-plan-product-form.md).

## Decision

ZAgentic adopts a thin **Composer + Plan** product form. Capability semantics, provenance, execution and durable rules stay owned by the existing skills, evidence protocols, execution chains and documentation governance. The complete boundary, input/output contract and ownership rules live in [Composer and Plan product form](../designs/zj-composer-plan-product-form.md) (`authority: primary`); this ADR keeps the verdict and its consequences.

The first validation slice required Human review before execution and had no automatic irreversible actions.

## Missing-capability protocol

Composer's three-case response (propose an existing skill, give a bounded suggestion, or report a gap) is defined in [Composer and Plan product form](../designs/zj-composer-plan-product-form.md). This ADR owns only the gap-line shape:

```text
required skill：简短地描述缺失skill的形状
```

## Plan template ownership

The versioned Plan template belongs to the Composer skill; its version-change rule is part of the [design page's contract](../designs/zj-composer-plan-product-form.md).

## Consequences

- Stage-based workflow, acceptance contracts, evidence packages, and debrief records can be reused as method mechanisms.
- A global router, host runtime state and shipping glue stay outside the product boundary.
- The PoC used fixed fixtures and contract checks; timing and success rates are descriptive observations, not causal acceptance baselines.
- A future thin orchestration layer requires a separate decision and evidence; it is not implied by this ADR.

## Evidence

The pstack investigation produced three evidence packages under `skills-outputs/`.
They were temporary session artifacts, removed by the 2026-10-22 governance sweep;
only git history retains them, so those paths no longer resolve. The durable output
of the investigation is the product-form decision this ADR records:

- [Composer and Plan product form](../designs/zj-composer-plan-product-form.md)
