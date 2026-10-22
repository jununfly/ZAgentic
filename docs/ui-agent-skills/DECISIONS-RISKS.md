# UI Agent Skills — 决策、风险与验收（DECISIONS-RISKS）

> 权威收敛页。逐条带来源 / 决策回链。讨论过程保留于 `discussions/ui-agent-skills-complete-solution/`，不在本页维护。
>
> 关联 roadmap：`docs/plans/ui-agent-skills-roadmap.json`（1-9-4 completed；1-9-5 单独立项 G-19..G-25；1-10 治理进行中）。

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

## 5. 回链

- 毕业裁定底表：`../../skills-outputs/ui-agent-skills/paired-runs/v1/GRADUATION-DECISION.md`
- 路线图：`../plans/ui-agent-skills-roadmap.json`（1-9-4、1-9-5、1-10）
- 权威枢纽：`../ui-agent-skills/INDEX.md`
