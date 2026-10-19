视角来源: 跨会话独立Agent

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
