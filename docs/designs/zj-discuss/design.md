# zj-discuss — 设计文档（Design / 完整规格）

> 本文件是 `zj-discuss` / `zj-discuss-view` 的**权威详细规格**，沉淀自一段长对话
> （立项 grill → 共识 → 落 skill → 自举验证 → 合并 → 阶段 2 处置 → gstack/决策模型复盘
> → 本轮 4 项追加改进）。目的是**避免对话进程丢失完整 context**。
> 产品定义见 `product.md`，组件与生命周期见 `architecture.md`。
> 角色语义唯一真源：`references/role-matrix.md`。

---

## 0. 决策模型与证据来源（复盘基准）

- **决策模型**：`docs/agreements/open-source-capability-fit-decision-model.md`（本仓库 SSOT；
  权威源 [ZInitiatives](https://github.com/jununfly/ZInitiatives/blob/main/docs/agreements/open-source-capability-fit-decision-model.md)，
  用户废弃项目，模型状态：已接受）。定义 `R × O` 证据矩阵 →
  有效拟合度（功能覆盖×语义匹配×可组合性）→ 总所有权成本 E →
  决策分类 `A`（直接采用）/ `B`（扩展采用，细分 B1/B2/B3）/ `C`（选择性复用）/ `D`（继续搜索）；
  默认优先级 `A > B1 > B2 > C > B3`（`D` 为搜索循环回环态，非终态否决；见 §2 待核对偏离）。
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
| R1 | `zj-discuss-view --all`（默认 {B,C,A}）+ 单角色 `--role X`（候选池任一 key 或自定义）；多角色由 `--all` 一次性打印启动包 | 一键触发 vs 手动 | 已回写（`--all` + 单角色 `--role`；见 §3.2 / architecture §1）。**`--role X,Y` 逗号语法已正式关闭**——单会话多角色即违反隔离，理由写入 SKILL.md Phase 2 步骤 2 |
| R2 | 静态 launch-pack 生成器（替代手工拷贝，不建运行时） | ACP 程序化派生 | 已回写 —— `scripts/launch_pack.py`（读声明必需集 → 每角色一份 `<slug>-launchpack-<role>.md`）；回归守卫 `tests/test_launch_pack.py`，其中 `NoRuntimeInvariant` 机械禁止其退化为运行时 |
| R3 | subdoc-template 增状态协议字段 + 预演结构性闸门（conclusion 无预演字段）+ 预演可见标签 | Completion Status 协议 | 已回写 —— `subdoc-template.md` 增 `状态协议`（DONE/DONE_WITH_CONCERNS/BLOCKED/NEEDS_CONTEXT）与 `⚠ 非独立` 标签、conclusion 禁引预演；**机械闸门** `scripts/check_subdoc.py`（退出码 0/1/2），守卫 `tests/test_check_subdoc.py` |
| R4 | 轻量可重算度量注册表（单一 schema，被 sub-01/02 同构引用） | compression 度量 | 已定义 schema（见 §9，未激活，待 PoC） |
| R5 | 集成边界文本：跨 provider 评审=组件引用、learnings=薄层复用、digest=voice-only | suite/reuse ladder | 已回写 —— **按处方落点进 `SKILL.md`「外部能力集成边界（选择性复用）」**（此前仅存于 §8 导致 SKILL 侧零命中），完整论证仍见 §8 |
| R6 | ZJ-CONTEXT.md 领域词注册 | — | 已回写（ZJ-CONTEXT.md `## Discussion methodology`） |
| R7 | 独立性阶梯「非降级自检项」成为 SKILL 硬规则 + 机械闸门 | gstack 跨 provider 范式 | 已回写 —— SKILL.md 硬规则 6 + `check_subdoc.py` 第 4 项检查。注：本项属**处方第 4 条的子条款**，未被 R3/R4 覆盖；按「六条」计数时会漏判，核账到子条款才暴露 |

### 决策记录（决策模型要求项）

> 本小节自 discussions 过程文件夹抽取而来，**在阶段 2 删除该文件夹之前**完成沉淀。
> 缺了它的后果：后人无法在上游变更时重新评估分类，只能盲信结论。

**候选项目及固定版本 O**：`github.com/garrytan/gstack` **v1.2.0**。能力清单：
O-u1 ACP 程序化派生、O-u2 router+preamble、O-r1 跨 provider 外部评审（`/codex`）、
O-r2 Completion Status、O-f1 compression 度量、O-c1 suite 协同、O-c2 2KB digest、
O-c3 跨 provider 选择性复用范式。

**R × O 证据矩阵（全局收敛）**

| R | 命中的 gstack O | 判定 | 约束来源 |
| --- | --- | --- | --- |
| R-u1 派发自动化 | O-u1 ACP 派生 | C 复用（产物形状 → 静态生成器） | 不引运行时，约束 1 |
| R-u2 角色零认知 | O-u2 router 思路 | C 复用（`--all` 参数化） | 不做常驻 router |
| R-r1 独立性升级 | O-r1 `/codex` | C 复用（推荐非强制） | 不引 gstack/base |
| R-r2 防回声室 | O-r2 状态协议 | C 复用（sub-doc 契约） | 极简 |
| R-f1 可度量价值 | O-f1 compression | C 复用（轻量日志度量） | 单一注册表 |
| R-c1 集成边界 | O-c1 suite | **否决（→ D 风险）** | suite 化会拥有主体状态 |
| R-c2 总所有权成本 | O-c2 digest | C 复用（voice-only） | 不覆盖方法体系 |

**自有责任 E 与成本估计**：digest 注入 ≈0.5 人日；`/codex` 跨 provider 评审 ≈3–5 人日；
launch-pack 生成器 ≈1–2 人日；状态协议 / 度量注册表 ≈1 人日；learnings 复用 ≈1 人日。
**总 E ≈ 7–10 人日**，全部为可移除薄层，无运行时 / 基座 ownership。
对照：自建 suite ≈2–4 周 + 长期运维 → D，已被红线排除。

**采用理由**：gstack 仅作组件来源，zj-discuss 方法体系（role-matrix / briefing / R×O）
为自有主体，无逻辑漂移；E 可控、可退。

**主要风险**：① 语义兼容未知（digest / learnings 注入不破坏 zj 子文档结构）→ 最小 PoC 验证；
② 跨 provider 派生依赖 Human 手动开启非主力 provider 会话，harness 无一键能力 → 不阻断（手动零成本）。

**退出路径**：任一 C 组件失效可独立替换，无 suite 级锁定；若 gstack 未来提供非破坏性的
外部方法体系接入不变式，可重评为 B1。

**重新评估触发**：① gstack 大版本变更 suite 接入不变式；② WorkBuddy harness 原生支持
spawn 不同 provider 的独立会话（届时 R-u1 / R-r1 的 C 复用形态可升级）。

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

- [x] R1–R7 七条 gstack 派生修订全部落地：R1/R2/R3/R5/R6/R7 已回写（见 §2 + §8）；
  **R4 已激活**（`scripts/metrics.py` + `tests/test_metrics.py`，§9）。
- [x] 语义兼容未知项（**独立于 R4**，§8 关联）：**最小 PoC 已通过**——digest 注入
  不破坏子文档 / MASTER 解析。结论见 §8「digest 注入 PoC」段：闸门与度量对 digest
  区块惰性，且 `split_sections` 已围栏感知（digest 围栏内嵌 `### 视角` 回声也不误判）。
  PoC 同时硬化了一个普遍解析 bug。R4 度量计算机只读重算、不注入，仍不受此影响。
- [ ] 跨 provider 评审（gstack `/codex` 范式）在 WorkBuddy harness 的可行性待验证——
  当前「跨会话独立 Agent」由隔离子 Agent 模拟，生产真隔离仍靠 Human 另开会话。
- [ ] **设计补丁：角色实现范式升级（ingest gstack 范式）** — PROPOSED，待评审。
  根因 = §0 立项意图（ingest 成熟角色实现）与 §2/§8 实际落地（C 模式抽取 + thin prompt
  角色）矛盾；方案 = 给 13 视角角色补 gated method（带闸门的可执行 method）+ 混合 ingest
  gstack domain 无关过程角色；决策模型重评 gstack 可迁移部分 C→B1、suite/运行时维持 D。
  详见 `patch-role-impl-paradigm-ingest.md`。**前置（阻塞）**：修复 §0 ZInitiatives 悬空引用
  （`docs/agreements/open-source-capability-fit-decision-model.md` 仓库内不存在、无 URL）。

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

**激活状态**：**已激活**（`scripts/metrics.py` 只读度量计算机 + `tests/test_metrics.py`
守卫；MASTER 处置契约增「复盘度量」可选块，见 `master-template.md`）。

> **关于此前「未激活」决议的修正（诚实勘误）：** 原 §9 把 R4 激活挂在「digest /
> learnings 注入不破坏子文档结构」的语义兼容 PoC 上，经复核这是**误挂的依赖**。度量
> 计算机**只读磁盘文件、不写入、不注入任何 digest / learnings**——它解析的是现有稳定
> 结构（视角区块、`视角来源` 标注、`## conclusion`、`## 解决思路`），与 §8 已显式推迟的
> 「结构性 digest 注入」是**正交**特性。后者仍按 §8 保持未决；前者独立激活，不受其阻断。
> closure 口径采用「子文档级闭合」（见 §7）：discussion 级 `total`=子文档数、
> `closed`=结论 claim（DONE/DONE_WITH_CONCERNS）的子文档数，零模板改动。
