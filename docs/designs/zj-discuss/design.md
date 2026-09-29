# zj-discuss — 设计文档（Design / 完整规格）

> 本文件是 `zj-discuss` / `zj-discuss-view` 的**权威详细规格**，沉淀自一段长对话
> （立项 grill → 共识 → 落 skill → 自举验证 → 合并 → 阶段 2 处置 → 开源范式复盘/决策模型复盘
> → 本轮 4 项追加改进）。目的是**避免对话进程丢失完整 context**。
> 产品定义见 `product.md`，组件与生命周期见 `architecture.md`。
> 角色语义唯一真源：`references/role-matrix.md`。

---

## 0. 决策模型与证据来源（复盘基准）

- **决策模型**：`docs/agreements/open-source-capability-fit-decision-model.md`（本仓库 SSOT）。定义 `R × O` 证据矩阵 →
  有效拟合度（功能覆盖×语义匹配×可组合性）→ 总所有权成本 E →
  决策分类 `A`（直接采用）/ `B`（扩展采用，细分 B1/B2/B3）/ `C`（选择性复用）/ `D`（继续搜索）；
  默认优先级 `A > B1 > B2 > C > B3`（`D` 为搜索循环回环态，非终态否决；见 §2 待核对偏离）。
- **可迁移模式（范式级借鉴，无 vendored 副本）**：抽取自开源「角色 = 带闸门的过程」范式，
  1. 跨 provider 异构独立性（`/codex` 外部评审 = 不同模型，权重高于同 provider 跨会话）
  2. user-sovereignty「呈现而非断言」（输出多视角与选项，不替 Human 下定论）
  3. Completion Status 协议（DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT）
  4. suite 协同 + learnings 持久化（非孤立 skill）
  5. ACP 程序化派生独立会话（零手工拷贝）
  6. router + preamble 统一注入
  7. reuse ladder / 2KB digest（零安装注入 ethos/voice）
  8. compression 度量（逻辑行/提交 → 3x–100x 压缩比）
  9. Boil the Ocean / completeness is cheap（完整实现近零成本 → 完整性门廉价）
  10. 引导式安装 + Quick start

---

## 1. 起源共识（grill 阶段 L0–L10）

| 层 | 结论 |
| --- | --- |
| L0 范围 | `discuss` = 复杂问题分解 + 每子文档独立多视角讨论 + 合成 + 末段沉淀交接；政策仅作每子文档讨论层参考 |
| L1 留存 | 两阶段生命周期：求解期保留 / 求解后 zj-docs-ontology 沉淀删文件夹 |
| L2 结构 | 仓库根 `discussions/<self-explain-slug>/`（无前缀）；MASTER + N 子文档；master 末尾固定「处置契约」段 |
| L3 执行纪律 | 分层：高利害跨会话 Agent（真隔离）/ 辅助 SubAgent（低隔离） |
| L4 分解机制 | 混合：SubAgent 起草候选分解 + Human 拍板 |
| L5 每子文档讨论 | 单 `discuss` + 单 `discuss-view` companion（role 参数化） |
| L6 合成回卷 | 增量（每子文档 conclusion → 更新 MASTER）+ 终局（重写解决思路） |
| L7 硬规则编码 | Read 原文 + 结构角色 + 防回声 + 收敛即停 + 结论须可执行沉淀指令 |
| L8 落点/命名 | 两 skill 落 `skills/productivity/`：`zj-discuss` + `zj-discuss-view` |
| L9 角色矩阵 | 4 角色（主力Ai/B/C/A）+ 收敛规则（已演进，见 §3） |
| L10 产物 | SKILL.md ×2 + references（master/subdoc/role-matrix 模板）+ README 两条 |

---

## 2. 开源范式 + 决策模型复盘：6 项待回写改进（分类 C；可迁移部分经 §10 重评为 B1，已 RATIFIED）

> 来源：用方法论自举讨论「如何深度改进 zj-discuss」的结论。分类 = C（选择性复用），
> 即外部范式作结构借鉴、zj-discuss 方法体系为自有主体；否决运行时编排器/suite-化
> （触发约束 1 → D，且适配层会拥有主体状态）。
>
> **C→B1 重评已 RATIFIED（见 §10）**：开源「方法 / 范式」可迁移部分（跨 provider
> 独立评审、闸门+状态纪律、learnings/retro 回路）经决策模型重评为 **B1**（范式级 ingest
> + adapt，不引外部运行时）；**suite / 运行时 / router 维持 D 红线不变**，digest 维持 C。
> 下表「判定」列已同步重评；意图-实际矛盾勘误见 §10.1。

| # | 改进 | 对应范式借鉴 | 状态 |
| --- | --- | --- | --- |
| R1 | `zj-discuss-view --all`（默认 {B,C,A}）+ 单角色 `--role X`（候选池任一 key 或自定义）；多角色由 `--all` 一次性打印启动包 | 一键触发 vs 手动 | 已回写（`--all` + 单角色 `--role`；见 §3.2 / architecture §1）。**`--role X,Y` 逗号语法已正式关闭**——单会话多角色即违反隔离，理由写入 SKILL.md Phase 2 步骤 2 |
| R2 | 静态 launch-pack 生成器（替代手工拷贝，不建运行时） | ACP 程序化派生 | 已回写 —— `scripts/launch_pack.py`（读声明必需集 → 每角色一份 `<slug>-launchpack-<role>.md`）；回归守卫 `tests/test_launch_pack.py`，其中 `NoRuntimeInvariant` 机械禁止其退化为运行时 |
| R3 | subdoc-template 增状态协议字段 + 预演结构性闸门（conclusion 无预演字段）+ 预演可见标签 | Completion Status 协议 | 已回写 —— `subdoc-template.md` 增 `状态协议`（DONE/DONE_WITH_CONCERNS/BLOCKED/NEEDS_CONTEXT）与 `⚠ 非独立` 标签、conclusion 禁引预演；**机械闸门** `scripts/check_subdoc.py`（退出码 0/1/2），守卫 `tests/test_check_subdoc.py` |
| R4 | 轻量可重算度量注册表（单一 schema，被 sub-01/02 同构引用） | compression 度量 | 已定义 schema（见 §9，未激活，待 PoC） |
| R5 | 集成边界文本：跨 provider 评审=组件引用、learnings=薄层复用、digest=voice-only | suite/reuse ladder | 已回写 —— **按处方落点进 `SKILL.md`「外部能力集成边界（选择性复用）」**（此前仅存于 §8 导致 SKILL 侧零命中），完整论证仍见 §8 |
| R6 | ZJ-CONTEXT.md 领域词注册 | — | 已回写（ZJ-CONTEXT.md `## Discussion methodology`） |
| R7 | 独立性阶梯「非降级自检项」成为 SKILL 硬规则 + 机械闸门 | 开源跨 provider 范式 | 已回写 —— SKILL.md 硬规则 6 + `check_subdoc.py` 第 4 项检查。注：本项属**处方第 4 条的子条款**，未被 R3/R4 覆盖；按「六条」计数时会漏判，核账到子条款才暴露 |

### 决策记录（决策模型要求项）

> 本小节自 discussions 过程文件夹抽取而来，**在阶段 2 删除该文件夹之前**完成沉淀。
> 缺了它的后果：后人无法在上游变更时重新评估分类，只能盲信结论。

**候选项目及固定版本 O**：开源「角色 = 带闸门的过程」范式参考实现 **v1.2.0**。能力清单：
O-u1 ACP 程序化派生、O-u2 router+preamble、O-r1 跨 provider 外部评审（`/codex`）、
O-r2 Completion Status、O-f1 compression 度量、O-c1 suite 协同、O-c2 2KB digest、
O-c3 跨 provider 选择性复用范式。

**R × O 证据矩阵（全局收敛）** — *判定列已按 §10.3 重评（C→B1 可迁移部分，D 红线维持）*

| R | 命中的开源候选 O | 判定 | 约束来源 |
| --- | --- | --- | --- |
| R-u1 派发自动化 | O-u1 ACP 派生 | C 复用（产物形状 → 静态生成器，维持） | 不引运行时，约束 1 |
| R-u2 角色零认知 | O-u2 router 思路 | **D（维持）** | router 即运行时，红线不变（§10.3） |
| R-r1 独立性升级 | O-r1 `/codex` | **B1（重评）** | 范式级 ingest 为验证/过程角色，不引 base |
| R-r2 防回声室 | O-r2 状态协议 | **B1（重评）** | 深化为每角色 gated method（§10.4 项1） |
| R-f1 可度量价值 | O-f1 compression | **B1（重评）** | learnings/retro 回路 + R4 度量（§10.4 项2） |
| R-c1 集成边界 | O-c1 suite | **D（维持）** | suite 化会拥有主体状态，否决 |
| R-c2 总所有权成本 | O-c2 digest | C 复用（voice-only，维持） | 不覆盖方法体系 |

**自有责任 E 与成本估计**：digest 注入 ≈0.5 人日；`/codex` 跨 provider 评审 ≈3–5 人日；
launch-pack 生成器 ≈1–2 人日；状态协议 / 度量注册表 ≈1 人日；learnings 复用 ≈1 人日。
**总 E ≈ 7–10 人日**，全部为可移除薄层，无运行时 / 基座 ownership。
对照：自建 suite ≈2–4 周 + 长期运维 → D，已被红线排除。

**采用理由**：外部范式仅作结构借鉴，zj-discuss 方法体系（role-matrix / briefing / R×O）
为自有主体，无逻辑漂移；E 可控、可退。

**主要风险**：① 语义兼容未知（digest / learnings 注入不破坏 zj 子文档结构）→ 最小 PoC 验证；
② 跨 provider 派生依赖 Human 手动开启非主力 provider 会话，harness 无一键能力 → 不阻断（手动零成本）。

**退出路径**：任一 C 组件失效可独立替换，无 suite 级锁定；若该开源项目未来提供非破坏性的
外部方法体系接入不变式，可重评为 B1。

**重新评估触发**：① 该开源项目大版本变更 suite 接入不变式；② WorkBuddy harness 原生支持
spawn 不同 provider 的独立会话（届时 R-u1 / R-r1 的 C 复用形态可升级）。

### 2.1 示例决策记录（B1 重评，可复核）

> 按 `docs/agreements/open-source-capability-fit-decision-model.md` 的「决策记录要求」字段，
> 落一条最小可复核示例，证明 B1 重评不是拍脑袋。第三方 Agent 凭此即可复核分类依据。
> 仅示范一项（O-r2 状态协议 / 闸门纪律），其余 B1 项（R-r1、R-f1）同构。

- **目标需求与关键能力**：复杂讨论的「是否已收敛 / 是否有效」须可机械判定（状态协议枚举 + 非降级锚点）。
- **候选项目及固定版本**：开源「Completion Status 协议」参考实现 **v1.2.0**（R-r2 命中的 O-r2）。
- **R × O 证据矩阵（本项）**：
  | R | 命中 O | 证据 | 原判定 | 重评 |
  | --- | --- | --- | --- | --- |
  | R-r2 防回声室 | O-r2 状态协议 | 借鉴的状态枚举 DONE/DONE_WITH_CONCERNS/BLOCKED/NEEDS_CONTEXT | C | **B1** |
- **选定组合 C 与缺口 G**：C = 状态枚举 + 闸门结构；G = 0（无需引外部文件/运行时）。
- **自有责任 E 及成本**：≈0.5 人日（把枚举下沉为 `check_subdoc.py` 闸门 + 每角色 gated method）；可移除薄层。
- **PoC 结论**：`check_subdoc.py` 已机械执行状态协议 + 非降级锚点（见 §8 / SKILL.md 结构性闸门），退出码 0 即有效。
- **最终分类**：**B1**（通过范式级 ingest，不维护 fork、不引运行时）。
- **采用理由 / 主要风险 / 退出路径 / 重评触发**：理由 = 与 zj-discuss 独立性阶梯语义高度匹配；风险 = 闸门过严致角色产出萎缩（§10.6 R1，阈值 PoC 校准）；退出 = 任一闸门失效可独立退回纯 C 引用；重评触发 = 同 §2「重新评估触发」。

> **范式级勘误（2026-09-28 ratified）**：本节 §2 的「分类 C」针对 R1–R7 六条具体改进
> （已落地），维持有效。但 §0 立项意图（ingest 外部成熟角色实现）与角色实际落地
> （thin prompt persona）的矛盾，已在 **§10** 勘误并将「角色实现范式」重评为 **B1**
> （范式级 ingest + adapt）。二者不冲突：R1–R7 = C 级薄层集成；角色实现范式 = B1 级
> 范式 ingest。维度不同，勿混读。

---

## 3. 本轮追加的 4 项改进（已实现于技能文件）

### 3.1 角色候选池 + 准备阶段推荐（改进 1）

- **候选池扩容**：base {B,C,A} 之外，新增 10 个可选角色 T/S/O/D/L/F/U/R/P/E，
  每个带 key / 名称 / 结构立场 / 差异锚点 / 一句话简介 / 推荐触发信号
  （完整定义见 `references/role-matrix.md`）。
- **准备阶段交互**（`zj-discuss` SKILL.md Phase 1 步骤 2）：
  - 向 Human 呈现「**推荐参与角色**」：每个角色带一句话简介 + 推荐理由（命中信号 / 为何 base）。
  - 再呈现「**其他可选角色**」：候选池未推荐者，每个带一句话简介，支持 Human 增删。
  - Human 确认后锁定为**声明必需集**，驱动收敛。
- **推荐启发式**：base 永远推荐；子问题命中信号（验收标准→T、权限→S、部署→O、
  数据→D、协议→L、预算→F、交互→U、理论→R、协作→P、伦理→E）则追加。

### 3.2 Phase 2 不写死 Agent 个数与角色映射（改进 2）

- 移除「B/C/A 三块」硬编码：子文档视角区块按**声明必需集**动态生成
  （`subdoc-template.md` 改为模式示例 + 生成说明）。
- `zj-discuss-view --role X` 的 X 可为候选池任一 key 或 Human 自定义 key
  （`zj-discuss-view/SKILL.md` argument-hint 与 workflow 已更新）。
- 硬规则 2/4 改为引用「声明必需集」，不再写死 B/C/A。

### 3.3 固定议程 + 动态议程（改进 3）

- **固定议程 F1–F5**（底线不变式，任何讨论必跑）：定义核心问题 / 角色确认分发 /
  各角色独立有效观点 / Human 逐轮拍板 / 合成共识沉淀。**不可跳过**。
- **动态议程**（自适应编排）：状态模型（开放问题闭合度 / 观点有效性 / 张力 / 收敛）
  → 每轮决策函数（聚焦轮 / 协调轮 / 重开真隔离会话 / 继续剩余角色 / 触发合成）。
  借鉴动态规划 / 自适应控制「依状态决定下一步」思想；护栏：只加深覆盖、不删固定阶段、
  不为凑数加视角。
- 落地位置：`zj-discuss` SKILL.md 新增「## 研讨会议程（固定 + 动态）」节。

### 3.4 需求文档化（改进 4）

- 本文件 + `product.md` + `architecture.md` 三件套，将「上面所有对话中的需求」
  固化为长期权威页，避免对话进程丢失 context。
- 在 `docs/README.md` 的 Primary design authorities 注册 `design.zj-discuss-*`。

---

## 4. 角色池完整定义（SSOT 摘要）

> 详见 `references/role-matrix.md`。此处为速查。

**编排者（非独立视角）**：主力AI — 产品实用主义 + 架构整合，主会话编排大脑，低权重（非隔离）。

**独立结构视角候选池**：

| key | 角色 | 默认 | 一句话简介 |
| --- | --- | --- | --- |
| B | 技术经理 | ✅ | 把方案从"能说"逼到"能做"，专问落地与代价 |
| C | 产品专家 | ✅ | 站在使用者与生态位置，问"凭什么用、值不值" |
| A | 架构师 | ✅ | 守护长期一致性与边界，专问"以后会不会炸" |
| T | 测试/质量 | ⚪ | 把"觉得对"变成"能证明对"，专问验证与质量 |
| S | 安全/威胁建模 | ⚪ | 站在攻击者视角，专问"哪里会被打穿" |
| O | 运维/SRE | ⚪ | 站在凌晨被叫醒的人视角，专问"上线后怎么死" |
| D | 数据/数据建模 | ⚪ | 站在数据生命周期视角，专问"数据怎么存怎么错" |
| L | 法律/合规 | ⚪ | 站在合规与风险视角，专问"会不会违法/违约" |
| F | 财务/成本 | ⚪ | 站在花钱的人视角，专问"值不值这个价" |
| U | 用户研究/UX | ⚪ | 站在真实使用现场，专问"人用起来顺不顺" |
| R | 学术/研究严谨 | ⚪ | 站在严谨方法视角，专问"论证站不站得住" |
| P | 流程/组织协作 | ⚪ | 站在"让事发生"的推手视角，专问"谁来做、怎么推" |
| E | 伦理/社会影响 | ⚪ | 站在社会与受影响者视角，专问"长期代价与公平" |

---

## 5. 硬规则（不可跳过）

1. **Read 原文**：每个视角须来自 `Read` 文件本身的 Agent；禁止转述口径；禁止「请反驳 A」对抗。
2. **结构错位角色**：独立视角 = 声明必需集（候选池任意子集，默认 base），每角色真结构差异；主力AI 是整合者，非隔离。
3. **防回声 + 承重警告**：同会话角色扮演 ≠ 运行期隔离；SubAgent 预演须标「同会话/低权重/非隔离/不可作结论依据」，conclusion 永不可引用预演。
4. **收敛**：覆盖声明必需集即停；动态议程可增聚焦轮但不凑数。
5. **结论须可执行**：子文档 conclusion 须含沉淀指令（改哪些文档 / 删哪些脚手架），否则不闭环。

---

## 6. 模板契约

- `master-template.md`：核心问题 + 解决思路 + 文档索引 + 跨子文档约束 + 处置契约段。
- `subdoc-template.md`：上下文 + 待讨论问题 + **按声明集动态生成的视角区块** +
  主力AI 整合立场 + briefings 节 + 拍板表 + conclusion（含沉淀指令）。
- `role-matrix.md`：候选池 + 推荐启发式 + 收敛规则（角色语义 SSOT）。

---

## 7. 开放项 / Backlog

- [x] R1–R7 七条开源派生修订全部落地：R1/R2/R3/R5/R6/R7 已回写（见 §2 + §8）；
  **R4 已激活**（`scripts/metrics.py` + `tests/test_metrics.py`，§9）。
- [x] 语义兼容未知项（**独立于 R4**，§8 关联）：**最小 PoC 已通过**——digest 注入
  不破坏子文档 / MASTER 解析。结论见 §8「digest 注入 PoC」段：闸门与度量对 digest
  区块惰性，且 `split_sections` 已围栏感知（digest 围栏内嵌 `### 视角` 回声也不误判）。
  PoC 同时硬化了一个普遍解析 bug。R4 度量计算机只读重算、不注入，仍不受此影响。
- [ ] 跨 provider 评审（外部 `/codex` 式范式）在 WorkBuddy harness 的可行性待验证——
  当前「跨会话独立 Agent」由隔离子 Agent 模拟，生产真隔离仍靠 Human 另开会话。
- [x] **设计补丁：角色实现范式升级（ingest 开源范式）** — **已 RATIFIED（2026-09-28，by zj）**。
  根因 = §0 立项意图（ingest 成熟角色实现）与 §2/§8 实际落地（C 模式抽取 + thin prompt
  角色）矛盾；方案 = 给 13 视角角色补 gated method（带闸门的可执行 method）+ 混合 ingest
  开源 domain 无关过程角色；决策模型重评可迁移部分 C→B1、suite/运行时维持 D。
  **内容已回流 §10，独立补丁文件已删除**（保持设计文档单一真源；执行阶段见 §10.4）。

---

## 8. 开源范式派生集成边界（R5，已回写）

分类 C 的硬边界：外部范式只作**结构借鉴 / 引用**，zj-discuss 方法体系为**自有主体**；
否决运行时编排器 / suite-化（触发约束 1 → D，且适配层会拥有主体状态）。三条具体边界：

- **跨 provider 评审（外部 `/codex` 式范式）= 组件引用，非运行时**：zj-discuss 的
  「跨会话独立 Agent」是本地近似；真跨 provider 隔离仍靠 Human 另开会话，不建编排器。
  外部多模型评审作为*可选增强*，不作为 zj-discuss 的依赖。
- **learnings 持久化 = 薄层复用**：zj-discuss 的「learnings」落地为本文档三件套
  （product/architecture/design）+ zj-docs-ontology 沉淀，而非共享 learnings DB；
  复用走「读设计文档」，不引共享运行时状态。
- **digest（2KB reuse ladder）= voice-only**：只注入 zj 的 ethos/voice（直接、结构化、
  第一性原理、敢反驳），**不**自动注入讨论状态 digest。语义兼容未知（见 §9），
  待最小 PoC 验证后再决定是否加结构性 digest。

> 边界判据：任何「引入运行时 / 共享状态 / 自动注入」的诉求，先回到 C-vs-D 决策——
> 若它让适配层拥有 zj-discuss 的主体状态，则落入 D，否决。

### digest 注入 PoC（语义兼容未知项已验证）

**PoC 目标**：验证在子文档 / MASTER 中加 digest 区块后，`check_subdoc.py`（结构性
闸门）与 `metrics.py`（度量计算机）把它当**惰性**处理——不计为独立视角、不污染
raw / solution 字符量、不触发违规、不破坏 conclusion 解析。

**PoC 结果（PASS）**：
- 新增可选 `## AI 上下文 digest（voice-only）` 区块（subdoc / MASTER 模板各一处），
  内容须置于 ``` 代码块内；闸门与度量对其完全惰性。
- **暴露并修复了一个普遍解析 bug**：原 `split_sections` 按行首 `#` 切分、**不认
  代码围栏**，导致 digest 围栏内嵌的 `### 视角：X` 回声会被误判为真实视角
  （视角计数 +1、raw 字符量虚增、闸门报缺来源）。两脚本的 `split_sections` 改为
  **围栏感知**后，围栏内 `#` 标题全部惰性；现有测试无回归。
- 回归守卫 `tests/test_digest_poc.py`（5 用例）：含 digest 的子文档度量与基线逐字段
  一致、闸门退出 0、MASTER digest 不污染 solution 字符量、且围栏内 `### 视角` 回声
  不计为视角。

**决策重申**：PoC 仅消除「注入会破坏解析」的未知，不改变 §8 的 voice-only 边界——
**仍不自动注入讨论状态 digest**。digest 区块是可选落点（人工 / agent 可填），不是
自动注入机制。若未来要加结构性（讨论状态）digest，本 PoC 已证明解析层兼容，门已开。

## 9. 复盘度量注册表（R4，已激活）

对应开源的 compression 度量（逻辑行/提交 → 3x–100x 压缩比）。zj-discuss 的
同构度量：一场讨论把 N 字的多角色辩论，压缩进 MASTER 解决思路的 M 字——比值即
「完整性近零成本」的量化证据（呼应 R9 Boil the Ocean / completeness is cheap）。

**单一 schema（讨论级与子文档级同构引用）：**

| 字段 | 含义 |
| --- | --- |
| `discussion_slug` / `sub_doc_id` | 讨论或子文档标识 |
| `roles_used` | 声明必需集中的角色 key 列表 |
| `viewpoint_count` | 有效视角数（排除低质 / 回声标记） |
| `open_questions_total` / `open_questions_closed` | 待讨论问题总数 / 已闭合数 |
| `closure_rate` | `closed / total` |
| `raw_volume_chars` | 全部子文档视角 + 辩论的字符总量 |
| `solution_volume_chars` | MASTER 解决思路终版字符量 |
| `compression_ratio` | `raw_volume_chars / solution_volume_chars`（开源式压缩比） |
| `recomputable` | 恒 `true`——全部字段从磁盘文件随时可重算，无隐藏状态 |

**激活状态**：**已激活**（`scripts/metrics.py` 只读度量计算机 + `tests/test_metrics.py`
守卫；MASTER 处置契约增「复盘度量」可选块，见 `master-template.md`）。

> **关于此前「未激活」决议的修正（诚实勘误）：** 原 §9 把 R4 激活挂在「digest /
> learnings 注入不破坏子文档结构」的语义兼容 PoC 上，经复核这是**误挂的依赖**。度量
> 计算机**只读磁盘文件、不写入、不注入任何 digest / learnings**——它解析的是现有稳定
> 结构（视角区块、`视角来源` 标注、`## conclusion`、`## 解决思路`），与 §8 已显式推迟的
> 「结构性 digest 注入」是**正交**特性。后者仍按 §8 保持未决；前者独立激活，不受其阻断。
> closure 口径采用「子文档级闭合」（见 §7）：discussion 级 `total`=子文档数、
> `closed`=结论 claim（DONE/DONE_WITH_CONCERNS）的子文档数，零模板改动。

---

## 10. 设计补丁流转：角色实现范式升级（已 RATIFIED）

> 来源：原 `patch-role-impl-paradigm-ingest.md`（PROPOSED → **RATIFIED 2026-09-28，by zj**）。
> 内容已回流本文件后，独立补丁文件已删除，保持设计文档单一真源。决策模型已落为本仓库
> SSOT（`docs/agreements/open-source-capability-fit-decision-model.md`），重评直接引用其定义。

### 10.1 根因勘误：§0 意图与实际落地的矛盾

`design.md` §0 立项意图是 **ingest 外部成熟角色实现**（让角色有真实行为，而非
thin prompt persona）。但文档主体用同一决策模型做了反方向：§2 将外部范式判为 C
（选择性复用，只作组件来源 / 模式抽取）、suite / 运行时判为 D（否决）；§8「外部能力集成边界」
重申红线；`role-matrix.md` 的 13 个角色只是「一句话立场 + 差异锚点 + 一句话简介」的
thin prompt。文档未标出该冲突，把 C 当自然结论——这是 §0「奇怪」感的根源（此前
「悬空引用」判断是表层）。

**结论**：§0 意图与 §2/§8 落地矛盾是真实根因，须显式勘误并纠正，而非当作既有结论接受。

### 10.2 两种 ingest 路径的取舍（已定）

- **范式级 ingest（已选）**：借开源「角色 = 带闸门的过程」范式重写自有角色，不碰
  外部文件、不引运行时。domain 匹配度高（套在 zj-discuss 讨论视角上）。
- **整包 ingest（否决）**：搬外部软件交付角色文件（`/ceo` `/qa` `/ship` …）进讨论
  视角，90% 软件专用，错位。
- **混合项（已选）**：开源 *domain 无关* 的流程角色（`/office-hours` 问题重构、
  `/plan-*` 评审闸门、`/retro` 复盘）作为「过程角色」整包-adapt，落**主力AI 编排层**
  （非 13 视角角色集），与现有「分解 / 准备 / 合成」阶段同源，适配成本最低。

### 10.3 决策模型重评（可迁移部分 C→B1，suite / 运行时维持 D）

| 开源能力 | 原判定（§2） | 本补丁重评 | 理由 |
| --- | --- | --- | --- |
| 跨 provider 独立评审（`/codex`） | C | **B1** | 与 zj-discuss 独立性阶梯语义高度匹配，ingest 为验证 / 过程角色 |
| 闸门 + 状态纪律（Completion Status、结构性 gate） | C（仅 R3 部分落地） | **B1** | 深化为每角色 gated method |
| learnings 回路（`/retro`） | C | **B1** | ingest 为收尾复盘过程角色 |
| reuse ladder / 2KB digest（voice-only） | C | C（维持） | 仍只覆盖表达语气，不改方法体系 |
| suite / 运行时 / router | D | **D（维持）** | 红线不变；范式级 ingest 不引外部运行时 |

> B1 仅针对「方法 / 范式」；suite / 运行时 D 红线**不变**。§8 集成边界文本中
> 「外部范式仅作结构借鉴，不引运行时」仍保留，但其语义从「推开成模式参考」修正为
> 「范式级 ingest 后仍以自有角色为主体、不引外部运行时」。

### 10.4 执行方案（ratify 后进入，待实现；不修改 skill 文件于本流转阶段）

1. **13 视角角色补 gated method**（范式 §4.1 四件套）：① 强制起点 `Read` 原文；
   ② 角色专属核查清单（取代一句话简介，这是「牙齿」）；③ 强制输出结构（≥N 条带证据
   有效观点，每条「发现 + 影响 + 建议」）；④ 闸门（≥N 条结构错位有效观点 + 引用原文证据
   + 不得与自身首轮锚定）。先 base {B,C,A}，再 T/S/O/D/L/F/U/R/P/E。
   （N 阈值已于 2026-09-29 PoC 校准：base N=3，C 在 solo/内部场景降 N=2，见 §10.6 R1。）
2. **过程角色 adapt**（§4.2）：`/office-hours`→准备阶段问题重构；`/plan-*`→scope / 架构
   / UX 评审闸门；`/retro`→收尾复盘（呼应 R4 度量注册表）。落主力AI 编排层，不进视角角色集。
3. **§2 决策矩阵更新**：可迁移部分 C→B1，并显式记录 10.1 意图-实际矛盾勘误。
4. **回归**：`check_subdoc.py` / `metrics.py` / `launch_pack.py` 现有测试零回归；
   必要时给 gated method 增补机械校验。

### 10.5 待评审问题决议（reviewer 已拍板，按 patch 倾向）

| # | 问题 | 决议 |
| --- | --- | --- |
| 1 | gated method 内联 `role-matrix.md` 还是拆 `references/role-methods/<key>.md`？ | **拆文件**（保持 SSOT 可读性） |
| 2 | 过程角色 adapt 只取闸门结构还是连具体评审项？ | **只取结构**，剥离软件专用措辞 |
| 3 | B1 重评后是否补示例决策记录？ | 由 `zj-open-source-capability-fit` skill 落为可复核工具，执行阶段补 1 条示例决策记录 |
| 4 | 本补丁是否转 `zj-roadmap-driven` 节点？ | 维持 design patch 形态；ratify 后可转录为 roadmap 节点驱动执行 |

### 10.6 风险（维持 patch §8）

- **R1 闸门过严导致角色产出萎缩**：阈值需 PoC 校准；先在 base 角色 PoC 一轮。
  **PoC 校准（2026-09-29 完成）**：被测原文 = `docs/agreements/open-source-capability-fit-decision-model.md`
  （真实 SSOT，非本次产物）；base {B,C,A} 按 gated method 各尝试 N=2/3/4/5，逐条标注质量。
  协议与原始产出见 `skills-outputs/zj-discuss/n-threshold-poc/{protocol,probe-views}.md`。

  - **数据**：B 真有效饱和 **4** 条（N≤4 全真，N=5 borderline 注水）；A 同构（N=5 回声 C 注水）；
    **C 真有效饱和仅 2 条**（N=3 已 borderline，N=4/5 注水萎缩）——印证 R1 风险集中于 C
    （solo/内部场景「市场原义空转」，见 `role-matrix.md` L37-38）。
  - **结论（base 初值建议）**：B/A 维持 **N=3**（安全区间 ≤4）；**C 在 solo/内部工具子问题
    （无真实市场信号）闸门降为 N=2**，触及外部用户/竞品/生态信号的子问题回 N=3。
    采用「方案 A」最小改动（不整体降 N，避免稀释 B/A 饱满视角）。
  - **落实**：`role-methods/C.md` 增 solo 豁免条款 + `role-matrix.md` L37-38 注记（见 §10.4 执行项）。
  - **诚实声明（已闭合）**：被测样本由本 Agent 同会话产出（作者即评审），存在自指偏差，原结论为初值建议。
    该自指偏差风险经 r1-closure roadmap 节点 1-3（盲评一致率 86.7%）与 1-4（fresh-context 独立子 Agent、
    Cohen's κ=0.667 substantial）**跨会话复核确认**：B/A 维持 N=3、C solo N=2 稳健，未触发节点 1-1 决策 D。
    故本节初值建议**已升级为锁定值**（见 §10.6.1）。

#### 10.6.1 R1 闸门阈值校准（已锁定）

> 校准闭环：同会话 PoC（#158）→ 盲评复核（节点 1-3）→ 跨会话独立评分者 κ（节点 1-4）→ 本节点锁值写回。
> 唯一保留风险（同会话自指偏差）已在 1-3/1-4 经独立第二评分者消除。

| 角色 / 场景 | 锁定 N | 跨会话证据 |
| --- | --- | --- |
| B（技术经理） | **3** | 严格 4 / 宽松 5 真有效；维持 N=3 稳健 |
| A（架构师） | **3** | 严格 4 / 宽松 4 真有效；维持 N=3 稳健 |
| C（产品专家）· solo/内部子问题（无市场信号） | **2** | 严格 2 / 宽松 3 真有效；N=3 将注水萎缩 → 降 N=2 跨会话确认 |
| C（产品专家）· 触及外部用户/竞品/生态信号 | **3** | 预设分支，非偏离 |

**锁值元数据**（节点 1-1 决策 E 要求保留）：
- 校准来源：R1 PoC（PR #158，2026-09-29）
- 跨会话复核：节点 1-4 fresh-context 独立子 Agent（`agent-4f80418b21664bdd`）
- 复核日期：2026-09-29
- 一致性：独立 vs 1-3 盲标 κ=1.000；独立 vs 原始保守标注二值 κ=0.667（substantial）
- 落点：`role-methods/{B,C,A,T,S,O,D,L,F,U,R,P,E}.md` 闸门④ + `role-matrix.md` L37-38
- 边界案例保留：B3（停止规则）、C3（目标适用范围）为 borderline，不自动计入 N（按节点 1-4 诚实局限）。
- **R2 过程角色 adapt 过度**：`/plan-*` 带入软件交付语境，adapt 时剥离代码专用措辞，只取评审闸门结构。
- **R3 决策模型重评被误读为放开 D 红线**：B1 仅方法 / 范式，suite / 运行时 D 不变；重评表显式标注 D 维持。
