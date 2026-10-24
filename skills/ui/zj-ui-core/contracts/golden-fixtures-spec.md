# Golden Fixtures 规范：字段保留 · semantic round-trip · 离线恢复 · schema lock（冻结版）

- **归属节点**：1-2-4（产品实现路线 · 计划层 · `exploit`），1-2 子树最后一片叶子。
- **文档性质**：契约冻结。本节点交付物为 **golden fixture 规范**（清单 / 覆盖矩阵 / 协议 / 闸门阈值），**不含产品代码落地，也不含可执行的 fixture 断言代码**——可执行断言待 Experience Version 把技能实现后再跑（该决策已 `decide` 落盘于 1-2-4 节点）。
- **依赖**：1-2-1（六类 schema v0.1）、1-2-2（编辑/patch/unknown 语义）、1-2-3（ui-flow/v1 六实体与迁移规则）。
- **同源约束**：保证边界与局限见 `guarantee-boundary.md`；毕业闸门与验收指标见 `graduation-gates.md`。
- **本文件版本**：v0.1（冻结）。

---

## 0. 范围与退出判据

> **退出判据原文**：golden round-trip、迁移、schema lock 和删除 adapter 后恢复测试通过。

本文件定义**如何证明** 1-2-1/1-2-2/1-2-3 中全部「待验证声明」：给出 fixture 清单、覆盖矩阵、三类协议（round-trip / 迁移·schema lock / 离线恢复）、warning 质量要求和数值闸门。

**交付物边界声明（重要）**：本规范是可执行的**验收依据**，不是已执行的验收结果。所有闸门值在 Experience Version 实现技能后由本规范驱动的 fixture 套件实测；本文件不构成"已通过"的证据。

---

## 1. 覆盖矩阵（基线）

**固定覆盖对象（sub-01 L79）**：canonical fixture 必须覆盖 `screen / state / component / intent / acceptance / source / unknown`。

**基线数量（sub-01 L37）**：验收至少包括 **1 个正常 flow + 3 个负例 + 一次离线恢复**。

**必测边界类别（sub-01 L94）**：空 screen、缺 required、未知字段、重复/冲突 action、超大字段、并发转换。

**失败分类（sub-01 L79）**：
- 必需语义缺失或改变 = **失败**（非 warning）；
- 可选字段不支持 = **逐字段 warning**；
- unknown 被压成空值、source 丢失、动作无法重放 = **失败**。

---

## 2. Golden fixture 清单（GF-01 … GF-11）

每条 fixture 定义：`输入 / 断言 / 失败分类`。

| ID | 内容 | 断言要点 | 失败分类 |
| --- | --- | --- | --- |
| GF-01 | 正常 flow round-trip | canonical → projection → canonical 回转后 `state/action/intent/acceptance` 语义集合等价 | 不一致 = fail |
| GF-02 | 缺 required 字段 | 必需字段缺失必须阻断 | **hard fail**（非 warning，sub-01 L79） |
| GF-03 | 未知字段 | 保留 `unknown` 四元组 `{path,raw,reason,source}` 并生成声明性 warning | 静默丢弃 = fail（MASTER L53） |
| GF-04 | adapter 越权修改 owned 字段 | adapter 修改 `intent`/`acceptance` 必须失败并报告字段路径 | **hard fail**（sub-01 L88） |
| GF-05 | unknown 被压成空值 | 不得将 unknown 编码为空字符串/null | **fail**（sub-01 L79） |
| GF-06 | 重复/冲突 action | 同一 `action + pre-state` 只允许一个 canonical transition | 拒绝提交（sub-01 L73/L115） |
| GF-07 | 并发转换 | 幂等键相同输入的并发提交不得产生重复 artifact 或半套结果 | 违反幂等 = fail（sub-01 L121） |
| GF-08 | 迁移 | v1 向后兼容加字段通过；破坏性变更须升主版本并提供迁移器 | 无迁移器的破坏性变更 = fail（sub-01 L31/L150） |
| GF-09 | schema lock 重跑 | schema/adapter 修改后重跑全套；失败保留旧 artifact、禁止下游发布 | 越权推进 = fail（sub-01 L100/L150） |
| GF-10 | 离线恢复 | 服务关闭时仅凭本地 canonical 重建 flow、恢复状态并重放动作 | 无法恢复 = **recovery error**（sub-01 L79） |
| GF-11 | adapter 删除恢复 | 删除 adapter 后仍可从最后完整 canonical revision 恢复 | 恢复失败 = fail（MASTER L56、sub-01 L135） |

---

## 3. Semantic round-trip 协议

**双向路径（sub-01 L37）**：`canonical fixture → adapter 投影 → ZAgentic canonical 回转`。

**等价口径（sub-01 L37）**：对**规范化后**的 `state / action / intent / acceptance` 做**集合等价检查**，不是字段数量比较，也不是 byte 相等。

**禁止 byte 相等比较（sub-01 L120）**：文本相等会把合法重排误判为变化，也检测不出字段被"默认化"的语义损失。改用**语义哈希**：同一输入重复转换必须得到相同语义哈希与 warning 集合（sub-01 L121）。

**逐项不变式（sub-01 L94）**：screen 标识、state 集合及转移、component 绑定、intent/action 参数、acceptance 条件、source 可追溯；`unknown` **只能增加为显式 warning，不能静默消失**。

---

## 4. 幂等与原子提交

**幂等键（MASTER L55 + sub-01 L121）**：每次转换绑定
`(fixture_id, input_revision, adapter_version, mapping_version)`。

**原子提交（sub-01 L121）**：输出先写入**临时版本**，校验通过后**原子提交**；避免部分成功留下半套结果。

**重复转换一致性（sub-01 L121）**：同一输入重复转换必须得到**相同语义哈希和 warning 集合**；转换失败**不得覆盖 canonical 输入**（sub-01 L58）。

---

## 5. 迁移与 schema lock 流程

**版本规则（sub-01 L31/L131/L150）**：
- v1 **仅允许向后兼容的加字段**；新增字段若不能安全忽略则必须升主版本。
- 破坏性变更 → 升**主版本**并提供**迁移器（migrator）**；`major` 版本未迁移即拒绝。

**schema lock（sub-01 L150/L154）**：schema lock + golden fixture 共同锁定契约。

**重跑与阻断（sub-01 L100）**：每次 schema 或 adapter 修改都重跑 fixture 套件；失败时**保留旧 artifact、标记验证失败，不得继续下游发布**。

**残留风险处置（sub-01 L151）**：长期 schema skew 靠 major 版本拒绝 + 明确 migration map + unknown/quarantine + golden fixture 重跑 + adapter removal test 控制。

---

## 6. 离线恢复与 adapter 删除恢复协议

**恢复基线（MASTER L56）**：adapter 删除、远程服务关闭或网络断开时，**最后一个完整 canonical revision 是唯一恢复路径**。

**恢复流程（sub-01 L121）**：
`最后完整 canonical revision → 校验哈希 → 重建索引 → 重新生成 projection`。

**必须覆盖的场景（sub-01 L121）**：服务关闭、进程中断、重复提交、并发提交。

**adapter removal test（sub-01 L135）**：adapter 删除后仍须能由本地 canonical 恢复；任何 remote ID 不能成为唯一索引。

**失败语义（sub-01 L79）**：服务关闭时仅凭本地 canonical artifact 重建 flow、恢复状态并重放动作，否则输出 **recovery error**——不得伪造成功（MASTER L99）。

---

## 7. warning 质量与分类

**warning 五要素（sub-01 L58）**：每条 warning 必须包含
`字段路径 / owner / source / 原因 / 处理建议`。

**两类区分（sub-01 L100）**：
- **声明性 unknown**（合法）：显式暴露不确定性，仅产生 warning，不得静默消失；
- **阻断性未声明丢失**（闸门失败）：关键语义被静默丢弃。

**unknown 与 warning 对应（sub-01 L37）**：`unknown` 数量与 warning 数量**一一对应**，不能出现"unknown 存在但无 warning"或反之。

---

## 8. 数值闸门与 fail-closed

**闸门（0 容忍，MASTER L54 + sub-01 L100）**：

| 指标 | 阈值 |
| --- | --- |
| 核心 state/action/intent/acceptance **静默丢失** | **0** |
| **未声明 warning** | **0** |
| **离线恢复成功率** | **100%** |
| 必填语义字段**保留率** | **100%**（MASTER L54） |
| unknown 四元组**保留率** | 100%（不可压空） |

**fail-closed（MASTER L101）**：policy / catalog / manifest 不可用时**失败关闭**；`offline simulator` 与 `deny-first fixtures` 在**无网络、无凭据、无外部设计工具**时仍必须可运行。

**通过判据（本节点退出判据收口）**：GF-01…GF-11 全部按断言通过，且上述闸门全部达标 → 1-2-4 达成。

---

## 9. 上下游契约义务

- **向上（1-2-1 / 1-2-2 / 1-2-3）**：本规范消费三者的冻结声明（schema 字段表、编辑/patch/unknown 语义、ui-flow/v1 六实体与迁移规则），把其中所有「待验证声明」转为可判定断言。三条不变量（deny-first / unknown 四元组 / 不直接执行 effect）在全部 fixture 中保持有效，不得弱化。
- **本节点为 1-2 整体退出判据收口**：1-2-4 打勾后，1-2（Canonical artifact 契约与 ui-flow/v1）可整体置 completed。
- **向下（后续实现阶段）**：Experience Version 实现 `zj-ui-flow` 等技能时，须按本规范建立 fixture 套件并实测闸门；实测结果回写 roadmap 作为 1-2 的真实验收证据（届时若出现偏差，须显式隔离并追踪，不得静默标为"已接受"）。
