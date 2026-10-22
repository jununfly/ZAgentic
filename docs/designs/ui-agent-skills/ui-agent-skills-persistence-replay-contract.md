# UI-Agent Skills · 1-3-4 持久化与可恢复重放契约

> **冻结文档。** 本文件定义 `plan` / `decision` / `revision` / `handoff` / `receipt` 五类编排记录的持久化结构、存储模型、跨会话重放协议、崩溃恢复不变式与一致性闸门。

> 本文件属于**计划层交付物**：不写存储引擎、不写重放代码、不跑断言。存储引擎与重放实现的**实际载体是 `zj-roadmap-driven` 技能**（single-file JSON + SQLite 双 carrier），并非 ui-agent-skills 的 1-6 节点；G-19..G-25 实测证据由 **1-9-5**（真实 `zj-roadmap-driven` skill + fixture 验证）回写（§6）。

> **与 1-3-1/2/3 的边界**：本节点只规定「记录什么、怎么存、怎么重放重建、崩溃怎么恢复」，不实现。PlanRecord 字段直接复用 1-3-2 §5.1，不重定义；run/lease/handoff 事件语义见 1-3-3，本文件只规定它们必须落盘成何种记录。

---

## 0. 来源与范围

- **权威源**：
  - `sub-02-skill-orchestration.md` B/L31（planner 纯函数持久化要求）、L79/L112（确定性 + 100 次重放同 hash）
  - `MASTER.md` L56（恢复基线 = 最后完整 canonical revision）、L99（恢复失败不得伪造成功）
  - 1-3-2 §5（Plan 结构与 `plan_hash`）、1-3-3 §2.1/§4/§5.2（run/lease/handoff 事件与 fencing 持久化要求）
  - `ui-agent-skills-golden-fixtures-spec.md`（离线/adapter 删除恢复协议、GF-10/GF-11）
- **不在本节点**：存储引擎选型与实现、重放代码、并发控制实现、任何可执行断言。存储引擎的实际实现归 `zj-roadmap-driven` 技能；本契约 G-19..G-25 的实测回写归 **1-9-5**（§6 已完成）。
- **退出判据**：跨会话可从 `revision`、`decision`、`plan`、`receipt`、`handoff` 重建当前工作 —— 由 §4 重放协议 + §6 闸门覆盖，属实测项，本节点不宣称通过。

---

## 1. 记录类型总览（五类，均 append-only、不可变）

| 类型 | 生产者（来源节点） | 触发时机 | 不可变 | 重建用途 |
|------|------------------|----------|--------|----------|
| `PlanRecord` | resolver（1-3-2） | 每次路由判定产生一次结论 | ✅ 不可变 | 重建 plan 状态（路由层） |
| `DecisionRecord` | human / planner | Human gate 选择、关键规划决策 | ✅ 不可变（只 append） | 审计与 replay 依据 |
| `RevisionRecord` | orchestrator | 每次 canonical artifact 提交 | ✅ 不可变 | 恢复基线 / 回退点 |
| `HandoffRecord` | orchestrator | Human gate / 跨进程交接 | ✅ 不可变 | 交接审计与 fencing 快照 |
| `ReceiptRecord` | verifier（1-9） | 验证产出 | ✅ 不可变 | 验收证据 |

> **核心原则**：记录一经写入**禁止原地更新**。任何「修改」都表现为一条新记录（新 `revision_id` / 新 `decision_id`），旧记录保留以供审计与重放。这与 1-3-2 的「plan 不可重入、重放必须同 hash」和 1-3-3 的「run 状态不反向改写 plan_hash」构成一致的不可变事实源模型。

---

## 2. 存储模型：append-only 日志 + canonical revision 快照

- **主存储 = append-only 事件日志**：五类记录按全局单调序号（逻辑时钟，非墙钟）顺序追加。逻辑序号由持久化的 `max_log_seq` 单调递增产生，**不依赖时间戳**（时间戳仅作审计，见 §3）。
- **canonical revision = 恢复唯一基线**：最后一个 `hash` 校验通过的 `RevisionRecord`（其 `artifact_revision` 指向一个完整、可校验的 canonical artifact 快照）。它是崩溃恢复、adapter 删除恢复、离线恢复的唯一起点（`MASTER.md` L56）。
- **索引为冗余派生，禁止当事实源**：任何「最新状态视图」都由日志 + canonical revision 重算得到（沿用 1-3-3 的教训：索引只是缓存，不能拿来做真相读）。
- **读路径**：重建当前工作 = 加载 canonical revision → 校验哈希 → 重放其后所有事件（§4）。写路径：新事件 append 到日志，必要时推进 canonical revision。

---

## 3. 记录 Schema（字段 + 是否进确定性哈希）

> 约定：`*_at` 时间戳与 `request_id` / `decided_by` 等**审计字段一律不进任何 hash**，否则破坏 1-3-2 的「同输入 100 次重放同 hash」闸门。

### 3.1 PlanRecord（字段复用 1-3-2 §5.1，此处只补持久化元数据）
| 字段 | 来源 | 进 hash | 说明 |
|------|------|---------|------|
| `plan_id` | 1-3-2 §5.1 | — | `pf-<fp[0:12]>-<stage>-<attempt>` |
| `plan_hash` | 1-3-2 §5.3 | 自身即 hash | 重放后须与之逐字节一致（闸门 G-19） |
| `route_fingerprint` | 1-3-2 | ✅ | 规范化输入指纹 |
| `stage_id` / `owner_skill` | 1-3-2 | ✅ | 路由结论 |
| `decision` | 1-3-2 | ✅ | 选择 rationale / 被拒候选 |
| `artifact_ref` | 1-3-2 | ✅ | `{artifact_kind, revision, schema_version}` |
| `next_action` | 1-3-2 | ✅ | ≤1 个（闸门 G-3 继承） |
| `status` | 1-3-2 | ✅ | PLANNED / WAITING_FOR_HUMAN / ... |
| `created_at` / `request_id` | 1-3-2 | ❌ | 审计用 |

### 3.2 DecisionRecord
| 字段 | 进 hash | 说明 |
|------|---------|------|
| `decision_id` | — | 确定性派生 `dc-<hash[0:12]>` |
| `node_id` | ✅ | 关联 roadmap 节点（如 `1-3-4`） |
| `question` | ✅ | 被决策的问题 |
| `chosen_option` | ✅ | 选定项 |
| `rejected_options` | ✅ | 被拒项清单 |
| `rationale` | ✅ | 决策理由 |
| `decided_by` | ❌ | human / agent（审计） |
| `plan_id` | ✅ | 关联 PlanRecord |
| `decided_at` | ❌ | 审计时间戳 |

### 3.3 RevisionRecord（canonical 链）
| 字段 | 进 hash | 说明 |
|------|---------|------|
| `revision_id` | — | 确定性派生 `rv-<hash[0:12]>` |
| `parent_revision_id` | ✅ | 构成不可变链；根 revision 的 parent = null |
| `artifact_kind` / `artifact_revision`(sha256) | ✅ | 指向 canonical artifact 快照 |
| `schema_version` | ✅ | 规范化 semver |
| `contributor` (owner_skill) | ✅ | 谁提交 |
| `change_summary` | ✅ | 变更摘要 |
| `hash` | 自身即 hash | 整条记录哈希，用于恢复校验 |
| `created_at` | ❌ | 审计 |

> 回退只能到**最近一个已验证的只读 revision**，不得跨 stage 回退（继承 1-3-3 §5.2）。

### 3.4 HandoffRecord
| 字段 | 进 hash | 说明 |
|------|---------|------|
| `handoff_id` | — | 确定性派生 `ho-<hash[0:12]>` |
| `from_stage` / `to_stage` | ✅ | 交接边界 |
| `kind` | ✅ | `HUMAN_GATE` / `PROCESS_BOUNDARY` |
| `payload` | ✅ | 决策 / 补齐的上下文 |
| `approved_by` | ❌ | 审计 |
| `decision` | ✅ | `approve` / `deny` / `timeout→BLOCKED_HANDOFF` |
| `fencing_snapshot` | ✅ | 交接时的 `max_token` 快照（供重启后 fencing 校验，见 §5） |
| `created_at` | ❌ | 审计 |

### 3.5 ReceiptRecord（对应 exit 判据的 receipt）
| 字段 | 进 hash | 说明 |
|------|---------|------|
| `receipt_id` | — | 确定性派生 `rc-<hash[0:12]>` |
| `plan_id` | ✅ | 关联 PlanRecord |
| `verification_result` | ✅ | `pass` / `fail` / `quarantine` |
| `evidence_ref` | ✅ | 证据引用 |
| `verifier` | ❌ | 审计 |
| `created_at` | ❌ | 审计 |

---

## 4. 跨会话重放协议（重建「当前工作」）

**输入**：持久化日志 + 最后一个 canonical `RevisionRecord`。

**步骤**：
1. 加载 canonical revision，校验其 `hash`（失败 → `recovery error`，禁止继续）。
2. 以 canonical revision 为基线，按 `log_seq` 升序重放其后的 `PlanRecord` / `DecisionRecord` / `HandoffRecord` / `ReceiptRecord`。
3. 重建 plan 状态（路由层）与 run 状态（执行层）；二者关联键 = `plan_id + route_fingerprint`（沿用 1-3-3 §2.1）。
4. 校验：重放后每个 `PlanRecord.plan_hash` 必须等于其存储值（闸门 G-19）。

**确定性（继承 1-3-2 G-4 / 1-3-3 G-17）**：同一份日志 100 次顺序随机重放，必须得到逐字节相同的 `plan_hash`、相同的 `next_action`、相同的终态。

**幂等**：重放可重复执行任意次，不产生副作用、不重复写入。重放使用的幂等键同 1-3-3 §3：`sha256(route_fingerprint + stage + artifact_id + artifact_revision)`，`attempt` 不进键。

---

## 5. 崩溃恢复与不变式

- **重启后必须从 canonical revision 恢复**，不得依赖内存态。
- **`fencing_token` 的 `max_token` 必须持久化**（1-3-3 §4.1 教训：若不持久化，进程重启后 fencing 失效，僵尸写漏洞重新打开）。`HandoffRecord.fencing_snapshot` 与日志中的 lease 事件共同保证重启后旧 token 仍被拒（闸门 G-24）。
- **恢复失败 = `recovery error`，禁止伪造成功**（MASTER L99 / golden-fixtures §recovery 语义）。
- **离线恢复**：无远程、无 adapter 时仍能从本地 canonical revision 重建 flow、恢复状态并重放动作（golden-fixtures GF-10/GF-11）。
- **adapter 删除恢复**：删除 adapter 后仍可从最后完整 canonical revision 恢复；恢复失败 = fail，不掩盖（MASTER L56）。

---

## 6. 一致性闸门（实测，归 1-9-5 回写）

> **实测主体**：`zj-roadmap-driven` 存储引擎（single-file JSON + SQLite 双 carrier），2026-10-22 用临时 fixture 实测（harness：原型 `verify_g19_g25.py`，**已随 skills-outputs/ 清理，2026-10-22**；结果：`gate-results.json`）。
> 该引擎**非**契约字面的「append-only 日志 + 重放 + parent-linked revision 链 + HandoffRecord」模型，而是「canonical 状态即事实源 + 单点 canonical revision 哈希 + lease 事件审计」模型。下表结论按**实际可验证的不变式**给出，机制差异见「实测结论与机制差异」段。

| 闸门 | 契约字面描述 | 实测结论 | 样本 | 说明 |
|------|--------------|----------|------|------|
| **G-19** | 跨会话重放后 `plan_hash` 与存储值一致 | **PASS（代理）** | 48 | 引擎无独立重放日志；以 `current_revision` 跨重启逐字节一致 + `canonical_json` 确定性作为等效代理 |
| **G-20** | 重放幂等（无重复写/无孤儿记录） | **PASS（代理）** | 48 | 多次 reload 记录数稳定，无附加副作用 |
| **G-21** | `decision` 不可变（无 update，只 append） | **PASS** | 24 | `update_node` 无 decisions 形参；原地修改次数 = 0 |
| **G-22** | `revision` 链完整（`parent_revision_id` 无断点） | **PARTIAL** | 48 | 单点 `current_revision` 哈希跨重启确定；**无 parent-linked 链**，字面「重建全量 revision 链」在本引擎 N/A |
| **G-23** | `handoff` 审计完整（每次 gate 有 `HandoffRecord`） | **PARTIAL** | 40 | 无独立 `HandoffRecord`；fencing 审计由 lease events（claimed/stolen/released + `fencing_token`）承载，持久化、可溯源 |
| **G-24** | 崩溃重启后 `fencing max_token` 恢复正确（旧 token 仍拒） | **PASS** | 24 | 侧车持久化 `fencing_token`；重启后旧 token 写拒（E_LEASE_HELD）、新 token 放行，≥10 次重启样本 100% |
| **G-25** | 恢复失败输出 `recovery error` 而非伪成功 | **PASS** | 40 | `load()` 对缺失/损坏文件抛 `FileNotFoundError` / `JSONDecodeError`，非静默成功 |

> **实测汇总**：7 闸门全部被测；5 PASS（其中 G-19/G-20 为代理验证）、2 PARTIAL（G-22/G-23，安全性质满足但字面机制未实现），0 FAIL。
> **1-3-4 节点 open 标注**：证据已回写，故解除「未实测」状态；但因 G-22/G-23 为 PARTIAL（机制差异），本节点标记为「**gate-evidence-in（with caveats）**」，而非无条件通过——契约字面机制（append-only 重放日志 / parent-linked revision 链 / HandoffRecord）在 `zj-roadmap-driven` 中未实现，若 ui-agent-skills 后续确需该字面机制，须另立项实现而非依赖本引擎。

---

## 7. 上下游义务

- **上游（产出记录）**：1-3-2 resolver 产 `PlanRecord`；1-3-3 run/lease/handoff 事件产 `HandoffRecord` 与 `RevisionRecord`；1-9 verifier 产 `ReceiptRecord`；规划期 Human 决策产 `DecisionRecord`。
- **下游（落地与验证）**：存储引擎与目录/SKILL.md 落地的**实际载体是 `zj-roadmap-driven` 技能**（single-file JSON + SQLite 双 carrier，满足本文件 §2/§3/§4），**并非** ui-agent-skills 的 1-6 节点（1-6 = 十个 UI skills 的契约化本地闭环，与存储引擎无关）；G-19..G-25 与 exit 判据实测证据由 **1-9-5** 用真实 `zj-roadmap-driven` skill + fixture 回写（§6 已完成）。

---

## 8. 退出判据对照

| 退出判据原文 | 覆盖位置 |
|--------------|----------|
| 跨会话可从 `revision` 重建 | §3.3 + §4 步骤 1–2 + §2 canonical revision |
| 跨会话可从 `decision` 重建 | §3.2 + §4 步骤 3 |
| 跨会话可从 `plan` 重建 | §3.1 + §4 步骤 3–4（G-19） |
| 跨会话可从 `receipt` 重建 | §3.5 + §4 步骤 3 |
| 跨会话可从 `handoff` 重建 | §3.4 + §4 步骤 3（G-23） |

全部由重放协议 + 闸门覆盖；实测归 1-9。
