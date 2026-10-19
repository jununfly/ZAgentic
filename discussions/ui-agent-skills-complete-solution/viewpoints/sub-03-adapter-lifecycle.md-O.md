## Agent viewpoints

视角来源: 跨会话独立Agent

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
