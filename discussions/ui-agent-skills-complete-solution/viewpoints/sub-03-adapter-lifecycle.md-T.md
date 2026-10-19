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
