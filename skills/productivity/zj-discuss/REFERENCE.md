# zj-discuss — 方法论参考（REFERENCE）

本文件是 `SKILL.md` 的**方法论主体**下沉层，承载篇幅大、属「引用而非复述」的参考内容：
研讨会议程、结构性闸门、Hard rules。改这里的任何一条，都要同步校验
`references/role-matrix.md`、`references/role-methods/`、模板与脚本测试，避免方法语义漂移。

`SKILL.md` 只保留概念、生命周期、Workflow 步骤与锚点；具体不变量与判定规则以本文件为准。

---

## 研讨会议程（固定 + 动态）

讨论的质量由一套**固定议程**保证底线，由**动态议程**在最需要时加深覆盖。
两者组合的目标：主旨简单清晰、结果导向；同时让复杂问题被充分解构与讨论，
使生成的解决方案**完整、严谨、可操作**。

### 固定议程（底线不变式，任何讨论都必须跑完）

- **F1 — 定义核心问题**：MASTER 的「核心问题 + 成功判据」必须清晰、可验证；
  含糊则回到解构，不进入讨论。
- **F2 — 角色确认与分发**：准备阶段锁定角色集；为每个角色生成 briefing（启动包），
  **由 Human 复制到**跨会话独立 Agent（见 SKILL.md Phase 2 步骤 2 / 5，**非自动分发**）。
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

---

## 结构性闸门（机械校验，不是自觉约定）

> 以下不变量由脚本强制，不依赖 Human 或 Agent 的自觉。跑完了、退出码为 0 才算数。

> **实现复用（2026-10-17）：** 结构性闸门的**通用机制**——Markdown 分段、视角来源标注
> 校验、非降级锚点校验、视角块切分与证据分类——已下沉到基础技能 **`zj-doc-collab`**
> （`skills/productivity/zj-doc-collab/scripts/gate_core.py`）。本技能的 `check_subdoc.py`
> 只保留领域层：状态枚举、`沉淀指令` 闭环校验、per-role N 闸门、`视角` 标题术语。
> `launch_pack.py` 同理复用 `zj-doc-collab/scripts/launch_pack_core.py`。两处均为**行为不变**
> 委托（96 项回归测试全绿），新增消费者无需改写本技能即可复用同一套机制。

```sh
python3 <skill-dir>/scripts/check_subdoc.py <sub-doc-path> [...]

它校验五项：

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

5. **观点块与证据闸门（gated method ④）** —— 每个跨会话独立视角须产出 **≥N**
   条带证据定位的观点块（N 见 `references/role-methods/<key>.md`，base N=3）。
   - 证据定位须带**行号或章节锚点**：`原文 L96` / `原文 <file> Lxx` /
     `原文 ## 章节` / `原文 §…`；**只给文件名不算** —— `原文 ADR 0008` 判无效，
     须写成 `原文 ADR 0008 L28`。
   - **未填的模板占位块计 0 条**：块内含 `<主题>` / `<...>` 类标记即判定为占位，
     复制 N 份空壳凑不出 N（否则模板会绕过模板自己的闸门）。
   - 失败时**逐块报因**（第几块是占位 / 第几块缺锚点 / 第几块没有引用），不笼统
     报「观点数不足」——数量不足与格式不达标的修法相反，报错会让人空转。

退出码：`0` 干净 · `1` 存在违约 · `2` 输入不可读。

**闸门与编排的顺序契约（不是 prose 建议）**：回填 `MASTER.md ## 文档索引` 与
追加 `## 合成信号` 之前，必须先跑一次 `check_subdoc.py` 且**退出码为 0**。
闸门存在 ≠ 闸门生效 —— 曾经出现过子文档 `exit=1` 却已被标 `DONE_WITH_CONCERNS`
并回填的情况，于是「非降级锚点」被静默降级。非 0 时先修文档重跑，不得先回填。

`状态协议` 把「是否已结论」从含糊的 ✅ 变成可判定枚举，并显式区分
`BLOCKED`（做不了）与 `NEEDS_CONTEXT`（信息不够）——终局合成时不会被一枚 ✅ 蒙混过关。

---

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

   > **边界说明（meta-run 实证）：** `视角来源: 跨会话独立Agent` 是**自证式断言**，
   > 机器无法验证该视角是否真跨会话（同会话预演若误标即可骗过锚点判据）。收敛拍板表（见
   > `references/subdoc-template.md` 的 `## Human 对 Agent X 的拍板`）应记录每视角的**隔离方式**
   > （跨 provider / 同 provider 跨会话 / 同会话），使真实隔离层级可见，避免把同会话预演
   > 误计入有效覆盖。跨 provider 不可强制（仅推荐），故该标记属结构性信任边界，非已验证
   > 不变式——不要把它误读为「机器已确认隔离」。
