# Research & Design Todo — 双模式（tracker 依赖 / 独立）的 wayfinder 与 roadmap-driven

> 状态：**todo（后置研究）** · 属于 `zj-wayfinder` 与 `zj-roadmap-driven` 的后续演进方向
> 创建：2026-08-11

## 背景

`zj-wayfinder` 与 `zj-roadmap-driven` 是 ZAgentic 中两个互补的工程 skill（前者规划、后者跟踪）。当前两者的"底层事实"不对称：

- **`zj-wayfinder` 依赖 issue-tracker**。它把地图、决策票、阻塞边、frontier 查询放在 issue-tracker 上（GitHub/GitLab/本地 md），通过 `/zj-setup-skills` 配置的 `Wayfinding operations` 段工作。优势是**便于 teamwork**（多 Agent 并发靠 claim + 原生 blocking 避让、人类在 tracker UI 可视化看到前沿），劣势是**依赖外部载体**、单点上下文分散在 tracker 上。
- **`zj-roadmap-driven` 无三方依赖**。它以本地 JSON 为唯一真相源 + 纯 Python stdlib CLI，完全独立。优势是 **context 完整、Human 能通盘把握**（md 轻量视图 + JSON 全量可查），劣势是单写者、不擅长多 Agent 并发。

这一不对称，使得同一类"规划/跟踪"工作，在两种工作方式（团队协作 vs 个人全盘掌握）下不得不各用各的 skill，而无法在同一个 skill 内无缝切换。

## 目标

为了保持整个项目的一致性、完整性，**`zj-wayfinder` 和 `zj-roadmap-driven` 都应该同时支持两种情形**：

1. **依赖 issue-tracker（方便 teamwork）** —— 地图/路线/决策票落在 tracker 上，多人、多 Agent 共享、可视化、并发避让。
2. **不依赖 issue-tracker（方便 context 完整 + Human 通盘把握）** —— 以本地文件/JSON 为真相源，Human 能在一次会话内纵览全貌、离线可用、完全自包含。

两种模式应是**同一 skill 的两个可切换后端/载体**，而非两个割裂的 skill。

## 设计要点（研究方向）

- **抽象一层"载体（carrier）"接口**：把 wayfinder 的地图/票/阻塞/frontier，与 roadmap-driven 的树节点/决策/状态，统一抽象为"共享工作空间（shared workspace）"的一组原语，背后可由 issue-tracker 或本地文件实现。skill 的流程逻辑与载体解耦。
- **模式选择**：由场景/偏好决定（团队协作 → tracker 模式；个人全盘掌握/离线 → 本地模式），并在文档中给出切换指引。
- **一致性**：两种模式产出同样的心智模型（地图/路线 + 决策记录），只是物理载体不同——这样跨模式迁移（从个人探索转为团队协作）时，认知模型不变。
- **配置**：复用 `/zj-setup-skills` 的配置通道，新增"载体模式"这一配置维度。

## 高阶展望（未来解锁）

如果未来有机会解决 **multi-agent & multi-human & multi-device 基于 shared context 的 co-design & co-work** 问题（多个 Agent、多个 Human、跨设备，共同基于一份共享上下文做联合设计与联合工作），上述"双模式 + 载体抽象"还能进一步解锁高阶用法：

- 多 Agent 各自认领决策票/节点，基于同一份 shared context 并发推进，冲突由 shared workspace 的并发原语（claim/lock/blocking）解决。
- 多 Human 跨设备看到同一张实时地图/路线，各自补充上下文，Human 的决策与 Agent 的跟踪在同一真相源上汇合。
- co-design（联合设计）与 co-work（联合工作）共享同一份 shared context，规划期（wayfinder）与执行期（roadmap-driven）无缝衔接。

**这要求先把"载体抽象 + 双模式"做扎实**，作为 multi-agent/multi-human 协作的基础设施。

## 待办清单

- [ ] 定义"shared workspace / carrier"原语抽象（地图/票/节点/决策/阻塞/frontier 的最小公共接口）
- [ ] 为 `zj-wayfinder` 设计 tracker 模式 ↔ 本地模式的双后端
- [ ] 为 `zj-roadmap-driven` 设计 tracker 模式 ↔ 本地模式的双后端
- [ ] 复用 `/zj-setup-skills` 增加"载体模式"配置维度
- [ ] 文档化两种模式的切换指引与适用场景
- [ ] （高阶，future）multi-agent & multi-human & multi-device 基于 shared context 的 co-design & co-work
