# AdapterBoundary 候选 capability-fit 证据账本

> 关联路线图节点：**1-7 AdapterBoundary 与 adapter 生命周期** → 子节点 **1-7-1**（固定版本 + capability-fit 证据账本）。
> 判定仪器：`zj-open-source-capability-fit`（`scripts/capability_fit.py`，机械闸门 G1–G6）。
> 数据快照日期：**2026-10-20**（Web 检索；版本/许可证以该日 npm/GitHub 公开信息为准）。

## 方法论决定（关键）

**capability-fit 必须按 adapter 的架构角色分群评估，不能用一套统一 R 集套所有候选。**
统一 R 集会把 Storybook 误判为 `D`——因为它同时背上"canonical 投影(R2)"和"catalog 受限生成(R3)"两项 critical 要求，而这两项是*投影/协议类* adapter 的职责，Storybook 作为*本地验证面*本就不负责（投影映射由 AdapterBoundary 适配层做，catalog 守门由 skill resolver 做）。

因此分两群：
- **A 群 · active 本地验证 adapter**（验证面）：Storybook。R = {离线渲染, a11y, 交互/响应式, 文档, 安全移除, 许可证}。
- **B 群 · opt-in 投影/协议/输入兼容 adapter**：json-render、A2UI、M3E Canvas。R = {离线渲染, canonical 投影, catalog 受限生成, 安全移除, 许可证}。

证据文件：
- `fit_input_validation.json` + `decision_record_validation.md`（A 群）
- `fit_input_projection.json` + `decision_record_projection.md`（B 群）
- （废弃）`fit_input.json` 为初版统一 R 集，仅留作对照，结论以分群版为准。

## 账本总表（exit criteria 对齐）

| 候选 | 角色 | 钉版本/commit | 许可证 | 依赖/SBOM | 仪器判定 | 关键风险 | owner | reviewer | 重评日期 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Storybook** | A 群·active 验证 | v10.6.1 (2026-09-30，latest stable；可改钉 v10.5.x 求稳) | MIT（部分子包 Apache-2.0） | 17 直接依赖；latest 无已知漏洞（Snyk） | **B**（key-cov 80%, fit 0.95, E 11） | R7 安全移除/降级需 AdapterBoundary 编排层实现；大依赖面 | zj（Human，待指派） | zjj（AI 搭档） | 2027-01-20 |
| **json-render** (@json-render/core) | B 群·opt-in 投影 | pre-1.0；集成前须钉具体 semver/commit | Apache-2.0 | monorepo 多包（core/react/vue/svelte/solid/…）；SBOM 待钉版本后扫 | **B**（key-cov 40%, fit 0.75, E 16） | 2026-01 新建、~449 stars、维护者极少（bus factor）；pre-1.0 API 不稳 | zj（Human，待指派） | zjj | 2027-01-20 |
| **A2UI** | B 群·opt-in 协议 | v0.8 stable / v0.9 draft / v1.0 candidate（钉 v0.8） | Apache-2.0（Google + CopilotKit） | spec 本身无运行时依赖；renderer 各自带依赖 | **B**（key-cov 20%, fit 0.77, E 16） | 协议成熟度（v0.9/v1.0 仍在演进）；需自集成 renderer | zj（Human，待指派） | zjj | 2027-01-20 |
| **M3E Canvas** (lnkiai/m3e-canvas) | B 群·（判定为 D） | 无 tagged release；须钉 main@<commit> | MIT | Next.js 16 静态 app；无后端 | **D**（key-cov 0%, fit 0.29, E 15） | 单维护者、~2 周新、病毒式增长未验证、无运行时、非 render/verify adapter | — | — | 仅 PoC 后重评 |
| **Figma MCP** | 核心毕业路径外 | — | — | — | 不进入核心毕业路径（路线图决策） | — | — | — | — |
| **Superdesign** | 核心毕业路径外 | — | — | — | 不进入核心毕业路径（路线图决策） | — | — | — | — |

## 分候选 R×O 摘要

### Storybook（A 群·active 验证）— 推荐 B（实施为 active adapter）
- native：R1 离线渲染、R4 a11y(@storybook/addon-a11y/axe)、R5 交互/响应式(@storybook/test)、R6 文档(autodocs/MDX)、R8 许可证/健康度。
- adapted：R7 安全移除（devDependency；移除后 canonical 完好 + build 仍可产静态 preview；降级面由 AdapterBoundary 保证）。
- **实施含义**：Storybook 作为首个 active 本地验证 adapter 通过；缺口 R7 必须在 1-7-2/1-7-5 由 AdapterBoundary 生命周期与 removal test 补齐。

### json-render（B 群·opt-in 投影）— 推荐 B
- native：R1 本地渲染、R3 catalog 受限生成（defineCatalog + zod，无任意代码执行，强项）。
- adapted：R2 canonical 投影（flat element tree + catalog 即声明式投影，需适配层映射）、R7 移除、R8 所有权（bus factor）。
- **实施含义**：仅在 opt-in 投影 golden fixture 中验证；集成前必须钉具体版本并扫 SBOM。

### A2UI（B 群·opt-in 协议）— 推荐 B
- native：R3 catalog 受限生成（secure-by-design，预批准 catalog，无代码执行，强项）。
- adapted：R1 需集成 renderer、R2 canonical 投影、R7 移除、R8 协议成熟度。
- **实施含义**：仅在 opt-in 协议 golden fixture 中验证；钉 v0.8，跟踪 v0.9/v1.0 演进。

### M3E Canvas（B 群）— 推荐 D（非 adapter 角色）
- R1/R2/R3/R8 均低于闸门：它本质是*本地 sketch→prompt 的 authoring 工具*，不渲染/验证最终 UI、不消费 canonical、单维护者无运行时。
- **结论**：维持 out-of-core。仅在 PoC 证明其导出的 prompt 能被 AdapterBoundary 作为 input fixture 消费后，才考虑纳入（sidecar 角色），否则不阻塞毕业。

## 闸门与就绪度
- G1 矩阵完整 / G2 需求字段 / G3 版本固定 / G4 证据非空：A、B 两群当前均通过（退出码 0）。
- G5 未知项 PoC：初版统一 R 集里 json-render R6、M3E R4/R6 曾标 unknown 并附 poc_plan；分群后在对应角色下已降级为 adapted/unsupported，无遗留 unknown 阻塞项。
- 版本"固定"为**实质缺口**：json-render（pre-1.0）、M3E（无 tag）当前仅为描述性占位，集成前必须钉到具体 semver/commit，否则不满足 G3 的"固定版本"精神。

## 后续（喂给 1-7-2..1-7-5）
1. 1-7-2：实现 AdapterBoundary v1（schema lock / mapping / fallback / removal test / 生命周期状态），补齐 Storybook 的 R7 缺口。
2. 1-7-3：Storybook active adapter（stories/a11y/viewport/interaction/docs）。
3. 1-7-4：json-render / A2UI / M3E 仅做 opt-in golden fixture（M3E 须先 PoC）。
4. 1-7-5：adapter 删除 / 断网 / 远程失败 的本地恢复与 degraded/disabled/quarantine 验证。
