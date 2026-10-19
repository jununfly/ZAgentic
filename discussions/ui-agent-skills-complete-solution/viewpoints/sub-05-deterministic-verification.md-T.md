视角来源: 跨会话独立Agent

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
