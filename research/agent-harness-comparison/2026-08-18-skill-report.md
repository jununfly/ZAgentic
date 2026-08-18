# 百人技术团队的 Harness Engineering 选型

## 1. Executive summary
在当前 commit-pinned 证据范围内，deepseek-harness 最适合作为百人团队的组织级底座：它把插件组合、持久事实、策略、沙箱和文档治理放在同一工程体系中。pi 更适合需要轻量内核与高自由度扩展的小团队或嵌入式场景；awesome-agent-harness 是生态地图和候选发现源，不是可直接承担组织级运行时职责的 harness。

- 百人技术团队优先选择 deepseek-harness 作为组织级 Harness Engineering 基座；先以少量 preset 和强制治理规则落地，再逐步扩展 provider 与工具组合。
- 当目标是小团队快速实验、嵌入现有产品或最大化 extension 自由度时，选择 pi；需要额外建设集中策略、发布治理和组织级隔离基线。
- 保留 awesome-agent-harness 作为持续扫描生态与补充候选的资料源，不把它作为 runtime 选型终点。

## 2. Key findings
- pi 提供项目级与全局 extension 自动发现，并允许注册工具、拦截事件和自定义 compaction，适合快速定制 agent 行为。 [[1]](https://github.com/earendil-works/pi/blob/2509b5c037d366979f2febfce4174b88aeaadc6a/packages/coding-agent/docs/extensions.md)
- pi 的治理主要通过 extension hook 组合实现，官方示例覆盖危险命令确认、路径保护和 Git checkpoint。 [[2]](https://github.com/earendil-works/pi/blob/2509b5c037d366979f2febfce4174b88aeaadc6a/packages/coding-agent/docs/extensions.md) [[3]](https://github.com/earendil-works/pi/blob/2509b5c037d366979f2febfce4174b88aeaadc6a/packages/coding-agent/docs/extensions.md)
- pi 已提供基于真实 AgentSession 的 model-backed behavioral eval harness，可比较 prompt、tool、skill、model 和 harness 配置。 [[4]](https://github.com/earendil-works/pi/blob/2509b5c037d366979f2febfce4174b88aeaadc6a/packages/evals/README.md)
- awesome-agent-harness 的核心产物是 agent harness landscape report 与生态分层资料，而不是一个可部署的 agent runtime。 [[5]](https://github.com/AutoJunjie/awesome-agent-harness/blob/1e3f26371ec1a765efe0268b1e63374bee2aaa04/reports/agent-harness-landscape-2026-03.md) [[6]](https://github.com/AutoJunjie/awesome-agent-harness/blob/1e3f26371ec1a765efe0268b1e63374bee2aaa04/reports/agent-harness-landscape-2026-03.md)
- deepseek-harness 把模型适配器、工具注册表、session log 与 agent loop 都作为 Cordis plugin，并通过 profile、bundle 和 patch layer 组装部署。 [[9]](https://github.com/deepseek-ai/deepseek-harness/blob/99f6f02fecdb7dff40c3fbc9470f5907c29f74ca/AGENTS.md) [[15]](https://github.com/deepseek-ai/deepseek-harness/blob/99f6f02fecdb7dff40c3fbc9470f5907c29f74ca/docs/architecture.md)
- deepseek-harness 用仓库级 AGENTS.md、Agent Notes 和文档门禁承载可执行规则、架构决策与持续维护约定。 [[7]](https://github.com/deepseek-ai/deepseek-harness/blob/99f6f02fecdb7dff40c3fbc9470f5907c29f74ca/.agents/notes/AGENTS.md) [[8]](https://github.com/deepseek-ai/deepseek-harness/blob/99f6f02fecdb7dff40c3fbc9470f5907c29f74ca/.agents/notes/README.md) [[12]](https://github.com/deepseek-ai/deepseek-harness/blob/99f6f02fecdb7dff40c3fbc9470f5907c29f74ca/docs/AGENTS.md)
- deepseek-harness 在架构层显式区分 filesystem policy 与 process sandbox provider，并要求 consumer 在 spawn 前包装 argv。 [[17]](https://github.com/deepseek-ai/deepseek-harness/blob/99f6f02fecdb7dff40c3fbc9470f5907c29f74ca/docs/architecture.md) [[18]](https://github.com/deepseek-ai/deepseek-harness/blob/99f6f02fecdb7dff40c3fbc9470f5907c29f74ca/docs/architecture.zh.md)
- deepseek-harness 的 Web 测试使用真实 HTTP 与 Chromium 驱动完整组合，并把测试机制放在最低所属文档层级。 [[11]](https://github.com/deepseek-ai/deepseek-harness/blob/99f6f02fecdb7dff40c3fbc9470f5907c29f74ca/apps/web/tests/README.md) [[13]](https://github.com/deepseek-ai/deepseek-harness/blob/99f6f02fecdb7dff40c3fbc9470f5907c29f74ca/docs/AGENTS.md)
- deepseek-harness 用 bundle、preset、package README 与双语文档约定把运行组合和团队知识治理标准化。 [[10]](https://github.com/deepseek-ai/deepseek-harness/blob/99f6f02fecdb7dff40c3fbc9470f5907c29f74ca/AGENTS.md) [[14]](https://github.com/deepseek-ai/deepseek-harness/blob/99f6f02fecdb7dff40c3fbc9470f5907c29f74ca/docs/AGENTS.md) [[16]](https://github.com/deepseek-ai/deepseek-harness/blob/99f6f02fecdb7dff40c3fbc9470f5907c29f74ca/docs/architecture.md)

## 3. Analysis & synthesis
### runtime-depth
pi 与 deepseek-harness 都是实际运行时，但 pi 的优势集中在轻量 extension 与快速定制；deepseek-harness 覆盖组合、持久事实、策略、沙箱与治理，更接近组织级平台。

### evaluation-readiness
pi 已具备 model-backed behavioral eval；deepseek-harness 同时展示真实组合测试和文档／规则治理。两者都可评测，但 deepseek-harness 的组织控制面更完整。

### catalog-role
awesome-agent-harness 适合作为候选发现与行业地图输入，不应与可执行 runtime 按同一交付责任比较。

### 3.7 Recommendation
- 百人技术团队优先选择 deepseek-harness 作为组织级 Harness Engineering 基座；先以少量 preset 和强制治理规则落地，再逐步扩展 provider 与工具组合。
- 当目标是小团队快速实验、嵌入现有产品或最大化 extension 自由度时，选择 pi；需要额外建设集中策略、发布治理和组织级隔离基线。
- 保留 awesome-agent-harness 作为持续扫描生态与补充候选的资料源，不把它作为 runtime 选型终点。

## 4. Information gaps & next steps
| Gap | Nature | Next step |
|---|---|---|

## 6. Source list
1. [earendil-works/pi@2509b5c037d366979f2febfce4174b88aeaadc6a:packages/coding-agent/docs/extensions.md](https://github.com/earendil-works/pi/blob/2509b5c037d366979f2febfce4174b88aeaadc6a/packages/coding-agent/docs/extensions.md) — Evidence `307daf860132117dc8cc8973`
2. [earendil-works/pi@2509b5c037d366979f2febfce4174b88aeaadc6a:packages/coding-agent/docs/extensions.md](https://github.com/earendil-works/pi/blob/2509b5c037d366979f2febfce4174b88aeaadc6a/packages/coding-agent/docs/extensions.md) — Evidence `f0712382de15af63da2aa15f`
3. [earendil-works/pi@2509b5c037d366979f2febfce4174b88aeaadc6a:packages/coding-agent/docs/extensions.md](https://github.com/earendil-works/pi/blob/2509b5c037d366979f2febfce4174b88aeaadc6a/packages/coding-agent/docs/extensions.md) — Evidence `ca814386180f42085e8b9fc7`
4. [earendil-works/pi@2509b5c037d366979f2febfce4174b88aeaadc6a:packages/evals/README.md](https://github.com/earendil-works/pi/blob/2509b5c037d366979f2febfce4174b88aeaadc6a/packages/evals/README.md) — Evidence `ad95f3df564a808abbf6e156`
5. [AutoJunjie/awesome-agent-harness@1e3f26371ec1a765efe0268b1e63374bee2aaa04:reports/agent-harness-landscape-2026-03.md](https://github.com/AutoJunjie/awesome-agent-harness/blob/1e3f26371ec1a765efe0268b1e63374bee2aaa04/reports/agent-harness-landscape-2026-03.md) — Evidence `61acbb432e472923f552394f`
6. [AutoJunjie/awesome-agent-harness@1e3f26371ec1a765efe0268b1e63374bee2aaa04:reports/agent-harness-landscape-2026-03.md](https://github.com/AutoJunjie/awesome-agent-harness/blob/1e3f26371ec1a765efe0268b1e63374bee2aaa04/reports/agent-harness-landscape-2026-03.md) — Evidence `627882abb304c0f3eadcab74`
7. [deepseek-ai/deepseek-harness@99f6f02fecdb7dff40c3fbc9470f5907c29f74ca:.agents/notes/AGENTS.md](https://github.com/deepseek-ai/deepseek-harness/blob/99f6f02fecdb7dff40c3fbc9470f5907c29f74ca/.agents/notes/AGENTS.md) — Evidence `ac4868213c4cc614e45dffcb`
8. [deepseek-ai/deepseek-harness@99f6f02fecdb7dff40c3fbc9470f5907c29f74ca:.agents/notes/README.md](https://github.com/deepseek-ai/deepseek-harness/blob/99f6f02fecdb7dff40c3fbc9470f5907c29f74ca/.agents/notes/README.md) — Evidence `0698bced22fc7caa841cf470`
9. [deepseek-ai/deepseek-harness@99f6f02fecdb7dff40c3fbc9470f5907c29f74ca:AGENTS.md](https://github.com/deepseek-ai/deepseek-harness/blob/99f6f02fecdb7dff40c3fbc9470f5907c29f74ca/AGENTS.md) — Evidence `5034ceda2dc527928700103e`
10. [deepseek-ai/deepseek-harness@99f6f02fecdb7dff40c3fbc9470f5907c29f74ca:AGENTS.md](https://github.com/deepseek-ai/deepseek-harness/blob/99f6f02fecdb7dff40c3fbc9470f5907c29f74ca/AGENTS.md) — Evidence `e90fef311a528345c088e24c`
11. [deepseek-ai/deepseek-harness@99f6f02fecdb7dff40c3fbc9470f5907c29f74ca:apps/web/tests/README.md](https://github.com/deepseek-ai/deepseek-harness/blob/99f6f02fecdb7dff40c3fbc9470f5907c29f74ca/apps/web/tests/README.md) — Evidence `55fb75382d79c825de6dc378`
12. [deepseek-ai/deepseek-harness@99f6f02fecdb7dff40c3fbc9470f5907c29f74ca:docs/AGENTS.md](https://github.com/deepseek-ai/deepseek-harness/blob/99f6f02fecdb7dff40c3fbc9470f5907c29f74ca/docs/AGENTS.md) — Evidence `3a03b460826a51ed6dd2ce87`
13. [deepseek-ai/deepseek-harness@99f6f02fecdb7dff40c3fbc9470f5907c29f74ca:docs/AGENTS.md](https://github.com/deepseek-ai/deepseek-harness/blob/99f6f02fecdb7dff40c3fbc9470f5907c29f74ca/docs/AGENTS.md) — Evidence `5eaaa9de18dc25ce52b762d6`
14. [deepseek-ai/deepseek-harness@99f6f02fecdb7dff40c3fbc9470f5907c29f74ca:docs/AGENTS.md](https://github.com/deepseek-ai/deepseek-harness/blob/99f6f02fecdb7dff40c3fbc9470f5907c29f74ca/docs/AGENTS.md) — Evidence `bcc4b876af4c260252c58d19`
15. [deepseek-ai/deepseek-harness@99f6f02fecdb7dff40c3fbc9470f5907c29f74ca:docs/architecture.md](https://github.com/deepseek-ai/deepseek-harness/blob/99f6f02fecdb7dff40c3fbc9470f5907c29f74ca/docs/architecture.md) — Evidence `3c73f886e995596623c209d6`
16. [deepseek-ai/deepseek-harness@99f6f02fecdb7dff40c3fbc9470f5907c29f74ca:docs/architecture.md](https://github.com/deepseek-ai/deepseek-harness/blob/99f6f02fecdb7dff40c3fbc9470f5907c29f74ca/docs/architecture.md) — Evidence `ae3b4aaed07561bb26d5421e`
17. [deepseek-ai/deepseek-harness@99f6f02fecdb7dff40c3fbc9470f5907c29f74ca:docs/architecture.md](https://github.com/deepseek-ai/deepseek-harness/blob/99f6f02fecdb7dff40c3fbc9470f5907c29f74ca/docs/architecture.md) — Evidence `4ecd9540b448e53894a97d08`
18. [deepseek-ai/deepseek-harness@99f6f02fecdb7dff40c3fbc9470f5907c29f74ca:docs/architecture.zh.md](https://github.com/deepseek-ai/deepseek-harness/blob/99f6f02fecdb7dff40c3fbc9470f5907c29f74ca/docs/architecture.zh.md) — Evidence `00f901fe777a56e3b61a51a0`
