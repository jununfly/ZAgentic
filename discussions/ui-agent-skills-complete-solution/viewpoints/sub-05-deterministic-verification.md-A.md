视角来源: 跨会话独立Agent

**观点 1**

**发现**：原文把范围限定为验证 oracle、fixture、浏览器/字体/网络运行环境和 receipt 证据，并明确不决定视觉方向或 adapter 采用（原文 L5-L7）；但 Q1 只问“哪些验证必须自动化、哪些保留 Human review”，尚未定义自动化 oracle 与人工判断的边界（原文 Q1，L12）。如果把“视觉正确”作为一个未分解的总断言，自动化截图、人工审美和产品决策会耦合成同一个不可复核的状态。

**影响**：同一条 claim 可能被不同角色以不同标准解释，receipt 即使记录了命令也无法证明它测到了什么；视觉方向或 adapter 变更还可能反向修改验证规则，突破本子问题的边界。长期看，旧 receipt 与新 oracle 不能比较，回归门禁会出现“绿但不可解释”或“全红但不知道哪一层失败”。

**建议**：把每个 claim 拆成稳定的机器契约和保留的人工断言两层：机器层至少覆盖尺寸、overflow、focus 顺序/可见性、contrast、reduced-motion、状态与极端 fixture；人工层只接收带截图/录屏/交互路径的待审项，并将结果记为 `human_review_required`、`accepted` 或 `rejected`，不能伪装成自动 `pass`。为两层分别分配 `claim_id`、`oracle_version` 和 `decision_owner`；只有机器层全部通过且人工层没有未决 blocker，聚合结果才可为 `pass`。这样直接回答 Q1，同时守住 L6 的子问题边界。

**观点 2**

**发现**：成功判据要求固定浏览器、字体、网络和 fixture 后可复跑（原文 L7），但没有规定“固定”的可识别身份，也没有列出时钟、时区、locale、随机种子、操作系统渲染栈或 provider 版本。Q2 要求区分环境噪声与真实缺陷，却尚未提供环境指纹和不匹配处理（原文 Q2，L13）。

**影响**：两个相同 commit 的 receipt 可能实际来自不同浏览器 patch、字体文件、网络响应或时间点，像素差异会被错误归因于代码；反过来，环境变化也可能掩盖真实缺陷。若只把环境写进日志而不参与状态机，复跑仍会被误报为回归，且跨机器 receipt 不能作为向后兼容证据。

**建议**：定义不可变 `environment_fingerprint`，至少包含浏览器/引擎及版本、OS/容器镜像、字体文件 hash、网络录制包或 mock manifest hash、timezone/locale、冻结时间、随机种子和 provider 标识；将它与 commit、fixture hash 一并写入 receipt。指纹不匹配时结果必须是 `environment_mismatch` 并进入 quarantine，不能计入通过率或覆盖率；允许在同一锁定环境内重跑确认。机制可以消除可重复的本地噪声，但不能彻底消除长期 provider 漂移：provider 漂移只能由固定版本、定期重评周期和状态降级控制，不能宣称已被验证机制解决。

**观点 3**

**发现**：原文要求覆盖 390/768/1440、键盘 focus、contrast、overflow、reduced-motion，以及长文本、空、错、1 条、1000 条、多语言，并要求 worst-case 覆盖率至少 95%（原文 L7）；但没有定义覆盖率的分母、组合键或“不适用”如何计数。Q2 也没有规定如何区分缺 fixture、环境失败和产品缺陷（原文 Q2，L13）。

**影响**：团队可以通过减少分母、把未运行的组合标为 N/A 或只测代表性语言而得到虚假的 95%；同一极端数据在不同层被重复计数，实际缺口无法被发现。更严重的是，`not_run`、`infra_error` 和 `product_fail` 如果都被压成一个红灯，后续修复会误改产品而不是修环境，长期回归历史失真。

**建议**：建立版本化验证矩阵，矩阵单元由 `viewport × interaction_mode × content_fixture × locale × motion_mode × browser_profile` 的显式 key 定义；分母是声明过的全部适用单元，`not_applicable` 必须有规则和证据，不能由执行者临时决定。每个单元只允许 `pass`、`fail`、`blocked`、`not_run`、`not_applicable` 五类状态，并把 `infra_error` 作为 `blocked` 的原因而不是产品失败。95% 只统计已执行且有结论的适用单元，剩余单元不能自动补绿；任何 `visual blocker` 或关键 a11y/interaction fail 都直接阻断聚合结果。

**观点 4**

**发现**：成功判据要求 fixture 可复跑且 receipt 能关联 claim、threshold、命令、commit 和 fixture（原文 L7）；当前文本没有规定 fixture 的所有权、版本、哈希、生成器或 schema 兼容策略。Q3 要求合并 visual/a11y/interaction/break/reduced-motion 结果，却没有规定这些结果怎样引用同一组输入（原文 Q3，L14）。

**影响**：fixture 一旦被编辑，旧 receipt 会失去可审计性；生成器升级后，长文本、多语言或 1000 条数据的实际边界可能静默改变。不同验证器若各自复制 fixture，视觉、a11y 与交互结果会互相矛盾，无法判断是 UI 差异还是输入差异；这构成跨系统接口契约不稳定和向后兼容风险。

**建议**：把 fixture 视为有版本的输入接口：每个 fixture 固定 `fixture_id`、`schema_version`、内容 hash、locale、时区、生成器版本和语义标签（如 `empty`、`error`、`1000_items`）；receipt 只引用不可变 hash，不引用可变路径。验证器统一读取同一 fixture manifest，新增字段采用向后兼容的可选扩展，改变语义必须递增 schema/oracle 版本并允许旧 receipt 继续按旧契约解释。将“矩阵单元—fixture hash—各类 claim”建成显式关联，保证 Q3 的多类结果可追溯到同一输入。

**观点 5**

**发现**：Q3 只提出要把 visual、a11y、interaction、break、reduced-motion 结果合并为可追溯 receipt（原文 Q3，L14）；成功判据进一步列出 receipt 需要关联 claim、threshold、命令、commit 和 fixture，并要求 visual blocker 为 0（原文 L7）。这已经暗示 receipt 同时承担证据包和门禁摘要，但没有定义聚合顺序、阈值来源或 schema 演进规则。

**影响**：若只保存最终 `pass/fail`，无法判断是哪个 claim、哪个 threshold 或哪条命令导致结果；若让人工编辑摘要，摘要可能与原始 artifact 不一致。receipt schema 变更还会破坏旧工具，导致历史结果无法比较；把 `blocked` 当作 `fail` 则会掩盖环境问题，把它当作 `pass` 则会突破 visual blocker=0 的硬约束。

**建议**：定义版本化、追加式 receipt envelope：顶层至少包含 `receipt_schema_version`、commit、环境指纹、fixture manifest hash、运行命令及其版本；每条证据包含 `claim_id`、类别、threshold/oracle 版本、结果状态、artifact hash、时间和失败原因；聚合摘要只能由这些条目按固定优先级计算。聚合规则应明确为：关键 `fail` 或 `visual blocker` → `fail`，`blocked/not_run` → `blocked`，未决人工项 → `human_review_required`，全部适用项通过且人工项结清 → `pass`。schema 采用可追加字段和迁移器，旧 receipt 保留原语义，不能静默按新阈值重算。

**观点 6**

**发现**：原文把浏览器、字体、网络、fixture 和 receipt 纳入确定性验证，但成功判据仍包含视觉与多语言体验等高语义断言（原文 L6-L7），Q1 也明确询问 Human review 的保留范围（原文 Q1，L12）。因此，生成式审美判断、法律判断和长期 provider 漂移不可能仅靠截图、a11y 扫描或 receipt 机制彻底解决；原文也没有声称可以解决这些长期风险。

**影响**：若把机器通过误读成“整体体验正确”，会把审美争议、语境化语言问题、法律风险或 provider 行为变化错误地归入已验证范围。对于无法判定的结果，继续自动发布会使状态机失去安全边界；对 provider 或规则变化不重评，则会使历史基线逐步失效。

**建议**：在 receipt 中显式区分四类剩余风险及处置：

- 可由机制消除或大幅收敛的风险：固定环境造成的非确定性、已定义的 overflow/contrast/focus/reduced-motion 契约、fixture 与命令不可追溯；用锁定运行时、哈希、自动 oracle 和追加式 receipt 处理。
- 只能保留 Human gate 的风险：生成式审美、品牌/语境化视觉判断和难以形式化的体验取舍；状态只能从 `human_review_required` 转为 `accepted`，不能由机器强行转绿。法律判断若被提出，也必须由合适的人工/合规 gate 处理，不能由本验证系统宣称已解决。
- 适合 fallback 或 quarantine 的风险：浏览器/字体/网络不匹配、录制缺失、provider 不可用或 artifact 不完整；使用已知锁定 fallback，或将该单元隔离为 `blocked/quarantined`，不得计入覆盖率通过。
- 只能靠重评周期和状态降级的风险：长期 provider 漂移、浏览器/字体升级、阈值或 fixture 语义改变；按固定周期重跑基线，发现指纹或分布变化时降级为 `stale`/`revalidation_required`，直到新的人工与机器门禁完成。

这样 Q1-Q3 的自动化、隔离与 receipt 方案保持边界清楚：机制证明“在声明的契约和环境下发生了什么”，而不是声称生成式审美、法律判断或长期 provider 漂移已经被彻底解决。
