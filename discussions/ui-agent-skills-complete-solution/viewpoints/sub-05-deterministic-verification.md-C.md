视角来源: 跨会话独立Agent

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
