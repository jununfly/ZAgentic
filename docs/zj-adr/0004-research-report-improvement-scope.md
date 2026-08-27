# Research report improvement: ratified scope expansion beyond the original alignment contract

The alignment contract in `ZAgenticOPN/docs/designs/agent-self-service-collaboration-experience-version-alignment.md` (Q1) limited this experiment to the old `skills/engineering/zj-research-report/` source skill, its reference/verification files, and the single device runtime copy. The actual deliverable landed in commit `869fa1f` ("rearchitect research skills and add technical report gate"), which changed 49 files: it migrated sibling skills, added `zj-code-research`, rewrote governance/index/docs, and relocated outputs — a full research-skills rearchitecture, not an isolated edit.

**Decision:** We ratify `869fa1f` as the intentional, broader scope for this work item. The report skill's quality gate (`validate_technical_report.py`), benchmark exemplar (`technical-proposal-exemplar.md`), and recompile pipeline could not be delivered as the narrow set the contract imagined; they depend on the shared recursive `./skills/` discovery and the new `skills/research/` bucket layout that the rearchitecture established. This ADR is the "formal scope decision" the reviewer requested as the alternative to narrowing the change (narrowing is impossible without rewriting already-pushed history, which the project forbids).

**New canonical paths (supersede the old contract paths):**
- Source skill: `skills/research/zj-tech-research-report/` (canonical name `zj-tech-research-report`).
- Compiler: `skills/research/zj-research/`.
- Runtime copies: `~/.codex/skills/zj-research-report/` and `~/.workbuddy/skills/zj-research-report/` (the latter kept as an intentional runtime alias — see the `ALIAS.md` in each copy — to preserve existing path references; SKILL.md keeps the canonical name).

**Consequences:** Future research-skill work follows the `skills/research/` layout and recursive discovery per `AGENTS.md`; the old `skills/engineering/zj-research-report/` path in the Q1 contract is obsolete. CI, triage rules (`zj-triage` A-ONLY), and the quality gate were updated to match in the same fix commit.

## Change authority & evidence (OPN)

This ADR is the ZAgentic-side ratification; the OPN-side formal change to the active alignment Spec is recorded in `ZAgenticOPN/docs/designs/agent-self-service-collaboration-experience-version-alignment.md` under **Q1 范围修订（经 OPN Work Item 追认）**. Authority chain:

- OPN Work Item `work-zj-research-report-improvement-20260820-canonical-scope` (scope `jununfly/ZAgentic/zj-research-report`), claimed by `workbuddy-01` / `device-a`.
- First reviewer `request_changes` (revision 7) accepted "补充正式 scope 决策" as the valid alternative to narrowing — OPN (reviewer = codex-01, acting for Human) sanctioned the ADR path.
- Second reviewer `request_changes` (revision 12) required formal OPN-side change evidence for the active alignment Spec; the Q1 范围修订 subsection in the OPN design doc is that evidence.
- The work item's claim → publish-result → submit → request_changes → re-claim → publish-result → submit cycle is the OPN-sanctioned scope-change mechanism; the alignment Spec is changed through that coordination record, not by a silent edit inside ZAgentic.

## Runtime alias (intentional, documented)

`~/.codex/skills/zj-research-report/` and `~/.workbuddy/skills/zj-research-report/` keep the legacy directory name while SKILL.md `name:` stays canonical `zj-tech-research-report`. Each copy carries an `ALIAS.md`; this is a board-approved exception to the `ZJ-CONTEXT.md` "Name-field coupling" invariant, recorded there and ratified above. It applies only to runtime install copies, never to the repo source skill.
