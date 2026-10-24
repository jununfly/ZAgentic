---
doc-kind: adr
authority: historical
status: accepted
---

# Research report improvement: ratified scope expansion beyond the original alignment contract

> 注 (2026-09-09): 本 ADR 批准的 **runtime alias 例外已退役** —— `~/.codex/skills/zj-research-report/` 与 `~/.workbuddy/skills/zj-research-report/`（`~/.claude/skills/` 下另有一份陈旧副本）已全部删除，安装目录统一使用 canonical 名 `zj-tech-research-report`。决策本身不变，仅"保留 legacy 目录名"这一后果被后续操作取代；正文保留原文，同步更新见 `ZJ-CONTEXT.md` 的 Name-field coupling 条目。

The alignment contract in `ZAgenticOPN/docs/designs/agent-self-service-collaboration-experience-version-alignment.md` <!-- # docs-ref-allow: 跨仓库引用，不在本仓 docs/ 树内 --> (Q1) limited this experiment to the old `skills/engineering/zj-research-report/` source skill, its reference/verification files, and the single device runtime copy. The actual deliverable landed in commit `869fa1f` ("rearchitect research skills and add technical report gate"), which changed 49 files: it migrated sibling skills, added `zj-code-research`, rewrote governance/index/docs, and relocated outputs — a full research-skills rearchitecture, not an isolated edit.

**Decision:** We ratify `869fa1f` as the intentional, broader scope for this work item. The report skill's quality gate (`validate_technical_report.py`), benchmark exemplar (`technical-proposal-exemplar.md`), and recompile pipeline could not be delivered as the narrow set the contract imagined; they depend on the shared recursive `./skills/` discovery and the new `skills/research/` bucket layout that the rearchitecture established. This ADR is the "formal scope decision" the reviewer requested as the alternative to narrowing the change (narrowing is impossible without rewriting already-pushed history, which the project forbids).

**New canonical paths (supersede the old contract paths):**
- Source skill: `skills/research/zj-tech-research-report/` (canonical name `zj-tech-research-report`).
- Compiler: `skills/research/zj-research/`.
- Runtime copies: installed under the canonical name `zj-tech-research-report`. The legacy-named copies and the `ALIAS.md` alias mechanism were **retired on 2026-09-09** (see the header note); no runtime alias exists today.

**Consequences:** Future research-skill work follows the `skills/research/` layout and recursive discovery per `AGENTS.md`; the old `skills/engineering/zj-research-report/` path in the Q1 contract is obsolete. CI, triage rules (`zj-triage` A-ONLY), and the quality gate were updated to match.

## Change authority & evidence (OPN)

This ADR is the ZAgentic-side ratification; the OPN-side formal change to the active alignment Spec is recorded in `ZAgenticOPN/docs/designs/agent-self-service-collaboration-experience-version-alignment.md` <!-- # docs-ref-allow: 跨仓库引用，不在本仓 docs/ 树内 --> under **Q1 范围修订（经 OPN Work Item 追认）**. Authority chain:

- OPN Work Item `work-zj-research-report-improvement-20260820-canonical-scope` (scope `jununfly/ZAgentic/zj-research-report`), claimed by `workbuddy-01` / `device-a`.
- First reviewer `request_changes` (revision 7) accepted "补充正式 scope 决策" as the valid alternative to narrowing — OPN (reviewer = codex-01, acting for Human) sanctioned the ADR path.
- Second reviewer `request_changes` (revision 12) required formal OPN-side change evidence for the active alignment Spec; the Q1 范围修订 subsection in the OPN design doc is that evidence.
- The work item's claim → publish-result → submit → request_changes → re-claim → publish-result → submit cycle is the OPN-sanctioned scope-change mechanism; the alignment Spec is changed through that coordination record, not by a silent edit inside ZAgentic.

## Runtime alias (retired 2026-09-09)

At adoption time the install copies at `~/.codex/skills/zj-research-report/` and
`~/.workbuddy/skills/zj-research-report/` kept the legacy directory name while
SKILL.md `name:` stayed canonical `zj-tech-research-report`, each copy carrying an
`ALIAS.md`. That was a board-approved exception to the `ZJ-CONTEXT.md`
"Name-field coupling" invariant, applying only to runtime install copies and never
to the repo source skill. The exception is **no longer in force**: both
legacy-named copies were deleted on 2026-09-09 and installs now use the canonical
name everywhere, so the invariant holds without exception. This section records
why the exception once existed; do not read it as current practice.
