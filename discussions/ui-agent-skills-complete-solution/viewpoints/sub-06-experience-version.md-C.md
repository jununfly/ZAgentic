视角来源: 跨会话独立Agent

**观点 1**

**发现**：原文把第一版范围描述为“锁定一个 React/Next.js 表单或审批流”，并要求列清纳入 skill 的输入、输出、禁止事项、依赖、停止条件和失败 fixture，但没有写目标使用者、要替代的现有工作方式、资源上限或明确的 out-of-scope 清单（原文 L6-L7）。对产品而言，这还不是可被用户理解和比较的 scope manifest。

**影响**：没有用户、任务和替代方案，团队很容易把“纳入更多 skill/adapter”误认为价值增加；同一个表单既可能服务熟悉 React 的开发者，也可能服务只关心审批结果的产品人员，两者对返工、决策时间和可接受的人工介入有不同权重。未写出的边界会让每个 Wave 都有理由扩张，最后无法回答“凭什么比 direct-prompt 更值得用”，也无法判断一个失败是产品不值，还是实现没有完成。

**建议**：在 Wave 0 先由 Human gate 批准一份不可变的 scope manifest，至少包含：目标 persona 与一个可观察的 job-to-be-done；唯一 canonical flow（表单或审批流二选一）；纳入的 skills/adapters 及其契约；明确排除的多页面、跨框架、发布部署、rollout、version-skew；资源上限；direct-prompt 与当前人工/脚手架流程的对照；返工率、用户决策时间、escaped UI defects 的定义、采集人和阈值。任何未列入 manifest 的功能只能进入 `QUARANTINED`，不计入本轮收益；manifest 发生变化必须回到人工 gate 重新评估，而不是在 Wave 中隐式吸收。

**观点 2**

**发现**：Q2 只提出“Wave 0–3 的依赖顺序、责任、退出条件和失败回退是什么”，原文没有给出四个 Wave 各自向用户交付什么、由谁判断价值或失败后恢复到哪条可用路径（原文 L10-L14）。这说明当前 Wave 名称还是编排占位符，不应被当成已经成立的产品路线。

**影响**：如果 Wave 只按工程产物推进，可能在尚未证明用户愿意采用前就投入 adapter 生态；如果 Wave 只按“代码能跑”推进，又会把一条不可解释的生成链误报成体验版本。失败时没有 fallback，团队会继续修补同一条链路，无法区分“skill 设计错了”“用户价值不成立”和“运行环境偶发失败”。

**建议**：把 Wave 定义成可回退的价值闸门：Wave 0 冻结 persona、canonical flow、scope manifest，并采集可重复的 baseline；Wave 1 只实现该 flow 必需的 skill/adapter 合同和失败 fixture，人工确认产物仍符合用户任务；Wave 2 执行三次成对运行并复核返工、决策时间和 escaped defect；Wave 3 只做 graduation review，不承诺 release/rollout。每个 Wave 的退出记录都必须包含证据、责任人和下一状态；失败时默认 fallback 到 direct-prompt 或现有人工流程，疑似偶发/未解释的 skill 或 adapter 进入 `QUARANTINED`，而不是让整条 Experience Version 带病前进。Wave 3 若指标冲突或证据不足，应 `RE-EVALUATE` 或状态降级为 `BASELINED`/`BLOCKED`，不能用“已完成四个 Wave”替代用户价值判断。

**观点 3**

**发现**：成功判据要求“至少三次完整运行相对 direct-prompt baseline 在返工率、用户决策时间和 escaped UI defects 上改善”（原文 L7），但没有规定 paired run 的任务、fixture、人员、提示词、模型/provider、顺序和缺陷严重度是否相同。仅有“三次”这个次数，不能证明改善来自 Experience Version。

**影响**：如果增强组拿到更容易的表单、更多上下文或更熟练的操作者，返工率和决策时间的下降会是选择偏差；如果一次运行漏记 UI defect，三次都“改善”也可能仍然把高伤害缺陷交给用户。直接 prompt 是必要基线，却不一定代表当前团队的最佳替代流程；没有第二个现实对照，就无法判断系统是在创造价值，还是只胜过一个刻意弱化的起点。

**建议**：把每次运行固定为同一任务意图、同一 fixture、同一验收约束和同一资源预算的 paired run，并记录执行者经验、提示词/上下文、模型与 provider、开始结束时间、人工介入、返工次数、决策正确性和按严重度分层的 escaped UI defects；顺序应交错或随机化，避免学习效应。保留 direct-prompt 作为强制基线，并以当前人工/脚手架流程作次级现实基线；Wave 0 的人工 gate 先确认三路任务可比。graduation 至少要求三次配对均完成、主要指标相对预设阈值改善且无 critical defect/决策错误，同时由 Human 抽查原始产物和 trace；缺少一对、指标定义变更或结果无法归因时，回退到 baseline 并触发重评，不得补跑一个更有利的样本来凑“三次”。

**观点 4**

**发现**：原文明确要求本轮“明确不承诺 release/rollout/version-skew”（原文 L7），但没有把这一限制转成用户可见的采用状态，也没有说明不同浏览器、框架版本或 adapter 版本下，现有三次运行的证据是否仍可消费。对于生态产品，别人是否敢在自己的项目里采用，取决于这种边界是否清晰，而不只是一次 demo 是否成功。

**影响**：若没有状态降级，`graduated` 很容易被下游理解成“可发布”或“跨版本稳定”；一旦 React/Next.js、provider 或 adapter 变化，旧证据会产生虚假的安全感。版本漂移不能靠同一组三次样本永久覆盖，既不能承诺本轮解决，也不能静默把旧的绿色结果继续当作当前结果。

**建议**：把 graduation 命名为“本 scope、固定环境、固定版本下的验证毕业”，并在产物中显式标注 `NOT_FOR_RELEASE`、适用框架/provider/adapter 版本和 expiry。环境或依赖发生变化时，旧状态自动降级为 `STALE`/`RE-EVALUATE`；无法判断是兼容性问题还是用户价值问题时先 `QUARANTINED` 受影响的 adapter，消费方 fallback 到最近有效的 baseline 或人工流程，但必须标明不是当前环境的 PASS。跨版本、跨框架和 rollout 应作为后续独立 scope，重新走 manifest、paired run 和 Human gate，而不是从本轮 graduation 推导出来。

**观点 5**

**发现**：Q3 已经警惕“代码能跑冒充成功”（原文 L14），而原文成功判据仍把运行结果集中表达为三项改善（原文 L7），没有写用户是否完成正确决策、是否愿意重复使用、人工介入是否反而增加了认知负担，也没有规定这些指标冲突时谁有否决权。

**影响**：代码可运行和平均耗时变短，都可能掩盖错误批准、错误拒绝、用户不信任或把复杂度转移给 reviewer 的情况。尤其审批流中，错误决策比多一次返工更严重；把所有风险折算成一个平均值，会让少量高伤害案例被“总体改善”冲掉。用户研究与产品判断不能完全由自动化 receipt 代替。

**建议**：graduation gate 增加产品安全阈值：任务完成必须保持决策正确性，critical/high UI defect、错误审批/拒绝、未解释的人工 override 和用户明确不愿复用均可否决；按 persona/任务难度分层看指标，不只看平均数。自动化可以计算返工、耗时和已定义的 defect，但 Human gate 必须抽查最终界面、关键状态和用户决策理由，并记录 reviewer、证据、override 原因和有效期。人工无法判断、证据缺失或用户反馈互相冲突时，状态只能 `BLOCKED`/`RE-EVALUATE`，fallback 到 direct-prompt/人工流程，不能以“无阻塞”或“代码成功”替代人工判断。

**观点 6**

**发现**：原文把“纳入的 skills/adapters、Wave 顺序、资源边界和毕业标准”列为本子问题要锁定的对象，同时又声明“不重新设计 artifact、adapter 或安全机制”（原文 L6）；但没有说明哪些能力是这个垂直切片不可替代的核心价值，哪些只是生态扩展，也没有给出新增 skill 的采用门槛。

**影响**：产品会面临两种相反风险：纳入过少，用户只能得到一个不能覆盖真实表单/审批任务的局部 demo；纳入过多，Experience Version 变成技能市场或 adapter 平台，资源与学习成本上升，三次运行无法解释到底是哪项能力带来改善。缺少采用门槛还会让一个“生态上很热门”但没有失败 fixture、停止条件或稳定输出的 skill 进入主路径。

**建议**：为 scope manifest 增加 capability selection 表：每个 skill/adapter 写清它对应的用户痛点、不可替代性、输入输出契约、失败 fixture、依赖、停止条件、资源预算和移除后的 fallback；只允许能直接服务 canonical flow 的最小集合进入 Wave 1。新增候选先在隔离环境 `QUARANTINED`，用独立 paired run 与现有集合比较；若没有增量用户价值、带来决策错误或资源超预算，就降级为 `EXCLUDED` 并记录重评条件。只有通过三次完整运行、人工体验 gate 和版本适用性检查的能力才可标 `GRADUATED`；本轮不得把“可被发现/可安装”误写成“已验证可采用”。
