# 开源能力拟合决策记录

> 由 `zj-open-source-capability-fit` 依据 [开源能力拟合决策模型](../../docs/agreements/open-source-capability-fit-decision-model.md) 生成。

## 目标需求 R

角色=active 本地验证 adapter：评估 Storybook 作为隔离渲染/a11y/交互/响应式/文档的本地验证面，并满足安全移除与许可证要求。

- **R1** [关键] 离线/本地渲染与静态预览：无远程依赖下隔离渲染组件/页面并产出静态 preview — 验收: 本地 dev server / build 产出静态产物，断网可回看
- **R4** [关键] 无障碍验证：DOM/ARIA、对比度、focus、overflow 硬门禁 — 验收: 提供 a11y 验证原语
- **R5** [关键] 交互与响应式测试：user-event 模拟 + viewport/响应式校验 — 验收: 可模拟交互并跨 viewport 校验
- **R6** [nice] 文档/产物面：stories/docs 生成供人工审阅 — 验收: 可从 artifact 生成可读文档/示例
- **R7** [关键] 安全移除与降级：adapter 可移除且 canonical + 本地验证在其删除后存活；具备生命周期状态 — 验收: removal test 证明删除后 canonical + 静态 preview + 本地验证仍可用
- **R8** [关键] 许可证与所有权可接受：清晰 OSS 许可证、可接受维护/bus factor、无 SBOM 红旗 — 验收: 许可证 permissive/兼容，维护健康或可隔离

## 候选 O1 · Storybook (v10.6.1 (latest stable, 2026-09-30; LTS 化可改钉 v10.5.x))

- **推荐分类**: `B`
- 关键需求覆盖率: 80% · 平均有效拟合度: 0.95 · 总所有权成本 E: 11

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | storybook.js.org：本地 dev server + build 产出静态 storybook，断网可回看 |
| R4 | native | 1.0 | 1.0 | 1.0 | 1.00 | @storybook/addon-a11y (基于 axe) 提供 DOM/ARIA/对比度/focus |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | @storybook/test play functions + @testing-library/user-event + viewport toolbar |
| R6 | native | 1.0 | 1.0 | 1.0 | 1.00 | Autodocs / MDX 从 stories 生成文档 |
| R7 | adapted | 0.7 | 1.0 | 1.0 | 0.70 | devDependency；移除后 canonical 完好，build 仍可产静态 preview；降级由 AdapterBoundary 编排保证 |
| R8 | native | 1.0 | 1.0 | 1.0 | 1.00 | MIT；~90.6k stars；8 维护者；Snyk health=Healthy |

### 依据
- 关键需求存在部分缺口但 E=11<=E_MID -> B

## 最终拍板 (Human/Agent 填)

- 选定组合 C 与能力缺口 G: ___
- 自有责任 E 及成本估计: ___
- PoC 结论: ___
- 最终分类 (A/B1/B2/B3/C/D): ___
- 采用理由: ___
- 主要风险: ___
- 退出路径: ___
- 重新评估触发条件: ___

**完成标准自检**: 第三方 Agent 仅凭本记录能否复核分类依据，并区分证据 vs 假设？