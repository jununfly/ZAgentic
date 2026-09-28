# 设计补丁：zj-discuss 角色实现范式升级（ingest gstack 范式）

- **状态**：PROPOSED（待评审 / 未 ratification）
- **作者**：zjj（基于 zj 对立项意图的澄清）
- **日期**：2026-09-28
- **类型**：设计补丁（design patch）+ 待评审 roadmap 节点候选
- **关联文档**：`design.md` §0 / §2 / §8；`references/role-matrix.md`；`SKILL.md`「外部能力集成边界」
- **一句话**：把 13 个视角角色从 thin prompt persona 升级为「带闸门的可执行 method」，借鉴 gstack 的范式（角色 = 强制工作流 + 闸门 + 状态的过程），而非照搬 gstack 的软件交付角色文件。

> 本补丁**不修改任何 skill 文件**。它是对 `design.md` §0 意图与实际落地之间矛盾的勘误，加上一套 ratify 后可执行的升级方案。ratify 后，本补丁内容应回流进 `design.md`（新开一节或并入 §2/§5），并删除本独立文件以保持设计文档单一真源。

---

## 1. 背景：§0 意图与实际产出的矛盾（根因）

`design.md` §0 的立项意图是：借本仓库自创的「开源能力拟合决策模型」，从 `github.com/garrytan/gstack` 这类 OSS **ingest 成熟的角色实现**，让角色有真实行为，而不是靠「简单且单薄的 prompt 令 Agent 扮演角色」。

但文档主体用同一决策模型做了相反的事：

- `design.md` §2 将 gstack 判为 **C（选择性复用，只作组件来源 / 模式抽取）**，并把 suite / 运行时判为 **D（否决）**；
- `SKILL.md`「外部能力集成边界」（§279–293）重申该红线，明确「gstack 仅作组件来源，不引运行时」；
- `references/role-matrix.md` 的 13 个角色，每个只是「一句话立场 + 差异锚点 + 一句话简介」——**纯 thin prompt persona**；`zj-discuss-view --role X` 仅给同一份 SKILL 传 role 参数，行为完全由 role-matrix 那一行驱动。

结论：**§0 说要 ingest 真实现现，文档主体却用决策模型把 gstack 推开成模式参考、自建 thin prompt**。文档未将该冲突标出，反而把 C 当作自然结论——这正是 §0 描述「奇怪」的真正根源（此前的「悬空引用」判断是表层，根因在此）。

---

## 2. 两种 ingest 路径的取舍（已在对话中澄清）

| 维度 | 范式级 ingest（选项 2） | 真·整包 ingest（选项 3） |
| --- | --- | --- |
| 抄什么 | gstack 的「角色观」（角色 = 带闸门的过程） | gstack 的具体角色 skill 文件（`/review`、`/qa`、`/ceo`、`/cso` …） |
| 仓库动作 | 不碰 gstack 文件；改写 `role-matrix` + 新增每角色 method | clone gstack → 搬文件进 `references/` → 逐文件改写 |
| domain 匹配 | ✅ 套在 zj-discuss 自己的讨论视角上 | ❌ gstack 角色是软件交付流程，对讨论视角错位，主要成本是剥离软件专用部分 |
| 买到 | 结构严谨性（闸门 / 状态 / 强制输出）套在正确 domain | gstack 打磨过的具体 checklist（对代码好，对讨论错配） |

**本补丁选择范式级 ingest，外加一个混合项**：把 gstack 中 *domain 无关* 的流程角色（`/office-hours` 问题重构、`/plan-*` 评审闸门、`/retro` 复盘）作为「过程角色」整包-adapt，落进主力AI 编排层（而非 13 个视角角色）。理由：这些流程角色与 zj-discuss 现有的「主力AI 分解 / 准备 / 合成」阶段同源，适配成本最低，且不破坏「视角角色 = 讨论视角」的语义。

> 不选整包 ingest 13 个视角角色：gstack 视角角色（`/ceo` `/em` `/reviewer` …）是软件交付流程的角色，直接搬进来 90% 是软件专用，对「讨论 / 决策视角」是错位的。

---

## 3. 目标与不做的事

**目标**
1. 消除 §0 意图与实际落地的矛盾，让设计文档自洽。
2. 给 13 个视角角色补「可执行 method + 闸门 + 状态」，使其不再是 thin prompt。
3. 用本仓库自创决策模型**重评** gstack：可迁移的「方法 / 范式」部分从 C 升到 **B1（ingest + adapt）**，但 suite / 运行时维持 **D（红线不变）**。
4. 决策模型已落为本仓库自创方法论 SSOT（`docs/agreements/open-source-capability-fit-decision-model.md`），重评 gstack 时直接引用本仓库模型，无需外部来源。

**不做**
- 不引入 gstack 运行时 / router / suite（维持 D 红线；范式级 ingest 只借范式重写自有角色，不引外部运行时）。
- 不照搬 gstack 软件交付命令（`/qa` 开浏览器、`/ship` 发布清单等）到讨论视角角色。
- 不在本补丁阶段修改 skill 文件（ratify 后才进入执行）。

---

## 4. 方案

### 4.1 给 13 个视角角色补 gated method

每个角色在保留 `role-matrix.md` 现有「结构立场 / 差异锚点」的前提下，增补四件套：

1. **强制起点**：`Read` 原文（沿用硬规则 1，不可转述）。
2. **角色专属核查清单（role-specific checklist）**——这是「牙齿」，取代一句话简介。
3. **强制输出结构**：≥ N 条带证据的有效观点 / 挑战；每条标明「发现 + 影响 + 建议」，禁止只给口头提醒。
4. **闸门（anti-degrade）**：至少 N 条结构错位的有效观点；必须引用原文证据；不得与自身首轮锚定（沿用硬规则 3 防回声）。

**示例——角色 S（安全 / 威胁建模）**
- 核查清单：STRIDE 六项（Spoofing / Tampering / Repudiation / Information Disclosure / Denial of Service / Elevation of Privilege）逐项过子文档设计；数据流与信任边界；权限模型；合规边界。
- 闸门：≥3 条带证据的威胁发现，每条标「威胁类别 + 影响 + 缓解建议」；不得只说「要注意安全」。

**示例——角色 B（技术经理，base）**
- 核查清单：可落地性（谁来做 / 做到什么程度算完）、依赖链、排期、回滚路径、落地代价。
- 闸门：必须给出「落地代价」估算 + 至少一个阻塞风险；不得只说「能实现」。

**示例——角色 A（架构师，base）**
- 核查清单：边界与不变式、向后兼容、与其他系统的耦合、长期演化成本。
- 闸门：必须指出至少一个「以后会炸」的耦合点并给缓解；不得只说「架构合理」。

> 13 个角色的完整 checklist 在本补丁 ratify 后的执行阶段补齐，写入 `references/role-matrix.md` 与各角色 method 区块（或拆为 `references/role-methods/<key>.md`）。本补丁只定范式与样例。

### 4.2 混合：gstack domain 无关流程角色整包-adapt

| gstack 源 | zj-discuss 落点 | 性质 |
| --- | --- | --- |
| `/office-hours`（重构问题 → 设计文档） | 主力AI 准备阶段的「问题重构」过程角色 | 过程角色（非视角） |
| `/plan-ceo-review` / `/plan-eng-review` / `/plan-design-review` | 准备阶段的 scope / 架构 / UX 评审闸门 | 过程角色（非视角） |
| `/retro` | 讨论收尾复盘（呼应 R4 度量注册表） | 过程角色（非视角） |

这些落进主力Ai 编排层，不进入 13 个视角角色集，保持「视角角色 = 讨论视角、过程角色 = 编排流程」的语义边界。

### 4.3 决策模型重评（本仓库 R×O 模型）

在本仓库自创决策模型下，对 gstack 的可迁移部分重新打分（维持 D 红线）：

| gstack 能力 | 原判定（§2） | 本补丁重评 | 理由 |
| --- | --- | --- | --- |
| 跨 provider 独立评审（`/codex`） | C | **B1** | 与 zj-discuss 独立性阶梯语义高度匹配，ingest 为验证 / 过程角色 |
| 闸门 + 状态纪律（Completion Status、结构性 gate） | C（仅 R3 部分落地） | **B1** | 深化为每角色 gated method |
| learnings 回路（`/retro`） | C | **B1** | ingest 为收尾复盘过程角色 |
| reuse ladder / 2KB digest（voice-only） | C | C（维持） | 仍只覆盖表达语气，不改方法体系 |
| suite / 运行时 / router | D | **D（维持）** | 红线不变；范式级 ingest 不引外部运行时 |

> 重评要点：§2 原把 gstack 一刀切为 C，偏离了 §0「ingest 实现」的意图。本补丁把「方法 / 范式」部分升 B1、「voice-only」维持 C、「运行时」维持 D，使决策模型结论与立项意图一致。

---

## 5. 前置依赖（阻塞）

1. **决策模型来源已闭合**：模型已落为本仓库自创方法论 SSOT（`docs/agreements/open-source-capability-fit-decision-model.md`），重评 gstack 直接引用本仓库模型，无需外部来源。

---

## 6. 执行步骤（ratify 后）

1. 决策模型已为本仓库自创方法论 SSOT，重评直接引用本仓库模型（§5.1 已闭合）。
2. 在 `role-matrix.md` 给 13 个视角角色各补 §4.1 四件套（先 base {B,C,A}，再 T/S/O/D/L/F/U/R/P/E）。
3. 新增过程角色（`/office-hours`、`/plan-*`、`/retro` adapt），落主力Ai 编排层（改 `SKILL.md` 准备 / 合成阶段 + `references/`）。
4. 更新 `design.md` §2 决策矩阵：gstack 可迁移部分 C→B1，并记录本补丁的意图-实际矛盾勘误。
5. 回归：`check_subdoc.py` / `metrics.py` / `launch_pack.py` 现有测试无回归；必要时给 gated method 增补机械校验。
6. 回填：本补丁内容回流 `design.md` 后删除本独立文件。

---

## 7. 验收标准（Definition of Done）

- [ ] 决策模型为可解析的本仓库自创方法论 SSOT（文件存在）。
- [ ] 13 个视角角色均含「核查清单 + 强制输出 + 闸门」，不再只有一句话简介。
- [ ] base 角色 {B,C,A} 的 gated method 经一次真实子文档走查验证「有牙齿」（能产出带证据的结构错位观点，而非复述 persona）。
- [ ] 过程角色（问题重构 / 评审闸门 / 复盘）已 adapt 并接入编排层。
- [ ] `design.md` §2 决策矩阵反映 C→B1 重评，且显式记录意图-实际矛盾勘误。
- [ ] 现有脚本测试零回归。
- [ ] 本补丁文件已删除（内容回流 design.md）。

---

## 8. 风险

- **R1 闸门过严导致角色产出萎缩**：闸门阈值（N 条 / 证据要求）需 PoC 校准，避免角色为达标而灌水。缓解：先在 base 角色 PoC 一轮。
- **R2 过程角色 adapt 过度**：`/plan-*` 等带入软件交付语境，需在 adapt 时剥离代码专用措辞。缓解：过程角色只取「评审闸门」结构，不复述 gstack 的具体审查项。
- **R3 决策模型重评被误读为「放开 D 红线」**：明确 B1 仅针对方法 / 范式，suite / 运行时 D 不变。缓解：重评表显式标注 D 维持。

---

## 9. 待评审问题（reviewer 需拍板）

1. 角色 gated method 是继续内联在 `role-matrix.md`，还是拆为 `references/role-methods/<key>.md`？（倾向后者，保持 SSOT 可读性。）
2. 过程角色 adapt 是否只取「闸门结构」，还是连 gstack 的具体评审项一起借鉴？（倾向只取结构。）
3. 决策模型重评升 B1 后，「fit 计算」「E 成本」已由 `zj-open-source-capability-fit` skill 落为本仓库可复核工具，是否还需补充示例决策记录？（关联 §5.1。）
4. 是否要把本补丁直接转为 `zj-roadmap-driven` 的 roadmap 节点（而非仅 design patch）？当前以 design patch 形态交付以便评审；ratify 后可转节点。
