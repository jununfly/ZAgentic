# zj-discuss — 设计文档（Design / 完整规格）

> 本文件是 `zj-discuss` / `zj-discuss-view` 的**权威详细规格**，沉淀自一段长对话
> （立项 grill → 共识 → 落 skill → 自举验证 → 合并 → 阶段 2 处置 → gstack/决策模型复盘
> → 本轮 4 项追加改进）。目的是**避免对话进程丢失完整 context**。
> 产品定义见 `product.md`，组件与生命周期见 `architecture.md`。
> 角色语义唯一真源：`references/role-matrix.md`。

---

## 0. 决策模型与证据来源（复盘基准）

- **决策模型**：ZInitiatives `docs/agreements/open-source-capability-fit-decision-model.md`
  —— `R × O` 证据矩阵 → 有效拟合度（覆盖×语义匹配×可组合性）→ 总所有权成本 E →
  A/B/C/D 分类（优先级 A > B1 > B2 > C > B3）。
- **证据源**：`github.com/garrytan/gstack` 本地副本（v1.2.0）。抽取的可迁移模式：
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

## 2. gstack + 决策模型复盘：6 项待回写改进（分类 C，尚未 ratification）

> 来源：用方法论自举讨论「如何深度改进 zj-discuss」的结论。分类 = C（选择性复用），
> 即 gstack 作组件来源、zj-discuss 方法体系为自有主体；否决运行时编排器/suite-化
> （触发约束 1 → D，且适配层会拥有主体状态）。

| # | 改进 | 对应 gstack 证据 | 状态 |
| --- | --- | --- | --- |
| R1 | `zj-discuss-view --all`（默认 {B,C,A}）+ 单角色 `--role X`（候选池任一 key 或自定义）；多角色由 `--all` 一次性打印启动包 | 一键触发 vs 手动 | 已回写（启动包 + `--all` + 单角色 `--role`；见 §3.2 / architecture §1） |
| R2 | 静态 launch-pack 生成器（替代手工拷贝，不建运行时） | ACP 程序化派生 | 已回写（Phase 2 启动包静态生成；见 §3.2） |
| R3 | subdoc-template 增状态协议字段 + 预演结构性闸门（conclusion 无预演字段）+ 预演可见标签 | Completion Status 协议 | 待回写（本轮未覆盖） |
| R4 | 轻量可重算度量注册表（单一 schema，被 sub-01/02 同构引用） | compression 度量 | 已定义 schema（见 §9，未激活，待 PoC） |
| R5 | 集成边界文本：跨 provider 评审=组件引用、learnings=薄层复用、digest=voice-only | suite/reuse ladder | 已回写（见 §8 gstack 派生集成边界） |
| R6 | ZJ-CONTEXT.md 领域词注册 | — | 已回写（ZJ-CONTEXT.md `## Discussion methodology`） |

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

- [x] R1–R6 六条 gstack 派生修订：R1/R2/R5/R6 已回写（见 §2 + §8）；**R4 已定义 schema、未激活**（§9）；
  **R3（subdoc-template 状态协议字段 + 预演结构性闸门）仍待回写**，本轮未覆盖。
- [ ] 语义兼容未知项：digest/learnings 注入不破坏 zj 子文档结构，需最小 PoC 验证（§9 关联）。
- [ ] 跨 provider 评审（gstack `/codex` 范式）在 WorkBuddy harness 的可行性待验证——
  当前「跨会话独立 Agent」由隔离子 Agent 模拟，生产真隔离仍靠 Human 另开会话。
- [ ] R4 度量注册表激活：PoC 通过后在 MASTER 处置契约增「复盘度量」可选块（§9）。

---

## 8. gstack 派生集成边界（R5，已回写）

分类 C 的硬边界：gstack 只作**组件来源 / 引用**，zj-discuss 方法体系为**自有主体**；
否决运行时编排器 / suite-化（触发约束 1 → D，且适配层会拥有主体状态）。三条具体边界：

- **跨 provider 评审（gstack `/codex` 范式）= 组件引用，非运行时**：zj-discuss 的
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

## 9. 复盘度量注册表（R4，已定义 schema / 未激活）

对应 gstack 的 compression 度量（逻辑行/提交 → 3x–100x 压缩比）。zj-discuss 的
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
| `compression_ratio` | `raw_volume_chars / solution_volume_chars`（gstack 式压缩比） |
| `recomputable` | 恒 `true`——全部字段从磁盘文件随时可重算，无隐藏状态 |

**激活状态**：**定义完成，未激活**。尚未接线进模板（不强制 MASTER / subdoc 写该字段），
因 §9 关联的「digest / learnings 注入不破坏子文档结构」语义兼容仍是未知项，需最小 PoC。
PoC 通过后再决定是否在 MASTER 处置契约增「复盘度量」可选块。
