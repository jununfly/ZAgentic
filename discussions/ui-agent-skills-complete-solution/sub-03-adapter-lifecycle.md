# 子问题：外部 adapter 的兼容性与退出路径

## 上下文

- **所属主文档：** [../MASTER.md](./MASTER.md)
- **本子问题独立性：** 只讨论 A2UI、json-render、M3E、Storybook 以及可选 Figma/Superdesign connector 的版本、映射、失败和移除；核心语义契约由 sub-01 提供，skill 路由由 sub-02 提供。
- **成功判据：** 每个 adapter 具备固定 commit/version、许可证、依赖、映射、schema lock、golden fixture、warning、fallback、removal test 和停用/重评阈值；远程服务关闭时核心流程仍可本地继续。
- **声明必需角色集：** B,C,A,T,O,L

## 待讨论问题（scope 草案）

- Q1：每个 adapter 的纳入标准、版本锁和 owner 是什么？
- Q2：schema 漂移、丢字段、网络失败、远程 ID 失效如何检测和回退？
- Q3：何时停止维护 adapter，如何删除且不破坏核心 artifact？

## Agent viewpoints（独立视角 — 须跨会话独立 Agent）

### 视角：B（技术经理 / 可落地）
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

### 视角：C（产品专家 / 用户价值·生态竞品）
`视角来源: 跨会话独立Agent`

**观点 1：adapter 应按可验证的用户任务纳入，而不是按生态名气扩张**

- **发现**：原文把 A2UI、json-render、M3E、Storybook 列为讨论对象，并把 Figma/Superdesign connector 标成可选，但没有给出每个生态对应的真实使用者、替代方案或需求证据（原文 L6）；Q1 又要求明确纳入标准、版本锁和 owner（原文 L12）。这说明当前的产品缺口不是“再接几个平台”，而是无法判断哪些 adapter 真正降低了目标用户的转换成本。
- **影响**：若把“生态存在”当作优先级依据，维护面会随名单线性增长，用户却无法获得稳定收益；尤其可选 connector 可能把远程服务和外部账号误变成核心路径。纳入决策应可被反例推翻：连续一个评审周期没有真实工作流采用，或用户仍选择直接使用生态原生导入/预览，就应证明 adapter 的差异价值不足。
- **建议**：为每个 adapter 建一张公开 adapter card：目标用户与任务、相对原生工具的节省步骤、生态边界、许可证/依赖、owner、固定 commit/version、schema lock 与 golden fixture。进入 active 前至少要有 **2 个相互独立的真实工作流**、每个工作流至少 **1 个可复现 fixture**，且 fixture 在锁定版本上 100% 通过；连续 **30 天无活跃使用**则进入重评队列。把 Storybook 等成熟生态作为参照，不以“能连接”作为价值证明，而以用户是否能在本地保留核心 artifact、少一步人工转换作为验收。

**观点 2：用户需要的是可预期的降级，不是“看似成功但字段丢失”的兼容**

- **发现**：成功判据明确要求 schema lock、golden fixture、warning、fallback，并要求远程服务关闭时核心流程仍可本地继续（原文 L7）；Q2 进一步点名 schema 漂移、丢字段、网络失败和远程 ID 失效（原文 L13）。原文已识别故障类型，但尚未规定用户可观察的降级顺序和“哪些字段绝不能静默丢失”。
- **影响**：schema 漂移若没有显式告警，会把兼容错误伪装成可交付 artifact，损害用户对所有 adapter 的信任；网络或远程 ID 故障若阻塞核心流程，则可选生态的故障半径会扩散到本地用户。产品优先级应先保障可恢复的本地结果，再追求生态特有能力：核心字段保真度比“成功调用远程服务”更重要。
- **建议**：每个 adapter 采用“版本锁 + schema lock hash + golden fixture”三件套：升级依赖或 schema 必须先生成新 fixture 并通过人工确认；CI 对 fixture 做 **100% 必需字段通过**检查，任一必需字段缺失即阻断发布。运行时按固定顺序降级为“精确映射 → 保留核心字段的本地 artifact → 明确 warning 的部分结果 → 可重试的失败”，禁止静默丢字段；远程请求超时、ID 失效或 schema 校验失败都必须落 warning code，并立即走本地 fallback。若同一 adapter 连续 **2 次发布检查失败**，冻结版本升级并回到上一已验证版本。

**观点 3：退出路径本身是用户价值承诺，必须证明删除 adapter 不会删除用户的核心资产**

- **发现**：Q3 同时要求定义停止维护的时机以及“如何删除且不破坏核心 artifact”（原文 L14）；成功判据也要求 removal test，并再次强调远程服务关闭时核心流程可本地继续（原文 L7）。这意味着 adapter 不能把外部 ID、远程对象或私有 schema 当作核心 artifact 的唯一表示。
- **影响**：没有明确停用阈值时，低使用率 adapter 会永久消耗维护预算；没有 removal test 时，任何升级或服务下线都可能让既有项目无法打开。反例很清楚：如果去掉 adapter 后既有核心 artifact 无法读取、导出或继续本地编辑，则当前集成不具备可接受的产品边界。
- **建议**：把生命周期固定为 candidate → active → deprecated → removed，并为每次迁移提供公告、替代 adapter 或本地导出。触发 deprecated 的条件设为 **连续 2 个发布周期无活跃工作流**、或 **连续 3 次兼容探针失败**；完成 **2 个发布周期**的迁移窗口、至少 **1 次公告**和 removal test 通过后才允许 removed。removal test 必须在无该 adapter、无远程服务的环境中读取并保存既有核心 artifact，验证核心字段与 golden fixture 一致；外部 ID 只能作为可丢弃的关联元数据。若核心 artifact 回归失败，自动阻止删除并恢复到上一版本。

### 视角：A（架构师 / 约束）
`视角来源: 跨会话独立Agent`

**观点 1**

- **发现**：原文 ## 上下文 L6 将 A2UI、json-render、M3E、Storybook 及可选 Figma/Superdesign connector 限定为外部 adapter，并明确核心语义契约由 sub-01 提供；但原文 ## 上下文 L7 只列出“固定 commit/version、许可证、依赖、映射、schema lock”等成功判据，没有声明 adapter 与核心 artifact 之间不可逆依赖的边界。
- **影响**：若外部 schema、SDK 类型或远程 ID 直接进入核心 artifact，任何一个 adapter 的升级或退出都会把兼容性债务传给核心流程；这会使 Q1 的纳入决定变成长期耦合，且无法满足远程服务关闭后核心流程仍能本地继续的要求。
- **建议**：定义稳定的 `AdapterBoundary v1`：输入和输出只使用 sub-01 的核心 artifact/能力信封，外部字段只能放在带 adapter 命名空间的扩展区，核心不得 import 外部 SDK。每个 adapter 必须提交一份 manifest，锁定 `adapterVersion`、上游 commit/tag、许可证、依赖版本、owner、映射版本和 `schemaLock` 哈希；CI 在 manifest、schema lock 或映射任一变化时拒绝合并，除非同时更新迁移说明与兼容性测试。

**观点 2**

- **发现**：原文 Q2 L13 直接提出 schema 漂移、丢字段、网络失败、远程 ID 失效的检测与回退问题；原文 ## 上下文 L7 又要求每个 adapter 有 golden fixture、warning、fallback，但尚未规定检测顺序、失败等级和本地可继续的具体契约。
- **影响**：没有分层失败语义时，字段丢失可能被静默当成成功，产生不可逆的半成品；网络或远程 ID 故障也可能把核心流程误变成远程流程，导致同一 artifact 在离线、升级和重放时不一致。
- **建议**：采用“schema lock 校验 → 映射完整性校验 → golden fixture 回放 → 运行时能力探测”的顺序。schema 不匹配或必需字段缺失必须硬失败并输出包含 adapter/version/schemaLock 的 warning；可选字段丢失只能产生可观测 warning，并使用明确的默认值/占位符。每个 adapter 至少保留一组输入、成功映射、字段缺失、未知字段、远程 ID 失效和离线场景的 golden fixture。任何网络、认证或 ID 失败都 fallback 到本地核心 artifact 与本地渲染/导出，保留原始本地 ID，不把远程错误写入核心状态；fallback 结果必须可被 removal test 重放。

**观点 3**

- **发现**：原文 Q1 L12 询问纳入标准、版本锁和 owner，Q3 L14 询问停止维护与删除；原文 ## 上下文 L7 已要求 warning、removal test 和停用/重评阈值，但没有生命周期状态、阈值数值或删除前后的不变式。
- **影响**：没有可执行阈值，adapter 会在“暂时不用但仍有风险”的状态无限期维护；删除时若只删代码而不验证 artifact，可把历史项目、缓存或离线重放一并破坏。反之，过早停用又会在没有迁移窗口时造成用户侧断裂。
- **建议**：为每个 adapter 固化 `candidate → active → deprecated → disabled → removed` 状态机，并由 owner 负责状态变更。默认重评闸门设为：连续 2 个发布周期使用率低于 1%，或连续 14 天 owner 无法响应，进入 deprecated；连续 2 个周期仍满足条件则 disabled；出现核心数据损坏或许可证/安全阻断可立即 disabled。deprecated 至少保留两个发布周期并持续 warning，disabled 后仍保留只读迁移器和 fixtures。真正 removed 前必须通过 removal test：卸载 adapter、断开远程服务，历史核心 artifact 仍能加载、渲染、导出且 schema lock 不变；同时保留迁移说明和最后一个锁定版本，若失败则禁止删除并回退到 disabled。

**观点 4**

- **发现**：原文 ## 上下文 L6 同时列出成熟 adapter 与“可选”的 Figma/Superdesign connector，原文 Q1 L12 则要求逐个决定纳入标准；这说明外部系统能力并不具有统一稳定性，不能默认存在一个覆盖所有 connector 的共同抽象。
- **影响**：过早做“大一统 adapter”会以最弱外部能力定义核心接口，扩大跨系统耦合；新增 connector 还可能把远程特性、供应商 ID 和网络可用性偷偷提升为核心前提，最终削弱向后兼容和移除能力。
- **建议**：核心只稳定最小能力集合（导入、映射、验证、导出、离线 fallback），其余能力通过 manifest 的 capability flags 协商；Figma/Superdesign 这类可选 connector 默认 feature-off，不能被核心 artifact 引用。adapter 专属配置必须命名空间隔离，且任何 capability 缺失都走已定义的本地 fallback。新增 adapter 只有在能提供版本锁、schema lock、golden fixture、owner、removal test，并通过至少一个旧版本 artifact 的兼容回放后才允许进入 active。

### 视角：T（测试 / 质量）
`视角来源: 跨会话独立Agent`

**观点 1**

- **发现**：Q1 目前只有“纳入标准、版本锁和 owner”的问题定义（原文 L12），而成功判据要求每个 adapter 同时具备固定 commit/version、许可证、依赖和 schema lock（原文 L7）；如果这些信息只存在说明文档，CI 无法证明运行的确实是被评审的版本。
- **影响**：同一 adapter 可能因浮动依赖、上游 tag 重指向或 owner 缺失而出现不可复现的映射差异；测试通过不能作为可审计的质量证据，回归定位成本也会随 adapter 数量增长。
- **建议**：为每个 adapter 建立机器可读 manifest，至少锁定 adapter commit、上游 commit/digest、运行时与依赖 lockfile 哈希、许可证、owner、schema 版本和状态。纳入闸门设为：manifest 字段完整、依赖无浮动范围、schema lock 哈希一致、owner 可响应，并通过一组固定 golden fixture；CI 以离线干净环境重建并比对 manifest 哈希，任何不一致直接阻断合并。将“缺 owner”或连续 2 个发布周期无法重建标为 `REVIEW`，不得继续扩大接入面。

**观点 2**

- **发现**：Q2 明确要求检测 schema 漂移、丢字段、网络失败和远程 ID 失效（原文 L13），且成功判据同时要求 schema lock、golden fixture、warning 和 fallback（原文 L7）；但原文尚未规定失败分类、断言粒度或边界输入。
- **影响**：只测“正常样例”会把字段静默丢失、旧 schema 被误接受、远程 ID 失效后生成空 artifact 等问题误判为成功；网络抖动还可能造成非确定结果，用户无法区分降级、警告和真实错误。
- **建议**：把每个 adapter 的验证固定为离线可执行的 contract suite：先校验 schema lock，再对 golden fixture 做双向映射并断言必需字段、可选字段、未知字段策略和 warning code。至少覆盖空输入、缺必需字段、额外字段、非法类型、极大 payload、重复/过期远程 ID；并以并发 N 次相同输入检查结果与 warning 稳定。网络、认证、超时和 404 分别注入，统一按“可重试则有限重试，否则转本地 fallback”断言；fallback 产物必须通过核心 schema，且输出 `adapter_id`、失败原因和版本，禁止静默吞错。任何 schema lock mismatch、必需字段丢失或 fallback 不能通过核心校验都应使 CI 失败。

**观点 3**

- **发现**：Q3 要求确定何时停止维护以及如何删除而不破坏核心 artifact（原文 L14）；成功判据也明确要求 removal test，且远程服务关闭时核心流程仍可本地继续（原文 L7）。这意味着退出路径必须像纳入路径一样有自动化验收，而不能靠人工删依赖后观察。
- **影响**：没有 removal test 时，adapter 的注册表、序列化分支或隐式依赖可能残留；删除后旧核心 artifact 不能读取、离线流程中断，退出成本反而高于继续维护。没有阈值还会让“暂时失败”和“应停用”混在一起。
- **建议**：为每个 adapter 定义可配置但有默认值的停用闸门：连续 3 次 nightly contract run 失败，或连续 2 个上游发布周期发生 breaking drift，或 owner 缺失超过 30 天，进入 `REVIEW`；复核后若下一周期仍失败则标为 `DISABLED`，新输入不得再路由，但历史 artifact 必须可读。删除前运行 removal suite：从 registry、依赖和入口移除后，核心 artifact 的创建/读取/round-trip、无网络运行、旧 golden fixture 回放均通过；扫描不得再引用 adapter 包或远程 ID，核心 schema 不能出现 adapter 专属必需字段。保留迁移 fixture 与版本记录，只有 removal suite 全绿才允许物理删除。

**观点 4**

- **发现**：子文档把 A2UI、json-render、M3E、Storybook 及可选 connector 放在同一 adapter 兼容性与退出范围内（原文 L6），但声明的成功判据是“每个 adapter”都满足质量条件（原文 L7），不能以一个 adapter 的通过结果代表全体。
- **影响**：不同 adapter 的字段映射、远程依赖和失败模式不同；若只维护一份共享样例或只跑在线集成测试，某个 adapter 的回归会被总体绿灯掩盖，且无法证明远程关闭时核心流程仍可用。
- **建议**：按 adapter 生成独立的 fixture 矩阵和报告，报告必须逐项列出版本锁、schema lock、映射覆盖率、warning/fallback、异常与并发用例、removal test。设硬阈值为：必需字段映射覆盖率 100%、golden fixture 100% 通过、核心离线路径 100% 通过、未分类 warning 为 0；可选字段缺失只能产生明确 warning，不得降低核心结果。CI 分为离线确定性门和在线探测门：在线门失败只允许按已定义 fallback 继续并记录，离线门失败或连续两次出现非确定输出则阻断发布；保留带输入 fixture、manifest 哈希、schema lock 哈希和失败日志的制品，确保任何失败可由另一台机器按同一版本重放。

### 视角：O（运维 / SRE）
`视角来源: 跨会话独立Agent`

**观点 1**

- **发现**：原文 L6-L7 将 A2UI、json-render、M3E、Storybook 及可选 connector 纳入范围，并要求固定 commit/version、依赖、schema lock 和 owner，但没有定义部署形态、版本升级闸门、值班责任或监控指标。
- **影响**：浮动依赖或无人负责的 adapter 会把一次升级变成线上兼容性事故；故障发生时也无法区分 adapter 故障与核心流程故障，运维成本不可预测。
- **建议**：为每个 adapter 建一份版本化 manifest，至少锁定精确 commit、lockfile digest、运行时镜像、远程 endpoint、主/备 owner、feature flag、SLO 和停用日期；禁止范围版本。只有 golden fixture 100% 通过、schema lock 无未审计变更、连续 2 次 canary 部署无新增 error/warning 才能升级。部署后监控 adapter error、fallback、p95 latency、schema mismatch 和请求量；fallback 超过请求量 1% 且持续 5 分钟，或出现 3 次连续核心流程失败，触发 on-call。

**观点 2**

- **发现**：原文 L7 要求 warning、fallback、golden fixture，原文 L13 询问 schema 漂移、丢字段、网络失败和远程 ID 失效，但没有规定哪些错误可降级、多久必须恢复、数据能丢多少。
- **影响**：没有硬阈值时，schema 漂移可能静默地产出残缺 artifact；远程调用重试还可能放大流量。凌晨值班人员无法判断是继续重试、切换本地还是回滚。
- **建议**：required 字段缺失或类型不兼容直接拒绝该 adapter 输出并切本地 fallback；unknown 字段只产生 warning，连续 3 个 golden fixture 失败即阻断发布。远程请求单次超时设为 2 秒、最多重试 1 次；5 分钟内错误率达到 5% 或连续 3 次失败即打开 circuit breaker，60 秒后再 half-open。远程 ID 无法解析时立即标记映射 stale，不得写入核心 artifact；同一 ID 在 5 分钟内出现 3 次失效则告警。fallback 必须在 30 秒内完成，核心 artifact 的 RTO 设为 60 秒、RPO 设为 0；adapter 缓存可接受的 RPO 不超过 1 小时，并以指标验证。

**观点 3**

- **发现**：原文 L7 明确要求远程服务关闭时核心流程仍可本地继续，但原文 L12-L14 尚未把“关闭”定义成可演练的运行模式，也没有给出监控、恢复或退出开关。
- **影响**：只在代码里保留理论 fallback 不等于可用；远程供应商维护、DNS/TLS 故障或权限撤销时，核心 artifact 仍可能被隐式阻塞，形成大面积 on-call 事件。
- **建议**：提供显式 `REMOTE_ADAPTERS=off`/按 adapter 的 feature flag，并在每次发布和每周自动演练一次远程全断场景：本地路径应完成核心流程，结果与 golden fixture 一致，核心流程 RTO ≤60 秒、RPO=0。远程关闭期间只记录降级计数，不因单次远程错误 paging；只有 fallback 持续超过 1%/5 分钟、核心本地路径失败 3 次，或本地恢复超过 60 秒才 paging。远程恢复采用 60 秒 half-open 和人工确认再全量放开，避免恢复风暴。

**观点 4**

- **发现**：原文 L7 要求依赖、fallback、removal test 和停用/重评阈值，原文 L14 将“何时停止维护、如何删除且不破坏核心 artifact”列为 Q3，但没有给出停维护、删除和回滚的可判定条件。
- **影响**：adapter 会因沉没成本长期占用构建、值班和依赖升级预算；直接删除又可能让历史 artifact 无法读取或让 skill 路由引用悬空。
- **建议**：将停维护候选定义为同时满足以下条件：连续 2 个发布周期无需求、过去 30 天使用量低于全部 adapter 请求的 5%，或供应商连续 14 天错误率高于 2%；进入候选后冻结版本，只修安全问题，并保留 14 天可回滚包。删除前必须通过全仓引用扫描、历史 artifact 读取、removal test 和远程关闭测试；核心 schema、golden fixture 及本地 renderer 不得依赖 adapter 包。删除后的 30 天保留 fallback telemetry，若核心 artifact 失败率超过 0.1%则回滚。

**观点 5**

- **发现**：原文 L6 将多个 adapter 与可选 connector 放在同一生命周期问题中，原文 L7 只列成功判据，没有容量、增长和资源预算；因此无法判断新增 adapter 是否会拖慢 CI、占满远程配额或增加本地降级延迟。
- **影响**：请求量增长时，重试和 golden fixture 矩阵会成倍放大成本；容量耗尽可能先表现为超时，最终误触发 fallback 或 on-call，且没有提前扩容窗口。
- **建议**：按 adapter 记录请求量、payload 大小、缓存命中率、远程配额、CPU/内存和 CI fixture 时长，并设置预算：p95 处理延迟不得超过 1 秒、单 adapter CI 时长不得连续 3 次增加超过 20%、远程配额使用率达到 70%即评估扩容，达到 85%自动限流。对远程调用使用有界队列与指数退避，队列满立即本地 fallback；每次版本发布前用 1x、2x、5x 当前请求量做容量演练，5x 仍需满足核心 RTO ≤60 秒。这样 Q1 的纳入、Q2 的回退和 Q3 的停维护都能以运行数据复评。

### 视角：L（法律 / 合规）
`视角来源: 跨会话独立Agent`

**观点 1**

- **发现**：原文 L7 把“固定 commit/version、许可证、依赖”列为每个 adapter 的成功判据，但 Q1（原文 L12）仍未规定纳入时要保存哪些许可证据、谁批准版本变化。
- **影响**：没有 SPDX 许可证、NOTICE/归属义务、传递依赖清单和不可变版本证据，就无法判断 copyleft 传染、商业使用限制或来源保留义务；未经复核的上游升级可能同时改变代码行为和合同义务，发布后才发现即构成合规违约面。
- **建议**：建立 adapter 合规登记表：上游 URL、不可变 commit/digest、直接与传递依赖 SBOM、SPDX 标识、NOTICE 文本、商业使用/再分发结论、owner 和复核日期必须齐全。缺任一许可证证据、发现与项目分发模式不兼容，或版本不是不可变引用时，纳入闸门直接拒绝；任何版本变更须由 owner 在合并前重新生成登记表并完成一次许可证复核，未完成则禁止发布。

**观点 2**

- **发现**：原文 L6 将 Figma/Superdesign connector 定义为可选外部连接器，原文 L7 又要求远程服务关闭时核心流程仍可本地继续；但当前 Q2（原文 L13）只提网络失败和远程 ID 失效，没有数据出境、隐私、服务条款或处理协议的门槛。
- **影响**：设计文件、远程 ID、提示词或用户 artifact 可能包含个人信息、客户机密或受合同约束的内容；若没有最小化、授权、保留期限和 DPA/服务条款依据，向远程服务发送数据可能触发隐私监管或客户合同违约。服务停机时若仍强依赖远程调用，还会把合规和可用性风险传导到核心 artifact 流程。
- **建议**：远程 adapter 默认关闭出站传输，只允许显式 opt-in；请求载荷在发送前必须通过字段级分类/脱敏清单，禁止发送未获授权的原始 artifact。纳入前必须存档服务条款版本、隐私政策版本、DPA/数据处理依据和数据保留/删除承诺；缺任一文件即只能作为本地禁用的实验 adapter。远程请求单次超时 3 秒或连续失败 2 次即切换本地 fallback，并在同一运行中不再重试；服务关闭时核心流程必须在无网络环境完成 golden fixture，且 CI 必须验证无出站请求。

**观点 3**

- **发现**：原文 L7 要求 schema lock、warning、fallback 和 golden fixture，Q2（原文 L13）要求处理 schema 漂移、丢字段、网络失败、远程 ID 失效，但没有定义何时属于可接受降级、何时必须阻断以避免错误交付。
- **影响**：静默丢字段或把失效远程 ID 当成有效结果，会造成 artifact 语义被篡改；若下游用户据此发布或交付，责任边界不可证明。仅记录 warning 不能替代对用户的告知、可追踪证据和合同承诺的履行证明。
- **建议**：把每次 adapter 运行的输入版本、schema 校验结果、缺失字段、远程 ID、fallback 原因和用户告警写入可审计日志。schema 校验失败、必填字段丢失、远程 ID 无法在 1 次查询内确认时，禁止静默成功：保留原始核心 artifact、标记 adapter 结果为不可发布，并转本地确定性 fallback；只有非必填字段缺失且 golden fixture 通过时才允许降级，并必须给出 warning。连续 2 个版本或 30 天未修复同一漂移问题时，自动进入停用评审，而不是继续以 warning 掩盖风险。

**观点 4**

- **发现**：原文 L7 要求 removal test 和停用/重评阈值，Q3（原文 L14）要求删除 adapter 且不破坏核心 artifact；原文 L69-L72 还要求把 PRD/ADR 和跨子文档约束沉淀下来，但目前均为待讨论。
- **影响**：没有退出路径，许可证变更、供应商终止服务、隐私条款变更或长期无人维护时，团队可能被迫继续运行一个不能合法使用或无法履约的 adapter；删除代码若连带删除映射数据，会破坏既有核心 artifact，形成数据可用性和客户合同风险。
- **建议**：设三类硬停用阈值并写入 ADR：收到许可证/隐私/服务条款重大变更或安全/合规通知，立即禁用新写入并在 24 小时内完成法律复核；远程服务连续不可用 24 小时或供应商宣布 EOL，立即切本地 fallback，并在 7 天内决定移除；连续 2 个发布周期无 owner、或连续 2 个版本/30 天 schema 不兼容，停止新增功能并进入重评。移除验收必须包括：卸载 adapter 后所有核心 golden fixture 通过、历史 artifact 可离线读取、CI 检测不到该 adapter 的出站调用和必需导入、许可证/NOTICE 清单同步删除或保留；任一项失败则只能隔离 adapter，不得合并删除。

## 主力AI 整合立场（主会话，非独立视角，低权重）

`视角来源: 同会话SubAgent(低权重)`

独立观点已通过 scope、架构和 UX 闸门。本题把外部项目当作可移除 B1 adapter，先保证本地 artifact 闭环，再以版本锁、schema lock、golden fixture、fallback 和 removal test 接入。

1. 每个 `adapters/<name>/adapter.yaml` 必须锁定不可变上游 commit/version、许可证与依赖、输入/输出映射、owner/reviewer、风险级别、schemaLock hash、fallback 和 removal test。核心代码不得 import 外部 SDK，外部字段只能进入 adapter namespace。

2. 适配顺序为 schema lock → 映射完整性 → golden fixture → 运行时能力/健康探测；required 字段缺失 hard fail，optional 字段逐字段 warning；网络/认证/远程 ID 失败最多一次有限重试后进入 `degraded/disabled`，回退到本地 canonical artifact/静态投影，不伪造成功。

3. 首轮只把本地可复现、能服务真实任务的 adapter 纳入 active：Storybook 作为验证入口，json-render/A2UI/M3E 先按 manifest 和 fixture 做 opt-in 兼容性验证；Figma/Superdesign 仅可选 connector，不成为核心路径或唯一索引。每个 active adapter 至少有两个独立工作流、一个 golden fixture 和一次离线关闭验收。

4. 生命周期固定为 `candidate → active → deprecated → disabled → removed`。连续两个发布周期无活跃工作流、连续兼容探针失败、上游 EOL/许可证或隐私条款重大变化即进入复评/停用；删除前必须卸载包、注册、依赖和路由，离线读取历史 artifact、golden fixture 和其他 adapter 全部通过，否则只隔离不删除。

## Human 对 Agent X 的拍板

| 轮次 | 视角 | 隔离方式 | Human 拍板 | 是否 conclusion | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 | B | 同 provider 跨会话 | 待拍板 | 否 | |
| 2 | C | 同 provider 跨会话 | 待拍板 | 否 | |
| 3 | A | 同 provider 跨会话 | 待拍板 | 否 | |
| 4 | T | 同 provider 跨会话 | 待拍板 | 否 | |
| 5 | O | 同 provider 跨会话 | 待拍板 | 否 | |
| 6 | L | 同 provider 跨会话 | 待拍板 | 否 | |

## conclusion（含沉淀指令）

- **子问题结论：** 外部项目只能以可移除 B1 adapter 存在，核心 artifact、skill 路由和安全策略不依赖其运行时或远程 ID。纳入的核心证据不是“能连接”，而是固定版本、许可证、映射、离线恢复和 removal test。
- **解法：** 用 adapter manifest + AdapterBoundary v1 + schema lock/golden fixture + warning/fallback + lifecycle state 实现；首个本地验证 adapter 先行，json-render/A2UI/M3E 采用 opt-in 兼容性 fixture，Figma/Superdesign 保持可选 connector。远程关闭、404、5xx、schema drift 都应本地继续或明确 disabled。
- **remaining-risks 控制：** 上游 version/schema 漂移、服务条款变化、远程不可用和许可证判断不能被一次适配彻底消除；用不可变版本、定期探针、owner/expiry、法律复核、quarantine、fallback 和 removal test 控制。条款/许可证重大变化立即停止新写入，不能靠 warning 继续。
- **沉淀指令：**
  - 改哪些 PRD / ADR / 文档：新增 AdapterBoundary/Lifecycle ADR 和 adapter card 模板；将准入、schema lock、active/deprecated/removed 阈值与离线回退写入项目文档。
  - 跨子文档约束登记：`sub-01` 是唯一 canonical source；`sub-02` 是唯一调用入口；`sub-04` 负责远程 capability/凭据 approval；`sub-05` 负责 adapter verification receipt。
  - 待删临时脚手架：本子文档 briefings 和 viewpoints 过程文件，待 `zj-docs-ontology` 分类；Human 确认前保留讨论目录。
- **状态协议：** DONE_WITH_CONCERNS

