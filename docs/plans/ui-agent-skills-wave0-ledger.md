# Wave 0 资源 / 许可证 / fixture / owner / 风险账本（EV-v0.1）

> 归属路线图节点：1-1-4（建立 Wave 0 资源、许可证、fixture、owner 与风险账本）
> 事实源：`docs/plans/ui-agent-skills-roadmap.json`
> 配套：`ui-agent-skills-scope-manifest.md`（v0.1 冻结）、`ui-agent-skills-ev-form-lock.md`（表单锁定）、`ui-agent-skills-ev-metrics.md`（指标预注册）
> 状态：Wave 0 账本版，可由 Human 复核；任何账本项变更须经 1-10 重评流程。
> 退出判据：五张账本无 `unknown` 漏洞；真实缺口仅以 `NEEDS_CONTEXT` 退出，不编造。

## 0. 总览与硬约束

- 本账本只登记 **Wave 0（EV-v0.1 表单 + 审批双样例）** 所需的资源、许可证、fixture、owner 与风险；Wave 1（审批链多级/会签、其余前端框架 adapter）与长期治理不在范围。审批流（A-* fixture）随 2026-10-21 范围扩张纳入本账本，具体条目在 **1-5-1** 登记。
- fixture 与部分资源（验证 harness、adapter）将在后续节点（1-5 / 1-7 / 1-8）落地；本账本只登记**意图 + owner + 状态**，不在 1-1-4 提前实现。
- 任何单元格不得为 `unknown` 而无处置；确有外部决策缺口的项标 `NEEDS_CONTEXT`。

---

## 1. 资源账本（Resources）

| ID | 资源 | 版本 / 约束 | 用途 | 状态 | Owner |
| --- | --- | --- | --- | --- | --- |
| R-ENV-1 | Node.js 运行时 | ≥ 18.17（Next.js 14 要求） | 本地 Next.js dev server | 可用 | zjj |
| R-ENV-2 | 系统 Python | `/Users/bilibili/anaconda3/bin/python3`（含 PyYAML 6.0.3） | 验证/CLI 脚本、harness | 可用（见 R-RISK-2） | zjj |
| R-ENV-3 | 托管 Python | 3.13.12（`.workbuddy/binaries`） | 非 PyYAML 依赖脚本 | 可用，缺 PyYAML | zjj |
| R-BRW-1 | Chromium（固定 major） | 与 1-5 指纹对齐 | 确定性截图/DOM/ARIA 验证 | 待固定版本登记 | zjj |
| R-ADP-1 | Storybook | active adapter（1-7-3） | 本地组件验证 adapter | 待 1-7 落地 | zjj |
| R-MOCK-1 | 本地 mock 数据层 | 内存 / fixture，无真实后端 | 表单持久化模拟 | 待 1-5/1-8 落地 | zjj |
| R-HAR-1 | 确定性验证 harness | 1-5-2 双 lane / 指纹 / 时钟 / seed | paired run 验证 | 待 1-5 落地 | zjj |
| R-REPO-1 | 十个 UI skill 仓库目录 | `skills/`（公共，递归发现） | skill 载体 | 已存在 | zjj |
| R-FIX-1 | fixture 存储目录 | 待 1-5 落地时确定 | 表单六类 fixture | planned | zjj |

---

## 2. 许可证账本（Licenses）

| ID | 组件 | 许可证 | 商用/再分发结论 | 缺口处置 |
| --- | --- | --- | --- | --- |
| L-NEXT | Next.js 14 | MIT | 可商用、可再分发 | 无 |
| L-REACT | React 18 | MIT | 可商用、可再分发 | 无 |
| L-TS | TypeScript 5.x | Apache-2.0 | 可商用、可再分发 | 无 |
| L-SB | Storybook | MIT | 可商用、可再分发 | 无 |
| L-CHROME | Chromium | BSD-3-Clause（Chromium 项目） | 本地使用合规；再分发需遵守 NOTICE/商标条款 | 仅本地验证，不打包再分发 → 接受 |
| L-PYYAML | PyYAML | MIT | 可商用 | 托管 Python 缺包，改用系统 Python（见 R-RISK-2） |
| L-FONT | 确定性渲染字体：Noto Sans SC（主）+ Inter（拉丁 UI）+ JetBrains Mono（条件项） | **SIL OFL 1.1**（三者均同许可族） | 可商用、可再分发（随验证环境分发须附 LICENSE 文本）；经 `@fontsource` npm 自托管锁版本 | 2026-10-20 zj 选定回填（原 `NEEDS_CONTEXT`），登记完成 |

> 说明：技术栈主体为 MIT/BSD/Apache 宽松许可，商用无阻碍。原唯一真实缺口 **L-FONT** 已于 2026-10-20 解决——zj 选定 Noto Sans SC + Inter + JetBrains Mono（许可均 SIL OFL 1.1），经 `@fontsource` npm 包自托管锁版本保证 CI/本地一致，许可登记本账本。env 指纹 `font` 轴已同步回填并重冻结（1-5-1）。

---

## 3. Fixture 账本（Fixtures）

表单六类 fixture 源自 `ui-agent-skills-ev-form-lock.md` §4 与 `ui-agent-skills-ev-metrics.md` §1，均对应指标预注册的 invalid-run 边界用例。

| ID | Fixture | 触发路径 | 预期结果 | 落地点 | 状态 | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| F-1 | 成功路径（合法 profile） | idle→validating→submitting→success | mock 200 + 本地持久化 | R-FIX-1（待定路径） | planned | zjj |
| F-2 | 空提交 | 必填校验 | 字段级 error，禁止提交 | R-FIX-1 | planned | zjj |
| F-3 | 非法格式（如邮箱/长度） | 实时校验 | 字段级 error message | R-FIX-1 | planned | zjj |
| F-4 | 重复提交（提交中再触发） | submitting 锁输入 | 第二次提交被拒/忽略 | R-FIX-1 | planned | zjj |
| F-5 | 服务端 422 | 模拟 mock 422 | error 态 + 可恢复回 editable | R-FIX-1 | planned | zjj |
| F-6 | 超时 | 模拟服务端超时 | fallback 到稳定路径 / 显式标记 | R-FIX-1 | planned | zjj |

适配器 fixture（opt-in，登记意图，详细归 1-7）：

| ID | Fixture | 归属 | 状态 | Owner |
| --- | --- | --- | --- | --- |
| F-A1 | Storybook stories / a11y / viewport / interaction / docs | 1-7-3 active | planned | zjj |
| F-A2 | json-render / A2UI / M3E Canvas golden fixtures | 1-7-4 opt-in | planned | zjj |

> 所有 fixture 在 1-5/1-8 落地时须保留原始日志与屏幕/DOM 证据（见 `ev-metrics.md` §4–5），否则该 run 按 invalid 处理。

---

## 4. Owner 账本（Responsibilities）

责任分配沿用 `ui-agent-skills-ev-form-lock.md` §5（2026-10-19 由 zj 确认）。

| 领域 | 责任人 | 类型 | 决策/验收方式 |
| --- | --- | --- | --- |
| 产品 / scope / 毕业判定 | **zj** | Human gate | 人工批准冻结（scope / metrics / 三次 run） |
| 实现（样例 / fixture / harness / skill） | **zjj** | AI 搭档 | 落盘交付物 + render，供 zj 复核 |
| 范围 manifest（1-1-1） | zjj 产出 / zj 批准 | 协作 | decide 落盘 |
| 表单锁定（1-1-2） | zjj 产出 / zj 批准 | 协作 | 已确认 |
| 指标预注册（1-1-3） | zjj 产出 / zj 批准 | 协作 | decide 落盘 |
| 账本（1-1-4） | zjj 产出 / zj 批准 | 协作 | 本文件 |
| Fixture（F-1~F-6） | zjj | 实现 | zj 按 acceptance 复核 |
| Adapter（Storybook active） | zjj 实现 / zj 验收 | 协作 | 1-7-3 |
| 验证 harness | zjj | 实现 | 1-5 |
| Graduation gate | zj | Human gate | 1-9-4 |

> 单一 AI 实现依赖（zjj）的冗余缺口见 R-RISK-6，由 zj 验收 gate 兜底，已确认可接受。

---

## 5. 风险账本（Risks）

| ID | 风险 | 影响 | 缓解 | Owner | 状态 |
| --- | --- | --- | --- | --- | --- |
| R-RISK-1 | Chromium 版本漂移 | 确定性验证结果不可比，paired run 失效 | 固定 major + 环境指纹登记（1-5-1） | zjj | open /  mitigated-by-design |
| R-RISK-2 | 托管 Python 缺 PyYAML | 验证/CLI 脚本跑不通（今日 #180 已撞） | 改用系统 Python（`anaconda3/bin/python3`） | zjj | mitigated（已发生并规避） |
| R-RISK-3 | 字体许可/可用性未定 | 跨机渲染不可复现，基线噪声 | 已选定 Noto Sans SC + Inter + JetBrains Mono（SIL OFL 1.1），`@fontsource` 锁版本并登记 L-FONT | zj | mitigated（2026-10-20，原 open / 阻塞于 NEEDS_CONTEXT） |
| R-RISK-4 | mock 数据边界模糊 | 与"无真实后端写回"约束冲突 | 明确 mock 仅本地 fixture；远程写回仅演练（form-lock §1） | zjj | mitigated-by-design |
| R-RISK-5 | adapter 网络依赖 | 断网/远程失败致验证中断 | degraded/disabled/quarantine 回退 + 本地 static preview（1-7-5 / 1-8-5） | zjj | open /  缓解路径已规划 |
| R-RISK-6 | 实现责任单点（zjj=AI） | 关键实现无人类冗余 | zj 验收 gate 兜底（已知约束，已接受） | zj | accepted |
| R-RISK-7 | 缺原始日志/证据留存 | 触发 invalid-run，样本作废 | `ev-metrics.md` §4–5 强制留存，复核者提出、zj 批准补跑 | zjj | mitigated-by-design |
| R-RISK-8 | Chromium 本地再分发合规 | 若打包分发触商标/NOTICE 条款 | 仅本地验证不打包（见 L-CHROME） | zjj | accepted |

---

## 6. 退出判据核对

- [x] 资源账本：9 项全登记，无 `unknown`（R-ENV-3 缺 PyYAML 已记缓解）。
- [x] 许可证账本：7 项登记；唯一真实缺口 L-FONT 标 `NEEDS_CONTEXT`，不编造。
- [x] fixture 账本：表单六类 + 适配器两类全登记，状态=planned，owner 明确。
- [x] owner 账本：zj / zjj 分工全维度登记，沿用已确认分配。
- [x] 风险账本：8 项登记，含已发生（#180）与已接受约束，缺口 R-RISK-3 与 L-FONT 同源、已 `NEEDS_CONTEXT`。
- [x] 无遗留 `unknown` 漏洞；仅有的外部依赖决策（字体）以 `NEEDS_CONTEXT` 退出。

> 注：账本随 1-5 / 1-7 / 1-8 落地会有 planned→available 的状态推进，但 1-1-4 的退出判据只要求"无 unknown 漏洞 + 缺口有 NEEDS_CONTEXT 处置"，本文件已满足。
>
> **2026-10-20 更新**：上述 §6 各条为 1-1-4 退出时点快照，保持原样作历史记录。其中唯一外部决策缺口 L-FONT 已解决（Noto Sans SC + Inter + JetBrains Mono，SIL OFL 1.1，`@fontsource` 锁版本），见 §2 L-FONT 条目与 §5 R-RISK-3 当前状态。
