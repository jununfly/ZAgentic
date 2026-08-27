# Research report improvement: ratified scope expansion beyond the original alignment contract

The alignment contract in `ZAgenticOPN/docs/designs/agent-self-service-collaboration-experience-version-alignment.md` (Q1) limited this experiment to the old `skills/engineering/zj-research-report/` source skill, its reference/verification files, and the single device runtime copy. The actual deliverable landed in commit `869fa1f` ("rearchitect research skills and add technical report gate"), which changed 49 files: it migrated sibling skills, added `zj-code-research`, rewrote governance/index/docs, and relocated outputs — a full research-skills rearchitecture, not an isolated edit.

**Decision:** We ratify `869fa1f` as the intentional, broader scope for this work item. The report skill's quality gate (`validate_technical_report.py`), benchmark exemplar (`technical-proposal-exemplar.md`), and recompile pipeline could not be delivered as the narrow set the contract imagined; they depend on the shared recursive `./skills/` discovery and the new `skills/research/` bucket layout that the rearchitecture established. This ADR is the "formal scope decision" the reviewer requested as the alternative to narrowing the change (narrowing is impossible without rewriting already-pushed history, which the project forbids).

**New canonical paths (supersede the old contract paths):**
- Source skill: `skills/research/zj-tech-research-report/` (canonical name `zj-tech-research-report`).
- Compiler: `skills/research/zj-research/`.
- Runtime copies: `~/.codex/skills/zj-research-report/` and `~/.workbuddy/skills/zj-research-report/` (the latter kept as an intentional runtime alias — see the `ALIAS.md` in each copy — to preserve existing path references; SKILL.md keeps the canonical name).

**Consequences:** Future research-skill work follows the `skills/research/` layout and recursive discovery per `AGENTS.md`; the old `skills/engineering/zj-research-report/` path in the Q1 contract is obsolete. CI, triage rules (`zj-triage` A-ONLY), and the quality gate were updated to match in the same fix commit.
