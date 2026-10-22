# UI Agent Skills — 决策、风险与验收（DECISIONS-RISKS）

> 权威收敛页。逐条带来源 / 决策回链。讨论过程保留于 `discussions/ui-agent-skills-complete-solution/`，不在本页维护。
>
> 关联 roadmap：`docs/plans/ui-agent-skills-roadmap.json`（1-9-4 completed；1-9-5 单独立项 G-19..G-25；1-10-4 治理触发条件已落盘）。

## 1. 毕业裁定（GRADUATION GATE）

- **状态**：`CONDITIONAL_ADOPTION`（pilot + 强制验证门禁）
- **签署**：zj，2026-10-22（run owner 不自裁，ev-metrics sub-06 P4）
- **Cohort**：R2 + R3 + R4（R1 因 DEV-4 中途改指令排除）
- **Config hash**：`404b5c8b822ef25a20ed4eed355ecb5e70f46d79999a7f786322b6cc997e38ce`（预算护栏 80，DEV-5）
- **证据包**：`SYNTHESIS-R2R3R4.md` / `CROSS-RUN-TABLE-R2R3R4.json` / `R4/*` / `RENDER-LAYER-COHORT.md` / `_tools/render-layer-report.json`
- **底表**：`../../skills-outputs/ui-agent-skills/paired-runs/v1/GRADUATION-DECISION.md`

### 证据要点

- 契约层（AI-operator，escaped-defect）：加权缺陷 skills 8.0 vs direct 13.33（−40%）；high 1.67 vs 3.67（−54.5%）；critical 0.0 vs 0.33（−100%）；代价 skills 全面更贵（返工 +303% / 墙钟 +357% / 调用 +48%）。
- 渲染层（BLK-3，真实 Chromium 155，6 lane × 7 断言）：A1 / A2 / A5 / A6 / A7 18/18 平价；唯一差异轴 A3 / A4 `aria-describedby` 关联——direct 0/3 全失败，skills 2/3（R3-h8 漏）。方向 `skills ≥ direct`（2 胜 1 平）。
- 解读：质量优势**窄（单 a11y 维度）、不稳健（skills 自己漏过 1 次）、且持续高成本溢价**。最优动作不是拒绝也不是盲采，而是**抬升验证地板**让两 lane 同标准——差距在验证层被抹平，采纳决策回归纯成本权衡。

## 2. 强制门禁 G-V1..G-V4（已 spec→代码闭环）

> 来源：GRADUATION-DECISION §GRADUATION-GATES；接线实现：PR #205（SKILL.md 规范层）+ PR #206（`skills/ui/zj-ui-core/scripts/ui_stages.py` `run_verify` `enforce_gates`，opt-in，默认关闭）；均已合入 main（789995c，2026-10-22）。

- **G-V1** 状态迁移 UI 可达性：契约状态机每个合法迁移须有 UI 可达入口 / 控件，否则验证失败（cohort §6 盲点 #1）。
- **G-V2** 无伪成功 / 无静默丢数据：`error` / `failed` 终态不得渲染 / 报为 `success`；提交 / 持久化失败须显式报错，不得静默空成功（盲点 #2）。
- **G-V3** 非法迁移返回值被检查：非法 / 未定义迁移返回值不得静默丢弃，须显式校验并拒（盲点 #3）。
- **G-V4** 必填输入 `aria-describedby` 关联：校验失败时每个必填输入须经 `aria-describedby` 关联错误区，缺失即失败（a11y；渲染层 A3/A4：direct 0/3、skills 2/3 缺失）。

## 3. Open 风险（记录，非阻塞）

| 风险 | 说明 | 状态 / 处置 |
|---|---|---|
| BLK-2 token 计量 | 成本以审计步数 / 墙钟计量，非真实 token 数 | open；paired-run 指标维持步数 / 墙钟口径 |
| 盲性未证实 | 6 次探针 4 命中，不可称双盲 | open；不宣称盲性结论 |
| provider drift（长期） | 候选 adapter（Storybook / json-render / A2UI / M3E）版本漂移 | 由 1-10-3 版本重评 + 1-10-4 revalidation 触发控制 |
| 生成式审美 | 主观审美判断不可机检 | 由 1-10 长期治理 Human gate 控制，不宣称解决 |
| 法律判断 | 合规 / 法律判断不可机检 | 同上，Human gate + quarantine 控制 |
| 1-9-5 持久化重放闸门 | G-19..G-25 待真实 skill + fixture 回写 1-3-4 文档闸门表 | 单独立项（roadmap 根级），待另开专项 |

## 4. 验收标准（acceptance）

- 毕业 gate：CONDITIONAL_ADOPTION 已签（1-9-4 completed）。
- 门禁硬拦截：G-V1..G-V4 在 `run_verify` 代码接线已合入 main，显式 `enforce_gates=true` 触发（默认关闭，避免误伤既有 adapter 路径）。
- Pilot 观察态：skills-path 仍 observational；每 run 跟踪两指标——成本溢价（返工 / 墙钟 / 调用）与 a11y-gate 通过率；未稳定前不升默认 / 生产路径。
- 重评触发：门禁生效后若 pilot 显示 skills-path a11y-gate 通过率 ≤ direct（门禁未闭合差距），升级到新一轮 gate review。
- 1-10-1 完成判据（本页范围）：稳定契约 / 决策 / 风险 / 验收已迁移到本权威页 + 来源 / 决策回链完整 + 讨论过程未删（**待 zj review**）。

## 5. 治理触发条件（rollout / pilot / kill-switch / adapter 移除 / revalidation）

> 来源：roadmap 1-10-4（5 条决策已落盘）。触发条件可执行；门槛数值（≥3 run / ≥2 run / ≥30 天 / 90 天）zj 2026-10-22 已采纳。

### 5.1 Pilot（试点）
- skills-path 维持 **observational**（非默认 / 非生产）；沿用 R2+R3+R4 cohort 与 G-V1..G-V4（`enforce_gates=true` 可选）。
- 每 run 跟踪两指标：**成本溢价**（rework / wall-clock / calls，基线 +303% / +357% / +48%）与 **a11y-gate 通过率**（skills vs direct）。
- 退出到 rollout-review 硬条件：a11y-gate 通过率 skills ≥ direct **连续 ≥3 run**，且成本溢价趋势不恶化（或 Human gate 接受溢价）。

### 5.2 Rollout（发布 / 推广）
- **非自动**：须显式 Human gate 签署 + 满足 pilot 退出条件 + G-V1..G-V4 在干净 run 上 `enforce_gates=true` 校验通过 + revalidation 通过。
- 分波推广（参考 1-1-4 Wave 0 资源）：**canary（1 个 experience-version）→ cohort → full**。
- 任一步回退到 observational 须重走 pilot 退出条件。CONDITIONAL_ADOPTION 状态不变。

### 5.3 Kill-switch（熔断）
自动熔断（置 `degraded` / `disabled` + 通知 owner + 冻结推广）：
- (a) a11y-gate 通过率 skills < direct **连续 ≥2 run**；
- (b) 重新出现 **critical escaped defect**（基线 critical=0）；
- (c) 某 **G-V1..G-V4 门禁回归**（曾通过现失败）；
- (d) **active adapter 远端不可达且无本地 degraded fallback**。
- 手动熔断：Human 或 owner 随时触发。熔断后须 revalidation 通过方可重新 promote。

### 5.4 Adapter 移除
- 触发：1-10-3 版本重评确认 **provider drift** 使候选版本与 capability-fit 证据账本不兼容 → 标记 `deprecate`；且 **1-7-2 removal test 通过**（本地恢复、degraded / disabled / quarantine 在无该 adapter 时仍成立）；且 **≥30 天弃用通知 + owner 签署 + 无活跃 pilot 依赖它**。
- 移除须保留 **AdapterBoundary v1** 与 fallback，保证本地路径不被破坏。与 1-7 adapter 生命周期联动。

### 5.5 Revalidation（重验证）
触发：
- 任一 **adapter 版本变更**（provider drift，由 1-10-3 触发）；
- **config hash 变更**（预算护栏 / 门禁）；
- **kill-switch 恢复后重 promote 前**；
- **G-V1..G-V4 spec 变更**；
- **周期性每 90 天**（zj 2026-10-22 已采纳）。
- revalidation = 重跑 verification-matrix（1-5）+ paired-run 子集 + 门禁检查，产出 `revalidation_required` 清除或 `stale` 标记。

## 6. 回链

- 毕业裁定底表：`../../skills-outputs/ui-agent-skills/paired-runs/v1/GRADUATION-DECISION.md`
- 路线图：`../plans/ui-agent-skills-roadmap.json`（1-9-4、1-9-5、1-10）
- 权威枢纽：`../ui-agent-skills/INDEX.md`
