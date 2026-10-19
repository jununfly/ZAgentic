### 视角：B

`视角来源: 跨会话独立Agent`

**观点 1**

**发现**：Q1 只提出“纳入标准、版本锁和 owner”，但原文尚未给出可执行的准入单据；成功判据又要求每个 adapter 同时具备固定 commit/version、许可证、依赖和映射（原文 L7、原文 L12）。

**影响**：如果先接入 A2UI、json-render、M3E、Storybook 及可选 connector，再补治理信息，排期会被隐性依赖拖长，且出问题时无法判断谁负责。按每个 adapter 估算，manifest/许可证与依赖核查 0.5 人日、映射和 owner 审核 0.5 人日、验收 0.5 人日；远程 connector 还应预留 1 人日的凭据/失效场景验证。未通过准入单的 adapter 不应进入主分支。

**建议**：建立版本化 `adapters/<name>/adapter.yaml` 作为准入门槛，至少锁定上游 commit 或不可变版本、许可证、依赖范围、输入/输出映射、owner、reviewer、风险级别和 fallback 类型；CI 检查字段完整且依赖无浮动范围。以“manifest 已审、映射示例可运行、owner 明确、成本被排期”为 Q1 完成标准，先以一个本地 adapter 做 1 个工作日的薄切片，再按依赖链逐个接入，远程 connector 采用独立可选阶段，不阻塞核心流程。

**观点 2**

**发现**：原文要求 schema lock、golden fixture、warning 和 fallback，但 Q2 只列出 schema 漂移、丢字段、网络失败、远程 ID 失效四类故障，没有规定在哪一层检测或什么结果算通过（原文 L7、原文 L13）。

**影响**：仅做运行时 try/catch 会把静默丢字段和错误渲染推迟到用户现场；远程服务关闭时还可能卡住核心 artifact，直接违反“核心流程仍可本地继续”的成功判据（原文 L7）。这会把每次上游升级变成不可估算的回归工作。

**建议**：为每个 adapter 提交一份 schema lock（锁定字段、类型、必填性和未知字段策略）及至少一组覆盖正常、丢字段、未知字段和坏版本的 golden fixture；CI 在依赖升级和 PR 时执行 schema diff，必填字段变化直接阻断，兼容新增字段只发结构化 warning。运行时将结果分为 `ready/degraded/disabled`：映射失败、网络超时或远程 ID 无效均记录 adapter 名、锁定版本、错误码和 warning，并在固定短超时后回退到本地核心 artifact/最近一次可用静态结果；验收是远程服务完全关闭时本地流程仍能生成核心 artifact，且 golden fixture 无非预期差异。

**观点 3**

**发现**：Q2 明确包含远程 ID 失效和网络失败，Q3 又要求 adapter 可停用和删除；但原文没有给出远程 ID 的健康检查、重试边界、fallback 产物或谁在失败时处理（原文 L13-L14）。

**影响**：无限重试会放大延迟和外部依赖成本；把远程 ID 写进核心 artifact 会形成不可移除的耦合，远程 connector 下线时无法保证本地继续。建议按一个 adapter 约 1 人日增加故障注入与手工验收，代价小于每次 connector 事故人工恢复的不可控成本。

**建议**：远程能力必须包在 adapter 边界内，核心 artifact 只保存稳定的本地语义和可选 provenance，不保存不可恢复的远程对象作为唯一真相。为远程请求设置单次超时、最多一次重试和熔断；ID 校验失败立即标为 `degraded`，发 warning 并使用本地映射/占位结果，无法安全映射时明确禁用该 adapter 而不是伪造成功。owner 每个发布周期检查健康指标；验收包含断网、服务 5xx、ID 404 三个 fixture/集成场景，三者都不得阻断核心 artifact 生成。

**观点 4**

**发现**：成功判据要求 removal test 和停用/重评阈值，但 Q3 只问“何时停止维护、如何删除”，没有定义阈值、观察窗口、决策人和删除后的回归边界（原文 L7、原文 L14）。

**影响**：没有量化阈值时，adapter 会因沉没成本长期维护，或因一次事故被仓促删除；删除若触及核心 schema、artifact 或默认路由，会产生隐性破坏。维护成本应可见：每次版本升级、fixture 修复和失败处理都记入 owner 的维护账本，连续两个发布周期仍无使用或持续失败即可触发复评。

**建议**：把停用规则写进 adapter manifest：例如连续两个发布周期（或至少 30 天）无实际调用，或连续两个周期成功率低于 95%，或上游停止维护/许可证不再可接受，即进入 `deprecated`；owner 在一个发布周期内提交复评，技术负责人批准后进入 `disabled`，再经过一个发布周期才删除。删除前必须通过 removal test：移除 adapter 包、注册项、依赖和路由后，核心 schema、核心 artifact、默认本地流程和其他 adapter 的 golden fixture 全部通过；保留迁移说明与版本记录，失败则回滚停用而非删除。

**观点 5**

**发现**：原文把五类外部能力放在同一 scope，却明确 Figma/Superdesign connector 是可选项；核心语义契约和 skill 路由又分别由 sub-01、sub-02 提供（原文 L6、原文 L8）。当前没有显式的关键路径、分阶段验收和“不纳入”的边界。

**影响**：若把可选远程 connector 与基础 adapter 一起作为首发硬依赖，会让集成排期和失败面扩大，并把其他子文档的契约问题重复实现。工程上应先交付能独立工作的本地闭环，再用相同协议接入可选项；否则无法证明远程关闭时核心流程仍可用。

**建议**：按“本地 adapter 基线 → schema lock/golden fixture → warning/fallback → 可选远程 connector”分四个里程碑排期，每个里程碑由 owner 提交可验收产物和风险清单；sub-01 只提供核心语义契约，sub-02 只提供路由入口，adapter 自己负责映射、版本锁、失败状态和 removal test。首发门槛是本地基线与远程关闭验收通过；任何 adapter 未达到该门槛只能以显式 opt-in 实验状态发布，不得成为核心 artifact 的必经依赖。
