# 子问题：确定性的视觉、可访问性与极端数据验证

## 上下文

- **所属主文档：** [../MASTER.md](./MASTER.md)
- **本子问题独立性：** 只讨论验证 oracle、fixture、浏览器/字体/网络运行环境和 receipt 证据；不决定界面视觉方向，也不决定 adapter 采用。
- **成功判据：** 固定浏览器、字体、网络和 fixture 后，390/768/1440、键盘 focus、contrast、overflow、reduced-motion、长文本/空/错/1 条/1000 条/多语言均可复跑；receipt 能关联 claim、threshold、命令、commit 和 fixture，visual blocker 为 0，worst-case 覆盖率至少 95%。
- **声明必需角色集：** B,C,A,T,U,O

## 待讨论问题（scope 草案）

- Q1：哪些验证必须自动化，哪些必须保留 Human review？
- Q2：如何隔离浏览器、字体、网络和时间造成的噪声，并区分真实缺陷？
- Q3：如何将 visual/a11y/interaction/break/reduced-motion 结果合并为可追溯 receipt？

## Agent viewpoints（独立视角 — 须跨会话独立 Agent）

### 视角：B（技术经理 / 可落地）
`视角来源: 跨会话独立Agent`

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

### 视角：C（产品专家 / 用户价值·生态竞品）
`视角来源: 跨会话独立Agent`

**观点 1**

**发现**：原文将边界限定为验证 oracle、fixture、浏览器/字体/网络运行环境和 receipt 证据，而不决定视觉方向或 adapter 采用（原文 L6）；成功判据要求多 viewport、多状态可复跑，并要求 receipt 可追溯（原文 L7）。这表明首要用户是 UI agent skill 的作者、维护者和评审者，而不是抽象的“所有用户”。原文没有写出他们当前的替代流程、决策时限或最昂贵的失败类型，因此“95% 覆盖率”和“visual blocker 为 0”还不是充分的产品价值证明。

**影响**：如果把检查数量、覆盖率或绿色徽章当成价值本身，系统可能增加维护成本，却没有减少发布决策时间、误报阻塞或缺陷逃逸。相对人工截图、手工点验和普通 CI 状态，真正可被用户感知的差异应是：另一位维护者能否不依赖聊天上下文复跑、定位并做出相同的批准或隔离决定。否则团队会为了达标而优化指标，而不是优化交付安全感。

**建议**：在试运行中把产品价值写成可验收的 baseline：固定一组长文本、空、错、1 条、1000 条和多语言 fixture，记录旧人工流程与 receipt 流程的决策耗时、误报阻塞率、重跑 verdict 一致率和缺陷定位耗时；至少保留“当前人工流程 / 普通 CI / 本 receipt”三路对照。若 receipt 不能让独立评审者在不看原始上下文时复跑并作出相同决定，自动化流程必须停止发布，不得以覆盖率达标替代用户价值。

**观点 2**

**发现**：Q1 要求划分哪些验证必须自动化、哪些必须保留 Human review（原文 L12）；成功判据列出 focus、contrast、overflow、reduced-motion 和极端数据等可测项，同时又使用了需要解释的“visual blocker 为 0”（原文 L7）。原文没有定义 blocker 的用户伤害等级、人工复核的退出条件或谁有权 override。

**影响**：所有差异若都成为同等级 release gate，会让无用户伤害的像素波动阻塞交付，也会把真正影响键盘用户、低视力用户或极端数据用户的缺陷留给“稍后人工看”。自动检查可以替代重复、阈值明确的判断，但不能把视觉层级、内容语义、品牌一致性、歧义交互或合规判断伪装成已解决的问题；这些不可彻底消除的风险必须显式进入产品状态。

**建议**：将 viewport 几何、overflow、focus 可达性、contrast 阈值、reduced-motion 行为、fixture 完整性和 receipt schema 设为自动 gate；将视觉层级、品牌/审美、语义歧义、法律或合规判断设为 Human gate。每个 Human gate 记录 reviewer、理由、关联截图/状态、有效期和升级人；自动 gate 任一失败、receipt 缺字段、人工 gate 未完成或 reviewer 无法判断时，流水线必须在生成 `PASS` 前停止并进入 `BLOCKED` 或 `QUARANTINED`。无法彻底消除的判断风险用人工 gate 控制，不能用“无 blocker”字样消除。

**观点 3**

**发现**：原文要求 receipt 关联 claim、threshold、命令、commit 和 fixture（原文 L7），Q3 要求将 visual、a11y、interaction、break、reduced-motion 合并为可追溯 receipt（原文 L14）。但原文没有指定 receipt 的消费者、版本兼容策略或跨 skill 的解释方式，也没有给出与截图清单、普通 CI 或视觉回归服务的竞品/替代方案比较（原文 L6-L14）。

**影响**：只有“通过/失败”的徽章无法区分真实用户缺陷、环境噪声、fixture 缺失和人工未复核；不同 skill 各自解释 receipt 后，生态会形成不可互换的证据孤岛。没有 baseline，就无法证明 95% 覆盖率或 0 blocker 比现有流程更可靠，也无法证伪“值得采用”的价值主张。生态价值不在于 receipt 更长，而在于下游工具和不同维护者可以稳定消费同一份证据。

**建议**：定义可版本化的最小模型：`claim -> check -> threshold -> fixture -> environment fingerprint -> command -> commit -> result`，并补 `risk_class`、失败证据、reviewer、override 理由、expiry、schema_version 和状态。提供机器可读字段与人类可读摘要，建立“旧人工流程 / 普通 CI / 本 receipt”的基线矩阵，比较重跑一致率、定位耗时、人工 override 率、跨项目移植成本和误报率。若 receipt 缺少任一必需关联、schema 版本不兼容或无法回到对应 fixture/命令，消费方必须停止将其解释为 `PASS`，fallback 只能回到最近有效 receipt 并标成 `STALE`，不能静默降级为成功。

**观点 4**

**发现**：Q2 明确要求隔离浏览器、字体、网络和时间噪声并区分真实缺陷（原文 L13）；成功判据也要求固定这些条件后可复跑（原文 L7）。这能降低同版本、同 fixture 下的随机差异，但原文没有定义浏览器/字体/provider 长期漂移后的用户可见状态；全篇状态仍是 `NEEDS_CONTEXT`（原文 L73），说明这部分尚未成为可执行的产品承诺。

**影响**：固定环境提高今天的重现率，却可能制造“receipt 永远有效”的错觉。浏览器或字体升级、远端 provider 改变、网络契约失效后，旧 receipt 不再代表新环境；若仍显示绿色，维护者会把过期安全感传给下游。时间、网络和字体的部分噪声可以隔离，但真实的 provider 漂移、平台差异和用户设备差异不可彻底消除，只能通过人工 gate、fallback、baseline 和状态降级控制。

**建议**：receipt 必须写入浏览器及渲染引擎版本、字体文件 hash、网络 fixture/协议版本、时间/locale/timezone、随机种子和生成器/provider 版本；将时间冻结、网络 stub、字体打包、固定 viewport/DPR 和禁用非必要动画作为环境控制。为版本升级、fixture/provider 变更、连续失败和超过 expiry 设置重评触发器，并使用 `PASS`、`PASS_WITH_HUMAN_GATE`、`STALE`、`QUARANTINED_ENV_DRIFT`、`BLOCKED` 状态。检测到环境漂移、基线缺失或关键命令失败时立即停止新环境的发布 verdict；`last-known-good` 只作为回滚与对照 baseline，必须明确标 stale 并触发 Human review，不能伪装成当前环境通过。

### 视角：A（架构师 / 约束）
`视角来源: 跨会话独立Agent`

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

### 视角：T（测试 / 质量）
`视角来源: 跨会话独立Agent`

**观点 1**

- **发现**：原文把 `390/768/1440`、键盘 focus、contrast、overflow、reduced-motion 以及多组极端数据列为成功判据，但 Q1 只提出“哪些验证必须自动化，哪些必须保留 Human review”，没有定义各类检查的 oracle、容差和人工验收边界（原文 L7、L12）。
- **影响**：如果只用截图差异或自动化 a11y 结果作为总 oracle，像素抗锯齿、字体 hinting、语义层级和视觉层次都可能出现误判；`visual blocker 为 0` 也会变成不可复核的主观标签。自动化通过不能证明界面在真实使用中可理解，人工意见也不能直接当作可回归的证据。
- **建议**：建立按 claim 分类的验收矩阵：DOM/ARIA、键盘路径、focus 可见性、contrast、overflow、断点尺寸、fixture 内容、reduced-motion 和网络请求用自动化断言；截图只对固定环境下的布局几何与关键区域做带校准容差的差异检查。以下风险只能保留 Human gate：视觉层次/信息优先级是否仍然可理解、刻意设计的视觉变化是否合理、自动 oracle 无法表达的多语言排版可读性。人工 gate 未签署时，结果必须是 `needs-human-review` 或状态降级，不能被自动通过覆盖。

**观点 2**

- **发现**：原文列出了长文本、空、错、1 条、1000 条和多语言 fixture，并要求 worst-case 覆盖率至少 95%，但没有定义 coverage 的分母、组合方式，也没有列出 loading、网络失败、字体缺失、RTL、emoji、不可断行长 token、动态更新等边界状态（原文 L7）。
- **影响**：在没有测试空间定义时，95% 可能只是执行了 95% 的脚本，而不是覆盖了 95% 的高风险状态；一个未覆盖的“多语言 + 1000 条 + 390 宽度”组合就可能让列表溢出或键盘路径失效。极端数据修复还容易回归正常数据和其他 viewport。
- **建议**：将 fixture 组织为可枚举的 case ID，至少按 `viewport × content-state × locale/text-shape × interaction-state × motion-state` 建矩阵，再以风险加权的 case 数计算 coverage；为每个 case 固定预期断言（无水平溢出、焦点可达、错误状态可恢复、列表分页/滚动边界成立）。缺少 fixture、覆盖率低于 95% 或新增高风险维度未完成重评时，结果进入 `quarantine`，不得以“非阻塞 case”直接放行；无法自动表达的语言可读性和真实键盘操作感受，必须走 Human gate。

**观点 3**

- **发现**：原文要求固定浏览器、字体、网络和 fixture 后可复跑，并把时间噪声列入 Q2，但没有要求锁定浏览器版本、字体文件 hash、操作系统/渲染参数、locale/timezone、DPR、时钟、随机种子或网络回放规则（原文 L7、L13）。
- **影响**：同一 commit 可能因浏览器升级、字体 fallback、系统 locale、GPU/DPR 或真实网络响应变化而产生不同截图和交互结果；反过来，重试也可能把真实的竞态缺陷误标成 flaky。没有环境指纹就无法判断失败是产品缺陷、基线漂移还是基础设施问题。
- **建议**：把浏览器与驱动版本、OS/容器镜像、字体包及 hash、DPR/色彩模式、locale/timezone、fake clock、随机 seed、网络 replay manifest 和 fixture hash 固化到运行包，并在 receipt 中逐项记录；同一 case 在锁定环境中至少重复验证，首个失败 artifact 必须保留。环境无法达到锁定条件时可使用受控 fallback（本地字体和网络回放），但 fallback 结果只能标记为降级证据，不能冒充完整通过；环境漂移、字体缺失或外部网络介入时应 quarantine 并触发重评，只有确认是环境问题后才能关闭，而非静默重试。

**观点 4**

- **发现**：原文要求 receipt 关联 claim、threshold、命令、commit 和 fixture，并要求合并 visual/a11y/interaction/break/reduced-motion 结果，但没有规定结果的唯一 ID、环境证据、artifact、失败分类、重试记录或最终判定规则（原文 L7、L14）。
- **影响**：多个检查结果即使都“绿”，也可能无法追溯到同一 commit、同一 fixture 和同一环境；缺少失败分类会把产品缺陷、测试错误和基础设施故障混为一谈，导致审计不能复现、回归不能定位，`visual blocker=0` 也无法证明没有漏报。
- **建议**：receipt 使用可校验的链路：`claim_id → check_id → case/fixture hash → environment fingerprint → resolved command → commit → raw result/artifact hash → threshold → retry history → verdict`，并为每类结果定义 `pass/fail/inconclusive/quarantined/needs-human-review`。任一链路字段缺失、artifact 与 commit 不匹配或结果无法复跑时，receipt 判无效并状态降级；基础设施故障可进入 quarantine，产品断言失败必须 fail，不能用 fallback 结果替代；visual blocker 的“零”必须由自动结果和已签署的人工 gate 共同满足。

**观点 5**

- **发现**：子问题明确只讨论“验证 oracle、fixture、浏览器/字体/网络运行环境和 receipt 证据”，但原文没有说明阈值如何从已知正确/错误样本校准，也没有规定浏览器或字体变化后何时重建 baseline（原文 L6-L7）。
- **影响**：未经校准的 screenshot threshold 可能过严而制造噪声，也可能过宽而吞掉真实的 1px 溢出、focus 消失或文本截断；baseline 自动更新会把缺陷永久固化为“正确”。这属于 oracle 失效，不是简单的 flaky test。
- **建议**：为每类 oracle 准备 known-good 与 mutation fixture（刻意制造溢出、低 contrast、隐藏 focus、错误 reduced-motion、截断和错态），用它们校准属性级阈值并证明已知缺陷必失败；几何、文字、颜色和动画分别设阈值，不使用一个全局像素比例。浏览器主版本、字体 hash、渲染镜像或设计基线变更时必须人工批准 baseline，并执行完整矩阵重评；在重评完成前旧 baseline 只能作为参考，状态降级为 `needs-revalidation`，不能直接放行。

**观点 6**

- **发现**：成功判据要求 visual blocker 为 0、覆盖率至少 95%，但 Q3 没有规定失败重试、flaky 认定、baseline 更新权限和 unresolved failure 的处置（原文 L7、L14）。
- **影响**：无限重试会隐藏竞态和偶发溢出，自动接受新截图会吞掉回归；若失败只在 receipt 中记为 warning，阻塞项可能被“证据完整”掩盖。质量系统最终会证明“流程跑过”，却不能证明“产品仍然正确”。
- **建议**：失败处理固定为：保留第一次失败；仅对已识别的基础设施错误做有限次数重跑；产品断言重复失败即 fail；未能分类的失败为 `inconclusive` 并 quarantine。baseline、阈值和 fixture 的变更必须由人工 gate 审批并关联原因、commit、前后 artifact；外部浏览器/字体/网络不可控时只能 fallback 到锁定的验证包，fallback 与生产环境不等价，须触发重评。任何未解决的 visual blocker、覆盖率不足、人工 gate 缺失或 oracle 未校准，都只能以状态降级结束，不能标为完成。

### 视角：U（用户研究 / UX）
`视角来源: 跨会话独立Agent`

角色立场：用户研究 / UX。以下判断只从真实使用流程、体验摩擦、可达性与可复跑证据出发，不替代视觉方向或 adapter 选型。

**观点 1：几何与规则通过，不等于用户流程通过**

- **发现**：成功判据覆盖了 390/768/1440、键盘 focus、contrast、overflow、reduced-motion 以及多类数据 fixture，但没有定义用户从进入页面到完成任务、发现当前状态、修复错误的可验证路径（原文 L7；原文 Q1 L12）。这会把“控件存在且不溢出”误当成“人能顺利完成任务”。
- **影响**：自动化截图、DOM/a11y 检查可能全部通过，但用户仍可能不知道焦点在哪里、空态下一步做什么、错误后如何恢复，或在 390 宽度下需要反复滚动才能理解上下文。此类断点会直接造成任务失败，却不一定形成 visual blocker；仅以 worst-case 覆盖率 95% 也无法证明流程可用（原文 L7）。
- **建议**：为每个关键 fixture 增加一条最小任务脚本，至少记录：入口、首个可操作控件、键盘焦点顺序、状态可理解性、成功条件和错误恢复动作。自动化验证顺序、可操作性、状态变化和焦点可见性；Human review 只保留给语义是否足够清楚、错误恢复是否符合用户预期、任务是否无需猜测。任务脚本未完成时，将 claim 标为 `needs-human-gate`，不得用截图通过替代。

**观点 2：极端数据的 UX oracle 必须验证“信息还能不能被理解”**

- **发现**：原文要求覆盖长文本、空、错、1 条、1000 条和多语言，但没有规定哪些字符串代表最坏情况，也没有明确文本扩张、RTL、复数、数字/日期格式、字体缺字和翻译语义的判定方法（原文 L7）。
- **影响**：同样通过 overflow 检查的两份 fixture，可能一份只是截断了低价值文本，另一份却截断了按钮、错误原因或关键字段；1000 条数据也可能技术上能渲染，却让用户无法定位、排序或返回上下文。多语言的字面不溢出并不代表术语、语气、方向和操作含义可用。
- **建议**：把 fixture 从“数量集合”扩展为“用户风险集合”：每个 locale 固定文本扩张样本、长单词、换行、RTL/双向文本、缺字字体、日期/数字/复数和错误文案，并给关键字段配置不可截断断言。自动化测几何、方向、可操作控件和格式；翻译是否改变操作含义、截断后是否仍能做决定、空/错状态是否给出恰当下一步，只能保留 Human gate。未知 locale、缺失翻译或缺字字体走 fallback，并隔离到 quarantine，不得静默当作默认语言通过。

**观点 3：应把“干净基线”和“可感知降级”拆成两条验证通道**

- **发现**：原文同时要求固定浏览器、字体、网络和 fixture 后可复跑，并把浏览器、字体、网络和时间噪声列为待隔离问题（原文 L6-L7；原文 Q2 L13）。这能证明基线稳定，却没有规定字体未加载、慢网、断网、超时、部分数据或时间变化时用户会看到什么。
- **影响**：如果只测 hermetic 基线，真实用户可能先看到布局跳动、不可读的 fallback 字体、无尽 loading 或无法恢复的网络错误；如果把真实环境的合理变化混进同一截图 oracle，又会产生误报，团队可能通过放宽阈值掩盖缺陷。两类错误都会损害信任和复现效率。
- **建议**：建立两个固定 lane：`baseline` 固定浏览器/字体/网络/时间，验证像素、焦点和状态的确定性；`degraded` 用可脚本化的字体缺失、延迟、断网、超时、时钟偏移和部分响应，验证 loading、fallback、重试、取消和保留输入。baseline 失败按真实缺陷处理；degraded 只在其降级文案、可恢复性和不丢数据通过人工 gate 后放行。无法区分环境噪声与产品缺陷的样本先 quarantine，不能调阈值消除；浏览器、字体、网络模拟器或时间策略变化时必须重评。

**观点 4：receipt 必须把机器证据接回用户风险，而不只是接回命令**

- **发现**：成功判据要求 receipt 关联 claim、threshold、命令、commit 和 fixture，Q3 又要求合并 visual/a11y/interaction/break/reduced-motion 结果，但没有要求记录对应的用户任务、状态、人工判断和环境指纹（原文 L7；原文 Q3 L14）。
- **影响**：receipt 可能证明“命令运行过”，却无法回答“哪个用户场景被证明了”“失败是否可恢复”“人工看过哪一张图”。多维结果被压成一个总分后，a11y 或交互的关键失败可能被视觉结果抵消；95% 覆盖率也可能集中在低风险 fixture，漏掉真正的最坏路径。
- **建议**：每个 receipt 条目至少增加 `user_task`、`state/fixture`、`risk_class`、环境指纹（浏览器/字体/网络/时间）、机器 artifact 链接、Human reviewer/时间、判定与豁免理由。保留 visual、a11y、interaction、break、reduced-motion 五个独立 verdict，再生成总状态；任何关键 claim 缺人工签名、缺环境指纹或缺用户任务映射时，状态降级为 `incomplete`，不能显示为 pass。这样 Q3 的合并仍可追溯到用户影响，而不是只追溯到 CI 命令。

**观点 5：把“只能靠人判断”的风险写成显式闸门，避免自动化冒充体验证据**

- **发现**：原文将 visual blocker 设为 0、worst-case 覆盖率设为至少 95%，但没有定义未决人工判断、非确定性样本或回归后的状态协议（原文 L7；原文 Q1 L12）。在 UX 现场，内容层级、错误语气、焦点是否让人知道当前位置、动画是否诱发不适等，不能由单一阈值完整替代。
- **影响**：若把缺人工 review 当作“暂无失败”，系统会把未知风险误报为通过；若把所有波动都当成失败，团队又会疲于处理无意义噪声。最危险的是关键路径被降级成默认态、空态或错误态后仍获得绿灯，用户要自行猜测或重复操作。
- **建议**：在 receipt 中采用明确处置矩阵：
  - **只能人工 gate**：关键任务是否无需猜测、焦点顺序是否符合心智模型、错误/空态是否能指导恢复、翻译/截断是否改变含义、reduced-motion 是否仍舒适可用。
  - **必须 fallback**：字体不可用、网络不可用、未知 locale、部分数据或浏览器能力缺失；fallback 要保留任务入口、输入和可恢复动作，并有专门 fixture。
  - **必须 quarantine**：截图或交互结果非确定、环境指纹缺失、失败无法归因、artifact 与 commit/fixture 不匹配；隔离期间不得计入覆盖率。
  - **必须重评**：浏览器/字体/网络模拟/时间策略、关键文案、fixture、a11y 规则或组件行为变更后，重新跑受影响任务，不接受旧 receipt 继承。
  - **必须状态降级**：visual blocker 非零、关键 claim 未完成人工 gate、worst-case 覆盖率低于 95%、或 receipt 缺少核心关联字段；状态只能是 `blocked`/`needs-human-gate`/`incomplete`，不能是 pass。
  这套矩阵直接回答 Q1-Q3：机器负责可重复的事实，人负责体验含义，未决风险通过 fallback、quarantine、重评或降级显式暴露（原文 Q1 L12-L14）。

### 视角：O（运维 / SRE）
`视角来源: 跨会话独立Agent`

**观点 1**

**发现**：原文 Q2 要求隔离浏览器、字体、网络和时间噪声（原文 L13），成功判据又要求固定浏览器、字体、网络和 fixture 后可复跑（原文 L7）；但当前草案没有规定 runner 镜像/虚拟机、浏览器 revision、字体包校验、OS/locale/timezone、时钟与随机种子、DNS/网络 stub、fixture 版本或 runner 健康状态。对 SRE 来说，这还不是可部署、可监控的验证服务契约。

**影响**：同一 commit 可能因 runner 漂移产生不同截图或 a11y 结果，CI 会把基础设施故障误报成产品缺陷，或者在环境不完整时错误地产生 PASS。更危险的是，on-call 无法从 receipt 判断是代码回归、字体缺失、网络未命中 fixture，还是浏览器启动失败；重跑只能增加噪声，不能恢复可追溯性。

**建议**：把验证 runner 当作有版本的发布依赖：固定并记录容器/VM image digest、OS、浏览器及 driver revision、字体文件 hash、locale/timezone、冻结时钟、随机种子、网络策略和 fixture digest。网络默认 deny，测试只能访问版本化本地 stub/proxy；runner 启动先执行 self-test，失败时输出 `INFRA_UNVERIFIED`，禁止降级成产品 PASS。每次 run 的 receipt 都带环境 manifest hash，发布只允许使用已登记的 runner digest；对 runner 做 drift detector 和定期 canary，环境 hash 变化先阻断并重新基线。验收应包括同一 commit/fixture 连续复跑三次结果一致，以及人为替换字体、时钟或网络后能被 self-test 拦截。

**观点 2**

**发现**：原文 Q1 明确要求区分必须自动化的验证和必须保留 Human review（原文 L12），成功判据同时包含 visual blocker 为 0、worst-case 覆盖率至少 95%（原文 L7），但尚未定义哪些结果是硬门、哪些是人工门，也没有失败分类、告警条件或夜间被叫醒的边界。

**影响**：若所有像素差异都硬阻断，抗锯齿或字体渲染噪声会制造大量误报；若人工可以随意“确认通过”，则会形成不可审计的旁路。没有 on-call 触发条件时，真正的 visual/a11y blocker 可能被淹没在 flaky 重试里，或者每个无害的差异都触发 pager，线上运维成本不可控。

**建议**：将几何尺寸、overflow、键盘 focus 可达性/顺序、contrast 阈值、reduced-motion 禁止动画、fixture 覆盖率、receipt 完整性和 blocker 数量设为自动硬门；将生成式审美、语义是否自然、用户主观观感及法律判断明确标成 `HUMAN_REQUIRED`，由有身份和过期时间的 reviewer 审批，不能由自动重跑替代。统一状态至少包含 `PASS`、`FAIL`、`INFRA_UNVERIFIED`、`HUMAN_REQUIRED`、`QUARANTINED`、`DEGRADED`；只有 `PASS` 才能作为新鲜验证证据。建议对单次失败先做有限次数、固定环境的重跑，连续三次仍是基础设施型失败就转 `QUARANTINED` 并创建带 owner/expiry 的工单；代码硬门、a11y blocker、覆盖率低于 95%、receipt 缺失或 runner drift 才触发发布阻断和 pager，普通单例 flaky 不直接叫醒 on-call。

**观点 3**

**发现**：原文 Q3 要求把 visual/a11y/interaction/break/reduced-motion 结果合并为可追溯 receipt（原文 L14）；成功判据只列出 receipt 能关联 claim、threshold、命令、commit 和 fixture（原文 L7）。这给出了最小关联键，但没有定义 run identity、环境证据、结果状态、重试历史、artifact 哈希、reviewer、保留期限、重放命令或恢复目标。

**影响**：没有不可变的 receipt 记录，聚合报告可能把不同环境、不同尝试或不同 fixture 的结果拼在一起；截图存在但无法证明对应哪条 claim，失败恢复后也无法判断哪些证据已经丢失。对发布审计和事故复盘而言，“有一张截图”不等于“有一条可重放的验证链”。

**建议**：为每个 claim 生成稳定的 `run_id`/`claim_id`，receipt 至少包含 schema version、commit、fixture digest、命令、threshold、runner/environment manifest hash、browser/font/network/time 配置、attempt、开始/结束时间、状态、失败分类、artifact/log hash、parent job、reviewer 与 expiry。receipt 和截图/trace 存入带版本与校验和的持久化存储，聚合器只接受引用完整且 hash 可验证的子结果，并提供一条不改变输入的 replay command。把恢复目标写进运行契约：例如 runner 故障后 30 分钟内恢复一套 pinned runner，receipt 元数据的 RPO 不超过最近一次已完成 run；若对象存储或 runner 恢复失败，发布状态必须是 `DEGRADED`/`BLOCKED`，不能拿旧 receipt 伪装本次 PASS。定期做一次丢 runner、丢 artifact、重放 receipt 的恢复演练，并记录实际 RTO/RPO，而不是只写目标数字。

**观点 4**

**发现**：成功判据把 390/768/1440 三种宽度、键盘 focus、contrast、overflow、reduced-motion，以及长文本、空、错、1 条、1000 条、多语言全部放进同一可复跑集合（原文 L7）；其中 1000 条数据和多语言会明显放大截图、DOM、日志和执行时间。Q1–Q3 还要求自动化、噪声隔离和 receipt 聚合同时成立（原文 L12-L14），但没有容量预算、并发上限、队列超时、artifact 保留量或覆盖率分母。

**影响**：验证矩阵按 viewport、fixture、locale、字体和浏览器相乘后，可能使 PR 队列拥塞、runner 内存耗尽或 artifact 存储失控；团队为了恢复交付速度可能偷偷跳过最重 fixture，导致报告仍显示“95%”但分母已变。容量压力本身会变成可靠性故障，并削弱极端数据验证的可信度。

**建议**：把矩阵写成版本化 manifest，明确分子/分母和每个 shard，不允许静默 skip；PR 运行高风险最小集，全矩阵在合并/夜间运行，但两者都必须保留 1000 条、多语言等 worst-case 的定期覆盖，且不降低成功判据的 95% 门槛。先为团队设定可观测预算，例如 PR 验证 p95 不超过 10 分钟、全矩阵 p95 不超过 60 分钟、队列等待 p95 不超过 5 分钟，再用实际数据调整；超预算时通过按 fixture/viewport 分片、并发上限、immutable artifact 去重和有界保留策略处理，而不是减少断言。持续监控 queue time、run duration、CPU/memory、截图/trace 字节数、失败重试率、quarantine 数量和 coverage denominator；任一资源达到 80% 预算就预警，达到硬上限则标为 `DEGRADED` 并阻止伪造完整 receipt。

**观点 5**

**发现**：原文把固定环境后的复跑、极端 fixture、receipt、visual blocker=0 和 worst-case 覆盖率≥95%作为成功判据（原文 L7），但 Q1–Q3 并未声称生成式审美、人工判断、长期外部 provider 变化或新环境组合可被完全自动化解决（原文 L12-L14）。因此 remaining-risks 必须区分“机制可消除的运行噪声”和“只能被控制的判断/漂移风险”。

**影响**：若把稳定的 CI 结果误写成全面正确，团队会把人工门、fallback 或过期证据当作 PASS；provider 更新、字体/浏览器新版本、真实网络变化和用户对美感的分歧仍可能在固定矩阵外发生。其后果不是一次 flaky，而是长期错误自信，最终在发布或 on-call 时才暴露。

**建议**：将可由机制消除或显著收敛的风险列为硬门：runner/浏览器/字体/时钟/网络/fixture 漂移、receipt 缺字段或 hash 不匹配、覆盖率分母变化、overflow/contrast/focus/reduced-motion 等可计算断言。将不能彻底消除的风险列为受控状态：生成式审美和法律判断必须走 `HUMAN_REQUIRED`；provider 不可用时可用版本化 snapshot 做确定性回归，但必须标 `FALLBACK_FIXTURE`，不得宣称已验证 live provider；flaky case 进入带 owner、expiry 和替代计划的 `QUARANTINED`，到期未处理自动重新阻断；长期 provider drift 只能用固定周期 synthetic probe、provider/version 变更触发重评和状态降级监控来发现与控制，不能声称已被解决。浏览器、字体、provider 或网络策略变更时强制重基线；在未重评期间，旧 receipt 只能作为历史证据，发布状态降为 `DEGRADED`，不能作为当前 PASS。

## 主力AI 整合立场（主会话，非独立视角，低权重）

`视角来源: 同会话SubAgent(低权重)`

经过独立视角交叉整合，本子问题采用“机器 oracle + 人工体验 gate + 可重放 receipt + 风险状态机”的四层方案。

1. **验证输入先冻结。** 建立版本化 `fixture-manifest` 与 `verification-matrix`。矩阵 cell 使用 `viewport × fixture × locale × interaction × motion × browser-profile` 的稳定 key；fixture 记录 schema/version/hash、生成器、locale、时区和语义标签。分母是声明过的全部适用 cell，`not_applicable` 必须有规则和证据，不能由执行者临时补绿。优先覆盖 390/768/1440、空/错/长文本/1 条/1000 条/多语言、键盘路径、reduced-motion，以及 loading/超时/断网等降级场景（对应原文 L7、L12-L14）。

2. **验证环境分两条 lane。** `baseline` 使用锁定的浏览器/引擎、OS/容器、字体 hash、DPR、locale/timezone、冻结时钟、随机种子和网络 replay；`degraded` 使用可脚本化的字体缺失、延迟、断网、超时和部分响应，验证 loading、fallback、重试、取消和输入保留。环境指纹、fixture manifest hash、commit 和 provider/config 版本进入 receipt。指纹不匹配、artifact 缺失或网络录制失效只能进入 `blocked/quarantined`，不能重试到绿或计入覆盖率。

3. **自动化与 Human review 分界。** 自动硬 gate 覆盖 DOM/ARIA、focus 可达与顺序、contrast、overflow/断点、状态存在性、reduced-motion 行为、网络请求边界、fixture 完整性和已校准的几何/颜色阈值；已知 mutation fixture 必须能证明 oracle 能抓住溢出、低 contrast、隐藏 focus、截断和错态。视觉层级、信息是否易懂、错误恢复、翻译/截断是否改变含义、品牌/生成式审美和法律/合规判断保留 Human gate。人工项未签署时为 `human_review_required`，不能自动通过。

4. **receipt 与聚合规则固定。** 每条 evidence 至少包含 `claim_id/check_id/risk_class/fixture_hash/environment_fingerprint/oracle_version/threshold/command/commit/artifact_hash/observed/status/reviewer/expiry`；保留原始失败证据和有限重试历史。聚合优先级为：关键 `fail` 或 visual blocker → `FAIL`；环境/基础设施无法验证 → `BLOCKED`；人工项未结清 → `HUMAN_REVIEW_REQUIRED`；孤立且不可归因的结果 → `QUARANTINED`；全部适用 cell 通过、visual blocker=0、worst-case 覆盖率 ≥95% 且人工项结清 → `PASS`。receipt schema 只允许可追加演进，旧 receipt 不按新阈值静默重算。

5. **落地顺序与责任。** P0 由 B/T/O 冻结 manifest、runner、字体/浏览器/网络锁和 receipt schema；P1 由 T/前端实现自动 oracle、mutation fixture 与双 lane；P2 由 U/C/设计 reviewer 完成关键任务、视觉语义和降级体验 gate。每一项缺 cell、缺 artifact、缺人工签名或状态无法解释都不算完成；verification 只证明“在声明环境和契约下发生了什么”，不替代产品方向或 adapter 选型。

**剩余风险控制：** 可控的环境噪声、可定义的几何/a11y/interaction/reduced-motion 缺陷由锁定运行环境、fixture hash、自动 oracle 和 receipt 消除或大幅收敛；生成式审美、语境化体验、法律判断只能由人工 gate 约束；浏览器/字体/provider 长期漂移在升级或固定重评周期触发全矩阵重跑，旧 receipt 降为 `stale/revalidation_required`，旧基线仅作 fallback；无法归因的结果进入 quarantine，不计覆盖率。

## Human 对 Agent X 的拍板

| 轮次 | 视角 | 隔离方式 | Human 拍板 | 是否 conclusion | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 | B | 同 provider 跨会话 | 待拍板 | 否 | |
| 2 | C | 同 provider 跨会话 | 待拍板 | 否 | |
| 3 | A | 同 provider 跨会话 | 待拍板 | 否 | |
| 4 | T | 同 provider 跨会话 | 待拍板 | 否 | |
| 5 | U | 同 provider 跨会话 | 待拍板 | 否 | |
| 6 | O | 同 provider 跨会话 | 待拍板 | 否 | |

## conclusion（含沉淀指令）

- **子问题结论：** 确定性验证不是“一张截图通过”，而是由版本化输入矩阵、锁定环境、可校准的自动 oracle、用户任务级 Human gate 和可重放 receipt 组成的证据链；它能可靠证明声明环境中的几何、a11y、交互、断点和动效约束，但不宣称审美、法律或长期 provider 漂移已被解决。
- **解法：** 先以 `fixture-manifest + verification-matrix + environment_fingerprint` 固定输入，再运行 baseline/degraded 双 lane；自动硬 gate 处理可形式化断言，Human gate 处理视觉语义与用户理解；receipt 记录 claim 到 artifact 的完整链路，聚合时对 FAIL/BLOCKED/HUMAN_REVIEW_REQUIRED/QUARANTINED 采取严格传播。visual blocker=0 与 worst-case 覆盖率 ≥95% 只有在分母、缺失 cell、人工签名和环境状态均满足时才允许 PASS。
- **remaining-risks 控制：** provider/浏览器/字体漂移触发重评并将旧证据标 stale；环境不一致或无法归因的失败进入 quarantine；人工无法及时判断则保持 human-review/block，不以重试或放宽阈值消除；旧基线仅作可回滚 fallback，不能冒充新环境通过。

- **沉淀指令：**
  - 改哪些 PRD / ADR / 文档：新增验证契约 ADR（matrix、双 lane、oracle 分层、receipt schema、聚合状态机）与 Experience Version 验收表；将 visual blocker=0、95% 分母定义、Human gate 和 revalidation 规则回填主方案。
  - 跨子文档约束登记：`sub-01` 的 artifact/receipt canonical owner；`sub-02` 的 verification gate 先于自动修改；`sub-03` 的 provider/环境 fingerprint 与 adapter 回退；`sub-04` 的敏感截图与 provenance 不得绕过 receipt。
  - 待删临时脚手架：本子文档的 briefings 和 viewpoints 过程文件，待 `zj-docs-ontology` 分类；在 Human 确认沉淀前保留本讨论目录。
- **状态协议：** DONE_WITH_CONCERNS

