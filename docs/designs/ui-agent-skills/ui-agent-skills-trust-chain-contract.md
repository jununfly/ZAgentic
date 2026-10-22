# UI Agent Skills — Policy→Approval→Sandbox Lease→Executor 信任链契约（1-4-2）

> 路线图节点：1-4-2（Trust boundary 路线第二片叶）
> 层：plan（仅冻结契约，不落地产品代码）
> 权威源：sub-04-trust-boundary.md（DONE_WITH_CONCERNS）、MASTER.md L25/L94-101、跨视角 B/A/T/S/L 整合立场
> 配套：1-4（trust chain 总节点）、1-4-1（catalog allowlist / effect intent）、1-4-3（provenance / asset-manifest / redaction / quarantine）、1-4-4（deny fixtures）

## 0. 定位与 Trust Chain 位置

唯一信任链（MASTER L94）：

`catalog allowlist → intent → policy → approval → sandbox lease → executor → provenance → receipt`

本节点冻结**中间四环**：`policy` → `approval` → `sandbox lease` → `executor`（单入口、deny-first）。上游意图（intent）由 1-4-1 生产并携带 `catalog_id/version/params_digest/request_hash/credential_refs`；本节点把 intent 转成"能否执行"的受控判定，并产出唯一可被 executor 消费的 `lease`。本节点**不**接管 provenance（归 1-4-3）与 deny fixture（归 1-4-4）。

Scope 边界：plan 层。本节点**只定义契约**（policy 判定顺序、approval 绑定结构、lease 签发/校验、executor 单入口语义、审计记录 schema、硬闸门），**不写** policy engine、approval service、sandbox 或 executor 代码；真实实现归 1-6（目录与 SKILL.md 落地）与 1-9（真实 skill + fixture 运行）。

## 1. 核心不变量

- **P1 — 单入口 deny-first**：所有 effect（代码执行、MCP、网络、凭据、截图上传、Figma/远程写回）**只能**经 executor 一个入口触发；任何绕过 executor 直接产生副作用的路径都是契约违规。默认全 deny，仅当 policy→approval→sandbox lease 全链通过才放行（sub-04 结论；A-观点1）。
- **P2 — policy engine 是 allow/deny 唯一事实源**：决策顺序固定为 `capability boundary → sandbox profile → approval policy`；判定结果（含 `reason_code`）是 executor 的唯一放行依据，任何 skill/adapter 不得自行改写（A-观点1；B-观点1；sub-04 沉淀指令：policy engine = allow/deny 唯一来源）。
- **P3 — approval 强绑定、不可复用**：approval 必须绑定 `catalog_id+version + action + params_digest + target + data_class + credential_scope + TTL + intent_hash`；不得跨版本、跨目标、跨 intent 复用；过期、重复、跨 intent 一律拒（A-观点1；L-观点1；T-观点1）。
- **P4 — lease 短时 + 带 fencing token**：sandbox lease 由 policy engine 签发，短时有效，携带 `capabilities / egress / credential_refs / file_roots / process_whitelist / time_window` 与单调递增 `fencing_token`；executor 校验 lease 与 intent/catalog 版本/params hash 一致，旧 token 写入一律拒（沿用 1-3-3 租约 fencing 语义；A-观点1/3）。
- **P5 — executor 是 lease 校验唯一入口**：executor 自身不生成放行决策，只校验"由 policy engine 签发且与 intent/catalog 版本/params hash 一致的短时 lease"，并写入每次 decision/approval/lease/execution 审计（A-观点1；sub-04 沉淀：executor = lease 校验唯一入口）。
- **P6 — fail closed**：policy engine、catalog、approval service 或 lease store 任一不可用时，运行失败（不得执行、不得生成成功产物），不模拟成功、不返回默认 allow（MASTER L101；S-观点4）。
- **P7 — 无 secret 泄漏**：secret 只经短时、最小 scope 的 credential broker 注入引用（ref），禁止出现在 prompt、产物、日志、截图或 audit 记录中（B-观点2；A-观点3；L-观点2）。
- **P8 — 幂等 / 可重放**：同一 `(intent_hash, lease)` 重放多轮只产生一份副作用；远程写回带 `idempotency_key`；审计记录可按 `execution_id` 顺序重建判定链（T-观点5；C-观点2）。

## 2. Policy Engine 契约

### 2.1 输入与判定顺序

输入：1-4-1 产出的 `intent` + 其引用的 catalog 条目。

判定顺序（不可跳过、不可重排）：

1. **capability boundary**：intent 的 `action/target/data_class` 是否落在 catalog 条目的 `required_capabilities` 与 `risk_class` 允许范围；越界 → `deny`。
2. **sandbox profile**：根据 capability boundary 选择 sandbox profile（file root、process 白名单、网络开关、time window）；无法初始化 sandbox → 硬阻断。
3. **approval policy**：按 risk_class 决定是否需要 approval；高风险动作（凭据读取、网络 egress、Figma/远程写回、敏感截图上传）必须由 approval 显式授权并绑定 `request_hash`；缺 approval 或 approval 不匹配 → `deny`（B-观点1；A-观点1）。

### 2.2 输出：decision record

policy engine 输出一条不可伪造的 `decision_record`（schema 见 §6），字段至少：`policy_version`、`catalog_id/version`、`intent_hash`、`capability_decision`、`approval_required`、`sandbox_profile`、`reason_code`、`actor`、`timestamp`。

- `reason_code` 取自稳定枚举（`CATALOG_MISS` / `CAPABILITY_ESCALATION` / `SANDBOX_INIT_FAIL` / `APPROVAL_MISSING` / `APPROVAL_MISMATCH` / `APPROVAL_EXPIRED` / `LEASE_INVALID` / `ALLOW`）。
- 任一缺失即 `deny`，不进入 approval/sandbox 阶段（S-观点1：未注册/unknown/intent 不匹配/审批过期/范围不符/sandbox 初始化失败/证据缺失均硬阻断）。
- policy engine 不可用时返回 `deny + reason_code=ENGINE_UNAVAILABLE`，不得模拟成功（P6）。

## 3. Approval 契约

### 3.1 绑定结构

approval 必须显式绑定以下对象（缺任一即非法，下游 lease 不予签发）：

| 绑定字段 | 来源 | 约束 |
|---|---|---|
| `catalog_id` + `catalog_version` | intent | 与 intent 引用一致 |
| `action` | intent | 属于 catalog 条目 allowed action |
| `params_digest` | intent（`sha256(params_canonical)`） | 与 intent 不一致 → 拒 |
| `target` | intent | 精确资源/文件/组件标识 |
| `data_class` | intent | `public`/`internal`/`sensitive`；sensitive 强制二次 approval |
| `credential_scope` | intent | 最小 scope，仅声明需取的 broker ref 种类 |
| `ttl` | 策略 | 短时；过期拒 |
| `intent_hash` | intent | 与本次 request 的 `request_hash` 一致（B-观点1；C-观点1） |

### 3.2 形态与生命周期

- approval 是**一次性的、可撤销的 capability token**（C-观点2），不是全局开关；撤销后 executor 立即拒绝（T-观点5）。
- 默认 deny 矩阵：无 approval 的代码执行 / MCP / Figma 写回 / 外网访问 / 凭据读取一律 `deny`（B-观点2）。
- 例外（网络 egress、screenshot upload）按 capability token 精确限定 `host/path/method/data_class`，DNS/redirect 重新校验（A-观点3；L-观点2）。
- 拒绝复用：过期、重复使用、跨 intent、跨 catalog 版本复用 → 全部 `deny`（T-观点1 并发/重复/跨 intent 用例）。
- approval 记录 schema 见 §6；每次例外须有 owner / expiry / 撤销方式（B-观点4）。

## 4. Sandbox Lease 契约

### 4.1 签发

lease **仅由 policy engine 在 policy 与 approval 全通过时签发**，短时有穷：

| 字段 | 含义 |
|---|---|
| `lease_id` | 确定性派生非 uuid |
| `fencing_token` | 单调递增，旧 token 写入一律拒（P4） |
| `capabilities` | 实际授予的 capability 集合（≤ intent 声明，不得 escalation） |
| `egress` | 网络出口 allowlist：`host/path/method/data_class`（默认全关） |
| `credential_refs` | 短时 broker 引用 ID 列表，**无 secret 值**（P7） |
| `file_roots` | 允许读写的文件根 |
| `process_whitelist` | 进程白名单 |
| `time_window` | 生效起止；超时 lease 失效 |
| `bound_intent_hash` | 绑定的 intent hash，与 lease 一起校验 |
| `bound_catalog_version` | 绑定的 catalog 版本 |

### 4.2 租约纪律

- sandbox 默认**无网络、无任意文件读取**；只有 lease 显式授权的 capability 才可执行（S-观点2）。
- lease 能力**不得超过** intent 声明（escalation → `LEASE_INVALID`）；executor 校验 `capabilities ⊆ intent.capability_set`。
- 进程重启后 `max_fencing_token` 由持久化恢复，旧 token 写入拒（沿用 1-3-3；G-24 实测归 1-9）。
- lease store 不可用 → fail closed（P6）。

## 5. Executor 单入口契约

### 5.1 唯一副作用入口

executor 是**唯一**产生 effect 的入口；P1 禁止任何其他路径触发副作用。executor 不做 allow/deny 决策，只执行"已签 lease 所授权的效果"。

### 5.2 接收与校验（严格四检）

executor 接收 effect 请求时，必须严格检查以下四项（即本节点 exit criteria 的承载点）：

1. **policy**：请求须附带有效 `decision_record`，且 `decision=ALLOW`、`reason_code` 非 deny；无 decision_record 或过期 → 拒。
2. **approval**：decision_record 关联的 `approval` 须处于有效状态（未撤销、未过期、绑定 `intent_hash` 与 `request_hash` 一致）；否则拒。
3. **sandbox lease**：须持有 policy engine 签发的 `lease`，且 `lease.fencing_token` 有效、`lease.capabilities ⊆ intent.capability_set`、`lease.bound_intent_hash == intent_hash`、`lease.bound_catalog_version` 一致；否则拒（`LEASE_INVALID`）。
4. **request digest**：`sha256(effect_request_canonical)` 必须等于 intent 的 `request_hash`（及 approval 绑定的 `request_hash`）；不一致 → 拒（`REQUEST_DIGEST_MISMATCH`）。

任一检查失败 → 不产生副作用、返回 `deny + reason_code`、写入最小审计事件（B-观点1；S-观点1；T-观点5）。

### 5.3 执行与副作用纪律

- 仅按 lease 授权的 capability 执行；远程写回带 `idempotency_key`、`request_digest`、目标确认、变更摘要，失败回退本地（MASTER L99；B-观点4）。
- secret 值不出现在 prompt、产物、日志、截图或 audit（P7）；远程服务不可用时失败不伪造成功（MASTER L101）。
- 每次执行写入 `execution_record`（§6），可被 `execution_id` 顺序重建判定链。
- 并发/重试下幂等：同一 `(intent_hash, lease)` 只产生一份副作用（P8）。

## 6. Decision / Audit 记录 Schema（贯穿四环）

所有决策/授权/租约/执行均产出不可伪造、可重放的记录，且**不得含 secret 明文**：

| 记录类型 | 关键字段 |
|---|---|
| `decision_record` | `policy_version`、`catalog_id/version`、`intent_hash`、`capability_decision`、`approval_required`、`sandbox_profile`、`reason_code`、`actor`、`timestamp` |
| `approval_record` | `approval_id`、`catalog_id/version`、`action`、`params_digest`、`target`、`data_class`、`credential_scope`、`ttl`、`intent_hash`、`approver`、`issued_at`、`expires_at`、`revoked` |
| `lease_record` | `lease_id`、`fencing_token`、`capabilities`、`egress`、`credential_refs`、`file_roots`、`process_whitelist`、`time_window`、`bound_intent_hash`、`bound_catalog_version`、`issued_at` |
| `execution_record` | `execution_id`、`intent_hash`、`decision_record_ref`、`approval_ref`、`lease_ref`、`effects_performed`、`side_effects_observed`、`status`、`timestamp` |

- 每条记录含 `policy_version`、`reason_code`、`actor`、`timestamp`；secret 只以 ref 形式出现（L-观点1；S-观点2）。
- 记录可被 `execution_id` 串联成完整判定链：`catalog decision → intent hash → capability decision → approval decision → sandbox decision → execution result`，拒绝事件必须带稳定 error code（T-观点5）。
- 判定链在策略/policy/catalog 版本变更时仍按记录回溯，不依赖当前 schema（A-观点6：四类契约定义版本与向后兼容策略）。

## 7. 硬闸门（本节点范围，实测归 1-9）

| 闸门 | 含义 | 实测归属 |
|---|---|---|
| G-POL-1 | 无 decision_record 或 decision≠ALLOW → executor 零副作用、返回 deny | 1-9 fixture |
| G-POL-2 | approval 缺失/撤销/过期/跨 intent/跨版本复用 → deny | 1-9 fixture |
| G-POL-3 | lease 缺失/旧 fencing token/capability escalation/绑定 intent 不一致 → `LEASE_INVALID` 拒 | 1-9 fixture |
| G-POL-4 | `request_digest ≠ intent.request_hash` → `REQUEST_DIGEST_MISMATCH` 拒 | 1-9 fixture |
| G-POL-5 | 任意非 executor 入口触发副作用 → 视为契约违规（无旁路） | 1-9 fixture（多入口同决策） |
| G-POL-6 | policy/catalog/approval/lease store 不可用 → fail closed，不模拟成功 | 1-9 fixture |
| G-POL-7 | secret 不出现在 prompt/产物/日志/截图/audit；credential 仅 ref | 1-9 fixture |
| G-POL-8 | 同一 `(intent_hash, lease)` 重放多轮仅一份副作用（幂等） | 1-9 fixture |
| G-POL-9 | 同一请求经 CLI/MCP/Figma 三入口得到同一 decision_record | 1-9 fixture（B-观点1 验收口径） |

fail closed 优先：policy/catalog/manifest 不可用时 fail closed；offline simulator 与 deny-first fixtures 在无网络/无凭据/无 Figma 时仍必须可运行（MASTER L101）。

## 8. 上下游契约义务

- **上游**：1-4-1 的 `intent` 是输入；`request_hash` 供 approval 与 executor request digest 绑定，`params_digest` 供 approval/lease/executor 一致性校验。intent 缺 `catalog_id/version/params_digest/request_hash` 时本节点不得签发 lease。
- **下游**：lease 是 1-4-3（provenance / asset-manifest / redaction / quarantine）的输入依据——provenance 与 receipt 必须承接本节点的 decision/approval/lease/execution 审计证据（sub-04 沉淀：sub-05 verification receipt 需承接 decision/audit；sub-02 不得绕过 executor）。
- **跨文档约束**（sub-04 conclusion 沉淀指令）：catalog registry = 能力声明唯一来源；**policy engine = allow/deny 唯一来源**；**executor = lease 校验唯一入口**；asset manifest = provenance 唯一来源；adapter（sub-03）只能申请既有 capability，不能自行扩权。

## 9. 退出判据对照（1-4-2 exit criteria）

> 原文："effect 单入口严格检查 policy、approval、sandbox lease 和 request digest"

| 判据要素 | 承载闸门 | 状态 |
|---|---|---|
| effect 单入口（executor 唯一入口，无旁路） | G-POL-1/5 | 契约已定义，实测 open（归 1-9） |
| 严格检查 policy | G-POL-1 | 契约已定义，实测 open（归 1-9） |
| 严格检查 approval | G-POL-2 | 契约已定义，实测 open（归 1-9） |
| 严格检查 sandbox lease | G-POL-3 | 契约已定义，实测 open（归 1-9） |
| 严格检查 request digest | G-POL-4 | 契约已定义，实测 open（归 1-9） |

## 10. 遗留 open 项（禁止当作已通过）

- 全部 G-POL-1..9 属**实测闸门**，需 1-6（真实 policy/approval/sandbox/executor 落地）+ 1-9（真实 fixture 运行）回写实测证据。
- 本节点 `completed` = **契约冻结落盘（plan 层）**，不等于闸门实测通过。任何 receipt / 运行不得把 G-POL 写成"已通过"。
- 待 1-9 真实跑通后，由 1-9 承载节点回写实测值并解除 open 标注。
- 与 1-4-3（provenance 承接审计）、1-4-4（deny fixtures 证明本节点 deny 语义真发生）共同解锁 1-4 整节点可声明完成。
