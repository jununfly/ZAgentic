# Resolver / Precedence / Plan Hash 契约（v0.1）

> **冻结文档。** 本文件定义 resolver 的纯函数契约：输入规范化、七步固定决策顺序、歧义分类与禁止 tie-breaker 规则、plan 结构与 `plan_hash` 算法、冲突冻结机制与重放一致性闸门。
>
> 归属路线图节点 1-3-2；事实源 `docs/plans/ui-agent-skills-roadmap.json`。
> 本文件属于**计划层交付物**：不写可执行 resolver 代码、不跑断言。lease/幂等/失败阶梯归 1-3-3；plan/decision/revision/handoff 持久化归 1-3-4。
>
> 依赖：`ui-agent-skills-skill-capability-manifest.md`（1-3-1，manifest 16 字段与 S1–S10 阶段目录）、`ui-agent-skills-canonical-schema.md`（1-2-1）。
>
> 权威来源：`sub-02-skill-orchestration.md` L31（planner 纯函数与 20 次一致）、L79（resolver 顺序、plan hash、100% 同 hash）、L85（Human gate 单一出口）、L112（规范化 + `route_fingerprint` + 100 次随机重放）、L181（租约写锁）、L201-207（整合立场）。

---

## 1. Resolver 是无副作用的纯函数

```
resolve(request, artifact_snapshot, registry, gate_state) -> Plan
```

- **只读输入**：请求描述、artifact revision 快照、manifest registry 快照、gate 状态。
- **零写入**：resolver 本身不写任何 canonical artifact、不发放 lease、不触发 skill 调用。
- **确定性**：相同输入的 100 次顺序随机重放必须得到逐字节相同的 `plan_hash`、相同的 `next_action`、相同的调用序列（闸门 `G-4`，见 §7）。
- **无隐藏输入**：不得读取时间戳、环境变量、文件系统路径、随机数、模型采样结果、registry 加载顺序。任何这类输入进入决策路径即视为契约违反。

### 1.1 输入契约

| 入参 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `request` | object | yes | `{goal, artifact_kind_hint, allow_effect: bool, request_id}`；`request_id` 只用于审计，**不进入 plan_hash** |
| `artifact_snapshot` | object | yes | `{artifact_kind, revision, schema_version, completeness}`；completeness 由 sub-01 schema 校验产出 |
| `registry` | manifest[] | yes | 1-3-1 定义的 16 字段 manifest 全量集合；加载前先过 §2 静态检查 |
| `gate_state` | enum | yes | `PENDING` / `APPROVED` / `REJECTED` / `EXPIRED` / `NOT_REQUIRED` |

---

## 2. 前置：registry 静态检查（加载期，非运行期）

以下三条在 registry 加载时判定，**不通过则整个 registry 不可发布**，resolver 拒绝运行（不是运行期降级）：

1. **写 owner 唯一**：每个 `(stage, artifact_kind)` 的 `owner_scope=write` 条目数恰为 1；为 0 或 ≥2 → `BLOCKED_OWNER_CONFLICT`。
2. **precedence 全序唯一**：同一 `stage` 内 `precedence` 不得重复；重复 → `CONFIG_ERROR`。
3. **manifest 字段完整**：16 字段缺任一 → 该 skill 从 registry 中剔除并记录 `manifest_invalid`，剔除后若导致写 owner 缺失 → 退回第 1 条。

> 与 1-3-1 §4 的 `FF-ORCH-04`（并列 precedence）的关系见 §4.1：**运行期不会出现「同 stage 内 precedence 并列」**，该 fixture 实际断言的是跨 stage 推断歧义与静态拦截的先后。

---

## 3. 输入规范化（canonicalization）

在决策之前必须先把输入变成唯一表示，否则字段顺序、空值表示差异会造成假差异（`sub-02 L112`）。

| 步骤 | 规则 |
| --- | --- |
| N1 字段排序 | 所有 object 按键名 **字典序** 排序后序列化 |
| N2 空值统一 | `null` / `""` / `[]` / `{}` / 缺失 统一归一为 `null`；`unknown` 保留四元组 `{path,raw,reason,source}`，**不得归一为 null** |
| N3 未知字段 | 显式拒绝，记录 `unknown_field:<path>` 并进入 `unknown[]`；**不得静默忽略** |
| N4 字符串归一 | UTF-8 NFC、去首尾空白、统一换行 `\n` |
| N5 数值归一 | 整数不带小数点；浮点固定精度（保留 6 位小数，去尾零） |
| N6 revision 归一 | `revision` 取 sha256 小写十六进制；`schema_version` 取规范化 semver |
| N7 序列化 | JSON，`separators=(',',':')`，`ensure_ascii=False`，`sort_keys=True` |

规范化失败（N3 命中且 `unknown_policy=block`）→ `INVALID_INPUT`，**停止、不生成 plan**。

---

## 4. 七步固定决策顺序

顺序**不可调整、不可跳过、不可短路**。每一步的产物都进 plan，供事后解释“凭什么选它”（`sub-02 C/L58`）。

| 步 | 动作 | 输出 | 提前终止条件 |
| --- | --- | --- | --- |
| **R1** | 校验 artifact / schema | `schema_check{artifact_kind, schema_version, revision, completeness}` | 校验失败 → `INVALID_INPUT`，停 |
| **R2** | 过滤 `forbidden` | `eliminated[{skill_id, reason:"forbidden:<item>"}]` | — |
| **R3** | 匹配 `required_capabilities` | `eliminated[{skill_id, reason:"missing_capability:<cap>"}]` | 候选 = 0 → `UNSUPPORTED_INPUT`，停（**不得降级为“尽力调用”**） |
| **R4** | 按 stage owner 过滤（写权限一致） | `eliminated[{skill_id, reason:"not_write_owner"}]` | 写 owner ≠1 → `BLOCKED_OWNER_CONFLICT`，停 |
| **R5** | 按 `precedence` 排序取最高 | `ranked[{skill_id, precedence}]` | **最高项不唯一 → `AMBIGUOUS`，停**（见 §4.1） |
| **R6** | 判定 Human gate | `gate{state, reason, ttl}` | `required` 且非 `APPROVED` → `WAITING_FOR_HUMAN`，停（批准前写入次数 = 0） |
| **R7** | 产出**一个** `next_action` | `next_action{skill_id, manifest_version, action, input_ref}` | — |

排序键固定为：`stage → artifact owner → precedence → skill_id`。**`skill_id` 只在前面各键全部相等时作为序列化稳定键使用，不作为并列消解依据**（见 §4.1）。

### 4.1 歧义分类与「禁止 tie-breaker」规则

两种歧义必须分开处理，混为一谈会让静态检查与运行期 fixture 互相矛盾：

| 类别 | 触发 | 处置 | 依据 |
| --- | --- | --- | --- |
| **A1 同 stage 内 precedence 并列** | 两个 skill 同 stage 且 `precedence` 相等 | **静态检查拦截**（§2.2），registry 不可发布 → `CONFIG_ERROR`。运行期不应出现；若出现说明静态检查被绕过 → 立即 `CONFIG_ERROR` 停止并告警 | `sub-02 T/L106`、L112 |
| **A2 跨 stage 推断歧义** | 请求未锁定 stage，多个不同 stage 的 skill 都通过 R2–R4（例：“看看这个表单” 同时命中 S7 review 与 S9 verify） | **不比较 precedence**（跨 stage 比较 precedence 是范畴错误），直接 `AMBIGUOUS` → `WAITING_FOR_HUMAN`；展示候选、各自 stage 与差异，最多提 **1 个**澄清问题 | `sub-02 U/L127`、L144 |

**禁止的 tie-breaker（显式列举，实现时不得引入）：**
- ❌ 时间戳 / 请求到达顺序
- ❌ registry 加载顺序 / 文件遍历顺序
- ❌ `skill_id` 字典序（仅允许作为 N7 序列化的**稳定排序键**，不得用来“选出胜者”）
- ❌ 模型措辞、采样温度、相似度打分
- ❌ “最近成功过的 skill” / 缓存命中

理由（`sub-02 B/L31`）：任何 tie-breaker 都会把**结构性冲突**伪装成一次成功路由——调用看似确定，责任却漂移，且无法从最终结果反推选择路径。

**自动推进阈值：** 允许自动产生 `next_action` 的最高候选数 **恰为 1**；≥2 → 停。此阈值为 0 容忍，不做“置信度阈值”折算。

---

## 5. Plan 结构与 plan_hash

### 5.1 Plan 字段（对齐 `sub-02 B/L31` 的持久化要求）

| 字段 | 类型 | 是否进 hash | 说明 |
| --- | --- | --- | --- |
| `plan_id` | string | ❌（由 hash 派生） | `pf-<route_fingerprint[0:12]>-<stage_id>-<attempt>`，**确定性派生，不用 uuid**；`attempt` 从 0 起。**`attempt` 段仅用于审计区分第几次尝试，不参与幂等键**（见 `ui-agent-skills-lease-state-machine.md` §3）——否则重试会拿到新幂等键并造成重复写入 |
| `plan_hash` | sha256 | — | §5.3 |
| `route_fingerprint` | sha256 | — | §5.2 |
| `stage` | enum | ✅ | 选定 stage（S1–S10） |
| `owner_skill` | string | ✅ | 唯一 write owner |
| `manifest_version` | semver | ✅ | 该 skill 的 manifest 版本 |
| `precedence_version` | sha256 | ✅ | registry 全量 `(skill_id, manifest_version, precedence)` 三元组的规范化哈希 |
| `candidates` | id[] | ✅（排序后） | 通过 R4 的候选，按 precedence 升序 |
| `eliminated` | object[] | ✅（排序后） | `{skill_id, reason}`，按 skill_id 字典序 |
| `next_action` | object | ✅ | 单个；`{skill_id, manifest_version, action, input_ref}` |
| `gate_state` | enum | ✅ | R6 结果 |
| `artifact_ref` | object | ✅ | `{artifact_kind, revision, schema_version}` |
| `status` | enum | ❌ | `PLANNED` / `WAITING_FOR_HUMAN` / `FROZEN_CONFLICT` / `UNSUPPORTED_INPUT` / `AMBIGUOUS` / `CONFIG_ERROR` / `INVALID_INPUT` |
| `created_at` | timestamp | ❌ | **禁止进 hash**（N/A：审计用） |
| `request_id` | string | ❌ | 审计用 |

> 同一 `plan_id` 重复出现两次 `ACCEPT` → 立即冻结写入并进入冲突仲裁（`sub-02 P/L175`），具体机制见 1-3-3。

### 5.2 route_fingerprint

```
route_fingerprint = sha256( canonical_json({
    normalized_request,      # §3 输出，不含 request_id
    artifact_ref,            # {artifact_kind, revision, schema_version}
    manifest_version_set,    # registry 中参与匹配的 skill_id→manifest_version
    precedence_version,
    gate_state
}) )
```

### 5.3 plan_hash

```
plan_hash = sha256( canonical_json({
    route_fingerprint,
    stage, owner_skill, manifest_version,
    candidates, eliminated, next_action,
    gate_state, artifact_ref
}) )
```

- **禁止纳入**：时间戳、随机 id、主机名、绝对路径、环境变量、locale、模型版本。
- **必须纳入**：一切会影响选择的输入，保证「选择相同 ⟺ hash 相同」。
- **major mismatch**：`manifest_version` 的 major 与 plan 中记录的不一致 → `BLOCKED_CONTRACT_MISMATCH`，**拒绝执行，不自动降级**（1-3-1 §5.3）。

---

## 6. 冲突冻结机制

冲突不是“换一个 owner 重试”，而是**冻结**——把不确定性停在零副作用处（`sub-02 A/L85`、P/L181）。

| 冲突类型 | 触发 | 冻结动作 | 终态 |
| --- | --- | --- | --- |
| `BLOCKED_OWNER_CONFLICT` | 写 owner 数 ≠1 | 不生成 plan、不发放 lease、写入次数 = 0；保留审计日志 | `FROZEN_CONFLICT` |
| `AMBIGUOUS`（A2） | 跨 stage 推断不唯一 | 不调用、不写入；展示 ≤3 个候选与差异，提 1 个澄清问题 | `WAITING_FOR_HUMAN` |
| `DOUBLE_ACCEPT` | 同一 `plan_id` 两个 `ACCEPT` | 立即冻结该 plan 与其 artifact 的所有写入 | `FROZEN_CONFLICT` + 升级 Human |
| `UNAUTHORIZED_WRITE` | 非 owner 或已过期 token 试图写 | 记为「未执行调用」，写入次数 = 0，保留审计 | `FROZEN_CONFLICT` |
| `CONTRACT_MISMATCH` | manifest major 不匹配 | 拒绝执行，不寻找“相似替代” | `BLOCKED_CONTRACT_MISMATCH` |

冻结规则：
1. 冻结期间 **0 次 skill 调用、0 次 artifact 写入**——不是“执行后去重”。
2. 冻结解除**只能**由 Human gate 的 `APPROVE(plan_id)` / `REJECT(reason)` / `CHOOSE(candidate_id)` 产生（`sub-02 P/L187`）。
3. gate 超时（默认 TTL 24h，`sub-02 A/L85`）→ `BLOCKED_NEEDS_SELECTION`；**超时 ≠ 批准**，不自动回退、不自动挑选。
4. 冻结与解冻事件全部进审计流，由 1-3-4 持久化。

---

## 7. 硬闸门（机械验收，1-3-4 / 1-6 实测）

| id | 断言 | 阈值 |
| --- | --- | --- |
| **G-1** | 同一 `(stage, artifact_kind)` 写 owner 数 | 恰为 1；0 或 ≥2 → `BLOCKED_OWNER_CONFLICT` |
| **G-2** | 同一输入重复 resolve 的 `plan_hash` | 100 次顺序随机重放，逐字节一致率 = **100%** |
| **G-3** | 一次 resolve 产出的 `next_action` 数 | **≤1** |
| **G-4** | 冻结状态下的 skill 调用次数与 artifact 写入次数 | 均为 **0** |
| **G-5** | 自动换 owner 次数（失败后） | **0**（失败阶梯见 1-3-3） |
| **G-6** | 20 个路由 fixture 中可解释为「匹配条件 + precedence」的比例 | **≥18/20**；任一不可解释 → 该 manifest 不可发布 |
| **G-7** | gate 为 `required` 时，批准前的写入/外部调用次数 | **0** |
| **G-8** | 引入 tie-breaker（时间戳/加载顺序/字典序/相似度）的代码路径数 | **0**（静态检查项） |

> G-2 与 G-6 的阈值来自 `sub-02` L79 / L207 与 L58，本文件只登记，**实测在 1-3-4 / 1-6 / 1-9**。

---

## 8. 上下游契约义务

- **对上游（1-3-1）**：本文件的 `candidates` / `eliminated` 直接消费 manifest 的 `forbidden`、`required_capabilities`、`owner_scope`、`writes`、`precedence`；manifest 字段集若变，§2 静态检查与 §5.1 必须同步。
- **对下游（1-3-3）**：lease 只能在 plan `status=PLANNED` 且 owner 唯一时发放；§6 的冻结状态下**禁止**发租约。`DOUBLE_ACCEPT` 的仲裁细节归 1-3-3。
- **对下游（1-3-4）**：§5.1 除 `created_at` / `request_id` 外的全部字段须持久化并可重放；plan/decision/revision 三者的 hash 链必须可回溯到 `route_fingerprint`。
- **对下游（1-4）**：effect 类 skill（S6）的 `gate_state` 必须由 sub-04 的 policy/approval 前置产生；resolver 不自己判安全。
- **对下游（1-6）**：十个 SKILL.md 落地时，其 `stop_conditions` 中的 `WAIT_HUMAN` 必须能映射到 §4 的 R6 / §6 的冻结终态。
- **对 1-9（paired run）**：G-2 / G-6 纳入每轮回归；skill/precedence/manifest 变更必须先过 G-1..G-8。

---

## 9. 退出判据自检（对齐 1-3-2 exit criteria）

1. **唯一 owner 与 precedence 规则已冻结**：§2 静态检查 + §4 R4/R5 + §4.1 禁止 tie-breaker。✅（本文件声明）
2. **resolver 顺序与 plan_hash 算法已冻结**：§4 七步 + §5.2/§5.3 公式与禁纳项。✅（本文件声明）
3. **冲突冻结机制已冻结**：§6 五类冲突 + 四条冻结规则 + 单一解除出口。✅（本文件声明）
4. **实测项（不在本节点内）**：G-1..G-8 全部需 1-3-4 / 1-6 / 1-9 用真实 manifest 与 fixture 实测后回写；本节点不宣称通过。

> 本文件为 resolver **冻结**层；第 4 项属实测，节点内不宣称通过。
