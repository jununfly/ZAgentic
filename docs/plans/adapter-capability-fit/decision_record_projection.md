# 开源能力拟合决策记录

> 由 `zj-open-source-capability-fit` 依据 [开源能力拟合决策模型](../../docs/agreements/open-source-capability-fit-decision-model.md) 生成。

## 目标需求 R

角色=opt-in 投影/协议/输入兼容 adapter：评估 json-render、A2UI、M3E Canvas 作为 canonical artifact 的声明式投影/协议与输入兼容面，并满足离线渲染、安全移除与许可证要求。

- **R1** [关键] 离线/本地渲染与静态预览：无远程依赖下可本地渲染 — 验收: 本地渲染，断网可用
- **R2** [关键] canonical artifact 投影/mapping：消费 canonical artifacts 并投影到 adapter 格式，schema lock + 可逆 mapping — 验收: 锁定 schema + 可逆映射层
- **R3** [关键] 声明式、catalog 受限生成（deny-first 兼容）：agent 产出受 catalog 约束的声明式 spec，无任意代码执行 — 验收: 输出经 catalog 校验，未注册组件/危险 action 被拒
- **R7** [关键] 安全移除与降级：adapter 可移除且 canonical + 本地验证在其删除后存活 — 验收: removal test 证明删除后 canonical + 静态 preview 仍可用
- **R8** [关键] 许可证与所有权可接受：清晰 OSS 许可证、可接受维护/bus factor、无 SBOM 红旗 — 验收: 许可证 permissive/兼容，维护健康或可隔离

## 候选 O2 · json-render (@json-render/core) (pre-1.0 (npm @json-render/core; 集成前须钉具体 semver/commit))

- **推荐分类**: `B`
- 关键需求覆盖率: 40% · 平均有效拟合度: 0.75 · 总所有权成本 E: 16

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 1.0 | 1.00 | registry 本地渲染 React/Vue/Svelte/Solid/RN，无远程依赖 |
| R2 | adapted | 0.7 | 0.8 | 1.0 | 0.56 | flat element tree + catalog 即声明式投影格式；canonical→spec 映射可行 |
| R3 | native | 1.0 | 1.0 | 1.0 | 1.00 | @json-render/core defineCatalog + zod：受 catalog 约束 JSON，无任意代码执行 |
| R7 | adapted | 0.6 | 1.0 | 1.0 | 0.60 | npm 依赖，可移除；移除后回退到直接代码生成 |
| R8 | adapted | 0.6 | 1.0 | 1.0 | 0.60 | Apache-2.0 ✓；但 2026-01 新建、~449 stars、维护者极少（bus factor 风险） |

### 依据
- 关键需求存在部分缺口但 E=16<=E_MID -> B

## 候选 O3 · A2UI (v0.8 (stable); v0.9 (draft); v1.0 (candidate))

- **推荐分类**: `B`
- 关键需求覆盖率: 20% · 平均有效拟合度: 0.77 · 总所有权成本 E: 16

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 0.8 | 1.0 | 1.0 | 0.80 | A2UI 为协议/spec；渲染需客户端 renderer；本地可渲染 |
| R2 | adapted | 0.7 | 0.9 | 1.0 | 0.63 | surface/component/dataModel 消息即声明式投影；canonical→A2UI 映射可行 |
| R3 | native | 1.0 | 1.0 | 1.0 | 1.00 | secure-by-design：预批准 catalog 组件，无代码执行，catalog 校验 |
| R7 | adapted | 0.6 | 1.0 | 1.0 | 0.60 | 协议为格式层；adapter=renderer 集成；可移除 |
| R8 | adapted | 0.8 | 1.0 | 1.0 | 0.80 | Apache-2.0，Google + CopilotKit，活跃；spec 成熟度风险（v0.8/v0.9/v1.0） |

### 依据
- 关键需求存在部分缺口但 E=16<=E_MID -> B

## 候选 O4 · M3E Canvas (lnkiai/m3e-canvas) (无 tagged release (Next.js 静态 web app；须钉 main@<commit>))

- **推荐分类**: `D`
- 关键需求覆盖率: 0% · 平均有效拟合度: 0.29 · 总所有权成本 E: 15

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 0.2 | 0.3 | 1.0 | 0.06 | 本地浏览器 sketch 工具，产出 prompt 给外部 AI 编码工具；本身不渲染/验证最终 UI |
| R2 | unsupported | 0.1 | 0.2 | 1.0 | 0.02 | 产出自然语言 prompt，不消费 UI-FLOW/v1，非结构化投影 |
| R3 | adapted | 0.3 | 0.5 | 1.0 | 0.15 | 使用 M3 Expressive 部件词汇，但为 sketch 工具非 agent 生成守门 |
| R7 | adapted | 0.8 | 1.0 | 1.0 | 0.80 | 独立本地工具；移除无影响；非运行时 adapter |
| R8 | adapted | 0.4 | 1.0 | 1.0 | 0.40 | MIT ✓；单维护者 lnkiai、~2 周新、病毒式增长未验证、无运行时 |

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