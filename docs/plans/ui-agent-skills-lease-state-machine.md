# Lease / 幂等键 / 失败阶梯 / 状态机契约（v0.1）

> **冻结文档。** 本文件定义执行层的 run 状态机、租约写锁（含 fencing token）、幂等键、四类失败结果与四级失败阶梯，以及 `NEEDS_CONTEXT` / `QUARANTINED` / `DEGRADED` 三个降级终态的语义与解除条件。
>
> 归属路线图节点 1-3-3；事实源 `docs/plans/ui-agent-skills-roadmap.json`。
> 本文件属于**计划层交付物**：不写可执行状态机代码、不跑断言。plan/decision/revision/handoff 持久化归 1-3-4。
>
> 依赖：`ui-agent-skills-skill-capability-manifest.md`（1-3-1）、`ui-agent-skills-resolver-contract.md`（1-3-2，路由层 plan 状态）。
>
> 权威来源：`sub-02-skill-orchestration.md` L37（B 状态集与三条硬路径）、L97（四类失败结果 + 幂等键 + `BLOCKED_RECONCILIATION`）、L118（T 状态链与故障注入）、L144（U 状态/阈值表）、L181（P 租约写锁与仲裁窗口）、L193（P 四级失败阶梯）、L205（整合立场）；`MASTER.md` L46/L110/L129（远程不可用 → 本地 fallback / `DEGRADED`）、L133（多 skill 抢占控制）；`ui-agent-skills-scope-manifest.md` §4（退出/降级状态）。

---

## 1. 两层状态：plan 状态（路由层）与 run 状态（执行层）

混用会让「同一时刻既有路由结论又有执行进度」变成两个互相矛盾的真相。二者**分层、单向驱动**：

| 层 | 归属 | 状态集 | 生命周期 | 谁写 |
| --- | --- | --- | --- | --- |
| **plan 状态** | 1-3-2 路由层 | `PLANNED` / `WAITING_FOR_HUMAN` / `FROZEN_CONFLICT` / `AMBIGUOUS` / `UNSUPPORTED_INPUT` / `CONFIG_ERROR` / `INVALID_INPUT` | 一次解析产生一次结论，**不可重入**（重放必须得到同一 hash） | resolver |
| **run 状态** | 本节点执行层 | 见 §2 | 一次 plan 对应一次 run；run 终止不回写 plan 状态 | orchestrator |

**单向规则**：`plan.status = PLANNED` 是 run 启动的**唯一**前置；run 的任何状态不得反向改写 `plan_hash` 或 plan 的选择结论。审计时二者的关联键是 `plan_id + route_fingerprint`。

---

## 2. Run 状态机

### 2.1 状态集

| 状态 | 含义 | 允许的自动动作 | 后续 |
| --- | --- | --- | --- |
| `PLANNED` | plan 已产出且 owner 唯一 | 申请 lease | → `GATED` 或 `READY` |
| `GATED` | 停在 Human gate 前 | **仅只读检查**；写入/外部调用次数 = 0 | → `RUNNING`（APPROVE）/ `CANCELLED_BY_HUMAN`（REJECT）/ `BLOCKED_NEEDS_SELECTION`（超时） |
| `READY` | 唯一 owner、输入完整、无需 gate | 仅调用一次 | → `RUNNING` |
| `RUNNING` | owner 持有有效 lease 并执行中 | 执行、心跳续租 | → `SUCCEEDED` / `FAILED` |
| `SUCCEEDED` | 输出通过校验并原子提交 | 释放 lease、交接到下一 stage | → 下一 stage 的 `PLANNED` |
| `FAILED` | 终态失败（含 `FAILED_BEFORE_SIDE_EFFECT` / `FAILED_AFTER_SIDE_EFFECT` / `OUTCOME_UNKNOWN`） | 见 §5 | → `FALLBACK` / `ESCALATED` / `STOPPED` |
| `FALLBACK` | 已按 §5.2 允许的显式降级路径继续 | 本地 fallback 执行 | → `SUCCEEDED` / `ESCALATED` |
| `ROLLED_BACK` | 已回退到最近一个已验证 revision | 无（等待升级） | → `ESCALATED` |
| `ESCALATED` | 已生成升级单，等待责任人确认 | 无 | → `STOPPED` 或人工重开 |
| `STOPPED` | 终止，零副作用保留 | 无 | 终态 |
| `NEEDS_CONTEXT` | 信息不足，不可判定（§6.1） | 无 | 终态（待 Human 补齐后**从 plan 阶段重算**） |
| `QUARANTINED` | 结果无法归因（§6.2） | 无 | 终态（待人工/合规复核） |
| `DEGRADED` | 远程/adapter 不可用，本地已降级完成（§6.3） | 本地 canonical 读写 | 终态（可交付但标记降级） |

### 2.2 状态迁移表

```
PLANNED ──gate required──> GATED ──APPROVE──> RUNNING
   │                          │
   │                          ├──REJECT────> CANCELLED_BY_HUMAN ──> STOPPED
   │                          └──超时──────> BLOCKED_NEEDS_SELECTION ──> STOPPED
   └──gate none──────────> READY ──> RUNNING
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
        SUCCEEDED              FAILED(side-effect)     OUTCOME_UNKNOWN
              │                       │                       │
       下一 stage PLANNED      ROLLBACK_REQUIRED         禁止再次调用
                                      │                       │
                               ROLLED_BACK ──> ESCALATED ──> STOPPED
                                      │
                               允许显式 fallback ──> FALLBACK ──> SUCCEEDED / ESCALATED
```

### 2.3 三条硬路径（对齐 `sub-02 L37`）

1. **owner 冲突 / 输入不完整 / 涉及不可逆写入 / 用户未选择** → 立即进 `GATED` 或 `NEEDS_CONTEXT`，**零 skill 执行**。
2. **仅网络/超时类暂态错误** → 自动重试 1 次（§5.2 L3 上限 2 次）；连续失败 → 回退最近已提交 revision → `ROLLED_BACK` → 升级。
3. **skill 已产出但 verify 失败** → 禁止下游继续，保留失败证据并回退，**不得静默重跑**。

---

## 3. 幂等键

```
idempotency_key = sha256( canonical_json({
    route_fingerprint,     # 1-3-2 §5.2
    stage,
    artifact_id,
    artifact_revision
}) )
```

**关键约束：`attempt` 不进幂等键。** 1-3-2 §5.1 中 `plan_id = pf-<fp[0:12]>-<stage>-<attempt>` 的 `attempt` 段仅作审计区分，若把它纳入幂等键，则第 2 次重试会拿到**新键**，导致同一语义写入被执行两次——这正是幂等键要防的事。

| 规则 | 断言 |
| --- | --- |
| K-1 | 同一 `idempotency_key` 的**有效写入次数恰为 1**；重复调用记为「未执行调用」，不执行后去重 |
| K-2 | 重试必须携带**同一个** `idempotency_key` |
| K-3 | 每个副作用携带 `request_id + artifact_revision`；`request_id` 仅供审计，不进任何 hash |
| K-4 | 部分写入（半写）必须执行补偿或标记 `ROLLBACK_REQUIRED`，**不得继续下游调用** |

---

## 4. 租约写锁（lease）

| 字段 | 值 / 规则 | 来源 |
| --- | --- | --- |
| 锁粒度 | `artifact_id + stage_id` | `sub-02 P/L181` |
| 初始 TTL | 15 分钟 | L181 |
| 续租次数上限 | 2 次（总时长上限 45 分钟） | L181 |
| **fencing token** | **单调递增整数**，每次 acquire/renew +1；**所有写操作必须携带当前 token** | 本节点新增（见 §4.1） |
| 抢占 | 过期前**不得**抢占；低 precedence 命中者只能 `SHADOWED`（观察，不得写入） | L181 |
| 回收 | 过期后进入 **2 分钟仲裁窗口**；窗口内无 owner 心跳才由 orchestrator 回收重派 | L181 |
| 释放 | owner 在输出状态写入完成后释放；接收者确认后才获得写锁 | `sub-02 P/L169` |
| 交接超时 | 10 分钟无人确认 → `BLOCKED_HANDOFF` 并升级流程维护者 | L169 |

### 4.1 为什么必须有 fencing token（本节点新增，sub-02 未覆盖）

只有 TTL 的租约存在**僵尸写**漏洞：owner A 因 GC 停顿/网络分区超过 TTL 而“假死”，lease 被回收重派给 B；A 恢复后仍认为自己持有锁，用旧锁写入 → 双 owner 写入同一 artifact，而双方都持有“合法”凭据。TTL 本身无法区分「已过期但仍在跑」的进程。

因此：
- lease 附带单调递增 `fencing_token`；orchestrator 侧记录该 `(artifact_id, stage_id)` 见过的**最大 token** `max_token`。
- 任何写请求携带 `token`：`token < max_token` → 一律 `UNAUTHORIZED_WRITE` 拒绝，写入次数 = 0，审计留痕。
- `token == max_token` 且 lease 未过期 → 允许。
- 回收重派时 `token + 1`，旧 owner 的任何后续写入自动失效，**不依赖时钟正确性**。

### 4.2 租约与冻结的关系

1-3-2 §6 的冻结态（`FROZEN_CONFLICT` / `UNAUTHORIZED_WRITE` 等）下**禁止发放 lease**；已发放的立即失效（`max_token + 1` 使其作废）。冻结态的调用次数与写入次数均为 0（复用 1-3-2 闸门 G-4）。

---

## 5. 四类失败结果与四级失败阶梯

### 5.1 四类失败结果（`sub-02 A/L97`）

| 结果 | 判定 | 可自动重试 | 后续 |
| --- | --- | --- | --- |
| `NOT_STARTED` | gate 未批准 / 未获 lease | 否 | `GATED` / `BLOCKED_NEEDS_SELECTION` |
| `FAILED_BEFORE_SIDE_EFFECT` | 已确认无副作用产生 | 是（≤2 次，同幂等键） | L3 阶梯 |
| `FAILED_AFTER_SIDE_EFFECT` | 已产生副作用 | **否**（除非显式声明幂等） | 补偿或 `ROLLBACK_REQUIRED` → `ROLLED_BACK` → `ESCALATED` |
| `OUTCOME_UNKNOWN` | 结果不可判定 | **禁止再次调用** | 原 owner reconcile → 仍不明 → `BLOCKED_RECONCILIATION` + 升级 Human |

> `OUTCOME_UNKNOWN` 是唯一「连重试都不许」的类别：再调一次可能把一次非幂等写入变成两次（`sub-02 A/L97`）。

### 5.2 四级失败阶梯（`sub-02 P/L193` + `L205`）

| 级 | 触发 | 责任人 | 自动动作 | 上限 / 超时 |
| --- | --- | --- | --- | --- |
| **L1 `MISSING_INPUT`** | 输入缺必填字段 | 当前 owner | 一次性列出全部缺口并暂停（追问 ≤2 次） | 追问用尽 → `NEEDS_CONTEXT` |
| **L2 `DECLINED`** | owner 返回 `DECLINE(reason)` | orchestrator | 按 precedence **只试 1 个次选** | 1 个次选；次选也 decline → `ESCALATED` |
| **L3 `RETRYABLE_ERROR`** | 网络/超时等瞬态错误 | 原 owner | 指数退避重试（同 `idempotency_key`） | 最多 2 次；仅 `FAILED_BEFORE_SIDE_EFFECT` 或已声明幂等 |
| **L4 `CONFLICT` / `UNSAFE`** | owner 冲突、越权、权限扩大、不可逆未获批 | — | **立即冻结 artifact 并升级** | **0 次自动动作** |

**统一终止规则**：任一级累计 2 次失败，或单级停留超过 15 分钟 → 停止自动推进，生成升级单。

**升级单必含字段**：`plan_id`、`route_fingerprint`、`owner_skill`、`failure_code`、已尝试动作列表、`idempotency_key`、当前 `fencing_token`、下一责任人。升级单须在 **1 个工作周期内**由责任人确认；未确认升级到子问题 owner，并把该失败 fixture 纳入下一轮验收。

### 5.3 回退规则

- 回退只能回到**最近一个已验证的只读 revision**，不得跨 stage 回退。
- 任何已写 artifact 必须先展示变更摘要与恢复方式。
- **禁止用另一个 skill「接管」来掩盖失败**（`sub-02 U/L148`）——那是自动换 owner，闸门 G-5 要求其计数为 0。
- 回退失败或状态未知 → 统一升级 Human gate 并冻结后续写入，**不继续「尽力完成」**。

---

## 6. 三个降级终态的语义（节点显式要求）

### 6.1 `NEEDS_CONTEXT`

- **判定**：输入不可判定、证据不足、追问预算用尽、或 `MISSING_INPUT` 未在 L1 内补齐。
- **与 `AMBIGUOUS` 的边界**：`AMBIGUOUS`（1-3-2 §4.1）是**路由不唯一**——候选有多个且都不该被选中；`NEEDS_CONTEXT` 是**信息不足**——可能只有一个候选，但缺必填输入。二者都零副作用停止，但解除方式不同：前者需要 Human 从候选中 `CHOOSE`，后者需要 Human **补齐信息**后从 plan 阶段重算。
- **硬要求**：不编造、不猜测、不以默认值填充必填语义字段（`sub-01` 不变式）。
- **解除**：Human 补齐后**从 plan 阶段重算**（不是从中间 skill 续写，`sub-02 U/L127`）。

### 6.2 `QUARANTINED`

- **判定**：结果无法归因——`environment_fingerprint` 缺失或 mismatch、素材 license/source/owner 未知、diff 无法定位到变更、验证结果无法归属到具体 skill/版本。
- **动作**：产物**不进默认产物**；不判 `PASS` 也不判 `FAIL`（判 FAIL 会把「不知道」伪装成「已验证失败」）。
- **解除**：人工/合规复核；license 类需补 `asset-manifest.json` 条目（`MASTER L100`）。
- **与 1-5 的关系**：verification receipt 的聚合状态包含 `QUARANTINED`（`MASTER L110`），本节点只定义编排层语义，具体阈值归 1-5。

### 6.3 `DEGRADED`

- **判定**：远程服务 / adapter /  connector 不可用（Figma/Superdesign/远程画布/网络断开），但**本地 canonical artifact 仍可读写**。
- **动作**：走本地 fallback（静态 preview、本地 fixture 重放）；canonical artifact 不受影响，项目可脱离 adapter 继续维护。
- **与 `DISABLED` / `QUARANTINED` 的边界**：`DEGRADED` = 能力降级但路径可用；`DISABLED` = adapter 被显式关闭或移除；`QUARANTINED` = 结果不可信。三者互斥，同一时刻只取其一。
- **禁止**：以 `DEGRADED` 冒充完整通过；不得把降级结果写成 `PASS`（`MASTER L129`）。

### 6.4 状态互斥表

| 状态 | 是否已写入 artifact | 是否可交付 | 是否需 Human |
| --- | --- | --- | --- |
| `SUCCEEDED` | 是（原子提交） | 是 | 否（除非 gate 要求） |
| `DEGRADED` | 是（本地 canonical） | 是，**标记降级** | 否，但需告知 |
| `QUARANTINED` | 不确定 | **否** | 是（复核） |
| `NEEDS_CONTEXT` | 否（零副作用） | 否 | 是（补齐信息） |
| `ROLLED_BACK` | 已回退 | 否 | 是（升级单） |
| `STOPPED` | 视停止点而定 | 否 | 是 |

---

## 7. 硬闸门（机械验收，1-3-4 / 1-6 实测）

| id | 断言 | 阈值 |
| --- | --- | --- |
| **G-9** | 同一 `idempotency_key` 的有效写入次数 | 恰为 **1** |
| **G-10** | `token < max_token` 的写请求被拒率 | **100%** |
| **G-11** | `OUTCOME_UNKNOWN` 之后的再次调用次数 | **0** |
| **G-12** | 非幂等写入失败后自动换 owner 次数 | **0** |
| **G-13** | `GATED` 状态批准前的写入 / 外部调用次数 | **0** |
| **G-14** | 30 个失败 fixture 中失败结果含 `reason + next_action` 的比例 | **100%** |
| **G-15** | 未选择/超时时的写入次数 | **0**（超时 ≠ 批准） |
| **G-16** | 同一 `plan_id` 出现两个 `ACCEPT` 时冻结生效 | **100%**（写入次数 = 0） |
| **G-17** | 并发同 `request_id` 重放（100 次）终态一致性 | **100%** 同一终态 |
| **G-18** | `QUARANTINED` / `NEEDS_CONTEXT` 被写成 `PASS` 的次数 | **0** |

> 阈值来源：`sub-02` L64 / L106 / L118 / L181 / L207；本文件只登记，**实测归 1-3-4 / 1-6 / 1-9**。G-1..G-8 见 1-3-2 §7，两套闸门叠加执行。

---

## 8. 上下游契约义务

- **对上游（1-3-2）**：`plan.status = PLANNED` 是发放 lease 的唯一前置；冻结态禁止发租约。幂等键排除 `attempt`（已在 1-3-2 §5.1 加注）。
- **对下游（1-3-4）**：§2 全部状态迁移、§4 租约 acquire/renew/release/回收事件、§5.2 升级单必须持久化并可重放；`fencing_token` 的 `max_token` 必须持久化（否则进程重启后 fencing 失效）。
- **对下游（1-4）**：`GATED` 的批准语义由 sub-04 的 policy/approval 产生；本节点只管 gate 的**编排位置**与「批准前零写入」，不管安全判定。
- **对下游（1-5）**：`QUARANTINED` 的聚合与阈值归 1-5；`DEGRADED` 不得计入 PASS 覆盖率。
- **对下游（1-6）**：十个 SKILL.md 的 `stop_conditions` 中的 `WAIT_HUMAN` / `ROLLBACK` / `ESCALATE` / `STOP` 必须能映射到 §2.1 的 run 状态。
- **对 1-9（paired run）**：G-9..G-18 纳入每轮回归；failure fixture ≥30 条。

---

## 9. 退出判据自检（对齐 1-3-3 exit criteria）

1. **lease 机制已冻结**：§4 粒度/TTL/续租/fencing token/抢占/回收/交接。✅（本文件声明）
2. **幂等键已冻结**：§3 公式 + `attempt` 排除规则 + K-1..K-4。✅（本文件声明）
3. **失败阶梯已冻结**：§5.1 四类结果 + §5.2 四阶梯 + 统一终止规则 + 升级单字段。✅（本文件声明）
4. **`NEEDS_CONTEXT` / `QUARANTINED` / `DEGRADED` 已冻结**：§6 判定、动作、解除条件与互斥表。✅（本文件声明）
5. **实测项（不在本节点内）**：G-9..G-18 需 1-3-4 / 1-6 / 1-9 用真实 fixture 实测后回写；本节点不宣称通过。

> 本文件为执行层 **冻结**层；第 5 项属实测，节点内不宣称通过。
