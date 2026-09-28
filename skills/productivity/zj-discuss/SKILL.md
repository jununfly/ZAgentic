---
name: zj-discuss
description: Run zj-discuss when the user faces a genuinely complex problem that flat chat cannot fully resolve, or points to an existing discussions/<slug>/ to resume. It decomposes the problem into a master doc + independent sub-documents, runs role-based multi-agent discussion via a fixed+dynamic agenda, synthesizes, and hands off to zj-docs-ontology. For a single issue, use zj-discuss-view + zj-steelman directly instead.
argument-hint: "<complex problem description, or an existing discussions/<slug>/ path to resume>"
---

# zj-discuss

A **methodology**, not a single-turn chat. It turns a genuinely complex problem —
one that flat prompt-and-answer chat cannot resolve in full — into a **document
set** that becomes the complete solution. The set is preserved as in-progress
authority during solving, then disposed of via `zj-docs-ontology` after the
problem is solved.

## Mental model

```
complex problem
  └─ decompose (Human + lead AI, one issue at a time)
       ├─ one MASTER.md  : core problem + solution approach + doc index
       └─ N sub-documents: each = one independent sub-problem + its solution
            └─ each sub-doc resolved by independent multi-agent discussion
document set = complete solution (phase 1)
  └─ after solving → zj-docs-ontology deposits durable parts, then folder deleted (phase 2)
```

`zj-discuss` is the **lifecycle owner** of this set. Per-sub-document
independent discussion is handled by its companion `zj-discuss-view`
(parameterized by role), which is loaded in a *separate* Agent session.

> 角色定义以 `references/role-matrix.md` 为**唯一真源**——本文件只引用、不复述，避免
> 概念与其描述耦合漂移（SSOT 不变式）。凡涉及角色语义，一律指过去看 role-matrix。

## Two-phase lifecycle (critical — read before using)

- **Phase 1 — solving:** the folder `discussions/<slug>/` is retained as the
  problem's **process-authority basis before resolution** plus the in-progress
  complete solution. It is **NOT** a long-term document.
- **Phase 2 — after resolution:** invoke `zj-docs-ontology` to classify the
  set — durable content (decisions, constraints, conclusions) deposits into the
  project's long-term `docs/` authority pages; pure process noise becomes a
  deletion candidate. Only after **Human confirmation** is the folder deleted.

This resolves the tension between "keep the complete solution" (phase 1) and
"delete transient material" (policy's disposition discipline, phase 2).

## Workflow

### Phase 0 — Scope gate

Confirm this is a problem flat chat cannot handle. If it is a *single* issue,
use `zj-discuss-view` + `zj-steelman` directly; do not spin up the full set.

### Phase 1 — Decompose + prepare roles (Q-A, hybrid)

1. Dispatch a **SubAgent** (low-isolation is acceptable here) to draft a
   candidate decomposition: a master outline + a list of sub-documents. Each
   candidate sub-document has: one-line problem statement, independence
   rationale, success criteria, and **suggested roles** derived from
   `role-matrix.md`'s recommendation heuristic (base {B,C,A} + any optional
   roles whose trigger signal the sub-problem hits).
2. **Role selection (preparation phase — hard interaction):** present to Human —
   (a) **推荐参与角色**: each with a one-line intro + why recommended (which
   signal matched / why base); (b) **其他可选角色**: the rest of the pool, each
   with a one-line intro, for Human to add/remove. Human confirms/adjusts → the
   locked set becomes the **declared required set** (per discussion, or per
   sub-document). See `role-matrix.md`.
3. **Human + lead AI review and finalize** the decomposition + role sets. Lock them.
4. Create the folder `discussions/<self-explain-slug>/` — kebab-case,
   self-explanatory, **no** `discuss-` prefix (the parent dir already says it).
   Default base dir is the repo root; configurable.
5. Generate `MASTER.md` from `references/master-template.md` and each
   sub-document stub from `references/subdoc-template.md`. The stub's viewpoint
   blocks are generated **per the sub-doc's selected role set** — variable count,
   not hardcoded B/C/A.

### Phase 2 — Per-sub-document independent discussion (Q-C + Q-E)

每个子文档的讨论轮次受下方「## 研讨会议程（固定 + 动态）」约束：固定议程 F1–F5 是不可跳过的底线，动态议程决策函数（状态评估 → 决策 → 执行 → 再评估）驱动每轮下一步，并在本阶段各步骤间闭环执行。

For each sub-document, according to its **declared required role set**
(variable, chosen in the preparation phase — **not** hardcoded B/C/A, **not**
fixed to three agents):

1. `zj-discuss` generates **one launch pack per selected role** (主力AI is the
   integrator and writes its stance in-main, no pack). **Run the static generator**
   instead of hand-writing them:
   ```sh
   python3 <skill-dir>/scripts/launch_pack.py <sub-doc-path> \
           --out <讨论文件夹>/briefings
   ```
   It reads the sub-doc's own **declared required role set** and writes
   `<讨论文件夹>/briefings/<sub-slug>-launchpack-<role>.md` per role, each stamped with
   that role's stance + the **mandatory "Read `<sub-doc-path>` original" order** + the
   exact `zj-discuss-view --role X <sub-doc-path>` command.
   **Refuse if the sub-document is not on disk**; role keys outside the pool are
   refused unless `--allow-custom`. The generator is deliberately **inert** — it only
   reads/writes Markdown and never starts a session.
2. Human copies each launch pack into a **separate cross-session independent Agent**,
   loads `zj-discuss-view --role X <sub-doc-path>` (X = that role's key — any key
   from the pool, or a Human-defined custom key); that Agent writes its
   independent viewpoint into `## Agent viewpoints`. Convenience:
   `zj-discuss-view --all <sub-doc-path>` prints the sub-doc's full role set as
   ready-to-paste launch lines.
   **Formal decision — `--role X,Y` is closed, not pending.** One session carries
   exactly one viewpoint; accepting several role keys in one invocation would be
   same-session multi-role, i.e. the collapsed isolation that hard rule 3 forbids.
   `--all` is the sanctioned substitute: it emits *separate* launch lines, one
   independent session each. Do not re-open this as a usability gap.
3. Every viewpoint header marks
   `视角来源: 跨会话独立Agent` or `同会话SubAgent(低权重)`.
4. The `## Human 拍板` table records each round; Human may challenge on
   evidence; technical deviations are **never** silently swallowed.
5. **跨会话启动包（默认输出，非可选开关）：** at the end of Phase 2 output, append
   a one-click-paste block — one line per required role:
   `zj-discuss-view --role X <sub-doc-path>` (X ∈ 声明必需集), plus the sub-doc
   path and role name. The template **only** generates cross-session
   invocations; no "same-session suffices for isolation" shortcut wording (see
   hard rule 3). This drives the Human-copied-briefing error rate to near zero.
6. **Convergence:** once the **declared required set** is covered (every selected
   role has contributed an effective viewpoint), stop adding roles and synthesize
   a conclusion. The dynamic agenda may insert focused extra rounds for unresolved
   questions or sharp tensions, but never to pad headcount. More views is a means,
   not a goal.

### Phase 3 — Synthesize & roll up (Q-D)

- **Incremental:** after each sub-doc's conclusion, update `MASTER.md`'s index
  status and append a sub-solution summary (link + 1–3 line essence +
  cross-cutting constraints).
- **Final:** when all sub-docs are concluded (or Human stops per convergence),
  run one final synthesis — rewrite `MASTER.md`'s "解决思路" as an integrated
  narrative. A SubAgent may draft it (low-risk); Human reviews.

### Phase 4 — Disposition contract (Q2')

`MASTER.md` already carries the fixed `## 本文件夹的性质与处置契约` section.
When the whole problem is resolved, invoke `zj-docs-ontology` to classify the
set and, after Human confirmation, delete the folder.

## 研讨会议程（固定 + 动态）

> 完整议程规范（F1–F5 固定议程 + 状态模型 / 决策函数 / 护栏）下沉到
> `references/agenda.md`，此处只保留锚点与调用关系。

讨论的质量由一套**固定议程**保证底线（F1–F5，不可跳过），由**动态议程**在最需要时加深
覆盖（状态评估 → 决策 → 执行 → 再评估闭环）。两者组合的目标：主旨简单清晰、结果导向；
同时让复杂问题被充分解构与讨论，使生成的解决方案**完整、严谨、可操作**。

每子文档的讨论轮次受此议程约束：固定议程是底线骨架，动态议程只能在 F1–F5 内部重排 / 增轮，
不得删减任一阶段。详见 `references/agenda.md`。

## 结构性闸门（机械校验，不是自觉约定）

> 以下不变量由脚本强制，不依赖 Human 或 Agent 的自觉。跑完了、退出码为 0 才算数。

```sh
python3 <skill-dir>/scripts/check_subdoc.py <sub-doc-path> [...]
```

它校验四项：

1. **视角来源标注** —— 每个 `### 视角：X` 区块必须标注 `视角来源:`，取值只能是
   `跨会话独立Agent` 或 `同会话SubAgent(低权重)`。
2. **预演标签** —— 标注为 `同会话SubAgent(低权重)` 的视角必须同时挂 `⚠ 非独立` 标签。
3. **结论不变式** —— `## conclusion` 必须带 `状态协议` 字段，取值 ∈
   {`DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`, `NEEDS_CONTEXT`}；且结论**不得以**
   `依据` / `采纳` / `参考` 等依赖措辞把 `预演` / `同会话SubAgent` 产出当作权威依据
   （硬规则 3(b)）。判据是「同一行内出现预演词 + 依赖词」：单纯**提及**这条规则本身
   （如「conclusion 无预演字段」）不算违约——否则闸门会狼来了、被人关掉。

4. **非降级锚点（硬规则 6）** —— 标为 `DONE` / `DONE_WITH_CONCERNS` 的结论必须有至少
   一条 `跨会话独立Agent` 视角作为锚点；只有同会话预演（或零视角）却宣称已结论 =
   静默降级，拒。`BLOCKED` / `NEEDS_CONTEXT` 未作收敛声明，**不受此约束**——诚实报
   「没做完」不是降级，把它误判才是误伤（同样出于「狼来了的闸门会被关掉」的考虑）。

退出码：`0` 干净 · `1` 存在违约 · `2` 输入不可读。

`状态协议` 把「是否已结论」从含糊的 ✅ 变成可判定枚举，并显式区分
`BLOCKED`（做不了）与 `NEEDS_CONTEXT`（信息不够）——终局合成时不会被一枚 ✅ 蒙混过关。

## Hard rules (Q-E — non-skippable)

1. **Read the original.** Every Agent viewpoint must come from an Agent that
   `Read` the file itself. No human-relayed summaries of A's stance to B. No
   "please refute A" adversarial instructions — assign structurally different
   roles instead.
2. **Structurally different roles.** The independent viewpoints are the **declared
   required role set** selected in the preparation phase — any subset of the
   candidate pool in `role-matrix.md` (default base {B,C,A}), each a genuinely
   different structural stance, not the same lens relabeled. **主力AI is the
   integrator** (main session, low weight), not one of the isolated viewpoints.
   Role count and role→agent mapping are **NOT** hardcoded — they follow the
   selected set. Role semantics are defined *only* in `role-matrix.md` (SSOT).
3. **Anti-echo-chamber + load-bearing warning.** Same-session roleplay is *not*
   runtime isolation; mark it `同会话SubAgent(低权重)` and treat its weight
   accordingly. **This warning is load-bearing:** the SubAgent 预演 口子 may stay
   as a low-threshold onboarding entry, but (a) it must always be flagged
   "同会话 / 低权重 / 非隔离 / 不可作为结论依据"; (b) `conclusion` and cross-cutting
   constraints **must never cite SubAgent 预演 output as authority** — only
   cross-session B/C/A are trustworthy. If the 口子 is observed to systematically
   lure Humans into skipping real isolation, delete it.
4. **Convergence.** Cover the **declared required set** (whatever was selected in
   the preparation phase), then stop adding perspectives. The dynamic agenda may
   insert focused rounds for unresolved questions or sharp tensions, but never to
   pad headcount. More views is a means, not a goal.
5. **Conclusion must be executable.** A sub-doc conclusion must include
   deposition instructions (which PRD/ADR to change, which temp doc to delete)
   — otherwise it is not a closed loop.
6. **独立性阶梯不许向下 —— 非降级自检项 (never degrade down the ladder).**
   The ladder runs **跨 provider 独立会话 > 同 provider 跨会话 > 同会话 SubAgent 预演**.
   Same-session preview is an onboarding door and **a floor you pass through, never a
   place to settle**. Self-check before marking any sub-document concluded:
   - 跨 provider（不同 model / provider 的独立会话）—— **推荐**，非强制；
   - 同 provider 跨会话 —— 零降级基线，**最低可接受**；
   - 同会话 SubAgent 预演 —— 仅脚手架，**永不可作为结论依据**（见硬规则 3）。

   判据：标为 `DONE` / `DONE_WITH_CONCERNS` 的子文档**必须**有至少一条
   `跨会话独立Agent` 视角作为锚点。此条由结构性闸门第 4 项机械执行，不是倡议。

## References

- `references/master-template.md` — MASTER.md skeleton (incl. disposition contract + 可选 voice-only digest 块).
- `references/subdoc-template.md` — per-sub-problem discussion doc skeleton (role-count-agnostic; 末尾含可选 voice-only digest 块).
- `references/role-matrix.md` — candidate role pool + recommendation heuristic + convergence rule (SSOT for role semantics).
- `references/agenda.md` — full agenda spec (F1–F5 fixed + dynamic state-model / decision-fn) — sunk from SKILL.md.
- `references/sibling-boundary.md` — sibling-skill invariants + external selective-reuse (C) boundary — sunk from SKILL.md.
- `scripts/launch_pack.py` — static per-role launch-pack generator (replaces manual briefing copying).
- `scripts/check_subdoc.py` — structural gate enforcing the four invariants above.
- `scripts/metrics.py` — R4 recomputable metrics registry (compression ratio etc.); read-only, prints JSON for a discussions/ folder or one sub-doc.
- `tests/` — regression guards for all scripts (`python3 <test-file>.py`).
- `docs/designs/zj-discuss/` — product / architecture / design docs (full spec, durable).

## 兄弟技能集成与外部能力边界

> 完整边界规范（sibling 不变式互斥 / handoff 子集 / docs-ontology 治理红线 / 外部能力
> 选择性复用 C 决策）下沉到 `references/sibling-boundary.md`，此处只保留锚点。

discuss 做**薄编排层**：兄弟技能已覆盖的能力一律调用、不在内重实现（引用而非重做）。
关键边界：

- **`zj-steelman`（防御式辩护）与 `zj-discuss-view`（协作式结构错位）不变式互斥** ——
  discuss-view 不得内置 defend 逻辑；「提案是否站得住」类子问题改调 `zj-steelman`。
- **`zj-handoff` 压缩契约 ⊇ discuss-briefing** —— 不重造压缩逻辑，仅追加角色立场两行头。
- **`zj-docs-ontology` 阶段 2 只吐指针** —— 分类 / 迁移 / 权威校验由其 Human 确认闭环完成，
  discuss 不得运行 `docs_governance.py`、不得决定最终分类。
- **外部能力全局决策 = C（选择性复用）** —— 外部项目只作组件来源，方法体系始终是自有主体；
  否决会话编排运行时 / router / suite 化（会让适配层拥有主体状态）。

详见 `references/sibling-boundary.md`。
