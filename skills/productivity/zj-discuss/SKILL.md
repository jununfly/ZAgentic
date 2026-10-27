---
name: zj-discuss
description: Run zj-discuss when the user faces a genuinely complex problem that flat chat cannot fully resolve, or points to an existing discussions/ (slug) directory to resume. It decomposes the problem into a master doc + independent sub-documents, runs role-based multi-agent discussion via a fixed+dynamic agenda, synthesizes, and hands off to zj-docs-ontology. For a single issue, use zj-discuss-view + zj-steelman directly instead.
argument-hint: "<complex problem description, or an existing discussions/ (slug) path to resume>"
source: zagentic

---

# zj-discuss

A **methodology**, not a single-turn chat. It turns a genuinely complex problem —
one that flat prompt-and-answer chat cannot resolve in full — into a **document
set** that becomes the complete solution. The set is preserved as in-progress
authority during solving, then disposed of via `zj-docs-ontology` after the
problem is solved.

> ⚠️ **Landing-guard 锁定纪律（不可下沉）**：本文件是被仓库根
> `tests/test_zj_discuss_*.py` landing guard 锁定的技能交付物。`研讨会议程（固定 F1–F5 + 动态）`
> 与 `Hard rules`（尤其硬规则 6「非降级阶梯」）**必须活在本 SKILL.md**，不得下沉到
> `REFERENCE.md` 或 `references/`。历史已两次回归（#153 → `12b0260`、`#167` `5e37d28`
> → #201/#202）：下沉后脚本层全绿、landing guard 红灯却无人触发。任何外移改动须先确认
> 目标块不在 landing guard 锁定清单内。行数指标（顶文件 ≤100 行）对此类方法论 skill
> 不可达——**纪律正确性优先于行数**。

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
   roles whose trigger signal the sub-problem hits). 重构后的子问题须过
   `references/process-roles.md` ① 的「问题重构闸门」（一事一议 / 独立可解 /
   成功判据可验证），不过则回到解构、不进入讨论。
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

每个子文档的讨论轮次受本文件「研讨会议程」约束：固定议程 F1–F5 是不可跳过的底线，动态议程决策函数（状态评估 → 决策 → 执行 → 再评估）驱动每轮下一步，并在本阶段各步骤间闭环执行。

For each sub-document, according to its **declared required role set**
(variable, chosen in the preparation phase — **not** hardcoded B/C/A, **not**
fixed to three agents):

1. `zj-discuss` generates **one launch pack per selected role** (主力AI is the
   integrator and writes its stance in-main, no pack). **Run the static generator**
   instead of hand-writing them:
   ```sh
   python3 <skill-dir>/scripts/launch_pack.py <sub-doc-path> \
           --out <项目根>/tmp/skills-outputs/zj-discuss/<sub-slug>
   ```
   （不传 `--out` 时默认落到 `<sub-doc 所在 git 仓库根>/tmp/skills-outputs/zj-discuss/<sub-slug>/`，
   符合 ADR 0010 的项目隔离区约定；`--out` 可覆盖。）
   It reads the sub-doc's own **declared required role set** and writes
   `<项目根>/tmp/skills-outputs/zj-discuss/<sub-slug>/<sub-slug>-launchpack-<role>.md` per role, each stamped with
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
   same-session multi-role, i.e. the collapsed isolation that hard rule 3 forbids
   (see 本文件「Hard rules」).
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
   not a goal. **收敛前须过 `references/process-roles.md` ② 的三道评审闸门
   （scope / 架构 / UX），不过不准标 `conclusion`。**

### Phase 3 — Synthesize & roll up (Q-D)

- **Incremental:** after each sub-doc's conclusion, update `MASTER.md`'s index
  status and append a sub-solution summary (link + 1–3 line essence +
  cross-cutting constraints).
- **Final:** when all sub-docs are concluded (or Human stops per convergence),
  run one final synthesis — rewrite `MASTER.md`'s "解决思路" as an integrated
  narrative. A SubAgent may draft it (low-risk); Human reviews. 终局合成后跑一次
  `references/process-roles.md` ③ 收尾复盘（对照 R4 度量注册表，沉淀进设计文档三件套，
  不引共享运行时）。

### Phase 4 — Disposition contract (Q2')

`MASTER.md` already carries the fixed `## 本文件夹的性质与处置契约` section.
When the whole problem is resolved, invoke `zj-docs-ontology` to classify the
set and, after Human confirmation, delete the folder.

## 方法论纪律（landing guard 锁定，必须活在 SKILL.md）

> ⚠️ 以下两块（研讨会议程 / Hard rules）是被仓库根 `tests/test_zj_discuss_*.py`
> landing guard 锁定的核心纪律，**必须**留在本文件，不得下沉到 `REFERENCE.md`
> 或 `references/`。历史已两次回归（#153 → `12b0260`、`#167` `5e37d28` → #201/#202）：
> 下沉后脚本层测试全绿、landing guard 红灯却无人触发。任何把它们外移的改动，必须先
> 确认目标块不在 landing guard 锁定清单内。`zj-write-a-skill` 的「顶文件 ≤100 行」
> 对此类方法论 skill 不可达——**纪律正确性优先于行数指标**。

### 研讨会议程（固定 + 动态）

讨论的质量由一套**固定议程**保证底线，由**动态议程**在最需要时加深覆盖。
两者组合的目标：主旨简单清晰、结果导向；同时让复杂问题被充分解构与讨论，
使生成的解决方案**完整、严谨、可操作**。

#### 固定议程（底线不变式，任何讨论都必须跑完）

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

#### 动态议程（自适应编排，依据讨论进程）

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

### Hard rules (Q-E — non-skippable)

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

   > **边界说明（meta-run 实证）：** `视角来源: 跨会话独立Agent` 是**自证式断言**，
   > 机器无法验证该视角是否真跨会话（同会话预演若误标即可骗过锚点判据）。收敛拍板表（见
   > `references/subdoc-template.md` 的 `## Human 对 Agent X 的拍板`）应记录每视角的**隔离方式**
   > （跨 provider / 同 provider 跨会话 / 同会话），使真实隔离层级可见，避免把同会话预演
   > 误计入有效覆盖。跨 provider 不可强制（仅推荐），故该标记属结构性信任边界，非已验证
   > 不变式——不要把它误读为「机器已确认隔离」。

### 结构性闸门（机械校验，不是自觉约定）

> 完整规则与「实现复用」说明见 `REFERENCE.md「结构性闸门」`；本文件只给锚点。

- `scripts/check_subdoc.py` 强制 5 项不变量：视角来源标注 / 预演标签 / 结论不变式 / 非降级锚点 / 观点块与证据闸门。
- 顺序契约：回填 `MASTER.md ## 文档索引` 与追加 `## 合成信号` 前，必须先跑 `check_subdoc.py` 且退出码 0；非 0 先修文档重跑，不得先回填。

> 结构性闸门的完整规则与「实现复用」说明见 `REFERENCE.md「结构性闸门」`；改任何方法论块都须同步校验 `references/role-matrix.md`、模板与脚本测试。



## References

- `REFERENCE.md` — 方法论参考：仅承载**未被 landing guard 锁定**的内容（结构性闸门等）；研讨会议程 / Hard rules 已上提至本 SKILL.md 作为锁定交付物。凡改这两处须同步校验 `references/role-matrix.md`、模板与脚本测试。
- `references/master-template.md` — MASTER.md skeleton (incl. disposition contract + 可选 voice-only digest 块).
- `references/subdoc-template.md` — per-sub-problem discussion doc skeleton (role-count-agnostic; 末尾含可选 voice-only digest 块).
- `references/role-matrix.md` — candidate role pool + recommendation heuristic + convergence rule (SSOT for role semantics).
- `references/role-methods/<key>.md` — per-role **gated method**（① Read 原文 ② 角色专属核查清单 ③ 强制输出结构 ④ 闸门）；每个视角角色一份，是角色语义的「牙齿」（design.md §10.4 项1）。
- `references/process-roles.md` — **过程角色**（非视角角色）的范式 adapt：`office-hours` 问题重构 / `plan-*` 评审闸门 / `retro` 收尾复盘，落主力Ai 编排层（design.md §10.4 项2）。
- `references/sibling-boundary.md` — sibling-skill invariants + external selective-reuse (C) boundary — sunk from SKILL.md.
- `scripts/launch_pack.py` — static per-role launch-pack generator (replaces manual briefing copying). 通用引擎委托给 `zj-doc-collab/scripts/launch_pack_core.py`；本文件保留 `PACK_TEMPLATE` / `PREP_TEMPLATE` / `zj-discuss-view --role` 执行命令等消费方内容。
- `scripts/check_subdoc.py` — structural gate enforcing the invariants (see `REFERENCE.md「结构性闸门」`). 通用闸机委托给 `zj-doc-collab/scripts/gate_core.py`；本文件保留 `VALID_STATUS` / `沉淀指令` 校验 / per-role N 闸门等领域层。
- `scripts/metrics.py` — R4 recomputable metrics registry (compression ratio etc.); read-only, prints JSON for a discussions/ folder or one sub-doc.
- `tests/` — regression guards for all scripts (`python3 <test-file>.py`).
- 产品 / 架构 / 设计文档（完整规格，长期维护）位于源仓库 `docs/designs/zj-discuss/`，**不随本 portable skill 安装**；本 skill 仅承载上方 references/ 与 scripts/ 中的可操作层。

## 兄弟技能集成（引用而非重做）

> 兄弟技能不变式（steelman / handoff / docs-ontology 治理红线）完整规范下沉到
> `references/sibling-boundary.md`，此处只保留锚点。

discuss 做**薄编排层**：兄弟技能已覆盖的能力一律调用、不在内重实现（引用而非重做）。
关键边界：

- **`zj-steelman`（防御式辩护）与 `zj-discuss-view`（协作式结构错位）不变式互斥** ——
  discuss-view 不得内置 defend 逻辑；「提案是否站得住」类子问题改调 `zj-steelman`。
- **`zj-handoff` 压缩契约 ⊇ discuss-briefing** —— 不重造压缩逻辑，仅追加角色立场两行头。
- **`zj-docs-ontology` 阶段 2 只吐指针** —— 分类 / 迁移 / 权威校验由其 Human 确认闭环完成，
  discuss 不得运行 `docs_governance.py`、不得决定最终分类。

详见 `references/sibling-boundary.md`。

## 外部能力集成边界（选择性复用）

> 全局决策 = **C（选择性复用）**：外部范式只作**结构借鉴**，
> `zj-discuss` 方法体系始终是自有主体。边界写进 SKILL 而不只写进 design 文档，
> 是为了防止「顺手引一个依赖」把方法所有权让渡出去。

| 外部能力 | 边界 | 为何这样划定 |
| --- | --- | --- |
| 跨 provider 评审（如外部 `/codex` 式范式） | **组件引用** —— 推荐更强隔离时使用；discuss 内不实现 provider 路由 | 引入路由即引入运行时，会把方法论变成编排器 |
| learnings / 经验持久化 | **薄层复用** —— 可借鉴其机制，但必须是可移除薄层 | 任何承载方法状态的适配层都等于拥有了主体 |
| 上游 digest（如 2KB digest） | **voice-only** —— 只覆盖表达语气，不覆盖方法体系 | 它不表达结构立场 / R×O，覆盖不到本方法的语义点 |

**否决项（不再复议）：** 会话编排运行时 / router / suite 化 —— 会让适配层拥有主体方法
状态，按决策模型重分类为 D。`scripts/launch_pack.py` 是这条红线的产物边界：它写文件，
不发起会话。
