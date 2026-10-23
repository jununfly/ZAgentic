# AdapterBoundary v1 规格说明

> 路线图节点 `1-7-2`（定义节点，非实现）。实现落在 `1-7-3`（Storybook active adapter）与 `1-7-5`（删除/断网/远程故障恢复）。
> 配套可机读契约：`skills/ui/zj-ui-core/contracts/adapter-manifest.schema.json`（adapter manifest 字段集的 JSON Schema v1）；示例：`examples/storybook-local-verify.manifest.json`。
> 前置结论来自 `1-7-1` capability-fit 证据账本：Storybook / json-render / A2UI = B（采纳），M3E = D（out-of-core）。

## 1. 定位

AdapterBoundary 是 **canonical artifact（ui-flow/v1、UI-BRIEF 等）** 与 **外部渲染/验证工具（Storybook、json-render、A2UI、M3E 等）** 之间的契约层：

- 每个外部工具以一份 **adapter manifest** 登记，声明它能兑现什么能力、消费哪些 canonical 字段、如何映射、谁负责、失败时如何回退、被删后哪些不变量必须仍成立。
- Boundary 负责 **schema lock（锁定 canonical 与 manifest 契约）**、**mapping 校验（禁止 silent drop）**、**owner/reviewer 登记**、**fallback 编排（降级/禁用/隔离）** 与 **removal test（删除后不变量）**。
- Boundary 本身不实现渲染逻辑；它只做契约仲裁与生命周期编排，具体能力由下游 adapter 实现。

> **实现（1-7-5, a1）**：`skills/ui/zj-ui-core/scripts/adapter_boundary.py` —— 四态状态机与调用守卫（§6.1）、三类故障回退分发（§6.2）、本地恢复不变量断言、removal_test 执行器（§7）。它是 **outcome 分类与回退契约的唯一事实源**；测试 double（`tests/ui_agent_skills_adapter_seam.py`）单向 import 其常量，两处不得各自定义。证据：`tests/test_ui_agent_skills_adapter_boundary.py`（28 用例）。测试主体分层见 [`invocation-seam.md`](./invocation-seam.md)。

## 2. adapter manifest 字段集（六个必需类别）

manifest 必须包含以下字段（完整 schema 见 `skills/ui/zj-ui-core/contracts/adapter-manifest.schema.json`，`additionalProperties:false`）。按节点退出标准，六类字段必须齐全：

| 类别 | 字段 | 说明 |
|---|---|---|
| **manifest 元信息** | `id` `role` `version` `source_commit` `license` | 稳定标识、架构角色、固定 semver、精确 commit、SPDX 许可 |
| **依赖/SBOM** | `dependencies.{sbom_ref, lockfile_ref, direct}` | 钉版本后的 SBOM 与锁文件引用（capability-fit G3/G4） |
| **能力声明** | `provides` `requires_canonical[]` | 兑现的能力；消费的 canonical artifact + 锁版本 + 字段白名单 |
| **映射** | `mapping[]` | canonical → adapter 投影规则；required 字段不得 silent drop；未知字段默认 `error` |
| **责任** | `owner` `reviewer` | 责任人与独立复核人 |
| **生命周期/回退/删除** | `lifecycle` `fallback{}` `removal_test{}` `reeval_date` `risk[]` | 四态状态、三类故障回退、删除不变量、重评日期、已知风险 |

`role` 取值：`active-verify`（A 群本地验证面）、`opt-in-projection` / `opt-in-protocol` / `opt-in-input`（B 群）、`out-of-core`（不进入核心毕业路径）。

## 3. schema lock

- **双锚点**：(a) canonical artifact schema 版本（如 ui-flow/v1 的锁版本）；(b) adapter manifest schema 版本（本文件 `version: 1.0.0`）。
- **canonical 字段增删**：任何 canonical 字段的新增/删除须 **bump schema-lock major**，并 **重跑所有 adapter 的 mapping 校验**（确保无 adapter 依赖被删字段、无 adapter 偷偷消费未声明字段）。
- **manifest 契约变更**：新增 manifest required 字段 = manifest schema major bump；存量 adapter 须同步补字段并重新过 capability-fit 闸门。
- **禁止 floating 版本**：`version` 必须为固定 semver，`source_commit` 必须精确；违反即 capability-fit G3 不通过。

## 4. mapping

- 声明式规则，逐字段描述 `canonical_field → adapter_field`，`rule ∈ {direct, transform, split, merge, drop}`。
- **required canonical 字段不得 silent drop**：若某 required 字段在 mapping 中被 `drop` 或未出现，Boundary 校验失败（error）。
- **未知字段 deny-first**：adapter 遇到未在 `requires_canonical.fields` 白名单内的 canonical 字段，默认 `unknown: error`（拒绝）；可显式声明 `ignore` / `pass-through`，但须在 manifest 中写明且经 reviewer 确认。

## 5. owner

- 每个 adapter 必须登记 `owner` 与 `reviewer`（二者不得为同一人/团队，确保独立复核）。
- 责任人负责：版本钉定、SBOM 更新、capability-fit 重评（按 `reeval_date`）、故障时的 fallback 执行与升级。

## 6. fallback 与生命周期状态

### 6.1 四态生命周期

| 状态 | 含义 | 进入条件 |
|---|---|---|
| `active` | 正常服务 | 默认；通过 capability-fit + 运行时健康检查 |
| `degraded` | 部分能力可用 | adapter 部分失效（如 Storybook 缺 a11y addon）；Boundary 用可用部分并标记缺口 |
| `disabled` | 主动关闭 | 人为关闭；canonical artifact + 静态 preview 仍服务 |
| `quarantine` | 被隔离 | 安全闸门/capability-fit 失败；永不调用，待修复或移除 |

> ⚠️ **术语消歧**：本处的 `quarantine` 是 **adapter 生命周期状态**（manifest `lifecycle` 枚举值，小写 `"quarantine"`，持久、管理隔离）。它**不等于** verification receipt 里的 `QUARANTINED` 状态（大写带 D，瞬态、单次运行证据不可信的判定，来源 `ui_skill_core` / `hard_gates`）。二者机制、层级、触发、持久性全不同，1-7-5 不得混淆。完整辨析见 [`quarantine-disambiguation.md`](./quarantine-disambiguation.md)。

> `removal`（删除）是 **经 removal_test 校验的瞬态**，不持久化为状态：删除动作完成后 adapter 从 registry 消失，不保留 `removed` 状态位。

### 6.2 故障回退（fallback）

每个 adapter 必须声明三类故障处置（`on_failure` / `on_network_loss` / `on_remote_failure`），取值 ∈ `{static-preview, local-verify, degrade, disable, quarantine}`：

- **本地恢复不变量**（任何回退都必须保证）：canonical artifact、静态 preview、本地验证（a11y/interaction baseline）在 adapter 不可用或断网/远程故障时仍可用。
- 对 A 群 `active-verify`（Storybook）默认 `on_failure: local-verify`、`on_network_loss: static-preview`、`on_remote_failure: static-preview`——本地验证优先，远程/网络问题回落静态 preview。

> 📐 **测试主体分层（1-7-5）**：回退决策的被测对象是 **boundary 在 adapter 调用 seam 上的行为**，与 adapter 自身有无运行时**正交**。故 Storybook（有真实运行时）作 L1 保真基准 + `SimulatedAdapterSeam` 作 L2 故障注入穷举矩阵；json-render / A2UI 无运行时投影引擎，声明式**退出** invocation/回退执行测试面（`invocation_surface: none`，deny-first 未声明即报错）。另：`network_loss` / `remote_failure` 在本仓库**无真实运行时观测支撑**（Storybook 为离线确定性引擎），属 seam 契约定义，不得声称已真实验证。完整契约见 [`invocation-seam.md`](./invocation-seam.md)。

## 7. removal test（删除后不变量）

删除任意 adapter 后，以下不变量必须仍成立（每条在 manifest `removal_test.invariants[]` 中登记 `id` / `description` / `verify`）：

1. **R1 canonical 可解析**：canonical artifact 仍可从本地 store 解析（不依赖被删 adapter）。
2. **R2 静态 preview 可服务**：静态 preview 仍可构建/服务。
3. **R3 本地验证可跑**：a11y/interaction baseline 等本地验证不依赖被删 adapter 仍可执行。
4. **R4 无悬空引用**：活跃 manifest / plan 中无指向被删 adapter 的引用。
5. **R5 resolver 仍可解析**：resolver 仍能解析体验，或显式报 `degraded`（不得崩溃/静默丢能力）。

> 这五条直接对应 `1-7` 父节点退出标准「删除 adapter、断网或远程故障后 canonical artifact、静态 preview 和本地验证仍可用」。

## 8. artifact 清单

- `skills/ui/zj-ui-core/contracts/adapter-manifest.schema.json` — adapter manifest JSON Schema v1（字段集事实源）。
- `adapter-boundary-v1.md` — 本规格说明。
- `examples/storybook-local-verify.manifest.json` — Storybook active adapter 示例 manifest（模板，供 `1-7-3` 消费；`source_commit` / `sbom_ref` / `lockfile_ref` 须在集成时钉死）。
- `quarantine-disambiguation.md` — `quarantine`(adapter 生命周期) vs `QUARANTINED`(receipt 判定) 消歧事实源。
- `invocation-seam.md` — adapter 调用 seam 契约：三层测试主体、故障注入保真度护栏、调用面 deny-first 索引、诚实账本。

## 9. 退出标准核对（1-7-2）

- [x] adapter manifest 字段齐全（六类：manifest 元信息 / 依赖-SBOM / 能力声明 / 映射 / 责任 / 生命周期-回退-删除），见 schema。
- [x] schema lock 定义（双锚点 + canonical 字段增删 bump major + 重跑 mapping 校验 + 禁止 floating）。
- [x] mapping 定义（声明式、required 禁 silent drop、未知字段 deny-first=error）。
- [x] owner 定义（owner + 独立 reviewer）。
- [x] fallback 定义（四态生命周期 + 三类故障回退 + 本地恢复不变量）。
- [x] removal test 定义（R1–R5 五条不变量）。
