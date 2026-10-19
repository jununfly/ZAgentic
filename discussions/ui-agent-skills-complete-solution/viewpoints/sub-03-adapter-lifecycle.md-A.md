视角来源: 跨会话独立Agent

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
