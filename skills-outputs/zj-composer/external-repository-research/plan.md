# Composer Plan

<!-- Composer template v1. Keep existing Plans pinned to their original version. -->

## Identity

- **plan_id:** `external-repository-research-v1-plan`
- **title:** Research the pinned pstack-claude repository
- **status:** `planned`
- **template_version:** `1`
- **generated_at:** 2026-10-09T16:00:00Z
- **composer_version:** `zj-composer/v1`
- **human_review:** `pending`

## Intent

- **goal:** Produce an evidence-backed assessment of the capability surfaces, reusable boundaries, and ownership model in the pinned pstack-claude repository.
- **scope:** Research https://github.com/michael-denyer/pstack-claude at commit 3b0bc62e13f507c426997ba472e3430dd3e4ef05 and synthesize findings for ZAgentic composition, including any adapter boundary.
- **constraints:** Use only fixed primary-source references, preserve commit provenance, keep unknowns explicit, and do not treat popularity as capability evidence.
- **desired_output:** A cited findings package, capability-fit decision record, and technical research report outline.
- **exclusions:** No repository changes, no capability installation, no production rollout, and no unpinned claims.
- **permission_boundary:** Read-only retrieval from fixed primary sources; no repository writes, Git publication, credentials, or irreversible actions.

## Capability composition

List steps in execution order. Each selected capability needs one reason tied to
an input or acceptance requirement.

### Step 1 — Map the pinned repository

- **skill_or_workflow:** `zj-code-research`
- **role:** Build a commit-scoped repository map and architecture study for the external repository.
- **reason:** It uses the fixed repository inputs to establish capability surfaces and pinned source paths required by the research questions.
- **inputs:** Fixed repository URL and commit revision from the fixture input.
- **outputs:** Repository map and architecture study with commit-scoped source references.
- **prerequisites:** The repository URL and revision are fixed in input.json.
- **dependencies:** none
- **excluded_alternatives:** Unpinned browsing or a feature list without source paths.

### Step 2 — Capture primary evidence

- **skill_or_workflow:** `zj-research`
- **role:** Capture cited primary-source findings and explicit unknowns from the pinned revision.
- **reason:** It provides the primary evidence and source traceability required for every non-trivial claim.
- **inputs:** Step 1 repository map, fixed research questions, and primary-source references.
- **outputs:** Sealed evidence ledger and cited findings file.
- **prerequisites:** Step 1 has produced a commit-scoped map and source paths.
- **dependencies:** Step 1
- **excluded_alternatives:** Narrative conclusions without Evidence IDs or revision pins.

### Step 3 — Evaluate capability fit

- **skill_or_workflow:** `zj-open-source-capability-fit`
- **role:** Evaluate the requested capabilities against the pinned repository using the R×O matrix.
- **reason:** It turns the evidence into a composable fit decision with ownership and adaptation boundaries.
- **inputs:** Step 2 sealed evidence ledger, capability requirements, and fixed repository revision.
- **outputs:** Versioned fit matrix and decision record with native, adapted, unknown, or unsupported findings.
- **prerequisites:** Step 2 has cited each material finding in its evidence ledger.
- **dependencies:** Step 2
- **excluded_alternatives:** Ad hoc adoption advice or a whole-repository recommendation without a fit matrix.

### Step 4 — Synthesize the research report

- **skill_or_workflow:** `zj-tech-research-report`
- **role:** Synthesize the evidence and fit decision into a bounded technical research report.
- **reason:** It provides synthesis that connects evidence to alternatives, ownership risks, validation gates, and a reviewable recommendation.
- **inputs:** Step 2 cited findings, Step 3 fit decision, and the original research questions.
- **outputs:** Technical research report outline with recommendation, risks, validation gates, and exit criteria.
- **prerequisites:** Steps 2 and 3 have passing provenance and fit gates.
- **dependencies:** Step 3
- **excluded_alternatives:** A report that silently upgrades unknown evidence into an adoption decision.

## Gaps and suggestions

No unresolved capability gaps.

## Human checkpoints

- **approval_point:** Human reviews the fixed research scope and Plan before handoff to the consuming research chain.
- **decisions_needed:** Human confirms the repository revision, research questions, and whether the resulting fit decision is sufficient for follow-up work.
- **rejection_path:** Preserve this Plan and record the reason; do not execute.
- **side_effect_authorization:** Human approval is required before any consuming chain action; the fixture permits only bounded local evidence artifacts.

## Evidence and provenance

- **skill_index_snapshot:** `catalog-v1-0bbd5fc19b5cde54b2fcd9a89e0a97dd0b9bd5ff98c64919cad5b96dfbd0c776`
- **catalog_revision_or_digest:** `0bbd5fc19b5cde54b2fcd9a89e0a97dd0b9bd5ff98c64919cad5b96dfbd0c776`
- **source_references:** selected=[zj-code-research -> skills/research/zj-code-research/SKILL.md | zj-research -> skills/research/zj-research/SKILL.md | zj-open-source-capability-fit -> skills/research/zj-open-source-capability-fit/SKILL.md | zj-tech-research-report -> skills/research/zj-tech-research-report/SKILL.md]; excluded=[Step 1 -> skills-outputs/zj-composer/external-repository-research/oracle.json | Step 2 -> skills-outputs/zj-composer/external-repository-research/oracle.json | Step 3 -> skills-outputs/zj-composer/external-repository-research/oracle.json | Step 4 -> skills-outputs/zj-composer/external-repository-research/oracle.json]; suggested=[none declared]; gap=[none declared]; external=https://github.com/michael-denyer/pstack-claude/commit/3b0bc62e13f507c426997ba472e3430dd3e4ef05
- **evidence_requirements:** Pin every repository claim to the fixed commit and cite a primary-source path or commit reference.
- **generated_assertions:** The four selected capabilities cover discovery, primary evidence, capability fit, and report synthesis in that order.
- **unknowns:** Pinned evidence may leave lifecycle or security behavior unverified; unknowns remain explicit until a primary source establishes them.

## Verification

- **step_checks:** Confirm each step has its declared source, reason, inputs, outputs, prerequisites, dependency, and excluded alternatives.
- **scenario_oracle:** The external-repository-research oracle checks fixed URL and revision, four-step order, evidence and fit reasons, provenance references, dependency direction, and forbidden authority expansion.
- **plan_acceptance:** `pending`

## Failure and rollback

- **failure_exits:** Stop if the pinned revision, primary source, evidence ledger, or fit matrix cannot be verified.
- **safe_stop:** Preserve the Plan and partial evidence, mark the missing evidence or unknown, and request Human review.
- **rollback:** Remove only derived local fixture outputs from the current run; preserve the frozen input, historical artifacts, and rejection reason.
- **undeclared_side_effect_response:** stop, preserve evidence, and escalate for Human review.

## Handoff

- **consuming_execution_chain:** Existing research evidence and report execution chain.
- **handoff_preconditions:** Human approval, complete provenance, passing Plan validation, and a passing fixture oracle.
- **authority_statement:** Composer proposes and documents; it has no execution authority.
