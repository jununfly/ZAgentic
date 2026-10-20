# UI Agent Skills — Catalog Allowlist 与 Effect Intent 契约（1-4-1）

> 路线图节点：1-4-1（Trust boundary 路线首片叶）
> 层：plan（仅冻结契约，不落地产品代码）
> 权威源：sub-04-trust-boundary.md（DONE_WITH_CONCERNS）、MASTER.md L18/L25/L37/L94-101、跨视角 B/A/T/S/L 整合立场
> 配套：1-4（trust chain 总节点）、1-4-2（policy/approval/sandbox/executor）、1-4-3（provenance/asset-manifest/redaction/quarantine）、1-4-4（deny fixtures）

## 0. 定位与 Trust Chain 位置

唯一信任链（MASTER L94）：

`catalog allowlist → intent → policy → approval → sandbox lease → executor → provenance → receipt`

本节点冻结**前两环**：catalog allowlist（能力声明）与 effect intent（副作用请求的无副作用描述）。后续 1-4-2 消费 intent 做 policy/approval/sandbox 判定，1-4-3 接管 provenance，1-4-4 用 deny fixtures 证明本节点定义的 unknown/deny 语义真的发生。

Scope 边界：plan 层。本节点**只定义契约**（schema、查询/生成语义、unknown 判定、硬闸门），**不写** catalog 注册表、intent 生成器或校验代码；真实实现归 1-6（目录与 SKILL.md 落地）与 1-9（真实 skill + fixture 运行）。

## 1. 核心不变量

- **I1 — 注册前提**：只有 catalog allowlist 中的条目才能生成 effect intent。未注册 component/action 一律形成 `unknown`/`deny` intent，不可执行，绝不自动降级或按名称猜测（A-观点1）。
- **I2 — unknown 四元组**：未知语义沿用 1-2 canonical schema 的 `unknown` 四元组 `path/raw/reason/source`，不得压成空值（MASTER L10/L53）。
- **I3 — intent 绑定 catalog**：intent 必须显式引用 `catalog_id + catalog_version + capability`；与 catalog 版本或参数哈希不一致即非法，不得执行。
- **I4 — fail closed**：catalog（或依赖的 registry）不可用时返回 `unknown`，不模拟成功、不返回默认 allow（MASTER L101；sub-04 A-观点1）。
- **I5 — plan/effect 分离**：`plan` 是无副作用纯数据，`effect` 是受控副作用；intent 是 effect 的纯数据描述，本身不产生副作用（MASTER L25；sub-04 A-观点2）。

## 2. Catalog Allowlist 契约

### 2.1 条目 Schema（最小集）

每个 catalog 条目至少包含：

| 字段 | 类型 | 含义 |
|---|---|---|
| `id` | string | 能力标识（component/action 的稳定名） |
| `version` | semver | 精确版本，固定且可签名 |
| `kind` | enum | `input` \| `component` \| `action` |
| `owner` | string | 平台安全负责人/维护者 |
| `required_capabilities` | string[] | 该条目声明所需的 capability 集合 |
| `risk_class` | enum | `low` \| `medium` \| `high` \| `critical` |
| `signature` | string | 条目签名（防篡改） |
| `source_revision` | string | 来源 revision（可追溯） |

（来源：B-观点1 `id/version/kind/owner/required_capabilities/risk_class`；A-观点1 `version`；C-观点1 签名且版本固定的 component/action）

### 2.2 查询语义

- `lookup(catalog_id, version) → entry | NOT_FOUND`
- `NOT_FOUND` → 形成 `unknown` intent，`reason_code=CATALOG_MISS`，不可执行。
- **版本精确匹配**：不允许"兼容默认""取最新"或"兼容默认值放权"（A-观点2：不能通过扩大旧枚举或兼容默认值放权）。版本漂移（intent 引用的 `catalog_version` 与 registry 不一致）→ `unknown`/`deny`（A-观点1；T-观点1 catalog 版本漂移 fixture）。
- **未签名 / 版本不匹配** → `unknown`（C-观点1：catalog 只允许签名且版本固定的 component/action）。

### 2.3 注册与治理（事实源归属）

- `catalog registry` 是**能力声明的唯一事实源**（sub-04 A-观点6：四个稳定边界之一 = 能力声明唯一来源）。
- 平台安全负责人维护 catalog；执行框架负责人维护拦截器；测试负责人维护 fixture（B-观点1 责任分工）。
- 新增 capability **必须新增 catalog 条目 + 显式 schema 版本**，不能通过扩大旧枚举或"兼容默认值"放权（A-观点2）。

## 3. Effect Intent 结构

intent 是 effect 的纯数据描述，字段集（来源：B-观点1、A-观点1、C-观点1）：

| 字段 | 含义 | 约束 |
|---|---|---|
| `intent_id` | 确定性派生标识 | `sha256(fingerprint[0:12]-catalog_id-catalog_version-action)` 风格，**非 uuid**（沿用 1-3-2 §5.1 确定性派生，保证重放一致） |
| `catalog_id` + `catalog_version` | 指向已注册且版本匹配的 catalog 条目 | 缺任一或引用未注册条目 → 非法（G-CAT-3） |
| `action` | 具体动作 | 必须属于该 catalog 条目的 allowed action 集合 |
| `target` | 资源/文件/组件标识 | |
| `params_digest` | 参数摘要 | `sha256(params_canonical)`；与 catalog 版本/哈希不一致 → 拒绝（I3/G-CAT-4） |
| `purpose` / `data_class` | 用途 / 数据分类 | `public` \| `internal` \| `sensitive`（用于下游 approval 判定） |
| `actor` / `caller` | 操作者 / 调用者 | |
| `request_hash` | 请求 hash | 高风险 approval 绑定此 hash（B-观点1；下游 1-4-2 消费） |
| `capability_set` | capability 集合 | 由 catalog 声明，effect 必须携带 |
| `credential_refs` | 凭据引用槽位 | 仅存短时 broker 引用 ID，**不存 secret 值**（secret 约束归 1-4-2/3，但结构预留） |

**不进 hash 的字段**（沿用 1-3-2 §5.1 不变量）：timestamp、random id、hostname、绝对路径、env、locale、model_version。

### 3.1 生成语义

- intent **只能由已注册 catalog 条目生成**；unknown 条目 → 拒绝生成 intent，进入 `unknown` 队列并显示原因（C-观点1）。
- **字段规范化**（沿用 1-3-2 规范化 N1-N7 精神）：固定序列化顺序、去除不可达字段、拒绝未知字段（T-观点1：intent 字段超长或未知字段 fixture）。
- intent 本身无副作用（I5）；execution 才产生副作用。

## 4. Unknown 语义

- 未注册 component/action = `unknown`（MASTER L96；A-观点1）。
- `unknown` **不得自动降级**为 allow，也**不得按名称猜测**（A-观点1：不能自动降级或按名称猜测）。
- `unknown` 形成 `unknown`/`deny` intent，写入最小审计事件（`reason_code` + `decision_record`），不执行（T-观点1：断言阻断或显式 unknown、无副作用、审计事件含决策点）。
- 与 1-2 `unknown` 四元组一致：`path`（调用点）/ `raw`（原始 component/action 名）/ `reason`（`CATALOG_MISS` 等）/ `source`（调用者）。未知能力也用同一四元组记录，不压空值（I2）。

## 5. 硬闸门（本节点范围，实测归 1-9）

| 闸门 | 含义 | 实测归属 |
|---|---|---|
| G-CAT-1 | 未注册 component/action → 100% 形成 unknown/deny intent，零执行 | 1-9 fixture |
| G-CAT-2 | catalog 缺失/版本不匹配/未签名 → fail closed（unknown），不返回默认 allow | 1-9 fixture |
| G-CAT-3 | intent 缺 catalog_id/version 或引用未注册条目 → 非法，拒绝生成 | 1-9 fixture |
| G-CAT-4 | intent 与 catalog 版本/参数哈希不一致 → 拒绝 | 1-9 fixture |
| G-CAT-5 | unknown 不压空值、不自动降级、不模拟成功 | 1-9 fixture |
| G-CAT-6 | plan/effect 分离：intent 无副作用，execution 才产生副作用 | 1-9 fixture |
| G-CAT-7 | 同一 intent hash 重放 100 次结果一致（确定性） | 1-9 fixture |

fail closed 优先：policy/catalog/manifest 不可用时 fail closed；offline simulator 和 deny-first fixtures 在无网络/无凭据/无 Figma 时仍必须可运行（MASTER L101）。

## 6. 上下游契约义务

- **上游**：sub-02 resolver（1-3-2）生成 skill 路由后，effect intent 的生成**必须先查 catalog**，不得绕过（sub-04 沉淀指令：sub-02 不得绕过 executor；此处延伸为不得绕过 catalog 查询）。1-2 canonical schema 提供 `unknown` 四元组定义（本节点 I2 引用）。
- **下游**：intent 是 1-4-2（policy→approval→sandbox→executor）的输入；`request_hash` 供 approval 绑定；executor 单入口只接受策略引擎签发且与 intent/catalog 版本/参数哈希一致的短时 lease（A-观点1）。1-4-3 的 provenance/manifest 承接 decision/audit 证据（sub-04 沉淀：sub-05 verification receipt 需承接 decision/audit）。
- **跨文档约束**（sub-04 conclusion 沉淀指令）：catalog registry = 能力声明唯一来源；policy engine = allow/deny 唯一来源；executor = lease 校验唯一入口；asset manifest = provenance 唯一来源；adapter（sub-03）只能申请既有 capability，不能自行扩权。

## 7. 退出判据对照（1-4-1 exit criteria）

> 原文："catalog 只允许注册组件/action，未知项只能形成 deny/unknown intent"

| 判据要素 | 承载闸门 | 状态 |
|---|---|---|
| catalog 只允许注册组件/action | G-CAT-1/2/3 | 契约已定义，实测 open（归 1-9） |
| 未知项只能形成 deny/unknown intent | G-CAT-4/5 | 契约已定义，实测 open（归 1-9） |

## 8. 遗留 open 项（禁止当作已通过）

- 全部 G-CAT-1..7 属**实测闸门**，需 1-6（真实 catalog 注册表 / intent 生成器落地）+ 1-9（真实 fixture 运行）回写实测证据。
- 本节点 `completed` = **契约冻结落盘（plan 层）**，不等于闸门实测通过。任何 receipt / 运行不得把 G-CAT 写成"已通过"。
- 待 1-9 真实跑通后，由 1-9 承载节点回写实测值并解除 open 标注。
