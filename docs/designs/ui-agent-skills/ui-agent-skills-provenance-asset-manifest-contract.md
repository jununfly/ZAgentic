# UI Agent Skills — Provenance / asset-manifest.json / Secret Redaction / License Quarantine 契约（1-4-3）

> 路线图节点：1-4-3（Trust boundary 路线第三片叶）
> 层：plan（仅冻结契约，不落地产品代码）
> 权威源：sub-04-trust-boundary.md（DONE_WITH_CONCERNS）、MASTER.md L50-56/L94-101、跨视角 B/A/T/S/L 整合立场、以及上游 1-4-1 §6、1-4-2 §8/P7 沉淀
> 配套：1-4（trust chain 总节点）、1-4-1（catalog allowlist / effect intent）、1-4-2（policy/approval/sandbox/executor）、1-4-4（deny fixtures）

## 0. 定位与 Trust Chain 位置

唯一信任链（MASTER L94）：

`catalog allowlist → intent → policy → approval → sandbox lease → executor → provenance → receipt`

本节点冻结**倒数第二环**：`provenance`（资产可追溯）与它的机器可读载体 `asset-manifest.json`、以及两条强制纪律——`secret redaction`（写路径剥离明文）与 `license quarantine`（许可证不可归因/不兼容即隔离）。上游 1-4-2 产出的 `decision_record / approval_record / lease_record / execution_record` 是本节点的**输入依据**：provenance 与 receipt 必须承接其审计证据（1-4-2 §8 沉淀：sub-05 verification receipt 需承接 decision/audit）。本节点**不**接管 receipt 聚合（归 1-5）与 deny fixtures 证明（归 1-4-4）。

Scope 边界：plan 层。本节点**只定义契约**（事实源归属、manifest schema、redaction 动作、quarantine 动作、硬闸门），**不写** manifest 生成器、redactor、quarantine 移动器或 provenance 采集代码；真实实现归 1-6（目录与 SKILL.md 落地）与 1-9（真实 skill + fixture 运行）。

## 1. 核心不变量

- **PR1 — asset manifest = provenance 唯一事实源**：所有外部/生成资产的可追溯信息**只**存于 `asset-manifest.json`（机器可读）；UI-DESIGN.md 等 artifact 内嵌的 `provenance` 字段降级为"引用该 manifest 的投影"，必须与该 manifest 逐字段一致，不得与 manifest 冲突（解决 canonical schema §2 与 1-4-1 §6 的潜在双源冲突）。manifest 缺失字段 → artifact 不得声称 provenance。
- **PR2 — provenance 全资产覆盖**：每个进入产物的资产（设计参考、字体、图片、组件、第三方 snippet、远程拉取物、截图）必须在 manifest 中登记 `hash/source/license/credit/owner/replacement/approval`，缺任一 → 不进默认产物（quarantine）。
- **PR3 — secret 永不落盘明文**：secret 值在任何 artifact / log / screenshot / audit / manifest 中均以 broker ref 形式出现，明文一律在写入前 redact（沿用 1-4-2 P7 / G-POL-7）。redaction 是写路径**强制动作**，非可选。
- **PR4 — license 未知/不兼容 → quarantine**：资产 license 无法归因（`unknown`）或超出允许集合（`incompatible`）→ 隔离，不进默认产物（沿用 canonical schema §2、skill-capability-manifest stop_conditions）。
- **PR5 — hash 绑定不可伪造**：每个资产由内容 hash（`sha256`）标识；manifest 条目 `content_hash` 与实际文件 hash 不符 → 拒绝采用（tamper 检测）。
- **PR6 — provenance 承接审计链**：manifest / provenance 必须可串联回 1-4-2 的 `decision/approval/lease/execution`（execution_record 引用 manifest `asset_id`），receipt 可归因。
- **PR7 — replacement 显式**：被 quarantine 资产必须记录 `replacement`（替代 asset_id）或显式 `replacement: null` + `reason`，不得静默丢失能力。

## 2. Provenance 契约（事实源归属）

### 2.1 单一事实源

- 机器可读的 `asset-manifest.json` 是 provenance 的**唯一事实源**（sub-04 跨文档约束：asset manifest = provenance 唯一来源）。
- artifact 内嵌 `provenance`（如 canonical schema §2 UI-DESIGN.md 的 `provenance{source,reference,license}`）仅作**人类可读投影**；其字段值必须可由 manifest 推导或与其逐字段相等，否则该 artifact 的 provenance 视为 stale，验证层标记 `STALE`（沿用 1-5 receipt 状态）。
- 谁负责写 manifest：`asset-manifest` owner（平台安全/合规负责人，沿 1-4-1 §2.3 责任分工）。adapter 只提交带 `projection_id` / `source_revision` 的投影，不拥有 canonical manifest 字段值（沿用 canonical schema 全局不变式"唯一 owner"）。

### 2.2 覆盖资产类型

| asset_type | 示例 | 必填 provenance 字段 |
|---|---|---|
| `font` | 字体文件 | source, license, credit |
| `image` | 图片/图标/截图 | source, license, credit |
| `component` | 第三方组件/snippet | source, license, owner |
| `design_reference` | 外部设计参考/配色 | source, license, credit |
| `remote_fetch` | 远程拉取物 | source, license, owner, approval |
| `generated` | 本地产物（含截图） | source(=generated/run_id), owner |

## 3. asset-manifest.json 契约（Schema）

### 3.1 顶层结构

```json
{
  "manifest_version": "0.1",
  "schema_lock": true,
  "generated_at": "2026-10-20T13:21:48+08:00",
  "generator": { "catalog_id": "zj-ui-design-system", "catalog_version": "0.1.0", "run_id": "<确定性派生>" },
  "assets": [ /* 见 §3.2 */ ]
}
```

- `manifest_version` 初值 `0.1`；breaking-change 走 gate（沿用 canonical schema 版本校验精神）。
- `schema_lock: true`：字段集固定，未知字段拒绝（沿用 1-3-2 规范化 N1-N7 精神）。
- `generator` 绑定 catalog 条目，使 manifest 本身可溯源到具体 skill 版本与 run。

### 3.2 资产条目 Schema（最小集，对齐退出判据）

每个 `assets[]` 条目：

| 字段 | 类型 | 含义 | 约束 |
|---|---|---|---|
| `asset_id` | string | 确定性派生标识 | `sha256(fingerprint[0:12]-asset_type-content_hash[0:12])` 风格，**非 uuid**（沿用 1-4-1 §3 intent_id 确定性派生） |
| `asset_type` | enum | 资产类别 | §2.2 枚举之一 |
| `content_hash` | sha256 | 资产内容 hash | 与实际文件 hash 不符 → 拒（PR5） |
| `source` | object | 来源 | `{type: external\|generated\|human\|remote, uri, fetched_at, catalog_id?}`；外部/remote 必须可归因（PR2） |
| `license` | object | 许可证 | `{spdx, status: known\|unknown\|incompatible\|pending, text_ref}`；`unknown/incompatible` → quarantine（PR4） |
| `credit` | object | 署名 | `{author, attribution_required, attribution_text}`；`attribution_required=true` 时 `attribution_text` 必填 |
| `owner` | string | 责任方 | 平台/团队/人；adapter 不拥有（PR1） |
| `replacement` | object\|null | 替代 | `{asset_id}` 或 `null`+`reason`；quarantine 时必须显式（PR7） |
| `approval` | object\|null | 采用授权 | `{approved_by, approval_ref, policy_version}`；高风险/remote 必填，引用 1-4-2 `approval_record` |
| `provenance_chain` | string[] | 审计链 | execution_id / intent_hash 列表，串联回 1-4-2 审计（PR6） |
| `quarantined` | bool | 隔离标记 | `true` 时资产不进默认产物 |
| `quarantine_reason` | string\|null | 隔离原因 | `quarantined=true` 时必填（`LICENSE_UNKNOWN` / `LICENSE_INCOMPATIBLE` / `SOURCE_UNKNOWN` / `HASH_MISMATCH` / `REDACTION_FAILED`） |
| `redacted` | bool | 是否已脱敏 | 含 secret 槽位的资产必须 `true` |

### 3.3 校验不变量

- 进入默认产物的资产：`quarantined === false` 且 `license.status ∈ {known, pending}` 且 `content_hash` 已校验一致且（高风险/remote）`approval != null`。
- 任一 artifact 声明的 provenance 与 manifest 同 `asset_id` 条目逐项相等，否则 manifest 胜出、artifact 标记 stale。
- `manifest_version` + `generated_at` + `assets[].content_hash` 整体参与 verification receipt 的 `artifact_hash` 计算（对齐 1-5）。

## 4. Secret Redaction 契约（写路径强制）

### 4.1 范围与模式

redactor 在以下**写路径**强制运行：

1. executor 写副作用前（1-4-2 §5.3）；
2. screenshot 落盘前（1-4-2 P7、G-POL-7）；
3. audit / decision / approval / lease / execution 记录落盘前（1-4-2 §6）；
4. 任何 artifact（含 asset-manifest.json）落盘前。

secret 模式（至少）：API key、bearer/long-lived token、password、private key（PEM）、含凭据的 connection string、broker ref 之外的任何 credential 明文。

### 4.2 动作与纪律

- 命中 secret 模式 → 替换为 `<redacted:secret_type:ref_id>` 或 `<redacted:secret_type>`；**绝不**保留明文。`ref_id` 仅指向 1-4-2 的 broker ref（无值）。
- secret 值不得以任何形式进入 manifest 的 `source.uri` / `license.text_ref` / 任意字段（PR3）。
- redaction 失败（模式无法判定、内容无法扫描、写入目标不可信）→ **fail closed**：该写操作不落盘、返回阻断（沿用 1-4-2 P6）。redaction 失败计为 `quarantine_reason=REDACTION_FAILED`。
- redactor 自身不持有 secret 值；它只消费 broker ref 与扫描明文模式，与 1-4-2 credential broker 解耦。
- 与 1-4-2 G-POL-7 同口径：secret 不出现在 prompt/产物/日志/截图/audit；credential 仅 ref。

## 5. License Quarantine 契约（隔离动作）

### 5.1 判定

- 允许集合：以 SPDX 允许列表 + 平台许可的 `pending`（待人工复核、未进默认产物）为基准。
- `license.status`：
  - `known`：在允许集合 → 正常采用；
  - `pending`：已登记但待人工复核 → 不进默认产物，可暂存；
  - `unknown`：无法归因（无 SPDX / 无 text_ref / 来源不可信）→ **quarantine**；
  - `incompatible`：超出允许集合（如 copyleft 与产物分发冲突、禁止商用）→ **quarantine**。

### 5.2 动作

- quarantine 动作：资产不进默认产物目录，移入 `.quarantine/`；manifest 条目置 `quarantined=true` + `quarantine_reason`（PR4）。
- 记录保留供合规复核（沿用 lease-state-machine §6.2 `QUARANTINED` 终态：结果不可信、待人工/合规复核、可解除）。
- `replacement` 必须显式：`{asset_id}`（指向替代资产）或 `null` + `reason`（无替代、能力降级，须 Human 知晓，不得静默丢失）（PR7）。
- 被 quarantine 资产不计入产品覆盖率/毕业分母（沿用 scope-manifest §4 与 lease-state-machine G-18 精神：QUARANTINED 不得写成 PASS）。

### 5.3 解除

- `unknown` → 补齐 `license.spdx` + `text_ref` 并经 approval → `known`；
- `incompatible` → 换用兼容替代资产（`replacement.asset_id`）或获合规例外授权 → 解除；
- 解除须经 Human/合规复核，写回 manifest `approval` 与 `provenance_chain`。

## 6. 与 1-4-2 审计链串联（承接纪律）

- 每个被采用的资产，`provenance_chain` 至少含其采用的 `execution_id`（来自 1-4-2 `execution_record`）；remote/高风险资产还含 `approval_ref`（来自 1-4-2 `approval_record`）。
- manifest 整体 hash 进入 1-5 verification receipt 的 `artifact_hash`，使"产物可归因"成立（scope-manifest §4 成功标准）。
- 1-4-2 的 `decision_record/approval_record/lease_record/execution_record` 不得含 secret 明文（本节点 PR3 与 1-4-2 P7 共同约束）；本节点 redactor 是这些记录落盘前的最后一道闸门。

## 7. 硬闸门（本节点范围，实测归 1-9）

| 闸门 | 含义 | 实测归属 |
|---|---|---|
| G-PRV-1 | asset-manifest.json 是 provenance 唯一来源；artifact 内嵌 provenance 与 manifest 一致 | 1-9 fixture |
| G-PRV-2 | 每个进入产物的资产在 manifest 登记全字段（hash/source/license/credit/owner/replacement/approval），缺 → quarantine | 1-9 fixture |
| G-PRV-3 | secret 明文零出现（prompt/产物/日志/截图/audit/manifest）；redaction 写路径强制 | 1-9 fixture（与 1-4-2 G-POL-7 同口径） |
| G-PRV-4 | license unknown/incompatible → quarantine，不进默认产物 | 1-9 fixture |
| G-PRV-5 | 资产 content_hash 与实际文件 hash 一致，否则拒（tamper 检测） | 1-9 fixture |
| G-PRV-6 | provenance 可串联回 decision/approval/lease/execution（execution_id/approval_ref） | 1-9 fixture |
| G-PRV-7 | 被 quarantine 资产显式 replacement 或 null+reason，不静默丢失能力 | 1-9 fixture |
| G-PRV-8 | redaction 失败 → fail closed 不落盘 | 1-9 fixture |

fail closed 优先：manifest/catalog/registry 不可用时 fail closed；redaction/quarantine 在无网络/无凭据时仍必须可运行（MASTER L101）。

## 8. 上下游契约义务

- **上游**：1-4-2 的 `decision_record/approval_record/lease_record/execution_record` 是本节点审计输入（§6）。1-4-1 的 `credential_refs` 结构预留 secret ref 槽位（1-4-1 §3），本节点 redactor 消费其 ref、永不持有值。
- **下游**：manifest hash 是 1-5 verification receipt 的 `artifact_hash` 输入；provenance 是 1-5 receipt「可归因」状态的承载（scope-manifest §4）。1-4-4 用 deny fixtures 证明本节点 quarantine/redaction 语义真发生（unknown license 资产被隔离、secret 明文零出现）。
- **跨文档约束**（sub-04 conclusion 沉淀指令）：catalog registry = 能力声明唯一来源；policy engine = allow/deny 唯一来源；executor = lease 校验唯一入口；**asset manifest = provenance 唯一来源**（本节点 PR1 落地）；adapter 只能申请既有 capability，不能自行扩权。

## 9. 退出判据对照（1-4-3 exit criteria）

> 原文："provenance 与 asset-manifest 记录 hash/source/license/credit/owner/replacement/approval"

| 判据要素 | 承载闸门 | 状态 |
|---|---|---|
| provenance 事实源（asset-manifest 唯一来源，artifact 投影一致） | G-PRV-1 | 契约已定义，实测 open（归 1-9） |
| 记录 hash | G-PRV-5 | 契约已定义，实测 open（归 1-9） |
| 记录 source | G-PRV-2 | 契约已定义，实测 open（归 1-9） |
| 记录 license | G-PRV-4 | 契约已定义，实测 open（归 1-9） |
| 记录 credit | G-PRV-2 | 契约已定义，实测 open（归 1-9） |
| 记录 owner | G-PRV-2 | 契约已定义，实测 open（归 1-9） |
| 记录 replacement | G-PRV-7 | 契约已定义，实测 open（归 1-9） |
| 记录 approval | G-PRV-2/6 | 契约已定义，实测 open（归 1-9） |
| secret redaction（写路径强制、零明文） | G-PRV-3/8 | 契约已定义，实测 open（归 1-9，与 1-4-2 G-POL-7 同口径） |
| license quarantine（unknown/incompatible 隔离） | G-PRV-4/7 | 契约已定义，实测 open（归 1-9） |

## 10. 遗留 open 项（禁止当作已通过）

- 全部 G-PRV-1..8 属**实测闸门**，需 1-6（真实 manifest 生成器 / redactor / quarantine 移动器落地）+ 1-9（真实 fixture 运行）回写实测证据。
- 本节点 `completed` = **契约冻结落盘（plan 层）**，不等于闸门实测通过。任何 receipt / 运行不得把 G-PRV 写成"已通过"。
- 待 1-9 真实跑通后，由 1-9 承载节点回写实测值并解除 open 标注。
- 与 1-4-4（deny fixtures 证明本节点 quarantine/redaction 语义真发生）共同解锁 1-4 整节点可声明完成。
