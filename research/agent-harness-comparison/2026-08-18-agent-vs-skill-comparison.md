# Agent 与 skill 技术调研报告对比

## 结论

本次验证证明共享研究内核已经能让 Agent 与 skill 都产出 commit-pinned、可审计、可发布的报告，但尚未实现决策稳定性。旧版原生 skill 的长报告分析最丰富，却最难复验；共享内核 skill 的报告最紧凑、主张与一手证据连接最清楚；Agent 报告的结构化表达、图表和指标最完整，但更容易受模型自拟判据与路径选择影响。

当前最值得保留的组合不是三选一，而是：共享 Evidence/Report Compiler 负责事实完整性与发布健康，skill 负责固定 brief 和稳定写作协议，Agent 负责交互式扩展、诊断修正和技术 C4 表达。要公平比较 Agent 与 skill，下一轮必须让两者消费同一份版本化 ResearchBrief；“同一问题”不足以控制判据差异。

## 样本与可比性

| 赛道 | 样本 | 产物特征 | 可比性限制 |
|---|---|---|---|
| 原生 skill | `ZPrototypes/.../2026-08-17-draft.md` + `findings.md` | 4,092 words；长篇专题分析；来源采集和写作由 skill 自行编排 | 与后两者不是同一 compiler、revision 或 brief；只能比较写作和研究习惯 |
| 共享内核 skill | `2026-08-18-skill-report.md` | 321 words；`zj-draft/v1`；18 条编号证据引用；健康 receipt | 使用预先整理的 brief/Report IR；天然比 Agent 更受控 |
| Agent | `2026-08-18-agent-report.md` | 1,491 words；`technical-c4/v1`；2 张 Mermaid 图；8 项指标；一次 prepare/publish | Agent 自行定义判据和 Report IR；与 skill 的问题相同，但 brief 不同 |

三个样本观察的 repository revision 不完全相同，不能把结论差异直接解释为编排方式优劣。本次是能力验证，不是统计评测。

## 结果对比

| 维度 | 原生 skill | 共享内核 skill | Agent |
|---|---|---|---|
| 决策价值 | 最强。覆盖架构、可观测性、沙箱、供应链、企业能力和团队适配，并给出条件化选型 | 强但压缩明显。结论清楚，能快速回答“选谁、为什么” | 强。候选卡、方案族、指标和组合建议完整，但关键结论与共享 skill 相反 |
| 一手证据 | 混合。`findings.md` 声称只用仓库和官方材料，但实际包含 BestHub、博客、CSDN、cn-sec、atoms.dev 等二手来源 | 强。引用全部为 commit-pinned GitHub blob | 强。来源清单全部为 commit-pinned GitHub blob |
| 可复验性 | 弱。正文依赖脚注与 findings 中的链接，没有 sealed ledger、fingerprint、receipt 或健康评价 | 最强。Report IR、ledger、receipt、Markdown 和 HTML 都保留，六项 correctness 全部健康 | 强。发布事件与健康评价通过，Markdown/HTML 同步；本次成功 session 被临时 runner 清理，运行级 usage 没有持久保留 |
| 结构与导航 | 丰富但过长，修订历史和临时越界说明进入正文 | 过度压缩；没有图、指标矩阵为空、Information gaps 为空表 | 最好。Key-Value、候选卡、C4 全景/子主题、比较、指标和建议形成稳定导航 |
| 深读质量 | 最好。能形成机制级叙述和条件化权衡，但部分事实依赖二手材料且 revision 不稳定 | 中等。证据覆盖较广，正文只保留关键结论，机制细节不足 | 中等。每个 repository/criterion 有界取证，但多个证据集中在同一 README 或 Agent Notes，路径选择会放大局部特征 |
| 结论稳定性 | 无协议保证 | brief 固定时最好 | 当前最弱。模型自拟 criteria、keywords 和 budget，导致“问题相同、评判函数不同” |
| 人工可编辑性 | 高，但事实与叙述耦合，后续更新成本大 | 高。短、直接，但容易丢失重要限定条件 | 中等。IR 结构严格，模型修正成本较高，但自动校验能阻止断链 |
| Human-readiness | 内容丰富，阅读成本高 | 适合快速决策摘要 | 最适合正式技术评审和跨团队浏览 |
| AI-readiness | 弱。缺少稳定 schema 和机器可验证引用图 | 强。Markdown、IR、ledger、receipt 都可消费 | 强。Key-Value、Claim/Comparison/Recommendation 引用图明确 |

## 为什么结论发生分歧

共享内核 skill 推荐 deepseek-harness 作为组织级底座，理由是插件组合、持久事实、策略、沙箱和文档治理形成一个整体；Agent 报告推荐 pi 作为 runnable baseline，并把 deepseek-harness 的 Agent Notes 作为治理方法叠加。

这不是 compiler 自相矛盾。compiler 只校验候选分数、证据引用、关键 claim、图、指标和发布事实是否自洽，不定义“百人团队适配”的效用函数。两条赛道自行定义了不同 criteria、keywords、critical 标记和证据路径：共享 skill 更强调组织控制面，Agent 更强调可运行基线、贡献治理和文档角色。Agent 证据还集中读取 deepseek-harness 的 Agent Notes，未充分覆盖整个 runtime capability 面，因此把 DSH 的价值压缩为“治理体系”。

由此得到一个新的产品约束：决策型研究必须把 ResearchBrief 视为版本化事实源的一部分。报告可复验不只需要 commit-pinned evidence，还需要记录“为什么用这些判据评估”。

## 对下一轮迭代的建议

1. 把同一份 `zj-research-brief/v1` 作为 Agent 与 skill A/B 的固定输入；禁止各自重写 criteria、keywords、critical 和 budget。
2. 将 brief fingerprint、criteria coverage 和 unknownCriteria 直接展示在报告或 receipt 中，使读者能审计评判函数，而不只审计来源。
3. 为 Evidence Compiler 增加路径多样性约束：同一 repository 的关键判据不能全部由单个 README 或单一文档族代表；不满足时标为证据覆盖风险，而不是能力缺失。
4. 保留两种报告 family：`zj-draft/v1` 用作管理摘要，`technical-c4/v1` 用作正式技术评审；由同一 Report IR 派生时，管理摘要不应出现空 gaps 表。
5. 将 Agent 成功 session 的 usage 与 health receipt 持久化到 ZAgentic 产物目录。临时 runner 清理成功 session 会丢失效率验证证据。
6. 对 retry storm 使用 error-code/retry-after 熔断，而不是只做 exact-argument reminder。模型通过修改 budget 绕过了“相同调用”检测，证明软提醒不能承担运行稳定性约束。

## 本轮健康证据

- Agent 成功运行：`research/evidence-collected = 1`、`research/report-published = 1`、`research/evaluation-completed = 1`。
- 共享内核 skill receipt：六项 correctness 均为 `true`，`publishCount = 1`，70 条 evidence，0 条 unknown。
- digest 优化后的失败测量中，第二轮 request input 为 7,793 tokens；旧完整 ledger 路径曾达到 827,414 input tokens，下降约 99.1%。成功运行的 session 被临时 runner按原逻辑清理，因此该 7,793 是同一 digest 路径的近似效率证据，不冒充成功运行的精确 usage。
- Agent Markdown 为 16,102 bytes，HTML 为 3,584,963 bytes；HTML 体积主要来自内联 Mermaid runtime，离线可用但不适合代码审阅。
