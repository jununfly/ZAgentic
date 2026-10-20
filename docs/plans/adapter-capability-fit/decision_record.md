# 开源能力拟合决策记录

> 由 `zj-open-source-capability-fit` 依据 [开源能力拟合决策模型](../../docs/agreements/open-source-capability-fit-decision-model.md) 生成。

## 目标需求 R

为 UI Agent Skills 的 AdapterBoundary 选定外部 adapter 候选：固定版本并经 R×O 证据闸门，区分 active 本地验证 adapter 与 opt-in 兼容性 fixture。

- **R1** [关键] 离线/本地渲染与静态预览：毕业时须能在无远程服务依赖下隔离渲染组件/页面并产出本地静态 preview — 验收: 本地 dev server / build 产出静态产物，断网仍可渲染与回看
- **R2** [关键] canonical artifact 投影/mapping：消费 canonical artifacts（UI-BRIEF/UI-DESIGN/UI-FLOW/v1）并投影到 adapter 格式，schema lock + 可逆 mapping — 验收: 存在锁定 schema 与可逆映射层，canonical→adapter→canonical 可复核
- **R3** [关键] 声明式、catalog 受限生成（deny-first 兼容）：agent 产出受组件/动作 catalog 约束的声明式 spec，不做任意代码执行 — 验收: agent 输出经 catalog 校验，未注册组件/危险 action 被拒
- **R4** [want] 无障碍验证：DOM/ARIA、对比度、focus、overflow 等硬门禁 — 验收: 提供 a11y 验证原语或明确宿主组件负责并可挂接验证
- **R5** [want] 交互与响应式测试：user-event 模拟 + viewport/响应式校验 — 验收: 可模拟交互并跨 viewport 校验布局
- **R6** [nice] 文档/产物面：stories/docs 生成供人工审阅 — 验收: 可从 artifact 生成可读文档/示例
- **R7** [关键] 安全移除与降级：adapter 可移除且 canonical artifact + 本地验证在其删除后存活；具备 install/enable/disable/quarantine/remove 生命周期 — 验收: removal test 证明删除 adapter 后 canonical + 静态 preview + 本地验证仍可用
- **R8** [关键] 许可证与所有权可接受：清晰 OSS 许可证、可接受维护/bus factor、无 SBOM 红旗 — 验收: 许可证 permissive/兼容，维护健康或可隔离，SBOM 无高危

## 候选 O1 · Storybook (v10.6.1 (latest stable, 2026-09-30; LTS 化可改钉 v10.5.x))

- **推荐分类**: `D`
- 关键需求覆盖率: 40% · 平均有效拟合度: 0.78 · 总所有权成本 E: 11

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | storybook.js.org：本地 dev server + `build` 产出静态 storybook；断网可回看 |
| R2 | adapted | 0.5 | 0.8 | 1.0 | 0.40 | CSF/stories 为组件级格式；canonical→stories 需我们写映射层 |
| R3 | adapted | 0.3 | 0.5 | 1.0 | 0.15 | Storybook controls/args 声明式，但非 catalog 守门；deny-first 由 skill resolver 负责 |
| R4 | native | 1.0 | 1.0 | 1.0 | 1.00 | @storybook/addon-a11y (基于 axe) 提供 DOM/ARIA/对比度/focus 校验 |
| R5 | native | 1.0 | 1.0 | 1.0 | 1.00 | @storybook/test play functions + @testing-library/user-event + viewport toolbar |
| R6 | native | 1.0 | 1.0 | 1.0 | 1.00 | Autodocs / MDX 从 stories 生成文档 |
| R7 | adapted | 0.7 | 1.0 | 1.0 | 0.70 | devDependency；移除后 canonical 完好，build 仍可产静态 preview；本地验证回退到静态 preview/其他 adapter |
| R8 | native | 1.0 | 1.0 | 1.0 | 1.00 | MIT；~90.6k stars；8 维护者；健康发布节奏（Snyk health=Healthy） |

### 依据
- 关键需求 R2 有效拟合度=0.40<0.5 -> 继续搜索(D)
- 关键需求 R3 有效拟合度=0.15<0.5 -> 继续搜索(D)

## 候选 O2 · json-render (@json-render/core) (pre-1.0 (npm @json-render/core; 集成前须钉具体 semver/commit))

- **推荐分类**: `B`
- 关键需求覆盖率: 40% · 平均有效拟合度: 0.55 · 总所有权成本 E: 16

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | registry 本地渲染 React/Vue/Svelte/Solid/RN，无远程依赖 |
| R2 | adapted | 0.7 | 0.8 | 1.0 | 0.56 | flat element tree + catalog 即声明式投影格式；canonical→json-render spec 映射可行 |
| R3 | native | 1.0 | 1.0 | 1.0 | 1.00 | @json-render/core defineCatalog + zod：agent 产出受 catalog 约束 JSON，无任意代码执行 |
| R4 | adapted | 0.3 | 0.6 | 1.0 | 0.18 | a11y 取决于宿主组件；json-render 自身无 a11y 验证 harness |
| R5 | adapted | 0.5 | 0.7 | 1.0 | 0.35 | data binding + actions/setState + visibility；响应式依赖宿主 CSS |
| R6 | unknown | 0.2 | 0.4 | 1.0 | 0.08 | 无内置 docs 生成面；可经 code export 间接产出 |
| R7 | adapted | 0.6 | 1.0 | 1.0 | 0.60 | npm 依赖，可移除；移除后回退到直接代码生成 |
| R8 | adapted | 0.6 | 1.0 | 1.0 | 0.60 | Apache-2.0 ✓；但 2026-01 新建、~449 stars、维护者极少（bus factor 风险） |

### 依据
- 关键需求存在部分缺口但 E=16<=E_MID -> B

## 候选 O3 · A2UI (v0.8 (stable); v0.9 (draft); v1.0 (candidate))

- **推荐分类**: `B`
- 关键需求覆盖率: 20% · 平均有效拟合度: 0.59 · 总所有权成本 E: 16

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 0.8 | 1.0 | 1.0 | 0.80 | A2UI 为协议/spec；渲染需客户端 renderer（React/Angular/Flutter/Lit）；本地可渲染 |
| R2 | adapted | 0.7 | 0.9 | 1.0 | 0.63 | surface/component/dataModel 消息即声明式投影；canonical→A2UI 消息映射可行 |
| R3 | native | 1.0 | 1.0 | 1.0 | 1.00 | secure-by-design：agent 仅用预批准 catalog 组件，无代码执行，catalog 校验 |
| R4 | adapted | 0.4 | 0.7 | 1.0 | 0.28 | renderer 映射到原生组件；a11y 取决于 renderer + 宿主；无内置 a11y harness |
| R5 | adapted | 0.5 | 0.7 | 1.0 | 0.35 | v1.0 actionResponse 支持客户端→服务端 RPC；数据绑定；响应式依赖宿主 |
| R6 | adapted | 0.4 | 0.6 | 1.0 | 0.24 | spec 机器可读且有文档，但非人工审阅型 docs 生成 |
| R7 | adapted | 0.6 | 1.0 | 1.0 | 0.60 | 协议为格式层；adapter=renderer 集成；可移除 |
| R8 | adapted | 0.8 | 1.0 | 1.0 | 0.80 | Apache-2.0，Google + CopilotKit，活跃；但 spec 成熟度风险（v0.8 稳/v0.9 草/v1.0 候选） |

### 依据
- 关键需求存在部分缺口但 E=16<=E_MID -> B

## 候选 O4 · M3E Canvas (lnkiai/m3e-canvas) (无 tagged release (Next.js 静态 web app；须钉 main@<commit>))

- **推荐分类**: `D`
- 关键需求覆盖率: 0% · 平均有效拟合度: 0.21 · 总所有权成本 E: 15

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 0.2 | 0.3 | 1.0 | 0.06 | M3E Canvas 是本地浏览器 sketch 工具，产出 prompt 给外部 AI 编码工具；本身不渲染/验证最终 UI |
| R2 | unsupported | 0.1 | 0.2 | 1.0 | 0.02 | 产出自然语言 prompt，不消费 UI-FLOW/v1，非结构化投影 |
| R3 | adapted | 0.3 | 0.5 | 1.0 | 0.15 | 使用 M3 Expressive 部件词汇（catalog of parts），但为 sketch 工具非 agent 生成守门 |
| R4 | unknown | 0.1 | 0.2 | 1.0 | 0.02 | 非验证工具 |
| R5 | adapted | 0.3 | 0.5 | 1.0 | 0.15 | 支持 screen flow/transition/phone-desktop 布局，但为 authoring 非运行时校验 |
| R6 | unknown | 0.2 | 0.3 | 1.0 | 0.06 | 导出 prompt 非 docs |
| R7 | adapted | 0.8 | 1.0 | 1.0 | 0.80 | 独立本地工具；移除无影响；但非运行时 adapter，降级面不适用 |
| R8 | adapted | 0.4 | 1.0 | 1.0 | 0.40 | MIT ✓；但单维护者 lnkiai、~2 周新、病毒式增长未经验证、无运行时 |

### 依据
- 关键需求 R1 有效拟合度=0.06<0.5 -> 继续搜索(D)
- 关键需求 R2 状态=unsupported -> 继续搜索(D)
- 关键需求 R3 有效拟合度=0.15<0.5 -> 继续搜索(D)
- 关键需求 R8 有效拟合度=0.40<0.5 -> 继续搜索(D)

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