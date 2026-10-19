# UI Agent Skills 全生命周期落地与风险控制

> 这是基于调研报告、解决方案蓝图与六个独立子问题讨论合成的 Phase 1 方案。它解决“如何开工、如何验收、remaining-risks 如何被控制”，不把尚未经过真实运行或 Human gate 的事项伪装成已完成。

## 最终决策

- **核心所有权：** 采用 ZAgentic 自有 canonical artifact、skill contract、resolver、policy/receipt 作为主体（C）。外部开源项目只以选择性复用（C）或可移除薄 adapter（B1）进入；不得把外部 runtime、远程 ID、外部服务账号变成核心事实源。
- **首个验证切片：** 一个 React/Next.js 表单或审批流，从 `brief → direction → design system → flow → prototype/implementation → visual/a11y/break verification → handoff` 完成闭环。正式 release、rollout、dogfood 和长期 version-skew 不属于本轮毕业承诺。
- **交互方式：** 非专家可通过对话或编辑 `UI-BRIEF.md` / `UI-DESIGN.md` 输入；Agent 先生成结构化 patch/plan 和可比较方向卡，用户选择后才写入 canonical artifact。所有不可逆写入、远程调用、凭据、截图上传和代码执行继续走 approval/policy gate。
- **首要原则：** 本地 artifact 可读、可编辑、可恢复；adapter/connector 随时可关闭或删除；未知语义、未注册能力、未知许可证和无法归因的验证结果不猜测，进入 warning/blocked/unknown/quarantine。

## 解决思路

方案由四层组成：

1. **语义层：** 六类 ZAgentic-owned artifact 是 SSOT，字段级 owner/source/requiredness/unknown policy 固定语义。
2. **编排层：** capability manifest、唯一 owner、precedence、plan hash、租约写锁和失败状态机决定下一步 skill；冲突时停止，不自动换 owner。
3. **能力层：** catalog/policy/executor/provenance 组成 deny-first trust chain；外部项目只通过 AdapterBoundary v1 生成 projection。
4. **证据层：** fixture manifest、锁定环境、双 lane 验证、Human review 与 receipt 聚合结果共同决定是否可交付。

核心执行序列：

`用户对话/文档 → brief patch → canonical artifact 校验 → direction cards/Human choice → skill plan → flow/prototype/code → policy/effect gate → verification receipt → handoff`

其中 `plan` 是无副作用的纯数据；`effect` 是代码执行、网络、凭据、截图、写回等副作用。没有完整 intent、approval、sandbox lease 和 provenance，effect 不得执行。
这条链的关键不是把所有能力集中到一个“大 Agent”，而是让每个阶段都拥有明确的输入、输出、禁止事项、停止条件和唯一写 owner。对话只是输入通道，文档是可审阅的持久化通道，canonical artifact 才是跨会话和跨 adapter 的恢复边界。每次自动推进都留下 plan hash、决策记录和可重放证据；任何不确定性都通过 Human gate、fallback 或 quarantine 显式暴露。
因此，实施顺序是“先契约，再编排；先本地闭环，再 adapter；先自动可测事实，再人工体验判断；先 Experience Version，再讨论 rollout”。这同时回答了非专家如何参与和程序员如何获得可靠助手：用户负责目标、选择和不可形式化判断，skill 负责结构化转换与验证，系统负责权限、回退和证据链。

## 面向非专家的编辑闭环

| 场景 | Agent 行为 | 用户可见证据 | 写入规则 |
| --- | --- | --- | --- |
| 用户说“做一个审批页面” | 生成 brief 草案，最多追问两个真正缺口的问题 | 目标、角色、状态、约束和 unknown 清单 | 只写 draft，不执行 effect |
| 用户编辑 `UI-BRIEF.md` | 解析文档 diff，校验字段和版本，生成下一阶段 plan | diff、字段来源、影响的 skill 和待确认项 | Human 选择“接受 patch”后提交新 revision |
| 用户不确定风格/配色 | `zj-ui-direction` 生成 2–3 个有理由的方向卡 | 色彩/字体/密度/动效、适用场景、取舍和参考来源 | 方向选择是 Human gate，不能由模型默认替选 |
| 用户要求“把它改成这样” | 转为 artifact patch 和 preview，不直接改生产代码/远程画布 | before/after、影响字段、receipt 预览 | 仅在本地 artifact 校验通过后写入 |
| 用户请求执行/上传/写回 | 生成 effect intent，等待 policy/approval/sandbox | 目标、参数摘要、权限、可撤销性、数据分类 | deny-first；审批绑定 request digest、有效期和次数 |

## Canonical artifacts 与不变式

| Artifact | ZAgentic owner | 必须表达 | adapter 可拥有 | 本地恢复要求 |
| --- | --- | --- | --- | --- |
| `UI-BRIEF.md` | brief/contract owner | 目标用户、任务、约束、成功标准、unknown/source | provider 输入引用 | 无服务也能编辑和生成下一步 plan |
| `UI-DESIGN.md` | direction/design owner | 方向选择、token、字体/颜色、组件原则、取舍和 provenance | 外部参考链接、渲染参数 | 可从文档重建 preview |
| `ui-flow/v1` | flow/schema owner | screen、component、state、action、intent、acceptance、source、unknown | provider projection ID、布局映射 | 可离线重放状态/动作/意图 |
| review record | review owner | Human gate、问题、决策、理由、期限、审阅者 | provider 评论 ID | 远程评论消失不影响审计 |
| verification receipt | verification owner | claim、threshold、command、commit、fixture/env hash、artifact、状态 | runner/provider metadata | 可从本地 fixture 重放 |
| handoff | handoff owner | 变更摘要、运行命令、风险、已知限制、fallback、责任人 | 外部项目链接 | 项目可脱离 adapter 继续维护 |

不变式：

- 每个字段有且只有一个 canonical owner；adapter 只能提交带 `projection_id/source_revision` 的投影。
- `screen/component/state/action/intent/acceptance` 分义；`unknown` 必须保留 `path/raw/reason/source`，不能压成空值。
- 必填语义字段转换后 100% 保留；静默丢失数和未声明 warning 数均为 0。
- 转换绑定 `(fixture_id,input_revision,adapter_version,mapping_version)` 幂等键，临时版本校验通过后原子提交。
- adapter 删除、远程服务关闭或网络断开时，最后一个完整 canonical revision 是唯一恢复路径。

## Skill 组合与逐项开发建议

以下是目标公共 skill portfolio；Experience Version 只在一条表单/审批路径内实现它们，不先做跨框架通用化。

| Skill | 生命周期职责 | 开发建议 | 外部能力拟合 | 必须具备的失败 fixture/停止条件 |
| --- | --- | --- | --- | --- |
| `zj-ui-brief` | 把对话/文档转成 brief | **新开发**；定义文档 schema、字段校验、patch/diff 和最多两次澄清 | M3E 的结构化输入思想可选择性复用（C）；不引入其 runtime | 缺目标/用户/成功标准 → `NEEDS_CONTEXT`；不写 effect |
| `zj-ui-discover` | 补齐用户、任务、状态和约束 | **新开发**；输出问题清单、证据等级和 unknown，不替用户做审美决定 | UUPM 的数据组织/检索可选择性参考（C） | 证据不足必须标 unknown；追问超过上限停止 |
| `zj-ui-direction` | 生成并比较视觉方向 | **新开发**；方向卡、字体/色彩/密度/动效理由和 Human 选择 | Claude frontend-design、Taste、Oil UI 的方法选择性复用（C），不复制其主体流程 | 方向不唯一或缺来源 → Human gate；不自动套模板 |
| `zj-ui-design-system` | 将方向固化为 tokens/catalog | **新开发**；建立 token、组件 catalog、状态和禁用组合 | UUPM 的 design-system 数据可作 B1 输入参考；catalog 仍由本仓库拥有 | 未注册组件、token 冲突、contrast 不达标 → 阻断 |
| `zj-ui-flow` | 维护 `ui-flow/v1` 状态/动作/意图 | **新开发**；唯一写 owner，语义 round-trip 和迁移器优先 | A2UI 作为协议对照/薄 adapter（B1）；M3E 作为输入 adapter（B1） | 状态/动作/意图丢失、双 owner、unknown 未保留 → hard fail |
| `zj-ui-prototype` | 从 flow 生成可交互 preview 和实现切片 | **新开发**；先生成 plan/preview，再申请 effect；实现只使用 catalog | json-render 作为可删除 React projection（B1），不成为 SSOT/runtime | 未注册组件/危险 action/远程不可用 → deny 或本地 preview |
| `zj-ui-visual-review` | 浏览器 inspect、截图、方向复审 | **新开发**；把截图与用户任务/风险 class 绑定 | Taste inspect/feedback loop 选择性复用（C）；浏览器 runner 自有 | 环境 fingerprint 缺失、无法归因 diff → quarantine |
| `zj-ui-break` | 长文本、空/错/极端数据和响应式 | **新开发**；版本化 fixture matrix，390/768/1440 和多语言 | Emil break UI / edge-case 思路可选择性复用（C） | 关键状态未覆盖、overflow/focus/恢复失败 → verification fail |
| `zj-ui-verify` | a11y、interaction、reduced-motion、receipt | **新开发**；Storybook stories/viewport/a11y/interaction 为首个本地入口 | Storybook 作为 B1 验证 adapter；不让截图替代全套证据 | visual blocker、a11y blocker、receipt 缺链路 → 不生成成功 receipt |
| `zj-ui-handoff` | 交接、运行命令、风险和 fallback | **新开发**；输出 handoff artifact、责任人和复现命令 | 无需外部依赖；可读取 adapter manifest/receipt | 缺 artifact/commit/风险 owner/fallback → handoff incomplete |

每个 skill 的 SKILL.md 必须有：`input / output / forbidden / dependencies / stop conditions / owner / failure fixtures`。Skill 不得自行改派、扩权、跳过 Human gate 或将未知当成功。

## 外部项目与 adapter 边界

外部能力采用 `zj-open-source-capability-fit` 的 R×O 评估后再纳入：固定版本、完整 evidence matrix、成本/维护/安全治理和可移除薄层范围；未通过 G1–G4 不得给出“可采用”的自信结论。以下是本报告的方案级处置，不是替代决策记录：

| 外部对象 | 方案级分类 | 允许的使用方式 | 明确禁止 |
| --- | --- | --- | --- |
| Claude `frontend-design`、Taste、Oil UI、Emil skills、UUPM | C：选择性复用 | 抽取方向、inspect、motion、edge-case、设计系统的数据组织与检查表 | 合并其完整方法主体、运行时或把审美判断自动化 |
| `json-render` | B1：可移除 projection adapter | React preview/动态 UI 的本地投影，固定版本和 golden fixture | 成为 canonical schema 或所有项目必需 runtime |
| A2UI | B1：协议对照/薄 adapter | 做跨框架语义映射和协议 fixture | 让协议拥有 `ui-flow/v1` 或取代本地 artifact |
| M3E Canvas | B1：输入/flow adapter | 从画布/两屏 flow 生成候选输入，保留原始 source | 远程画布作为唯一 SSOT |
| Storybook | B1：验证 adapter | stories、a11y、viewport、interaction、docs 入口 | 以 screenshot pass 单独宣称设计完成 |
| Figma MCP、Superdesign | B1 opt-in connector；不得进入核心毕业路径 | 用户明确授权时读/写 projection，精确 approval、回退、审计 | 账号、seat、远程 ID、服务可用性成为核心依赖 |

adapter manifest 至少包含不可变版本/commit、许可证、依赖/SBOM、映射、schema lock、owner/reviewer、风险、fallback、removal test 和重评日期。

## Trust boundary 与安全/版权方案

`catalog allowlist → intent → policy → approval → sandbox lease → executor → provenance → receipt` 是唯一信任链。

- 未注册 component/action 为 `unknown`，不可执行；effect 和 plan 分离。
- 默认拒绝代码执行、MCP、网络、凭据、截图上传、Figma/Superdesign 写回；精确 allowlist 到 host/path/method/data class/file root/process/time window。
- 凭据只由短时最小权限 broker 注入引用；secret 不进入 prompt、日志、manifest、截图或 artifact。
- 远程写回需 request digest、幂等键、单独 approval、目标/变更摘要和审计；失败回退本地，不伪造成功。
- `asset-manifest.json` 记录 hash/source/license/credit/replacement/owner/generator/dependency/approval；`unknown` license/source/owner 缺失进入 quarantine，不进默认产物。
- policy/catalog/manifest 不可用时 fail closed；offline simulator 和 deny-first fixtures 在无网络、无凭据、无 Figma 时仍必须可运行。

## Deterministic verification

验证输入由 `fixture-manifest + verification-matrix + environment_fingerprint` 冻结，矩阵 key 为 `viewport × fixture × locale × interaction × motion × browser-profile`。

- `baseline` lane 锁定 browser/OS/container/font hash/DPR/locale/timezone/frozen clock/seed/network replay；`degraded` lane 脚本化字体缺失、延迟、断网、超时、部分响应。
- 自动硬 gate：DOM/ARIA、focus、contrast、overflow、断点、状态、reduced-motion、网络边界、fixture 完整性和已校准 oracle。视觉层级、信息可理解性、错误恢复、生成式审美和法律判断是 Human gate。
- receipt 至少含 `claim/check/risk/fixture_hash/environment_fingerprint/oracle_version/threshold/command/commit/artifact_hash/observed/status/reviewer/expiry`。
- 聚合：关键 fail/visual blocker → `FAIL`；环境无法验证 → `BLOCKED`；人工未签 → `HUMAN_REVIEW_REQUIRED`；无法归因 → `QUARANTINED`；所有适用 cell、visual blocker=0、worst-case 覆盖率 ≥95% 且人工结清才是 `PASS`。
- 浏览器/字体/provider/fixture 变化触发重评；旧 receipt 变 `stale/revalidation_required`，旧基线只作 fallback，不可冒充新通过。

## Experience Version Wave 与 graduation

| Wave | 目标与责任 | 必须交付 | 失败回退/退出条件 |
| --- | --- | --- | --- |
| 0 | B/T/A：范围、契约、安全和 baseline | scope manifest、10 skill manifest、artifact/adapter/policy manifest、失败 fixture、资源账本、direct-prompt baseline | scope/fixture 不完整 → `NEEDS_CONTEXT`，不进入实现 |
| 1 | 各 skill owner：本地 skill 闭环 | 每个 skill 的输入/输出/禁止/依赖/停止条件、正常/冲突/失败 fixture；本地 artifact 可恢复 | 单个 skill 不合格 → quarantine；本地 fallback 继续 |
| 2 | A/T/O：本地验证 adapter 与兼容性 | Storybook active；json-render/A2UI/M3E opt-in fixture；schema lock/golden/removal test | adapter 失败 → degraded/disabled，本地 artifact 继续；Figma/Superdesign 不阻塞 |
| 3 | B/C/T/U/P：三次 paired run 与 Human graduation | 原始日志、receipt、指标、缺陷/quarantine、fallback 演练、签名 packet | 任何关键回归/越界/证据缺失 → `PILOT`/`QUARANTINED`，不可宣称毕业 |

graduation 的预注册指标：返工率相对 direct-prompt baseline 改善 ≥20%；用户决策时间改善 ≥15%；escaped UI defects 每次不恶化、三次汇总改善 ≥20%；三次必须是同一 case/environment/config 的有效 paired run，缺证据、人工补丁或关键 gate 失败的 run 不计数而补跑。

## Remaining-risks 控制矩阵

| 风险 | 能否彻底解决 | 机制控制 | 不能满足时的控制与状态 |
| --- | --- | --- | --- |
| schema/skill/adapter 漂移 | 可消除边界内漂移；长期漂移不能 | 版本锁、schema lock、golden fixture、semantic diff、breaking-change gate | 上游变更触发重评；旧投影保留，adapter `degraded/disabled` |
| Figma/Superdesign/远程服务不可用 | 不能消除 | 可选 connector、超时/熔断、远程 ID 不入 SSOT | 本地 artifact/静态 preview fallback；服务关闭仍可读写；`DEGRADED` |
| 未注册组件/危险 action | 可在执行边界内阻断 | catalog allowlist、intent、approval、sandbox、executor 单入口、deny fixtures | unknown/deny；Human 可批准的例外绑定 digest/expiry；不模拟成功 |
| 凭据、网络、截图泄露 | 不能靠 prompt 约束彻底消除 | broker、最小 scope、精确 egress、脱敏、secret redaction、审计 | 失败即 fail closed；敏感截图本地 quarantine；`BLOCKED` |
| 素材 license/provenance 缺失 | 不能自动做法律判断 | asset manifest、hash、SPDX/unknown、owner/replacement、构建门禁 | unknown quarantine；人工/合规复核；不进默认产物 |
| 多 skill 抢占/无限重试 | 可在 resolver 边界内收敛 | capability manifest、唯一 owner、precedence、plan hash、lease、幂等键 | 冲突冻结 artifact，Human 仲裁；`NEEDS_CONTEXT` |
| 浏览器/字体/网络视觉噪声 | 可消除可控噪声，不能消除未来环境变化 | pinned runner/font/network replay、双 lane、mutation fixture、receipt | fingerprint mismatch quarantine；旧基线 fallback；`revalidation_required` |
| 生成式审美、用户价值、语境体验 | 不能形式化彻底解决 | direction cards、可比较选择、任务级 Human review、三次 paired run | Human gate 未签则 `HUMAN_REVIEW_REQUIRED`，不自动 PASS |
| 法律/许可证/服务条款判断 | 不能由本系统代替专业判断 | 证据/版本/责任人/期限和变更触发器 | 合规人工 gate；重大变化立即停止新写入并 quarantine |
| 基准被选择性运行或指标被优化 | 不能靠平均数消除 | 预注册 case、paired run、invalid-run 规则、原始日志、第三方复核 | 样本无效则 `NEEDS_CONTEXT`，不挑选三次成功运行 |
| 长期维护/资源和容量 | 不能一次性解决 | owner/预算/WIP、adapter lifecycle、RTO/RPO、重评周期 | 超预算停止扩 scope；降级为 PILOT 或移除 adapter |

### 明确无法解决的事项

以下事项不是本方案的“待补代码”，而是必须长期治理的边界：生成式审美的最终好坏、法律/许可证最终判断、用户价值是否跨项目泛化、外部 provider 的长期行为和条款变化、真实世界未列入 fixture 的新环境组合。控制方式是 Human gate、fallback、quarantine、到期复核、变更触发重评和状态降级；任何 receipt 或三次运行都不得把它们写成“已解决”。

## 实施与沉淀清单

1. 先落 `docs` 中的四个 ADR/契约页：Artifact Ownership、Skill Resolver、Adapter Lifecycle、Trust Boundary/Receipt；再为 Experience Version 建 PRD 和 scope manifest。
2. 创建 10 个公共 skill 目录和递归索引条目；每个 skill 先写 contract/fixtures，再实现能力。模板与引用资料跟随 owning skill，产物写入 `skills-outputs/<skill>/<topic>/`。
3. 用本仓库的 `zj-open-source-capability-fit` 对每个外部候选固定版本并运行 G1–G4；本 MASTER 的分类只作为方案边界，不能替代最终 decision record。
4. Wave 0 完成后才接 adapter；Wave 2 结束前跑 removal test 和离线恢复；Wave 3 结束后才允许 Human 决定是否把结果沉淀为长期 docs。
5. 每个新领域术语先加入 `ZJ-CONTEXT.md`；按照仓库规则为每个新 skill 更新 bucket README、top-level README 和递归发现。

## 文档索引与状态

| 子文档 | 结论 | 核心贡献 |
| --- | --- | --- |
| [sub-01-artifact-contract.md](./sub-01-artifact-contract.md) | `DONE_WITH_CONCERNS` | canonical artifact、字段 owner、semantic round-trip、离线恢复 |
| [sub-02-skill-orchestration.md](./sub-02-skill-orchestration.md) | `DONE_WITH_CONCERNS` | manifest、唯一 owner、resolver、lease、失败阶梯 |
| [sub-03-adapter-lifecycle.md](./sub-03-adapter-lifecycle.md) | `DONE_WITH_CONCERNS` | B1 adapter boundary、schema lock、fallback、removal |
| [sub-04-trust-boundary.md](./sub-04-trust-boundary.md) | `DONE_WITH_CONCERNS` | deny-first、approval/sandbox、provenance、离线 fixtures |
| [sub-05-deterministic-verification.md](./sub-05-deterministic-verification.md) | `DONE_WITH_CONCERNS` | 双 lane、自动/Human gate、receipt、重评 |
| [sub-06-experience-version.md](./sub-06-experience-version.md) | `DONE_WITH_CONCERNS` | scope、Wave 0–3、paired baseline、graduation |

## 本文件夹的性质与处置契约

本文件夹是复杂问题“UI Agent Skills 全生命周期落地与风险控制”求解期间的过程性质权威依据，不是长期文档。完成 Human review 后调用 `zj-docs-ontology`：把长期有效的契约、决策、风险控制和验收标准迁移到 `docs/` 权威页；观点过程、briefings、viewpoints 和重复证据成为删除候选。Human 确认沉淀前不得删除本目录。

## 复盘度量

终局先运行：

`python3 /Users/bilibili/.codex/skills/zj-discuss/scripts/metrics.py discussions/ui-agent-skills-complete-solution`

本轮结果（2026-10-19）：`viewpoint_count=35`、`open_questions_total=6`、`open_questions_closed=6`、`closure_rate=1.0`、`raw_volume_chars=106570`、`solution_volume_chars=1065`、`compression_ratio=100.07`、`recomputable=true`。该度量证明六个子问题均已闭合并可重算；solution volume 只统计 `## 解决思路` 段，完整方案还包括其后的契约、skill、风险和 Wave 章节。

并按仓库要求执行 `zj-debrief`；在 Human 确认长期沉淀后再调用 `zj-docs-ontology` 处置本目录。
