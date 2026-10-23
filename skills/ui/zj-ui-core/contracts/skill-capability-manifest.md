# Skill Capability Manifest 契约（v0.1）

> **冻结文档。** 本文件定义十个 UI skill 的 capability manifest 字段集、逐 skill 全量填表、阶段责任卡（`stage × artifact-kind → 唯一 write owner`）与 failure fixture→owner 覆盖矩阵。
>
> 归属路线图节点 1-3-1（ui-agent-skills 路线图已收口，carrier 文件已清理）。
> 本文件属于**计划层交付物**，仅冻结契约：不创建 skill 目录、不写 resolver 代码、不跑可执行断言（与 1-2 一致）。resolver 算法与 plan hash 归 1-3-2；lease/幂等/失败阶梯归 1-3-3；持久化与重放归 1-3-4；目录与 SKILL.md 落地归 1-6。
>
> 权威来源：`discussions/ui-agent-skills-complete-solution/MASTER.md` L17（编排层定义）、L58-75（skill portfolio 与七字段要求）、L133（多 skill 抢占风险）、L146-147（沉淀清单）；`sub-02-skill-orchestration.md` L201-207（整合立场）、L73（owner 数=1 闸门）、L97（四类失败结果）、L181（租约写锁）。

> **1-6-2 增补（不改上文冻结内容）**：`skills/ui/` 多了一个**第十一个**技能 `zj-ui-core`，它是
> **S0 base carrier**，不属于本文定义的十个 stage：`stage=S0`、`precedence=5`、`owner_scope=read`、
> `writes=[]`、`failure_fixtures=[]`（它没有自己的 failure fixture，fixture 属于各 stage）。
> 存在的理由：本桶不允许共享 `_lib/`（`skills/<bucket>/` 的直接子目录必须含 `SKILL.md`），而
> "unknown 四元组 / deny-first / 原子提交"只应有一份实现。它的 16 字段同样适用，只是 §2 的阶段
> 目录与 §4 的 fixture→owner 矩阵仍按十个 stage 计算。引擎契约见
> `/docs/designs/ui-agent-skills/ui-agent-skills-stage-engine.md`。

---

## 1. Manifest 字段集（每个 skill 必须全量登记）

`MASTER L75` 要求每个 SKILL.md 含 `input / output / forbidden / dependencies / stop conditions / owner / failure fixtures`；`sub-02 L201` 追加 `skill_id / version / stage / required_capabilities / precedence`。合并为下列 16 个字段，**缺任一即 manifest 无效，resolver 不得加载该 skill**。

| # | 字段 | 类型 | 必填 | 语义 / 机器判定点 |
| --- | --- | --- | --- | --- |
| 1 | `skill_id` | string | yes | 全局唯一，形如 `zj-ui-brief`；不得与 registry 中其他条目前缀冲突 |
| 2 | `manifest_version` | semver | yes | minor 只允许追加可忽略字段；major 不兼容必须拒绝执行（0 次 major mismatch 自动降级） |
| 3 | `stage` | enum | yes | 见 §2 阶段目录；一个 skill 只归属一个 stage |
| 4 | `owner_scope` | enum{`write`,`read`,`emit`} | yes | `write` = 该 stage 下该 artifact 的唯一写 owner；`read` = 只读观察者；`emit` = 只产出非 canonical 产物 |
| 5 | `writes` | artifact-kind[] | yes | 该 skill 拥有写锁的 artifact；与 `owner_scope=write` 一一对应，不得为空 |
| 6 | `reads` | artifact-kind[] | yes | 只读依赖；不含自身 `writes` |
| 7 | `input` | object[] | yes | 入口契约：`{name, type, required, source}`；`required=yes` 缺失 → `MISSING_INPUT` |
| 8 | `output` | object[] | yes | 出口契约：`{name, type, artifact_kind, atomic}`；`atomic=true` 表示必须原子提交 |
| 9 | `forbidden` | string[] | yes | 禁止事项；resolver 在**匹配 capability 之前**先过滤 forbidden，命中即淘汰该候选 |
| 10 | `dependencies` | string[] | yes | 前置 stage / artifact revision / 外部 adapter（adapter 只能是已注册 capability） |
| 11 | `required_capabilities` | string[] | yes | 运行所需能力（浏览器 runner、font hash、网络回放…）；缺失 → `BLOCKED`，不得静默降级为成功 |
| 12 | `stop_conditions` | object[] | yes | `{condition, action, next}`；`action ∈ {STOP, WAIT_HUMAN, RETRY_ONCE, ROLLBACK, ESCALATE}` |
| 13 | `owner` | string | yes | 人类责任岗（不是 skill 名）；冲突升级的接收者 |
| 14 | `precedence` | int | yes | 全局全序；同一 `(stage, artifact)` 内不得并列，并列 → `AMBIGUOUS` |
| 15 | `failure_fixtures` | id[] | yes | ≥3 条：正常 / 冲突 / 失败；每条必须能定位到 `owner`（见 §4） |
| 16 | `human_gate` | enum{`required`,`conditional`,`none`} | yes | 触发条件与超时语义由 §5.4 统一规定，skill 不得私自定义第二种 gate |

**机器可判定闸门（静态检查，新增 skill 先过这一关）：**
1. 每个 `(stage, artifact_kind)` 的 `owner_scope=write` 条目数 **恰为 1**；为 0 或 ≥2 → `BLOCKED_OWNER_CONFLICT`，不生成 stage plan、不写 artifact。
2. 同一 `stage` 内 `precedence` 不得重复。
3. `writes` 中的 artifact 必须属于 `sub-01` 已定义的六类 canonical artifact，或显式声明为非 canonical 产物（如 preview）。
4. `forbidden` 不得为空数组——“没有禁止事项”本身是不可接受声明。

---

## 2. 阶段目录与阶段责任卡

采用**一 skill 一阶段**的 10 阶段划分，使 `(stage, artifact) → 唯一 write owner` 由结构保证而非靠优先级补救（对齐 `sub-02 A 观点1`）。`sub-02 B 观点1` 的五阶段 `intake → plan → execute → verify → close` 作为**阶段汇总视图**映射其上：

| phase（汇总） | stages |
| --- | --- |
| INTAKE | S1, S2 |
| PLAN | S3, S4 |
| EXECUTE | S5, S6 |
| VERIFY | S7, S8, S9 |
| CLOSE | S10 |

阶段责任卡字段（对齐 `sub-02 B 观点1` / `P 观点1`）：`stage_id`、唯一 `owner_skill`、输入 artifact 状态、输出状态、禁止动作、交接接收者、Human gate、替补/升级者。

| stage | 阶段 | write owner | 写 artifact | 前置 | 退出条件 | 回退目标（rollback_target） |
| --- | --- | --- | --- | --- | --- | --- |
| S1 | INTAKE | `zj-ui-brief` | `UI-BRIEF.md` (draft) | 用户目标 + 当前 artifact 状态 | 四类必填齐全或显式 `unknown` 四元组 | 无（入口）→ `NEEDS_CONTEXT` |
| S2 | DISCOVER | `zj-ui-discover` | `UI-BRIEF.md` (`unknown[]`/证据) | S1 通过 | 证据等级登记完毕；追问 ≤2 次 | S1 最后 revision |
| S3 | DIRECTION | `zj-ui-direction` | `UI-DESIGN.md` (方向候选) | S2 通过 | 2–3 张方向卡 + **Human 选择已签** | S2 revision |
| S4 | DESIGN_SYSTEM | `zj-ui-design-system` | `UI-DESIGN.md` (tokens/catalog) | S3 Human 选择 | token/catalog 落盘；contrast 达标；无未注册组件 | S3 revision |
| S5 | FLOW | `zj-ui-flow` | `ui-flow/v1` | S4 通过 | 六义齐全 + semantic round-trip 通过 | S4 revision |
| S6 | BUILD | `zj-ui-prototype` | preview / 实现切片（**非 canonical**） | S5 + effect gate 通过 | preview 可交互；只用 catalog 内组件 | S5 revision |
| S7 | REVIEW | `zj-ui-visual-review` | `review record` | S6 通过 | Human gate 签署；问题/决策/理由/审阅者齐全 | S6 revision |
| S8 | BREAK | `zj-ui-break` | `verification receipt` (break cell) | S7 通过 | 390/768/1440 + 多语言 + 极值覆盖完成 | S6 revision |
| S9 | VERIFY | `zj-ui-verify` | `verification receipt` (a11y/interaction/motion) | S7、S8 完成 | 硬 gate 通过；receipt 链路完整可归因 | S6 revision |
| S10 | HANDOFF | `zj-ui-handoff` | `handoff` | S9 `status=PASS` | 变更摘要/命令/风险/限制/fallback/owner 齐全 | S9 revision |

交接规则（`sub-02 P 观点1`）：owner 只在**输出状态写入完成后**释放 artifact 写锁；接收者确认后才获得写锁。超时未确认 → `BLOCKED_HANDOFF` 并升级给流程维护者，**不自动改派**。

---

## 3. 十个 skill 的 capability manifest

`manifest_version` 初值统一 `0.1.0`（计划层未实现，实现时按 semver 规则升版）。`precedence` 取 stage 序号 ×10，为后续同 stage 内插入候选留出间隔。

### S1 · `zj-ui-brief`
- **owner**：brief/contract owner | **owner_scope**：`write`（`UI-BRIEF.md`） | **precedence**：10
- **input**：`{用户对话或 UI-BRIEF.md 编辑, text, required=yes}`、`{现有 artifact 版本, revision, required=no}`
- **output**：`{UI-BRIEF.md draft, artifact_kind=UI-BRIEF.md, atomic=true}`、`{unknown[], artifact_kind=UI-BRIEF.md}`
- **forbidden**：执行 effect（代码执行/网络/凭据/写回）；替用户编造 `goal_users`/`success_criteria`；把 `unknown` 压成空值；连续追问超过 2 个问题
- **dependencies**：`sub-01` brief schema；上游对话/文档 `input_revision`
- **required_capabilities**：文档解析 + schema 校验
- **stop_conditions**：缺目标/用户/成功标准 → `MISSING_INPUT` → `WAIT_HUMAN`（最多补 2 问，仍缺 → `NEEDS_CONTEXT`）；schema 校验失败 → `STOP`
- **human_gate**：`conditional`（仅当缺失必填且已追问 2 次）
- **failure_fixtures**：`FF-BRIEF-01`（正常）、`FF-BRIEF-02`（缺 success_criteria → NEEDS_CONTEXT，零写入）、`FF-BRIEF-03`（草稿含非法字段 → deny-first 拒绝，不提交 revision）

### S2 · `zj-ui-discover`
- **owner**：brief/contract owner | **owner_scope**：`write`（`UI-BRIEF.md` 的 `unknown[]`/证据） | **precedence**：20
- **input**：`{UI-BRIEF.md draft, revision, required=yes}`、`{追问预算=2, int, required=yes}`
- **output**：`{问题清单, non-canonical}`、`{证据等级, non-canonical}`、`{unknown[] 条目, artifact_kind=UI-BRIEF.md, atomic=true}`
- **forbidden**：替用户做审美/业务决定；把证据不足写成已证实；追问超过 2 次；改写 S1 已冻结的必填字段值
- **dependencies**：S1 通过的 revision
- **required_capabilities**：证据分级（可归因来源）
- **stop_conditions**：证据不足 → 标 `unknown` 四元组并继续；追问用尽仍不足 → `NEEDS_CONTEXT` → `WAIT_HUMAN`
- **human_gate**：`conditional`（追问用尽）
- **failure_fixtures**：`FF-DISC-01`（正常补齐）、`FF-DISC-02`（证据不足必须标 unknown，不得填充猜测值）、`FF-DISC-03`（追问超上限 → 停止且不写 artifact）

### S3 · `zj-ui-direction`
- **owner**：direction/design owner | **owner_scope**：`write`（`UI-DESIGN.md` 方向候选） | **precedence**：30
- **input**：`{UI-BRIEF.md, revision, required=yes}`
- **output**：`{方向卡 ×2–3, non-canonical}`、`{direction_choice 候选, artifact_kind=UI-DESIGN.md}`
- **forbidden**：自动替用户选定方向；套用未注明来源的模板；方向不唯一时默认取第一个；把外部方法主体并入本 skill
- **dependencies**：S2 revision；外部参考 provenance（license/source 必填）
- **required_capabilities**：可比较方向卡生成 + provenance 登记
- **stop_conditions**：方向不唯一或缺来源 → `WAIT_HUMAN`（Human gate，不自动套模板）；来源 license unknown → `quarantine`
- **human_gate**：`required`（方向选择是不可形式化的审美判断）
- **failure_fixtures**：`FF-DIR-01`（正常 3 卡 + Human 选 1）、`FF-DIR-02`（两卡并列且 precedence 无法消解 → 不写入、展示候选）、`FF-DIR-03`（来源 license unknown → quarantine，不进默认产物）

### S4 · `zj-ui-design-system`
- **owner**：direction/design owner | **owner_scope**：`write`（`UI-DESIGN.md` tokens/catalog） | **precedence**：40
- **input**：`{UI-DESIGN.md 方向选择, revision, required=yes}`、`{token/catalog 草案, object}`
- **output**：`{tokens, artifact_kind=UI-DESIGN.md, atomic=true}`、`{component catalog, artifact_kind=UI-DESIGN.md}`、`{禁用组合清单, non-canonical}`
- **forbidden**：注册未声明来源的组件；输出 contrast 不达标的配色；合并外部 runtime；让 adapter 拥有 catalog 字段值
- **dependencies**：S3 Human 选择；`sub-01` design schema；字体 license 台账
- **required_capabilities**：contrast 计算 + 组件注册表
- **stop_conditions**：未注册组件 / token 冲突 / contrast 不达标 → `STOP`（阻断，不降级通过）；font license unknown → `quarantine`
- **human_gate**：`none`（阻断类失败直接停，审美类已在 S3 签过）
- **failure_fixtures**：`FF-DS-01`（正常固化）、`FF-DS-02`（未注册组件 → 阻断、零写入）、`FF-DS-03`（contrast 不达标 → 阻断且不得静默替换为“相近色”）

### S5 · `zj-ui-flow`
- **owner**：flow/schema owner（**唯一写 owner**，语义 round-trip 与迁移器优先） | **owner_scope**：`write`（`ui-flow/v1`） | **precedence**：50
- **input**：`{UI-DESIGN.md, revision, required=yes}`、`{UI-BRIEF.md, revision, required=yes}`
- **output**：`{ui-flow/v1 六义, artifact_kind=ui-flow/v1, atomic=true}`、`{迁移器输出, artifact_kind=ui-flow/v1}`
- **forbidden**：合并六义中任意两义；让协议/外部 schema 拥有 `ui-flow/v1`；丢弃 `unknown` 四元组；接受第二个写 owner
- **dependencies**：S4 revision；`ui-flow/v1` schema lock；A2UI / M3E 仅作 B1 adapter 输入
- **required_capabilities**：semantic round-trip + 离线重放 + migration map
- **stop_conditions**：状态/动作/意图丢失、双 owner、`unknown` 未保留 → **hard fail**；major version mismatch → `BLOCKED_CONTRACT_MISMATCH`（不得寻找“看起来相似”的替代）
- **human_gate**：`none`
- **failure_fixtures**：`FF-FLOW-01`（正常六义 round-trip）、`FF-FLOW-02`（双 owner 并发写 → 冻结 + `BLOCKED_OWNER_CONFLICT`），`FF-FLOW-03`（intent 丢失 → hard fail 且禁止下游继续）

### S6 · `zj-ui-prototype`
- **owner**：prototype owner | **owner_scope**：`emit`（只产出非 canonical 产物） | **precedence**：60
- **input**：`{ui-flow/v1, revision, required=yes}`、`{component catalog, revision, required=yes}`、`{effect intent, object, required=conditional}`
- **output**：`{preview / 实现切片, artifact_kind=non-canonical}`、`{effect intent 申请, non-canonical}`
- **forbidden**：直接使用 catalog 外组件；绕过 policy/approval/sandbox 执行 effect；把 json-render 投影变成 SSOT；写入 canonical artifact
- **dependencies**：S5 revision；`sub-04` policy→approval→sandbox lease→executor 单入口
- **required_capabilities**：本地 preview 运行时 + effect intent 生成器
- **stop_conditions**：未注册组件 / 危险 action → `deny`；远程不可用 → 本地 preview 或 `STOP`；effect 未获批 → `WAIT_HUMAN`（零副作用）
- **human_gate**：`required`（任何不可逆/外部写入）
- **failure_fixtures**：`FF-PROTO-01`（正常本地 preview）、`FF-PROTO-02`（未注册组件 → deny，不生成实现）、`FF-PROTO-03`（远程 adapter 不可用 → 本地静态 preview fallback，不得伪造成功）

### S7 · `zj-ui-visual-review`
- **owner**：review owner | **owner_scope**：`write`（`review record`） | **precedence**：70
- **input**：`{preview/实现切片, required=yes}`、`{用户任务与风险 class, object, required=yes}`、`{environment_fingerprint, object, required=yes}`
- **output**：`{review record, artifact_kind=review record, atomic=true}`、`{问题清单+决策+理由, artifact_kind=review record}`
- **forbidden**：用截图通过单独宣称设计完成；把无法归因的 diff 判为 PASS；把 Human 未签写成已签
- **dependencies**：S6 产物；浏览器 runner（自有）
- **required_capabilities**：浏览器 inspect + 截图 + 环境 fingerprint
- **stop_conditions**：fingerprint 缺失 / diff 无法归因 → `QUARANTINED`；Human 未签 → `HUMAN_REVIEW_REQUIRED`
- **human_gate**：`required`（视觉层级、信息可理解性、生成式审美是 Human gate）
- **failure_fixtures**：`FF-VR-01`（正常签署）、`FF-VR-02`（fingerprint 缺失 → quarantine，不产出成功结论）、`FF-VR-03`（Human 未签 → `HUMAN_REVIEW_REQUIRED`，下游不得继续）

### S8 · `zj-ui-break`
- **owner**：verification owner（break lane） | **owner_scope**：`write`（`verification receipt` 的 break cell） | **precedence**：80
- **input**：`{preview/实现切片, required=yes}`、`{fixture matrix（长文本/空/错/极值/多语言）, required=yes}`、`{viewport 390/768/1440, required=yes}`
- **output**：`{verification receipt (break cell), artifact_kind=verification receipt, atomic=true}`
- **forbidden**：降低 viewport/locale 覆盖率以通过；把 overflow/focus/恢复失败记为 warning 而非 fail
- **dependencies**：S7 通过的 review record；fixture-manifest
- **required_capabilities**：版本化 fixture matrix + responsive runner
- **stop_conditions**：关键状态未覆盖 / overflow / focus / 恢复失败 → `FAIL`；环境无法验证 → `BLOCKED`
- **human_gate**：`none`（自动硬 gate）
- **failure_fixtures**：`FF-BRK-01`（正常全矩阵）、`FF-BRK-02`（1440 下 overflow → FAIL 且 receipt 记录实测值）、`FF-BRK-03`（fixture 缺失 → `BLOCKED`，不得以“部分通过”冒充 PASS）

### S9 · `zj-ui-verify`
- **owner**：verification owner | **owner_scope**：`write`（`verification receipt` 的 a11y/interaction/motion cell） | **precedence**：90
- **input**：`{preview/实现切片, required=yes}`、`{verification matrix, required=yes}`、`{environment_fingerprint, required=yes}`、`{oracle_version, required=yes}`
- **output**：`{verification receipt, artifact_kind=verification receipt, atomic=true}`、`{聚合状态, enum}`
- **forbidden**：receipt 缺链路字段仍生成成功结论；用 baseline 冒充新通过；把 stale 基线当当前证据
- **dependencies**：S7、S8 完成；Storybook active adapter（B1）
- **required_capabilities**：DOM/ARIA、focus、contrast、reduced-motion、网络边界检查
- **stop_conditions**：visual blocker / a11y blocker / receipt 缺链路 → **不生成成功 receipt**；fingerprint 变化 → `stale/revalidation_required`
- **human_gate**：`conditional`（人工未签 → `HUMAN_REVIEW_REQUIRED`）
- **failure_fixtures**：`FF-VER-01`（正常 PASS 全链路）、`FF-VER-02`（a11y blocker → 无成功 receipt 且下游冻结）、`FF-VER-03`（fingerprint mismatch → `STALE`，旧基线只作 fallback）

### S10 · `zj-ui-handoff`
- **owner**：handoff owner | **owner_scope**：`write`（`handoff`） | **precedence**：100
- **input**：`{全部 canonical artifact revision, required=yes}`、`{verification receipt (PASS), required=yes}`、`{commit sha, required=yes}`
- **output**：`{handoff, artifact_kind=handoff, atomic=true}`（含变更摘要、运行命令、风险、已知限制、fallback、责任人）
- **forbidden**：在 receipt 非 PASS 时产出完整 handoff；省略 fallback 或 owner；把外部项目链接写成唯一依赖
- **dependencies**：S9 `status=PASS`；adapter manifest/receipt（只读）
- **required_capabilities**：变更摘要生成 + 复现命令登记
- **stop_conditions**：缺 artifact/commit/风险 owner/fallback → `handoff incomplete`；adapter 不可用时仍必须可产出（项目可脱离 adapter）
- **human_gate**：`conditional`（缺任一项必填 → 停止并列出缺口）
- **failure_fixtures**：`FF-HO-01`（正常完整 handoff）、`FF-HO-02`（缺 fallback → incomplete，不标记完成）、`FF-HO-03`（adapter 已删除 → 仍能产出 handoff，证明可脱离 adapter 维护）

---

## 4. Failure fixture → owner 覆盖矩阵

每个 skill 的 failure fixture 必须能定位到唯一责任岗（`owner` 字段），否则该 fixture 不算可验收。`sub-02 B 观点4` 要求每个 skill 三 fixture（正常 / 冲突 / 失败），`T 观点1` 追加空 manifest、未知 key、极值、并发重放四类。

| skill_id | 正常 fixture | 冲突 fixture | 失败 fixture | 责任岗（owner） |
| --- | --- | --- | --- | --- |
| `zj-ui-brief` | FF-BRIEF-01 | FF-BRIEF-02（缺必填 → NEEDS_CONTEXT） | FF-BRIEF-03（非法字段 → deny-first） | brief/contract owner |
| `zj-ui-discover` | FF-DISC-01 | FF-DISC-02（证据不足 → 必须标 unknown） | FF-DISC-03（追问超上限 → 停） | brief/contract owner |
| `zj-ui-direction` | FF-DIR-01 | FF-DIR-02（并列候选 → 不写入） | FF-DIR-03（license unknown → quarantine） | direction/design owner |
| `zj-ui-design-system` | FF-DS-01 | FF-DS-02（未注册组件 → 阻断） | FF-DS-03（contrast 不达标 → 阻断） | direction/design owner |
| `zj-ui-flow` | FF-FLOW-01 | FF-FLOW-02（双 owner → 冻结） | FF-FLOW-03（intent 丢失 → hard fail） | flow/schema owner |
| `zj-ui-prototype` | FF-PROTO-01 | FF-PROTO-02（未注册组件 → deny） | FF-PROTO-03（远程不可用 → 本地 fallback） | prototype owner |
| `zj-ui-visual-review` | FF-VR-01 | FF-VR-02（无法归因 → quarantine） | FF-VR-03（Human 未签 → 冻结下游） | review owner |
| `zj-ui-break` | FF-BRK-01 | FF-BRK-03（fixture 缺失 → BLOCKED） | FF-BRK-02（overflow → FAIL） | verification owner |
| `zj-ui-verify` | FF-VER-01 | FF-VER-03（fingerprint mismatch → STALE） | FF-VER-02（a11y blocker → 无成功 receipt） | verification owner |
| `zj-ui-handoff` | FF-HO-01 | FF-HO-02（缺 fallback → incomplete） | FF-HO-03（adapter 删除 → 仍可产出） | handoff owner |

**跨 skill 冲突 fixture（编排层，非单 skill）**：

| fixture | 断言 | 期望终态 |
| --- | --- | --- |
| `FF-ORCH-01` 双 owner 争同一 artifact | 写 owner 数 = 2 | `BLOCKED_OWNER_CONFLICT`，不生成 plan、写入次数 = 0 |
| `FF-ORCH-02` 越权写入 | 低 precedence skill 试图写他人 artifact | 记录为“未执行调用”，写入次数 = 0，审计留痕 |
| `FF-ORCH-03` 幂等重放 | 同一 `request_id` 重放 100 次 | 有效写入次数 = 1，plan 逐字节一致 |
| `FF-ORCH-04` 并列 precedence | 同 stage 内 precedence 重复 | `AMBIGUOUS` → `WAITING_FOR_HUMAN`，零 skill 执行 |
| `FF-ORCH-05` 空 manifest / 未知 stage | manifest 为空或 stage 未注册 | `CONFLICT` / `UNSUPPORTED_INPUT`，调用计数 = 0 |

---

## 5. 全局不变式（本文件声明，1-3-2/1-3-3 实现）

1. **唯一写 owner**：`(stage, artifact_kind)` 的写 owner 数恰为 1；0 或 ≥2 一律 `BLOCKED_OWNER_CONFLICT`。多个只读 skill 只能串接在 owner 之后。
2. **确定性 resolver 顺序**（1-3-2 实现）：校验 artifact/schema → 过滤 `forbidden` → 匹配 `required_capabilities` → 按 stage owner 过滤 → 按 `precedence` 排序 → 最高分**唯一**才生成 plan → 判定 Human gate → 只发**一个** `next_action`。并列、缺字段、owner 不唯一、权限扩大 → 立即 `WAITING_FOR_HUMAN` / `NEEDS_CONTEXT`，**不猜、不自动换 owner、不按发现顺序取第一个**。
3. **版本与 plan 冻结**：plan 固定 `skill_id + manifest_version + plan_hash`；minor 只追加可忽略字段，major 不兼容必须拒绝执行（0 次 major mismatch 自动降级）；无显式 migration map 时 `BLOCKED_CONTRACT_MISMATCH`，不寻找“相似替代”。
4. **Human gate 单一出口**：gate 只能由编排器集中发出**一次**，skill 禁止私开第二个 gate；gate 结果只接受 `APPROVE(plan_id)` / `REJECT(reason)` / `CHOOSE(candidate_id)`；批准前只允许只读计划生成，**写入次数必须为 0**；超时 ≠ 批准。
5. **失败分类与结果一致性**（`sub-02 A 观点5`）：统一为 `NOT_STARTED` / `FAILED_BEFORE_SIDE_EFFECT` / `FAILED_AFTER_SIDE_EFFECT` / `OUTCOME_UNKNOWN`。仅无副作用或已声明幂等的动作可自动重试，最多 2 次且携带同一 idempotency key；`OUTCOME_UNKNOWN` **禁止再次调用**，先由原 owner reconcile，仍不明则升级 Human；非幂等写入失败后不得切换 owner。
6. **幂等键**：`plan_id` + `artifact_id + stage_id`（`sub-02 P 观点3`）；同一 request 的有效写入次数 = 1，第二次调用必须记为“未执行调用”而非执行后去重。
7. **租约写锁**（1-3-3 实现）：最高 precedence 者获租约，低优先级命中者只能 `SHADOWED` 观察，不得写入；过期前不得抢占，过期后经仲裁窗口才由编排器回收重派。
8. **失败阶梯**（`sub-02 P 观点5`）：`MISSING_INPUT` → 当前 owner 一次列缺口并暂停；`DECLINED` → orchestrator 按 precedence 只试 1 个次选；`RETRYABLE_ERROR` → 原 owner 有界重试；`CONFLICT/UNSAFE` → 立即冻结 artifact 并升级 Human。任一级累计 2 次失败或超时即停止自动推进。
9. **skill 不得**：自行改派、扩权、跳过 Human gate、把未知当成功、把 adapter 能力外泄进 owner/precedence 决策。

---

## 6. 跨子文档约束（登记，不重复定义）

- **sub-01（artifact 契约）**：字段语义与 owner/source/requiredness **不可由 skill 改写**；本文件的 `writes` 只能引用 sub-01 已定义的六类 canonical artifact。
- **sub-03（adapter 生命周期）**：adapter 只能作为**已注册 capability** 进入 `required_capabilities`，不得拥有 canonical 字段值，不得改变 owner 或 precedence。
- **sub-04（trust boundary）**：policy/approval/sandbox 是 resolver 的**前置**——effect 类 skill（S6）在未获批前不得产生副作用。
- **sub-05（deterministic verification）**：verification gate 是**自动修复的前置**；验证失败先保留证据并回退，不得静默重跑。

---

## 7. 上下游契约义务

- **对上游（1-2）**：本文件的 `writes` / `reads` 必须与 `/docs/designs/ui-agent-skills/ui-agent-skills-canonical-schema.md` 的六类 artifact 与 `/docs/designs/ui-agent-skills/ui-agent-skills-ui-flow-v1-contract.md` 的六义一致；如 1-2 修订 schema，必须回写本文件的 `dependencies`。
- **对下游（1-3-2）**：必须可直接实现 §5.2 的 resolver 顺序、§5.3 的 plan hash 与 §5.4 的 gate 语义；本文件不给出具体哈希算法与并列消解阈值（留给 1-3-2 决策并 `decide` 落盘）。
- **对下游（1-3-3）**：必须可实现 §5.5 四类失败结果、§5.6 幂等键、§5.7 租约与 §5.8 失败阶梯。
- **对下游（1-6）**：十个 skill 目录与 SKILL.md 落地时，必须逐字包含本文件 §1 的 16 个字段，且 `failure_fixtures` 引用 §4 的 fixture id。
- **对 1-9（paired run）**：§4 的跨 skill 冲突 fixture（`FF-ORCH-01..05`）纳入每轮回归套件；skill/precedence/manifest 变更必须先过这套 fixture。

---

## 8. 退出判据自检（对齐 1-3-1 exit criteria）

1. **十个 manifest 字段齐全**：§3 逐个登记 16 字段，无空缺。✅（本文件声明）
2. **每个 skill 的 failure fixture 可定位 owner**：§4 矩阵覆盖 10×3 + 5 条跨 skill fixture，每条对应唯一责任岗。✅（本文件声明）
3. **实测项（不在本节点内）**：manifest 静态检查通过率 100%、`(stage,artifact)` 写 owner 数=1、同输入 100 次重放 plan 一致、0 次越权写入、0 次失败后自动换 owner —— 需 1-6 / 1-9 用真实 skill 与 fixture 实测后回写。

> 本文件为 manifest **冻结**层；第 3 项属实测，节点内不宣称通过。
