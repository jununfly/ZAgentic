# ui-flow/v1 契约：六实体语义与迁移规则（冻结版）

- **归属节点**：1-2-3（产品实现路线 · 计划层 · `exploit`）
- **文档性质**：契约冻结，交付物为 ui-flow/v1 语义与迁移规范，**不含产品代码落地**。
- **依赖**：1-2-1（六类 schema 冻结 v0.1）、1-2-2（编辑/patch/unknown 语义冻结）。
- **引用源**：
  - `discussions/ui-agent-skills-complete-solution/MASTER.md` L45 / L52-56 / L68 / L94-96
  - `discussions/ui-agent-skills-complete-solution/sub-01-artifact-contract.md` L31/L52/L67/L73/L79/L88/L94/L100/L109/L115/L121/L127-155
- **本文件版本**：v0.1（冻结；后续变更经 1-2-4 golden fixtures 校验）。

---

## 0. 范围与退出判据（本节点退出判据）

> **退出判据原文**：ui-flow/v1 可离线表达并重放 screen/component/state/action/intent/acceptance。

本文件冻结以下内容，全部以**可机器校验**的方式表达，供 1-2-4 golden fixtures 评审：

1. 六实体的语义定义与字段注册表（owner/source/requiredness/unknown_policy …）。
2. 「分义」原则与不可混淆结构。
3. 状态转移模型与离线重放流程。
4. 迁移规则与 schema lock。
5. adapter 边界与拒绝行为。
6. 继承 1-2-2 的三条不变量。
7. hard fail 与数值闸门。

**停止条件（贯穿全文）**：
- 状态/动作/意图丢失、双 owner、unknown 未保留 → **hard fail**（MASTER L68）。
- 核心语义静默丢失 ≠ 0、未声明 warning ≠ 0、离线恢复成功率 ≠ 100% → **闸门失败**（sub-01 L100）。
- adapter 越权覆盖 canonical / 把 unknown 压成空值 / 远程 ID 成为唯一索引 / 无法离线恢复 → **拒绝写入并保留上一 canonical 版本**（sub-01 L135）。

---

## 1. 六实体语义与字段注册表

**归属（MASTER L45）**：`ui-flow/v1` 的 ZAgentic owner = `flow/schema owner`；必须表达 `screen / component / state / action / intent / acceptance / source / unknown`；adapter 可拥有 `provider projection ID`、布局映射；本地恢复要求 = 可离线重放状态/动作/意图。

**六实体语义（sub-01 L31/L73/L131）**：
- `screen`：界面边界（呈现对象）。
- `component`：呈现对象（绑定 screen）。
- `state`：可观察状态（state 集合及转移）。
- `action`：状态变化输入（action 参数）。
- `intent`：行为目的（intent 参数，明确触发动作及前置/后置状态）。
- `acceptance`：可验证断言（acceptance 条件）。
- `source`：产生者与版本（可追溯）。
- `unknown`：原始值 + 原因 + 所在路径（见第 6 节四元组）。

**字段注册表（sub-01 L129/L109）**：每个字段建立不可变 `field_id`，强制记录：
`owner / source / requiredness / schema_version / unknown_policy / read_write / recovery`。
- ZAgentic-owned 且 required 的字段转换后**必须 100% 保留，缺失即阻断**（sub-01 L88）。
- adapter 输出的 provider ID、渲染配置、映射只能在 adapter 命名空间中存在，不得进入 canonical 字段（sub-01 L129）。

---

## 2. 「分义」与不可混淆结构

**分义原则（MASTER L53）**：`screen/component/state/action/intent/acceptance` **必须语义分离**，不得混用。

**不可混淆结构（sub-01 L73/L132）**：
- screen/component 描述**呈现对象**；
- state 描述**可观察状态**；
- action 描述**状态变化输入**；
- intent 描述**行为目的**；
- acceptance 描述**可判定结果**。

**唯一转移约束（sub-01 L73）**：同一 `action + pre-state` **只能产生一个 canonical transition**，禁止一对多语义歧义。

**反模式（sub-01 L72，明确禁止）**：
- 把 state/action/intent 混在组件属性或 screen 快照中 → adapter 只保留最终视觉而丢失触发原因与可验证行为。
- 把 unknown 用缺字段或 null 代替 → 混淆「未知 / 未提供 / 明确为空」。

---

## 3. 状态转移模型与离线重放

**状态边表达（sub-01 L115）**：flow 用有向状态边 `from_state / action / to_state / intent` 表达；实体以**稳定 ID** 存储，引用只指向 ID。

**两层模型（sub-01 L115）**：「版本化 canonical 文件 + 可重建索引」。
- 索引必须可由 canonical 重建。
- 发现**悬空引用 / 重复 ID / 非法状态边** → 拒绝提交。

**离线重放（退出判据核心，MASTER L45/L56 + sub-01 L121）**：
- 本地恢复要求：可离线重放状态/动作/意图。
- 恢复流程：`最后完整 canonical revision → 校验哈希 → 重建索引 → 重新生成 projection`（sub-01 L121）。
- adapter 删除 / 远程关闭 / 网络断开时，最后一个完整 canonical revision 是**唯一恢复路径**（MASTER L56）。
- 服务关闭时仅凭本地 canonical artifact 重建 flow、恢复状态并重放动作，否则输出 **recovery error**（sub-01 L79）。

---

## 4. 迁移规则与 schema lock

**版本演进（sub-01 L31/L131/L150）**：
- v1 **仅允许向后兼容的加字段**；新增字段若不能安全忽略则必须升主版本。
- 改变既有语义 → 必须升**主版本**并提供**迁移器（migrator）**。

**schema lock（sub-01 L150/L154）**：schema lock + golden fixture 共同锁定契约；任何 schema 或 adapter 修改都重跑 fixture 套件，失败时**保留旧 artifact、标记验证失败，不得继续下游发布**（sub-01 L100）。

**幂等键与原子提交（MASTER L55 + sub-01 L121）**：每次转换绑定
`(fixture_id, input_revision, adapter_version, mapping_version)`；
输出写入**临时版本**后**原子提交**；同一输入重复转换必须得到相同语义哈希与 warning 集合。

---

## 5. adapter 边界与拒绝

**投影而非事实源（MASTER L52 + sub-01 L67/L110）**：
- adapter 只能提交带 `projection_id / source_revision` 的投影或带版本的转换事件，**禁止直接覆盖 canonical 字段**。
- adapter-derived 被当作 canonical、远程 ID 成为唯一索引 → 契约失败（sub-01 L67）。

**越权拒绝（sub-01 L88/L135）**：
- `fixture-adapter-mutates-owned-field`：adapter 修改 `intent` / `acceptance` 等 ZAgentic-owned 字段 → **必须失败并报告字段路径**。
- 任何 adapter 越权覆盖 canonical、把 unknown 压成空值、无法离线恢复 → **拒绝写入并保留上一 canonical 版本**。

---

## 6. 继承 1-2-2 的三条不变量

本节点**不得弱化** 1-2-2 已冻结的三条不变量（1-2-2 文档第 3/4/5 节）：

1. **deny-first**：未注册 / 未知字段不静默丢弃，一律显式拒绝并标注（MASTER L97）。
2. **unknown 四元组**：`unknown` 必须保留 `{ path, raw, reason, source }`，不能压成空值（MASTER L53）；关键字段为 unknown 时 acceptance 只能是 unknown，不能判定为通过（sub-01 L52）。
3. **不直接执行 effect**：effect 走信任链 `catalog allowlist → intent → policy → approval → sandbox lease → executor → provenance → receipt`（MASTER L94）；无完整链路不执行（MASTER L25/L96）。

---

## 7. hard fail 与数值闸门

**hard fail 情形（MASTER L68 + sub-01 L79/L88）**：
- 状态/动作/意图丢失、双 owner、unknown 未保留 → hard fail。
- 必需语义缺失或改变 = 失败；unknown 被压成空值、source 丢失、动作无法重放 = 失败（sub-01 L79）。
- adapter 修改 owned 字段（intent/acceptance）= 失败（sub-01 L88）。

**数值闸门（sub-01 L100，0 容忍）**：
- 核心状态/动作/意图**静默丢失 = 0**；
- **未声明 warning = 0**（warning 须含字段路径、owner、source、原因、处置建议，sub-01 L58）；
- **离线恢复成功率 = 100%**。

**warning 分类（sub-01 L100）**：分为「声明性 unknown」（合法，仅显式 warning，不得静默消失，sub-01 L94）与「阻断性未声明丢失」（闸门失败）。

**测试覆盖基线（sub-01 L94）**：空 screen、缺 required、未知字段、重复/冲突 action、超大字段、并发转换。

---

## 8. 上下游契约义务

- **向上（1-2-1 / 1-2-2）**：六类 schema 的 `owner/source/requiredness/unknown policy` 已冻结，本文件在其上施加 ui-flow/v1 的实体语义、转移模型与迁移规则；三条不变量沿用 1-2-2，不得弱化。
- **向下（1-2-4）**：本文件所有「静默丢失=0 / 未声明 warning=0 / 离线恢复=100% / unknown 保留 / 语义 round-trip」均为**待验证声明**，由 golden fixtures 在 1-2-4 实测，本文件不构成已通过证据。
- **跨子文档约束（sub-01 L154）**：`sub-02` 只消费 canonical artifact；`sub-03` 只能通过 AdapterBoundary v1；`sub-04` 的 provenance/approval 作为 artifact 输入；`sub-05` 的 receipt 由本注册表定义 canonical owner。
