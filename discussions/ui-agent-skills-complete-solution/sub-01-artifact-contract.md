# 子问题：核心 artifact 与语义契约

## 上下文

- **所属主文档：** [../MASTER.md](./MASTER.md)
- **本子问题独立性：** 只定义 ZAgentic-owned artifact、字段责任、状态/动作语义和转换不变式；不决定 skill 调用顺序，也不评价某个具体 adapter 的采用价值。
- **成功判据：** 为 `UI-BRIEF.md`、`UI-DESIGN.md`、`ui-flow/v1`、review、verification receipt、handoff 建立字段/owner/source/unknown 表；至少一个典型 flow 能在 adapter 转换后保留状态、动作和意图，丢失字段产生 warning，外部服务关闭后仍能本地恢复。
- **声明必需角色集：** B,C,A,T,D

## 待讨论问题（scope 草案）

- Q1：哪些 artifact 和字段必须由 ZAgentic 拥有，哪些只能是 adapter 投影？
- Q2：`ui-flow/v1` 如何表达 screen、state、component、intent、acceptance、unknown 和 source，才能安全演进？
- Q3：如何用 canonical fixture、往返转换和 warning 证明 adapter 没有静默丢失语义？

## Agent viewpoints（独立视角 — 须跨会话独立 Agent）

### 视角：B（技术经理 / 可落地）
`视角来源: 跨会话独立Agent`

**观点 1**

- 发现：原文 L6-L7 将范围限定为 ZAgentic-owned artifact，并要求为六类 artifact 建立 `field/owner/source/unknown` 表，但尚未规定字段的唯一责任方、交付顺序或“完成”的判定；原文 ## 待讨论问题（scope 草案）的 Q1 仍处于待决状态。
- 影响：若没有唯一 owner，adapter 可能反向成为语义事实源，出现字段重复维护、变更互相覆盖和责任空档。按六类 artifact、一个 adapter、一个典型 flow 估算，不先完成责任矩阵会产生 2-3 人日返工；外部服务关闭时也无法判断应恢复哪一份本地数据。
- 建议：先建立契约责任矩阵：`screen/state/component/intent/acceptance/unknown/source` 等语义字段由 ZAgentic 契约维护者拥有，adapter 只能拥有 provider ID、渲染配置和投影映射；每个字段必须且只能有一个 owner，并标注 canonical source、是否必需、未知值策略及回退值。以 1-2 人日完成矩阵，验收条件是六类 artifact 无未分配字段、无多 owner 字段，且 adapter 删除后可由本地 artifact 重建状态、动作和意图；无法确定归属的字段进入 `unknown` 并阻断发布。

**观点 2**

- 发现：原文 L12-L14 分别提出 artifact 归属、`ui-flow/v1` 字段表达和转换证明三个问题，但原文尚未给出 schema 版本边界；原文 L7 只要求典型 flow 保留状态、动作和意图，并未规定未知字段、来源信息或演进失败时的行为。
- 影响：如果 `v1` 把未知字段当作可忽略扩展，新增组件或状态会在旧 adapter 中静默丢失；如果直接修改既有字段含义，旧 fixture 即使格式校验通过也会产生语义漂移。关键路径应是“责任矩阵 → schema 定稿 → adapter 转换”，至少需要 3-4 人日实现可验证 schema。
- 建议：将 `ui-flow/v1` 定义为带稳定 ID 的规范包：`screen` 描述界面边界，`state` 描述可观察状态，`intent` 明确触发动作及前置/后置状态，`acceptance` 引用可验证断言，`source` 记录产生者与版本，`unknown` 必须包含原始值、原因和所在路径。v1 内只允许向后兼容的加字段；改变既有语义必须升主版本并提供迁移器。

**观点 3**

- 发现：原文 L7 已明确要求至少一个典型 flow 在 adapter 转换后保留状态、动作和意图，丢失字段产生 warning，并能在外部服务关闭后本地恢复；原文 L14 尚未定义 canonical fixture、往返方向、warning 阈值或失败处置。
- 影响：仅检查“转换成功”无法发现静默丢字段；把所有差异降为 warning 会让关键语义损失与 provider 元数据差异混在一起。没有固定阈值时，测试人员、adapter 维护者和契约维护者会对“完成”各自解释。
- 建议：建立 canonical fixture → adapter 投影 → ZAgentic canonical 回转的双向测试，对规范化后的 `state/action/intent/acceptance` 做集合等价检查；关键语义静默丢失数必须为 0，任一关键字段丢失直接 hard fail，非关键 provider 字段丢失逐字段 warning，`unknown` 数量与 warning 数量一一对应；验收至少包括 1 个正常 flow、3 个负例和一次离线恢复。

### 视角：C（产品专家 / 用户价值·生态竞品）
`视角来源: 跨会话独立Agent`

**观点 1**

- 发现：Q1 只提出哪些 artifact/字段应由 ZAgentic 拥有，但原文 L6 同时排除了具体 adapter 采用价值；文档没有定义目标用户、核心任务或相对替代方案。
- 影响：无法证明“自有 canonical artifact”解决了真实用户的迁移、协作或恢复痛点，也无法判断哪些字段值得承担长期维护成本，容易把 adapter 内部复杂度误当成用户价值。
- 建议：补充“用户任务—替代方案—价值证据”表，至少对比 vendor-native 导出、纯 Markdown/手工交接和 ZAgentic canonical artifact；只有直接支撑跨 adapter 迁移、意图保真或服务关闭后恢复的字段才列为 ZAgentic-owned，其余列为 adapter projection。验收应包括该 flow 脱离原 adapter 后仍能本地打开并继续判断下一步。

**观点 2**

- 发现：Q2 要求 `ui-flow/v1` 表达 screen、state、component、intent、acceptance、unknown 和 source（原文 L13），但没有规定字段必需性、未知值语义、来源可信度或版本演进方式。
- 影响：不同 adapter 可能把“未提供”“不支持”“尚未确认”都编码为空值，导致用户误以为设计已经确定；版本升级后即使结构可解析，也可能改变 acceptance 或 state 的产品含义。
- 建议：把字段分成 required、optional、unknown 三类，并固定 owner、source、语义版本和 fallback。`unknown` 必须带原因与来源，不能等同于空字符串；关键字段为 unknown 时 acceptance 只能是 unknown，不能判定为通过；adapter 无法表达 required 字段时必须进入 warning/blocked 路径。

**观点 3**

- 发现：成功判据要求典型 flow 经 adapter 转换后保留 state、action、intent，字段丢失产生 warning，并能在外部服务关闭后本地恢复（原文 L7）；Q3 也要求 canonical fixture、往返转换和 warning（原文 L14），但没有给出阈值、warning 内容或失败时的写入策略。
- 影响：转换可能返回“成功”却静默丢失用户意图；warning 若没有字段路径、严重级别和处置责任，使用者无法判断是否可以继续交付，部分转换还可能覆盖原始 canonical artifact。
- 建议：建立语义比较器，required 字段静默丢失数必须为 0，任何丢失都必须生成包含字段路径、owner、source、原因和处理建议的 warning。转换失败不得覆盖 canonical 输入；服务不可用时必须从本地 artifact 恢复并展示未确认项，否则验收失败。

### 视角：A（架构师 / 约束）
`视角来源: 跨会话独立Agent`

**观点 1**

- 发现：原文 L6 将“ZAgentic-owned artifact、字段责任、状态/动作语义和转换不变式”纳入范围，但原文 L12 仍把 artifact/字段 owner 与 adapter 投影列为待决问题；原文 L7 明确要求建立 `field/owner/source/unknown` 表。
- 影响：如果只在 artifact 层标注 owner，而不在字段层标注 owner/source，adapter 很容易把外部默认值写回 canonical，形成隐式双主。外部服务关闭时也无法判断哪些字段可恢复、哪些只能显示 unknown。
- 建议：为每个字段建立强制注册表，包含 `owner`、`source`、读写方向、是否可缺省、unknown 表达和恢复策略；adapter 输出只能是候选 projection 或带版本的转换事件，不能直接覆盖 canonical 字段。字段无 owner/source、adapter-derived 被当作 canonical、服务关闭后无本地恢复路径时，必须契约失败。

**观点 2**

- 发现：原文 L13 要求 `ui-flow/v1` 表达 screen、state、component、intent、acceptance、unknown、source；原文 L7 要求转换后保留状态、动作和意图，但没有规定它们的边界、转换关系或版本兼容规则。
- 影响：若把 state、action、intent 混在组件属性或 screen 快照中，adapter 可能只保留最终视觉而丢失触发原因和可验证行为；把 unknown 用缺字段或 null 代替会混淆未知、未提供和明确为空。
- 建议：定义不可混淆的结构：screen/component 描述呈现对象，state 描述可观察状态，action 描述状态变化输入，intent 描述行为目的，acceptance 描述可判定结果；规定同一 `action + pre-state` 只能产生一个 canonical transition。新增字段若不能安全忽略则必须升版本并提供迁移器。

**观点 3**

- 发现：原文 L7 要求典型 flow 经 adapter 转换后保留状态、动作和意图并能本地恢复；原文 L14 要求 canonical fixture、往返转换和 warning，但没有给出语义等价口径。
- 影响：没有损失分类时，byte-level 差异可能被误判为失败，而 action/intent 丢失可能只被当成格式差异；必需字段丢失与可选字段不支持也会走同一 warning 路径。
- 建议：canonical fixture 固定覆盖 screen、state、component、intent、acceptance、source、unknown。必需语义缺失或改变 = 失败；可选字段不支持 = 逐字段 warning；unknown 被压成空值、source 丢失、动作无法重放 = 失败。服务关闭时仅凭本地 canonical artifact 重建 flow、恢复状态并重放动作，否则输出 recovery error。

### 视角：T（测试 / 质量）
`视角来源: 跨会话独立Agent`

**观点 1**

- 发现：原文 L6 将范围限定为 ZAgentic-owned artifact、字段责任和转换不变式；原文 L12 要求区分 owner 与 adapter 投影，但尚未给出可判定的 ownership 规则。
- 影响：若 ownership 只是文档约定，adapter 可以把必需字段当可选投影，验收无法区分合法 unknown 与转换丢失。
- 建议：为每个字段建立机器可校验的 `owner/source/required/unknown-policy` 表；ZAgentic-owned 且 required 的字段转换后必须 100% 保留，缺失即阻断；增加 `fixture-adapter-mutates-owned-field`，adapter 修改 intent 或 acceptance 时必须失败并报告字段路径。

**观点 2**

- 发现：原文 L13 要求 ui-flow 表达 screen、state、component、intent、acceptance、unknown、source，原文 L14 要求 canonical fixture、往返转换和 warning，但没有规定状态/动作/意图逐项不变式。
- 影响：只比较 JSON 可解析或字段数量相同，会漏掉 state 被合并、action 顺序改变、intent 丢失、acceptance 降级为描述等行为回归。
- 建议：定义逐项不变式：screen 标识、state 集合及转移、component 绑定、intent/action 参数、acceptance 条件和 source 可追溯；unknown 只能增加为显式 warning 不能静默消失。测试需覆盖空 screen、缺 required、未知字段、重复/冲突 action、超大字段和并发转换。

**观点 3**

- 发现：原文 L7 把字段 warning 与外部服务关闭后的本地恢复列为成功判据，但没有定义 warning 严重级别、恢复验证结果或回归门槛。
- 影响：真正的语义丢失可能与普通 unknown 混在一起；没有离线恢复测试时，服务正常期间通过的流程可能在 adapter 不可用时无法复现。
- 建议：将 warning 分为声明性 unknown 与阻断性的未声明丢失；建立“核心状态/动作/意图静默丢失=0、未声明 warning=0、离线恢复成功率=100%”闸门。每次 schema 或 adapter 修改都重跑 fixture 套件，失败时保留旧 artifact、标记验证失败，不得继续下游发布。

### 视角：D（数据 / 数据建模）
`视角来源: 跨会话独立Agent`

**观点 1**

- 发现：原文 L7 要求建立 `字段/owner/source/unknown` 表，但没有规定字段唯一标识、版本、必填级别和未知值保存规则；原文 L12 只提出 owner 与投影的区分。
- 影响：同名字段可能被不同 artifact 或 adapter 重复解释；投影回写时无法判断权威来源，未知字段还可能被静默删除，导致 ownership 漂移和不可审计。
- 建议：为每个字段建立不可变 `field_id`，强制记录 `owner、source、requiredness、schema_version、unknown_policy`。adapter 只能生成带 `projection_id` 和 `source_revision` 的派生数据，禁止覆盖 canonical；必需字段缺失数和静默丢弃数均必须为 0。

**观点 2**

- 发现：原文 L13 要求 ui-flow 表达 screen、state、component、intent、acceptance、unknown、source，但没有定义主键、引用关系、状态转移约束或存储形态。
- 影响：只适合展示的嵌套文档会造成重复实体、悬空引用和竞态更新；只存 adapter 输出又无法支持本地 diff、恢复和审计。
- 建议：采用“版本化 canonical 文件 + 可重建索引”两层模型；实体以稳定 ID 存储，引用只指向 ID，flow 用 `from_state、action、to_state、intent` 表达有向状态边；索引必须可由 canonical 重建，发现悬空引用、重复 ID 或非法状态边时拒绝提交。

**观点 3**

- 发现：原文 L14 要求 canonical fixture、往返转换和 warning，原文 L7 要求转换后保留状态、动作和意图，但没有规定幂等键和语义比较基线。
- 影响：重试可能生成重复 artifact，部分成功可能留下半套结果；文本相等比较会把合法重排误判为变化，也检测不到字段被默认化的语义损失。
- 建议：每次转换绑定 `(fixture_id, input_revision, adapter_version, mapping_version)` 作为幂等键，输出写入临时版本后原子提交；同一输入重复转换必须得到相同语义哈希和 warning 集合。恢复按“最后完整 canonical revision → 校验哈希 → 重建索引 → 重新生成 projection”执行，并覆盖服务关闭、进程中断、重复提交和并发提交。

## 主力AI 整合立场（主会话，非独立视角，低权重）

`视角来源: 同会话SubAgent(低权重)`

独立观点已通过 scope、架构和 UX 闸门。本题冻结“ZAgentic canonical artifact + 字段级 owner/source/unknown + 可验证转换不变式”的语义底座；adapter 只生成可删除的 projection。

1. 为 `UI-BRIEF.md`、`UI-DESIGN.md`、`ui-flow/v1`、review、verification receipt、handoff 建立字段注册表：`field_id/owner/source/requiredness/unknown_policy/read_write/recovery/schema_version`。screen/component/state/action/intent/acceptance 等语义字段由 ZAgentic 拥有；provider ID、渲染配置和映射只能在 adapter 命名空间中存在。

2. `ui-flow/v1` 分离呈现对象、可观察 state、action、intent 和 acceptance；稳定 ID 与 schema version 必须固定，未知值保留 `path/raw/reason/source`。必需字段缺失或语义改变 hard fail；可选 provider 字段只产生逐字段 warning。v1 只允许可安全忽略的加字段，破坏性变更必须升主版本并提供迁移器。

3. 建立 canonical fixture → adapter projection → canonical 回转的语义比较器；核心 state/action/intent/acceptance 静默丢失为 0，未声明 warning 为 0，unknown 必须保留；离线关闭 adapter 时从最后完整 canonical revision 校验哈希、重建索引和恢复 flow，成功率 100%。转换使用 `(fixture_id,input_revision,adapter_version,mapping_version)` 幂等键并原子提交。

4. 责任与回退：契约维护者拥有 schema/registry，adapter owner 只能维护映射，验证 owner 维护 fixture。任何 adapter 越权覆盖 canonical、把 unknown 压成空值、远程 ID 成为唯一索引或无法离线恢复，都拒绝写入并保留上一 canonical 版本。

## Human 对 Agent X 的拍板

| 轮次 | 视角 | 隔离方式 | Human 拍板 | 是否 conclusion | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 | B | 同 provider 跨会话 | 待拍板 | 否 | |
| 2 | C | 同 provider 跨会话 | 待拍板 | 否 | |
| 3 | A | 同 provider 跨会话 | 待拍板 | 否 | |
| 4 | T | 同 provider 跨会话 | 待拍板 | 否 | |
| 5 | D | 同 provider 跨会话 | 待拍板 | 否 | |

## conclusion（含沉淀指令）

- **子问题结论：** ZAgentic 必须拥有六类核心 artifact 的语义和字段责任；adapter 只能读、转换、渲染并生成可删除的 projection。`ui-flow/v1` 以稳定 ID、显式 state/action/intent/acceptance、字段级 source/owner/unknown 和 schema 版本作为 SSOT。
- **解法：** 先落字段注册表和 v1 schema，再用 canonical fixture 双向 round-trip 与语义比较器验证；核心语义静默丢失、未声明 warning 和离线恢复失败均为 0 容忍。版本/映射升级采用 schema lock、迁移器、幂等键和原子提交，失败保留旧 canonical。
- **remaining-risks 控制：** 未来 adapter 语义扩展和长期 schema skew 不能靠一次 v1 完全消除；通过 major 版本拒绝、明确 migration map、unknown/quarantine、golden fixture 重跑和 adapter removal test 控制。远程服务关闭时以本地 canonical 为唯一恢复路径。
- **沉淀指令：**
  - 改哪些 PRD / ADR / 文档：新增 Artifact Ownership & `ui-flow/v1` ADR，字段注册表、unknown policy、schema lock、semantic round-trip 和 offline recovery 写入契约文档。
  - 跨子文档约束登记：`sub-02` 只消费 canonical artifact；`sub-03` 只能通过 AdapterBoundary v1；`sub-04` 的 provenance/approval 作为 artifact 输入；`sub-05` 的 receipt 由该注册表定义 canonical owner。
  - 待删临时脚手架：本子文档 briefings 和 viewpoints 过程文件，待 `zj-docs-ontology` 分类；Human 确认前保留讨论目录。
- **状态协议：** DONE_WITH_CONCERNS

