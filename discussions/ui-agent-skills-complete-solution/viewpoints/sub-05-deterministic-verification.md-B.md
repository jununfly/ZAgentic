视角来源: 跨会话独立Agent

**观点 1**

**发现**：原文 L7-L8 把成功判据和声明必需角色集写得很全，但没有把 390/768/1440、交互状态、数据状态、语言和动效组合成有 owner、有顺序的交付单元；原文 Q1 又要求区分自动化与 Human review。若直接追求“全量一次跑完”，关键路径、完成定义和失败后的责任边界都不清楚。

**影响**：首轮实施容易陷入视觉截图调参，无法判断是 fixture 缺口、环境问题还是产品缺陷；“worst-case 覆盖率至少 95%”也会变成事后统计，而不是发布闸门。以 1 名前端、1 名测试并行为假设，首版 harness、fixture manifest 和 receipt 最少应按约 3–5 人日排期，环境锁定与首批基线再预留约 1–2 人日；若没有这段关键路径，交付时间不可承诺。

**建议**：分三段交付并写入任务验收：P0（平台/测试）冻结浏览器、字体、网络回放、时钟和 fixture manifest；P1（测试/前端）自动跑几何、overflow、focus、contrast、reduced-motion 和状态矩阵；P2（设计/产品指定 reviewer）只处理自动化无法判定的视觉语义，并将结果回写 receipt。每段必须指定 owner 和阻塞升级人；“完成”定义为必测矩阵每个 cell 都有 PASS/FAIL/HUMAN_REVIEW/QUARANTINED 状态，缺 cell 不算通过，而不是只看总覆盖率。这样 Q1 有明确自动化边界和排期出口。

**观点 2**

**发现**：原文 L7 明确要求固定浏览器、字体、网络和 fixture 后可复跑，原文 Q2 要求隔离浏览器、字体、网络和时间噪声；但原文没有规定这些输入如何被版本化、校验或注入。特别是“长文本/空/错/1 条/1000 条/多语言”仍只是场景名，不是可审计的 fixture 契约。

**影响**：同一 commit 可能因字体 fallback、系统 locale、远端请求、当前时间或随机数据产生不同截图和交互结果，误报会吞噬测试容量，真缺陷也可能被“重新跑一次”掩盖。只保存截图而不保存输入 hash，无法证明复跑使用了同一测试条件。

**建议**：建立可提交的 manifest，每个 case 至少包含 `case_id`、数据/locale/时区 hash、viewport、浏览器与字体版本、网络录像 hash、固定 clock/seed、预期 oracle 和 owner；CI 在启动时校验全部 hash，禁止隐式访问外网和宿主机字体。把每个 case 的环境快照写入 receipt，并提供 `replay <run_id>` 命令。上述机制可以消除大部分可控噪声；浏览器升级、字体供应链变化、provider 长期漂移仍不能被一次锁定彻底解决，必须通过新版本建立新基线、旧基线 quarantine 和人工复核后再放行。

**观点 3**

**发现**：原文 Q1 直接询问哪些验证必须自动化、哪些必须保留 Human review；原文 L7 又把 visual blocker 设为 0，却没有给“自动通过”“必须人工看”“阻塞发布”的判定边界。像 pixel diff、contrast、overflow 可以有数值 oracle，但视觉层级、语义是否清楚、生成式审美是否合适并不能由单一阈值可靠推出。

**影响**：把所有截图差异都自动判 FAIL 会造成噪声和排期失控，把所有差异都自动判 PASS 又会把 blocker 隐藏在平均分里。生成式审美、法律判断以及长期 provider 漂移不会因为有截图或阈值就被彻底解决；它们若没有人工 gate，发布状态会产生虚假的确定性。

**建议**：按 oracle 能力分层：几何/overflow、键盘 focus 顺序、contrast、状态存在性、reduced-motion 行为、网络请求白名单由自动化硬失败；像素差异先经过确定阈值和区域白名单，超阈值进入 HUMAN_REVIEW；视觉语义、生成式审美、法律/合规判断保留带 reviewer、时间和理由的人工 gate。人工 gate 必须能看到 baseline、candidate、diff、fixture 和 commit；超时或 reviewer 缺失状态只能是 BLOCKED，不得降成 PASS。对暂时无法稳定判定的 case 使用 QUARANTINED，并要求 fallback（旧基线/静态 fixture）和重评日期，避免以“通过率”替代真实验收。

**观点 4**

**发现**：原文 Q3 要求把 visual/a11y/interaction/break/reduced-motion 结果合并为可追溯 receipt，原文 L7 只列出了 receipt 必须关联 claim、threshold、命令、commit 和 fixture，没有规定字段完整性、聚合规则或失败状态传播。

**影响**：如果 receipt 只是多份测试日志的链接，无法从一个 claim 追到具体输入和观测值，也无法解释“总体验收通过但某个 viewport 失败”的矛盾；视觉 blocker 可能被平均覆盖率 95% 掩盖。证据不可关联时，复核和回滚的成本会随 case 数量线性放大。

**建议**：为每条 claim 生成不可变 receipt 记录：`run_id`、`claim_id`、`test_kind`、`fixture_id/hash`、环境版本、命令、commit、threshold、observed、artifact 路径、reviewer/review_at、status 和 `supersedes`。聚合采用最严格传播：任一 blocker 为 BLOCKED，任一硬 oracle FAIL 为 FAIL，人工未完成为 HUMAN_REVIEW，隔离项为 QUARANTINED；只有所有必测 cell 完成且 blocker=0 才能 PASS。CI 增加 receipt schema 校验和“每个 claim 必有证据”检查；建议保留至少最近 30 次运行或 90 天（取较长者），把不完整 receipt 当作验证失败而非缺省通过。

**观点 5**

**发现**：原文 L7-L14 同时覆盖多 viewport、多状态、多语言、可访问性、交互、断点和动效，原文 L8 还声明 B、C、A、T、U、O 均为必需角色，但没有给出变更后的基线管理、环境升级和失败回退责任。

**影响**：验证系统本身会发生漂移：浏览器/字体升级可能产生大量无意义 diff，网络 provider 改变可能让回放失效，新增语言或 1000 条数据可能暴露资源上限。机制能消除被固定输入和版本控制覆盖的噪声，但不能消除生成式审美判断、法律判断或长期 provider 漂移；把这些风险写成“deterministic 已解决”会让 release gate 失真。

**建议**：建立风险状态机和 owner：环境升级先进入 CANDIDATE，跑全量矩阵并由人工 gate 审核；基线变化进入 QUARANTINED，保留旧基线作为 fallback，完成差异归因后才能替换；provider 回放失效则降级为 BLOCKED/DEGRADED，禁止伪造 PASS，并在固定重评周期（建议每月一次、每次浏览器/字体/provider 变更立即触发）重新评估。对人工不可消除的剩余风险，receipt 必须记录 reviewer、理由、有效期和下次重评日期；若到期未复核，状态自动降级为 HUMAN_REVIEW 或 BLOCKED。发布责任由测试 owner 维护自动 gate，设计/产品 owner 维护视觉人工 gate，平台 owner 维护环境与 fallback，不能由单一“覆盖率 95%”指标代替这些职责。
