---
name: zj-discuss
description: Decompose a complex problem that flat chat cannot fully resolve into a master doc + independent sub-documents (one issue, one doc); select roles from a configurable pool with recommendations, run multi-agent independent discussion per sub-problem via a fixed+dynamic agenda, synthesize, and hand off to zj-docs-ontology for durable deposition. Solves the pain of thin chat failing to surface every facet of a hard problem.
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

讨论的质量由一套**固定议程**保证底线，由**动态议程**在最需要时加深覆盖。
两者组合的目标：主旨简单清晰、结果导向；同时让复杂问题被充分解构与讨论，
使生成的解决方案**完整、严谨、可操作**。

### 固定议程（底线不变式，任何讨论都必须跑完）

- **F1 — 定义核心问题**：MASTER 的「核心问题 + 成功判据」必须清晰、可验证；
  含糊则回到解构，不进入讨论。
- **F2 — 角色确认与分发**：准备阶段锁定角色集；为每个角色生成 briefing（启动包），
  **由 Human 复制到**跨会话独立 Agent（见 Phase 2 步骤 2 / 5，**非自动分发**）。
- **F3 — 各角色独立提出有效观点**：每个声明角色都须 `Read` 原文、写出结构错位的
  有效观点；出现回声 / 低质则按硬规则 3 处置。
- **F4 — Human 逐轮拍板**：每轮 `## Human 拍板` 留痕，允许凭证据 challenge，
  技术偏差不静默吞。
- **F5 — 合成共识并沉淀**：每个子文档 conclusion 含可执行沉淀指令；终局合成
  MASTER 解决思路；产出 = 完整文档组（解决方案）。

固定议程是**不可跳过**的骨架：动态议程只能在 F1–F5 内部重排 / 增轮，不得删减任一阶段。

### 动态议程（自适应编排，依据讨论进程）

动态议程以**状态评估 → 决策下一轮 → 执行 → 再评估**的闭环，在固定议程框架内
按需加深，而非固定顺序走完。它借鉴动态规划 / 自适应控制的「依据当前状态决定下一步」思想。

**状态模型（每子文档跟踪）：**
- 开放问题是否已解（scope 草案 Q1/Q2/… 的闭合度）
- 各声明角色是否已贡献**有效**观点（低质 / 回声标记）
- 是否存在**张力 / 分歧**（两角色结论冲突）
- 是否达成收敛（声明集全覆盖 + 可执行 conclusion）

**每轮决策函数（输出下一轮动作）：**
- 存在未解开放问题 → 派发针对该问题的聚焦轮（相关角色）。
- 两角色观点尖锐分歧（张力）→ 针对该分歧**重开真隔离会话对齐分歧**（相关角色各开独立 Agent 重新 `Read` 原文对齐），而非各说各话；**不引入候选池（`role-matrix.md`）之外的角色**。
- 某观点低质 / 回声 → 标记为 `同会话SubAgent(低权重)` 并要求**重开真隔离会话**。
- 覆盖不全 → 继续剩余角色。
- 已达收敛且 conclusion 可执行 → 触发 F5 合成，结束该子文档。

**护栏：** 动态议程永不可跳过 F1/F5 等固定阶段；它只为「加深覆盖」增轮或重排，
不稀释严谨性。结果导向：一旦收敛 + 可执行结论达成即停，不为多加视角而多加。

## 结构性闸门（机械校验，不是自觉约定）

> 以下不变量由脚本强制，不依赖 Human 或 Agent 的自觉。跑完了、退出码为 0 才算数。

```sh
python3 <skill-dir>/scripts/check_subdoc.py <sub-doc-path> [...]
```

它校验三项：

1. **视角来源标注** —— 每个 `### 视角：X` 区块必须标注 `视角来源:`，取值只能是
   `跨会话独立Agent` 或 `同会话SubAgent(低权重)`。
2. **预演标签** —— 标注为 `同会话SubAgent(低权重)` 的视角必须同时挂 `⚠ 非独立` 标签。
3. **结论不变式** —— `## conclusion` 必须带 `状态协议` 字段，取值 ∈
   {`DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`, `NEEDS_CONTEXT`}；且结论**不得以**
   `依据` / `采纳` / `参考` 等依赖措辞把 `预演` / `同会话SubAgent` 产出当作权威依据
   （硬规则 3(b)）。判据是「同一行内出现预演词 + 依赖词」：单纯**提及**这条规则本身
   （如「conclusion 无预演字段」）不算违约——否则闸门会狼来了、被人关掉。

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

## References

- `references/master-template.md` — MASTER.md skeleton (incl. disposition contract).
- `references/subdoc-template.md` — per-sub-problem discussion doc skeleton (role-count-agnostic).
- `references/role-matrix.md` — candidate role pool + recommendation heuristic + convergence rule (SSOT for role semantics).
- `scripts/launch_pack.py` — static per-role launch-pack generator (replaces manual briefing copying).
- `scripts/check_subdoc.py` — structural gate enforcing the three invariants above.
- `tests/` — regression guards for both scripts (`python3 <test-file>.py`).
- `docs/designs/zj-discuss/` — product / architecture / design docs (full spec, durable).

## Integration with sibling skills

> 边界原则：**引用而非重做。** discuss 做薄编排层，凡兄弟技能已覆盖的能力一律调用，
> 不在 discuss 内重实现（防逻辑漂移）。

- **`zj-steelman`（辩护）vs `zj-discuss-view`（结构错位）—— 不变式互斥，禁止共享实现。**
  discuss-view 的 role 视角 = **协作式结构错位**（丰富讨论：B 问排期/风险、C 问用户/价值、
  A 问边界/不变式，互补而非对抗）；zj-steelman = **防御式辩护**（检验提案可辩护性，判
  Strong/Adequate/Weak）。前者永不攻击、后者专司辩护。故 **discuss-view 不得内置 defend 逻辑**；
  对「提案是否站得住」类子问题，discuss 改调 `zj-steelman` 取其判定。

- **`zj-handoff`（压缩契约）⊇ `discuss-briefing`（受控切片）。** briefing := handoff 输出契约
  （引用不重复 + suggested-skills + 落 temp 目录）＋ `[role-stance 章]` ＋ `[强制 Read 原文令]`。
  discuss **不重造压缩逻辑**，handoff 契约为其基础子集；仅追加 discuss 专属两行头。

- **`zj-docs-ontology`（Human-owned 治理）— discuss 阶段 2 只吐指针，绝不自行分类/迁移。**
  discuss 阶段 2 仅产出 `<conclusion>` + `<suggested-category>` + `<pointer>`，随即移交
  `zj-docs-ontology`；**分类、提案迁移、链接/权威校验一律由 docs-ontology 在其 Human 确认闭环内
  完成。discuss 不得运行 docs_governance.py，不得决定最终分类。**

- `zj-grilling` — use beforehand to sharpen the core problem framing.

## 外部能力集成边界（选择性复用）

> 源自 gstack v1.2.0 复盘，全局决策 = **C（选择性复用）**：外部项目只作**组件来源**，
> `zj-discuss` 方法体系始终是自有主体。边界写进 SKILL 而不只写进 design 文档，
> 是为了防止「顺手引一个依赖」把方法所有权让渡出去。

| 外部能力 | 边界 | 为何这样划定 |
| --- | --- | --- |
| 跨 provider 评审（如 gstack `/codex` 范式） | **组件引用** —— 推荐更强隔离时使用；discuss 内不实现 provider 路由 | 引入路由即引入运行时，会把方法论变成编排器 |
| learnings / 经验持久化 | **薄层复用** —— 可借鉴其机制，但必须是可移除薄层 | 任何承载方法状态的适配层都等于拥有了主体 |
| 上游 digest（如 gstack 2KB digest） | **voice-only** —— 只覆盖表达语气，不覆盖方法体系 | 它不表达结构立场 / R×O，覆盖不到本方法的语义点 |

**否决项（不再复议）：** 会话编排运行时 / router / suite 化 —— 会让适配层拥有主体方法
状态，按决策模型重分类为 D。`scripts/launch_pack.py` 是这条红线的产物边界：它写文件，
不发起会话。
