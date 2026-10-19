# 子问题：Experience Version 的范围、顺序与 graduation

## 上下文

- **所属主文档：** [../MASTER.md](./MASTER.md)
- **本子问题独立性：** 只锁定第一版垂直切片、纳入的 skills/adapters、Wave 顺序、资源边界和毕业标准；不重新设计 artifact、adapter 或安全机制。
- **成功判据：** 锁定一个 React/Next.js 表单或审批流；每个纳入 skill 有输入/输出/禁止事项/依赖/停止条件/失败 fixture；至少三次完整运行相对 direct-prompt baseline 在返工率、用户决策时间和 escaped UI defects 上改善；明确本轮不承诺 release/rollout/version-skew。
- **声明必需角色集：** B,C,A,T,U,P

## 待讨论问题（scope 草案）

- Q1：Experience Version 的最小可交付切片和不应纳入的内容是什么？
- Q2：Wave 0–3 的依赖顺序、责任、退出条件和失败回退是什么？
- Q3：如何设计 baseline、三次运行和 graduation criteria，避免“代码能跑”冒充成功？

## Agent viewpoints（独立视角 — 须跨会话独立 Agent）

### 视角：B（技术经理 / 可落地）
`视角来源: 跨会话独立Agent`

**观点 1**

**发现：** 原文把 Experience Version 限定为“第一版垂直切片”，要求锁定一个 React/Next.js 表单或审批流，同时只锁定纳入的 skills/adapters、Wave 顺序、资源边界和毕业标准；还明确本轮不重新设计 artifact、adapter 或安全机制（原文 L6-L7）。但目前没有给出可执行的 scope manifest，也没有写出纳入项的数量上限或变更规则。

**影响：** 没有 manifest 时，任何新增 skill、adapter 或第二条用户路径都可能被解释成“仍属于首版”，关键路径、评估分母和资源预算会一起漂移；最后即使三次运行完成，也无法证明完成的是同一个切片。

**建议：** 在 Wave 0 设一个硬 scope gate，由 B 担任 DRI，落一页 manifest：固定一个 route、一个输入/输出数据形状、纳入 skills/adapters 清单、明确不做的 artifact/adapter/security redesign、负责人、预算上限和变更审批人。首版建议最多纳入关键路径所需的 3 个 skill 和 1 个 adapter；新增项必须重新标记为下一版或触发整套 baseline 重跑。验收标准是：另一名工程师能依据 manifest 判断某项改动属于本版还是超范围，且 scope 变更不会静默进入正在进行的三次运行。

**观点 2**

**发现：** Q2 只提出 Wave 0–3 的依赖顺序、责任、退出条件和失败回退问题，原文没有预先给出任何 wave 的 owner、前置条件或失败处理（原文 Q2，L13）。

**影响：** 如果先做实现、后补 fixture 或 baseline，Wave 2 的“完整运行”就会混入不可比较的数据；如果失败没有明确回退，团队会把局部修补误当成推进，形成无止境的首版扩张。

**建议：** 采用以下可执行顺序，并让每个 Wave 的退出证据成为下一 Wave 的输入：

- Wave 0（B+T）：冻结 scope manifest、case ID、失败 fixture、baseline 记录格式和资源预算；退出条件是 manifest 已签字且 direct-prompt baseline 至少能在同一环境跑通一轮。失败则回到 scope/fixture 修订，不进入实现。
- Wave 1（实现 owner）：接入清单内 skills/adapters，并逐项完成输入、输出、禁止事项、依赖、停止条件和失败 fixture；退出条件是每项都有可执行检查。某项不合格就 quarantine 该项，先用通过项或 direct-prompt fallback，不把它算作整片通过。
- Wave 2（B+T+U）：做三次 paired run，每次都包含同一 case 集的 baseline 与 Experience Version，并保存返工、决策时间和 escaped UI defects 的原始记录；缺输入、人工补丁或中途失败的运行不计数，修复后补跑。
- Wave 3（B 召集 C/A/T/U/P）：只审 graduation packet，不扩展功能；退出条件是预注册的三项指标门槛、无阻断缺陷、回退步骤和风险状态均有证据。未通过则保持 PILOT 或 QUARANTINED，不得以“代码能跑”替代退出条件。

**观点 3**

**发现：** 原文成功判据要求“至少三次完整运行”相对 direct-prompt baseline 在返工率、用户决策时间和 escaped UI defects 上改善，Q3 进一步要求避免“代码能跑”冒充成功（原文 L7、Q3，L14）；但尚未定义 paired run 的 case、分母、计时起止、缺失数据和阈值。

**影响：** 没有预注册的测量口径，团队可以通过换题目、改变 prompt、漏报失败或只展示成功路径来制造改善；三次运行也可能只是三次不相同的演示，不能支持 graduation。

**建议：** 在 Wave 0 先锁定同一 case 集、输入、环境、provider/model/config 记录和运行脚本；三次运行各自形成一对“direct-prompt baseline / Experience Version”，禁止临时改 prompt 或手工修输出后再计入。建议把指标定义写入验收表：返工率 = 需要再次修改的任务数/完成任务数；决策时间 = 用户看到可选结果到作出接受/修改决定的时间；escaped UI defects = 通过首轮验收后才发现的 UI 缺陷率。建议的初始门槛是返工率和决策时间相对 baseline 各至少改善 20% 和 15%，escaped UI defects 不得在任何一次 paired run 中恶化且汇总值至少改善 20%；baseline 为零或样本不足时，改走人工审查，不强行套百分比。任一完整性检查失败，整次运行标记 invalid 并补跑，而不是用部分数据凑满三次。

**观点 4**

**发现：** 原文给出了成功指标和“本轮不承诺 release/rollout/version-skew”的边界，但没有写出谁对最终判定负责、什么证据包算完成，也没有在 Human 拍板表中形成任何已拍板记录（原文 L7、L56-L63）。

**影响：** graduation 很容易退化为“工程师说完成、评审者凭印象同意”；发生指标冲突或回退时，没有单一负责人决定继续、补跑还是降级，责任和时间都会被摊薄。

**建议：** 建立 RACI 和状态机：B 是 DRI；T 维护运行完整性、缺陷和指标计算；U 维护用户决策时间的测量协议；P 负责排期和拍板记录；A 只审边界与兼容性；C 审用户价值。状态至少包含 DRAFT → READY → PILOT → GRADUATED，并允许回到 QUARANTINED；任何 S1/S2 UI 缺陷、关键 fixture 失败或指标回归都阻止升级。graduation packet 必须含 scope manifest、三次 paired run 原始日志、指标表、缺陷清单、fallback 演练记录和 Human gate 签名；缺一项就不算“做到什么程度算完”。

**观点 5**

**发现：** 原文将“资源边界”列为本子问题必须锁定的内容，但没有给出人力、时间或协调成本；同时声明必需角色集包含 B、C、A、T、U、P，且六轮 Human 拍板仍全部为“待拍板”（原文 L6、L8、L54-L63）。

**影响：** 若不设 time-box，六个角色会在实现过程中反复重开范围；资源消耗和机会成本无法与收益比较，Wave 3 可能在没有新增证据的情况下继续消耗工程时间。

**建议：** 在 Wave 0 把预算写成上限而不是口头承诺：实现与接入不超过 5 个工程人日，fixture/测量协议不超过 2 个协作人日，三次运行与 graduation review 不超过 2 个工程人日（不含等待用户参与的日历时间）。B 每个 Wave 结束时记录实际消耗；超过上限即暂停新增功能，选择拆小切片、减少纳入项或降级为实验性 PILOT。C/A/T/U/P 只在各自证据包需要时进入 gate，避免把“必需角色集”误解为每个人都要持续参与施工。

**观点 6**

**发现：** 原文明确本轮不承诺 release、rollout 和 version-skew，只要求完成首版垂直切片和毕业标准（原文 L6-L7）；原文没有声称生成式审美、法律判断或长期 provider 漂移已被解决，且结论区仍是“待讨论”（原文 L65-L73）。

**影响：** 若把一次三运行结果解释为长期质量保证，会把未解决的主观审美、合规判断和 provider 漂移风险伪装成技术完成；这会使错误结果进入真实流程，也会掩盖维护成本。

**建议：** 把 remaining-risks 分成可由机制控制和只能由治理控制两类。机制可消除或强约束的是：必填输入/输出缺失、禁止事项未执行、停止条件未触发、失败 fixture 未覆盖、指标分母不一致、运行日志缺失；这些由 schema/check、fixture、日志和状态机自动挡住。生成式审美仍需人工 UX gate，法律判断仍需人工合规 gate，长期 provider/model 漂移仍需人工复评，均不能宣称被彻底解决。对失败 skill/adapter 使用 quarantine，对用户路径保留 direct-prompt fallback；provider/model/config 或 skill 变更、关键缺陷和指标回归时，按状态机将 GRADUATED 降为 PILOT/QUARANTINED，并至少每 30 天或每次上述变更重新评估。这样首版的 graduation 只代表受限切片在已声明条件下通过，不代表 release/rollout/version-skew 具备承诺。

### 视角：C（产品专家 / 用户价值·生态竞品）
`视角来源: 跨会话独立Agent`

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

### 视角：A（架构师 / 约束）
`视角来源: 跨会话独立Agent`

**观点 1：scope manifest 必须是第一版垂直切片的唯一边界契约**

- **发现**：原文把本轮职责限定为“第一版垂直切片、纳入的 skills/adapters、Wave 顺序、资源边界和毕业标准”，同时明确“不重新设计 artifact、adapter 或安全机制”（原文 L6）；成功判据又要求锁定一个 React/Next.js 表单或审批流，以及每个纳入 skill 的输入、输出、禁止事项、依赖、停止条件和失败 fixture（原文 L7）。但 Q1 只提出“最小可交付切片和不应纳入的内容”，没有定义一个可冻结、可追溯的 scope manifest（原文 L12）。
- **影响**：没有 manifest，纳入项、资源边界和“不承诺 release/rollout/version-skew”的排除项会散落在讨论文字中；Wave 推进时很容易把临时适配、额外 skill 或兼容性工作偷偷算进 Experience Version，导致后续三次运行无法判断是在评估同一个版本。边界变动还会使前后运行失去可比性。
- **建议**：先建立并人工批准一份 manifest，至少固定 `slice_id`、React/Next.js 路由和仓库提交、纳入 skill/adapter 清单、每个 skill 的五类契约字段与失败 fixture、资源预算、owner、明确的 out-of-scope，以及 evidence/run ID。Wave 0 之后 manifest 只允许追加证据，不允许静默改边界；任何新增或删除纳入项都必须人工 gate，并触发重评，当前状态至少降为 `candidate`，不能沿用原 graduation 资格。

**观点 2：skill 与 adapter 的接口要可演进，但不能借“不承诺 version-skew”突破兼容边界**

- **发现**：原文一方面将纳入 skills/adapters 和每个 skill 的输入/输出/依赖列为本轮范围（原文 L6-L7），另一方面明确本轮不承诺 release、rollout、version-skew（原文 L7），并声明不重新设计 artifact、adapter 或安全机制（原文 L6）。这给出了范围限制，却没有给出跨 skill、adapter、主流程之间的稳定接口不变式。
- **影响**：如果把“没有 version-skew 承诺”理解成可以任意改 schema，adapter 输出可能在同一垂直切片内发生隐式漂移；上游 skill 能跑而下游表单状态、校验或审批动作已不再可解释。相反，若提前做全局兼容层，又会越过“不重新设计 adapter”的范围，形成第一版的隐性平台化负担。
- **建议**：在 manifest 中固定本切片内的最小契约：输入/输出 schema、必填与未知字段策略、停止条件、错误分类和 adapter 版本/提交。只允许向后兼容的增量字段；破坏性变化必须停在人工 gate，不能进入已登记 run。违反契约的 skill/adapter 输出进入 quarantine，优先 fallback 到上一个已登记的 adapter 或 direct-prompt baseline；若无安全 fallback，则状态降级并重评，不以局部“代码能跑”放行。

**观点 3：Wave 0–3 应按依赖关系形成单向晋级，每个 Wave 都要有可回退的状态边界**

- **发现**：原文将“Wave 0–3 的依赖顺序、责任、退出条件和失败回退”列为独立待讨论问题（原文 L13），说明顺序、责任和失败处理尚未被锁定；同时成功判据要求每个纳入 skill 具备完整契约与失败 fixture（原文 L7）。
- **影响**：若先做端到端演示再补 manifest、fixture 或接口契约，后续失败无法定位是范围漂移、skill 不合格还是 adapter 集成问题；若 Wave 之间没有状态边界，失败项会被下一 Wave 吞掉，最后把未完成的证据包装成毕业。
- **建议**：采用单向依赖并写入 manifest：Wave 0 冻结 scope manifest、资源边界、fixture 和 direct-prompt baseline；Wave 1 逐个验收纳入 skill 的输入/输出/禁止事项/依赖/停止条件；Wave 2 只在 Wave 1 全部通过后接入 adapter，跑通同一个 React/Next.js 垂直流；Wave 3 冻结版本并执行三次 paired run、证据审计和 graduation gate。每一 Wave 指定 owner 与退出证据；失败只回退到最近一个已通过 Wave，单个坏 skill/adapter quarantine，不得通过扩大范围绕过退出条件。

**观点 4：baseline 必须是可复现的 control manifest，而不是一句“direct-prompt”或一次成功演示**

- **发现**：原文要求“至少三次完整运行相对 direct-prompt baseline”比较返工率、用户决策时间和 escaped UI defects（原文 L7），Q3 还明确要求避免“代码能跑”冒充成功（原文 L14）。但原文没有规定 baseline 的任务集合、代码快照、模型/工具预算、人员、顺序或指标口径。
- **影响**：如果 baseline 每次换任务、换提交或换资源预算，三次差异可能来自输入难度而不是 Experience Version；如果只保留 Experience 的成功样本，返工率和 escaped defects 会被选择偏差掩盖。这样即便数值看似改善，也不能证明同一切片相对 direct-prompt 有架构上的收益。
- **建议**：在 Wave 0 为每个任务生成固定的 baseline manifest：任务/fixture ID、仓库提交、环境、模型与工具预算、参与者、起止事件定义和 defect 分类。每次运行都对同一任务做成一对 control/experience，预先固定配对和顺序规则，保留完整日志；三次 paired run 必须各自包含 baseline 与 Experience，不能用一次 baseline 去支撑三个不同版本。Experience 失败时记录失败原因并 fallback 到 baseline，但该 pair 仍须标为失败或不计入毕业，不能删除失败样本。

**观点 5：graduation 是证据状态转换，不是“流程跑通”的别名**

- **发现**：原文的成功判据同时要求 React/Next.js 表单或审批流、skill 契约、失败 fixture、至少三次完整运行以及三项指标相对 direct-prompt 的改善（原文 L7）；Q3 明确要求设计 graduation criteria 以防止“代码能跑”冒充成功（原文 L14）。但原文尚未定义三次运行的完整性、三项指标的汇总方式、阈值或回归处理。
- **影响**：没有预注册的 graduation gate，团队可以用“平均改善”掩盖某一次未完成、严重 escaped UI defect 或某一项指标恶化；也可能把垂直切片的候选状态误报为可 release。尤其原文已经明确本轮不承诺 release/rollout/version-skew（原文 L7），因此 Experience graduation 与产品发布资格必须保持分离。
- **建议**：在任何运行前人工批准阈值和聚合规则：三次 pair 均有完整 control/experience 证据；返工率、用户决策时间、escaped UI defects 三项都按同一预注册口径改善，且严重 UI defect 不得被平均值抵消。graduation 只产生 `graduated-experience` 状态，不产生 release/rollout/version-skew 权限；缺一项证据、出现不可接受回归或阈值未定时，状态保持 `candidate`/`needs_context`。escaped defect 的严重度判断必须人工 gate，无法判定时 quarantine 并重评。

**观点 6：变更、失败和证据缺口必须显式状态降级，不能靠口头 fallback 掩盖**

- **发现**：原文要求 skill 提供停止条件和失败 fixture（原文 L7），要求讨论 Wave 失败回退（原文 L13），并把三次完整运行与 escaped UI defects 纳入成功判据（原文 L7）；但没有规定失败运行、范围变更、证据缺失或人工无法判断时的状态协议。原文还明确本轮不承诺 release/rollout/version-skew（原文 L7）。
- **影响**：没有状态机时，fallback 可能被误记为成功路径，quarantine 可能被重新纳入汇总，或一次 adapter 变更后继续复用旧的 graduation 结果；这会破坏长期一致性和跨 run 可比性，也会把尚未解决的风险传递到发布阶段，尽管发布本来就不在本轮承诺内。
- **建议**：至少区分 `candidate`、`wave-passed`、`quarantined`、`needs-re-evaluation`、`graduated-experience` 和 `downgraded`。契约破坏、未完成 pair、缺 fixture/日志、严重 escaped defect 只能通过 quarantine、fallback、人工 gate 或状态降级处理；scope manifest、skill/adapter schema、模型/工具预算、仓库提交或任务集发生影响可比性的变化时，强制重评并作废旧 graduation 证据。任何自动化流程只能建议状态，最终 graduation 与从 quarantine 恢复必须人工 gate。

### 视角：T（测试 / 质量）
`视角来源: 跨会话独立Agent`

**观点 1：scope manifest 必须先成为可执行的测试边界**

- **发现**：原文把本子问题限定为锁定“第一版垂直切片、纳入的 skills/adapters、Wave 顺序、资源边界和毕业标准”，并明确“不重新设计 artifact、adapter 或安全机制”（原文 L6）；同时成功判据要求每个纳入 skill 具备“输入/输出/禁止事项/依赖/停止条件/失败 fixture”（原文 L7）。但当前 scope 草案没有给出 manifest 的字段、冻结时点、fixture 完整性判定或超范围行为的处置。
- **影响**：若没有冻结的 manifest，测试会在运行中偷偷扩大纳入范围，导致 baseline 与 Experience Version 比较的对象不一致；缺少失败 fixture 还会把“异常路径没有验证”误报成“代码能跑”。这会直接污染返工率、用户决策时间和 escaped UI defects 三项证据，且无法判断失败来自 skill、adapter、环境还是测试数据。
- **建议**：在 Wave 0 产出并签名一份 scope manifest，至少固定切片入口、纳入/排除的 skill 与 adapter、每个 skill 的六项契约字段、fixture ID/预期失败类型、依赖版本、浏览器/数据/权限前提、指标采集规则和 owner。manifest 变更必须触发重评；未登记的能力只能标记为 out-of-scope，不能进入 graduation 分母。验收条件是：每个纳入项都能映射到一个成功 fixture、一个失败 fixture 和一条可复现命令；任一缺项则 Wave 0 不退出。

**观点 2：Wave 0–3 应按“证据先于实现”设置退出和回退**

- **发现**：原文只提出“Wave 0–3 的依赖顺序、责任、退出条件和失败回退是什么”（原文 L13），没有给出顺序本身；而成功判据要求至少三次完整运行并相对 direct-prompt baseline 改善（原文 L7）。因此不能把四个 Wave 仅当作开发阶段，也不能用某个页面能运行替代 Wave 退出证据。
- **影响**：没有逐 Wave 的可复现退出条件，会出现先跑体验、后补契约和 baseline 的顺序错误；一旦后补测量，前面的“改善”无法追溯，失败时也无法知道应回退实现、回退 scope 还是暂停整条 Experience Version。跨 Wave 的回归风险会在最后一次运行才集中暴露。
- **建议**：采用以下测试闸门和责任映射：Wave 0 由 scope/测量 owner 负责，冻结 manifest、fixture、随机化/配对方案和 direct-prompt baseline，缺一项即回到准备态；Wave 1 由 skill/adapter owner 负责，逐项验证输入/输出/禁止事项/依赖/停止条件及失败 fixture，契约或适配失败时只能 fallback 到已知稳定路径并记录原因；Wave 2 由垂直切片 owner 与测试 owner 负责，完成端到端 UI 流程、异常路径和人工体验 gate，发现 flaky fixture 或非确定性 adapter 时 quarantine，不得吞掉失败；Wave 3 由独立验收 owner 负责，执行三次 paired run、回归和 graduation review，任一硬闸门失败则回到最近一个通过的 Wave 或将状态降为 `NEEDS_CONTEXT`。每个 Wave 的退出记录都应包含运行 ID、版本、fixture、结果和未关闭风险。

**观点 3：baseline 和三次 paired run 必须先注册比较协议，才能证明改善**

- **发现**：原文要求“至少三次完整运行相对 direct-prompt baseline 在返工率、用户决策时间和 escaped UI defects 上改善”（原文 L7），并把 Q3 明确写成“如何设计 baseline、三次运行和 graduation criteria，避免‘代码能跑’冒充成功”（原文 L14）。原文没有规定一对运行的任务、人员、输入、时间预算、环境、顺序和指标口径如何保持可比。
- **影响**：如果 baseline 与 Experience Version 使用不同任务难度、不同 fixture、不同浏览器状态或不同时间预算，三项指标的变化可能只是实验偏差；若把三次单独操作误作三次完整运行，样本不足以覆盖失败分支。尤其是用户决策时间会受学习效应影响，返工率会受任务复杂度影响，escaped UI defects 又依赖运行后的人工复查，三者不能只靠日志中的“成功”字段推断。
- **建议**：在 Wave 0 预注册 paired-run protocol：每次 run 使用同一批已锁定任务/fixture、相同角色权限和环境快照，分别执行 direct-prompt 与 Experience Version，记录运行前后版本、输入、时长、用户决策起止事件、返工定义、缺陷严重度及复核者；对任务顺序做 counterbalance，避免三次都由熟悉 Experience Version 的同一顺序驱动。三次 run 必须各自完整覆盖成功与失败 fixture，并保留原始事件和屏幕/DOM 证据；缺事件、换环境或中途人工修补的 pair 标为 invalid，不能补算为改善。

**观点 4：graduation 是质量证据闸门，不是“代码能跑”标签**

- **发现**：原文成功判据把“锁定一个 React/Next.js 表单或审批流”、skill 契约和“三次完整运行相对 direct-prompt baseline 的改善”放在同一组，并明确本轮“不承诺 release/rollout/version-skew”（原文 L7）；Q3 又要求避免“代码能跑”冒充成功（原文 L14）。这意味着 graduation 至少要同时证明范围、契约、行为和对照指标，而不能只依赖构建或冒烟通过。
- **影响**：若只设自动化构建/端到端 happy path 作为毕业条件，空输入、异常响应、重复提交、权限边界、长文本、并发点击和 adapter 超时等边界失败会以 escaped UI defects 形式逃逸；若三次运行中有一次严重回归仍允许毕业，平均改善会掩盖不可接受的单次事故。由于不承诺 release/rollout/version-skew，毕业也不能被解释成生产发布许可。
- **建议**：将 graduation 设为联合闸门：scope manifest 完整且无未评估变更；所有纳入 skill 的六项契约和失败 fixture 通过；React/Next.js 目标流的成功、失败、空/异常/极值、重复/并发和权限场景有可复现证据；三次 paired run 全部有效，三项预注册指标在聚合结果上优于 direct-prompt baseline，且任一 run 不得出现未接受的 critical/high escaped UI defect 或不可解释的指标恶化；人工复核确认用户决策时间的起止事件和视觉/交互缺陷。任一条件不满足只能保持候选态或降为 `NEEDS_CONTEXT`，不能以“代码可运行”替代。

**观点 5：不同风险必须使用不同控制，不可用单一自动化闸门兜底**

- **发现**：原文把失败回退列为 Wave 顺序问题的一部分（原文 L13），把 escaped UI defects 列为成功指标（原文 L7），并明确不承诺 release/rollout/version-skew（原文 L7）。这些风险的可观测性和可逆性不同：代码/契约失败可自动复现，视觉和用户决策质量需要人看，fixture 非确定性会污染统计，版本或 scope 改变则会使既有证据失效。
- **影响**：把所有异常都记成测试失败会掩盖安全的降级路径；把所有异常都自动 fallback 又可能悄悄改变被测系统；把 flaky 结果留在样本中会制造虚假改善；把旧 run 沿用到新 manifest 或依赖版本则会产生不可比证据。尤其人工无法可靠替代自动化边界覆盖，自动化也无法单独证明视觉缺陷和用户决策是否可接受。
- **建议**：明确控制边界：
  - 只能用**人工 gate**控制的风险：视觉层级、可理解性、关键错误提示、实际用户决策起止确认，以及自动化难以判定的 UI 语义；人工复核必须留截图/录屏、复核者、严重度和处置。
  - 适合**fallback**控制的风险：skill/adapter 的可预期超时、非关键能力缺失或可恢复错误；fallback 到 manifest 中预先登记的稳定路径或 direct-prompt，并显式标记 pair 结果，不能静默成功。
  - 必须**quarantine**的风险：flaky fixture、非确定性 adapter、环境污染、缺失事件或无法重现的 escaped defect；隔离项不得进入 graduation 的改善分母，修复后以新运行 ID 重跑。
  - 必须**重评**的风险：scope manifest、依赖/浏览器/模型版本、任务集合、指标定义或 paired protocol 发生变化；变化后旧三次 run 只能作为历史记录，不能直接沿用为当前证据。
  - 必须**状态降级**的风险：critical/high escaped UI defect、任一指标不可解释地恶化、三次 run 不完整、baseline 不可比、人工 gate 未通过或 fallback 未登记；将候选/毕业状态降为 `NEEDS_CONTEXT`，暂停向 release/rollout 解释的传播。

**观点 6：回归证据要覆盖边界与失败路径，否则三次运行仍不足以证明质量**

- **发现**：角色任务要求逐个待讨论问题回答“怎么测、边界 case、回归风险、质量证据、可复现验证步骤”（T 角色方法）；原文却只在成功判据中列出失败 fixture 和 escaped UI defects（原文 L7），没有明确空值、异常、极值或并发等边界清单。Q1 又要求界定最小切片和不应纳入内容（原文 L12），说明边界本身需要显式裁决。
- **影响**：三次 happy-path 运行可以全部通过，却仍可能在空表单提交、服务返回 malformed payload、重复点击审批、超长字段、并发更新或权限变化时产生 UI 错误；这些缺陷若未进入 fixture 和回归集，最终的 escaped UI defects 数值会被系统性低估。无法复现的失败也无法判断是产品缺陷还是环境噪声。
- **建议**：为 manifest 中的每个 skill 和目标流建立最小边界矩阵：空/缺失、非法类型、最大长度、超时/重试、服务异常、重复提交、并发状态变化、权限不足和浏览器刷新；每个 case 固定输入、预期 UI 状态、允许 fallback、日志事件和严重度。Wave 1 先做契约/fixture 验证，Wave 2 做端到端和人工 UI gate，Wave 3 在三次 paired run 后重跑全部高风险回归集；任何未定位、不可复现或与环境相关的结果先 quarantine，不能以“偶发”关闭。

### 视角：U（用户研究 / UX）
`视角来源: 跨会话独立Agent`

**观点 1：把 scope manifest 当作用户旅程的可审计合同，而不是技能清单**

- 发现：原文把本轮边界描述为“只锁定第一版垂直切片、纳入的 skills/adapters、Wave 顺序、资源边界和毕业标准”，但没有规定一个能被用户和评审共同检查的 manifest 结构（原文 L6）。成功判据只要求锁定一个 React/Next.js 表单或审批流，并列出每个 skill 的输入、输出、禁止事项、依赖、停止条件和失败 fixture（原文 L7）。
- 影响：如果没有从真实任务开始和结束状态出发的 manifest，团队可能把“skill 已接入”误当成“用户能完成任务”；表单填写、校验、补救、提交/审批和失败恢复之间的断点会被拆散到不同 Wave，返工率和决策时间也无法归因到具体体验环节。首版还容易悄悄扩张到 release、rollout 或 version-skew，而这些并不在本轮承诺内（原文 L7）。
- 建议：在 Wave 0 人工冻结一份 scope manifest，至少包含目标用户/任务、起始条件、成功终态、主路径、一个可预期失败路径、每个 skill 的输入/输出/禁止事项/依赖/停止条件/失败 fixture、adapter 边界、键盘与辅助技术要求、明确不支持的路径。把 artifact、adapter、安全机制的重新设计排除在本轮之外（原文 L6），把 release/rollout/version-skew 标为 out of scope（原文 L7）。只有用户研究或 UX 评审确认“用户知道下一步、知道何时停止、知道失败后怎么办”后，manifest 才能过人工 gate；这类理解和信任风险不能仅由自动化通过来替代。

**观点 2：Wave 0–3 应按用户证据递进，而不是按代码完成度递进**

- 发现：原文提出 Q2 要决定 Wave 0–3 的依赖顺序、责任、退出条件和失败回退，却没有给出四个 Wave 的用户侧职责或退出证据（原文 L13）。这使“Wave 完成”容易退化成接口已连通或代码能跑，正好无法回答 Q3 要避免的“代码能跑冒充成功”（原文 L14）。
- 影响：没有先冻结任务和观察口径，后续每个 Wave 都可能更改用户目标、提示语或失败判定；没有先验证停止/回退，用户会在不确定时继续提交；没有在最后一波单独检查可达性，键盘用户、屏幕阅读器用户或低熟悉度用户的阻塞会被平均数据掩盖。此类风险一旦进入后续 Wave，通常不能靠补一条自动测试完全消除。
- 建议：按以下用户证据设定责任和闸门：Wave 0 由研究/产品冻结 manifest、任务版本、用户画像、基线脚本、三次 paired run 的记录模板和无障碍检查表；退出条件是代表性用户能复述目标、起止条件和失败后的下一步。Wave 1 由实现者只交付一条主路径及可见的停止/回退提示；退出条件是用户在无讲解情况下完成主路径，失败时不会被迫继续。Wave 2 纳入失败 fixture、边界输入、键盘/读屏与恢复路径；任一关键失败都走 fallback 或把具体 skill/adapter quarantine，而不是让整条流程继续冒险。Wave 3 由独立评审完成三次 paired run、逐条复核指标和人工 UX gate；不满足即 re-evaluate 或 status downgrade，不能以 Wave 3 的“代码完成”替代毕业。

**观点 3：三次运行必须是三次可比的 paired run，且把用户学习效应隔离出来**

- 发现：原文只要求“至少三次完整运行相对 direct-prompt baseline 在返工率、用户决策时间和 escaped UI defects 上改善”，没有说明一次运行的单位、配对方式、顺序、任务等价性或指标计算口径（原文 L7）。Q3 又明确要求 baseline、三次运行和 graduation criteria 足以防止“代码能跑”冒充成功（原文 L14）。
- 影响：若三次运行只是开发者重复点击同一 happy path，用户会因熟悉任务而变快；若 baseline 与 Experience Version 使用不同数据、提示或失败 fixture，返工率和决策时间不能归因；若 escaped UI defects 只统计自动化发现的问题，最容易漏掉文案歧义、焦点丢失、错误恢复和用户误提交。
- 建议：预先登记三次运行 R1/R2/R3，每次都包含同一类 React/Next.js 表单或审批任务的一对匹配条件：同一任务目标、等价数据和同一成功定义，一次用 direct-prompt baseline，一次用 Experience Version；对顺序做 counterbalance，并记录用户是否首次接触、是否获得帮助、等待时间和中途退出。每次固定记录：(1) 返工次数及导致返工的用户动作，(2) 从任务开始到用户作出并确认决定的时间，等待时间单列，(3) 独立观察员在用户完成后发现的 escaped UI defects，按严重度分级。三次都必须是完整任务而非只跑通代码；任一配对出现用户被主持人救援、关键错误提示不可理解或关键无障碍阻塞，就保留该失败证据并触发 fallback/quarantine，不得用另外两次平均掉。

**观点 4：graduation 要同时证明“做得到、做得明白、出错能收住”**

- 发现：原文把改善返工率、用户决策时间和 escaped UI defects 作为至少三次运行的成功判据，并明确本轮不承诺 release/rollout/version-skew（原文 L7）；但没有给出毕业时的最低用户成功标准、关键缺陷护栏、主持人介入规则或“有改善但仍有风险”的状态表达。
- 影响：只要平均值变好，团队就可能把仍然存在的关键误提交、不可达操作或用户无法解释的决定当成毕业；反过来，单个非关键视觉问题也可能阻塞整个 Experience Version。没有中间状态，评审只能在“成功/失败”之间二选一，无法把可接受的已知风险限制在本轮 scope 内。
- 建议：graduation 采用三层判定并逐项留证：每个 R1–R3 配对任务都完成；三项指标按预注册方向相对 baseline 改善（返工率、决策时间、escaped UI defects 均不劣化，关键 UI/无障碍缺陷为零或已明确隔离）；用户能独立解释“我在决定什么、系统为什么阻止/允许、失败后怎么恢复”。将主持人救援、无法完成、关键错误未被用户察觉、键盘/读屏无法到达关键控件列为人工否决项。状态至少区分 `graduated-for-slice`、`graduated-with-concerns`、`quarantined`、`re-evaluate` 和 `fallback-to-baseline`；任何关键人工否决都应降级或隔离，而不是借由“本轮不承诺 rollout”来掩盖。

**观点 5：把不可由指标充分捕获的体验风险明确交给人工 gate、fallback、quarantine 和重评**

- 发现：原文要求锁定 skills/adapters、资源边界和毕业标准（原文 L6），同时要求每个 skill 具备停止条件和失败 fixture（原文 L7）；但它没有声称自动指标能够判断用户是否理解、是否信任结果、是否在不确定时做出安全决定，也没有规定失败后的状态控制。原文还明确本轮不承诺 release/rollout/version-skew（原文 L7），所以不能把线上真实反馈当作本轮默认补救机制。
- 影响：以下风险只能通过人工观察和人工判定获得足够证据：用户误解审批后果或错误提示；关键控件虽有技术语义但视觉/读屏顺序不使人理解；用户在停止条件处不知道该停；失败后 fallback 让用户丢失已填内容或重复提交；adapter 的异常输出被用户当成可信结果。若这些风险混入三次运行的总分，平均指标会给出虚假的安全感。
- 建议：使用明确的控制矩阵：用户无法说明结果含义、关键可达性或停止条件不清晰 → 人工 gate 不通过并 `re-evaluate`；skill/adapter 触发未定义失败、输出不可信或可能造成重复提交 → 立即 fallback 到 direct-prompt baseline，并 quarantine 该 skill/adapter 及其失败 fixture；同一问题在后续修订后仍复现 → 保持 quarantine，不得以新一次成功覆盖旧证据；只有重新运行等价 paired run、复核用户证据和人工无障碍检查后才可解除隔离。任何关键缺陷、主持人救援、用户无法独立恢复或指标任一护栏恶化 → status downgrade；这些状态控制必须写入 run record，不能只留在口头评审里。

### 视角：P（流程 / 组织协作）
`视角来源: 跨会话独立Agent`

**观点 1：RACI 必须落到每个 Wave 的交付物，而不能只停留在角色名单**

- **发现**：原文把本子问题的边界写成第一版垂直切片、skills/adapters、Wave 顺序、资源边界和毕业标准，且 Q2 明确要求 Wave 0–3 的“责任、退出条件和失败回退”（原文 L6、原文 L13）；但当前没有把“谁负责产出、谁复核、谁批准、谁被通知”映射到任何交付物。原文的 B/C/A/T/U/P 是声明必需的讨论角色集（原文 L8），不是实施 RACI。
- **影响**：没有实施级 RACI 时，Wave 可能由“最先动手的人”隐式接管；失败 fixture、指标记录或退出证据无人签收，后续 Wave 仍可能继续。这样即使三次运行完成，也无法证明是同一套被授权、被复核的流程。
- **建议**：为每个 Wave 建一行交接登记：交付物、Responsible、Accountable、Consulted、Informed、入口条件、退出证据、回退目标、截止时间。至少区分 skill/adapter 实作者、运行记录责任人、质量复核者和 Human 批准者；每一行只能有一个 Accountable。Human 必须 gate 住范围、baseline 冻结、Wave 退出和 graduation；其余日常复核可以由指定责任人执行，不能用“角色已参与讨论”代替签收。

**观点 2：Wave 0–3 要用“可签收的 handoff contract”连接，而不是用口头依赖推进**

- **发现**：Q2 要求依赖顺序、责任、退出条件和失败回退（原文 L13），但成功判据只列出了目标垂直切片、skill 契约字段和三次运行指标（原文 L7），没有定义上一 Wave 交给下一 Wave 的最小包、签收者或未通过时的状态。
- **影响**：Wave 之间会出现隐性前置条件：例如契约字段尚未齐全就开始集成，或集成失败后把半成品继续带入毕业评审。组织上会把“没有交接证据”误当成“没有阻塞”，并且难以定位是依赖缺失、责任缺位还是验收失败。
- **建议**：将顺序固化为可审计的交接链：Wave 0 交付已批准的切片范围、排除项、资源上限和冻结的 baseline 方案；Wave 1 交付每个纳入 skill 的输入/输出/禁止事项/依赖/停止条件/失败 fixture；Wave 2 交付同一垂直切片的完整集成运行包和逐项指标记录；Wave 3 只接收已签名的三次 paired-run 证据并执行 graduation review。下一 Wave 只能在上一 Wave 的 Accountable 签收后启动；退出失败自动回退到最近一次通过的 Wave，未合格产物进入 quarantine，不能靠口头豁免穿越 Wave。

**观点 3：资源边界要成为 scope gate 和 WIP 限制，而不是一句原则性声明**

- **发现**：原文明确本子问题要锁定“资源边界”，同时规定本轮不重新设计 artifact、adapter 或安全机制，也不承诺 release/rollout/version-skew（原文 L6–L7）；但没有给出纳入 skill/adapter 数量、可用工程人时、运行次数、评审容量或新增范围的处理规则。
- **影响**：当实现遇到阻力时，团队很容易通过临时增加 skill、重做 adapter 或把 release 兼容性带进来“解决”问题，导致 Experience Version 失去可比性；资源耗尽也会被伪装成延期，而不是一个可识别的范围失败。
- **建议**：在 Wave 0 由 Human 批准资源账本：一个 React/Next.js 表单或审批流、固定纳入清单、固定运行预算、固定评审人力和明确 out-of-scope 清单；每个 Wave 设 WIP 上限，新增 skill/adapter、改变 artifact/security 设计或触及 release/rollout/version-skew 都必须重新评估并由 Human 批准。超出预算时，自动停止新范围、保留最近通过的 baseline 和运行证据；若无法在边界内完成，将候选状态降级为 scope-incomplete/NEEDS_CONTEXT，而不是宣称毕业。

**观点 4：baseline 与 paired run 必须由 Human 先冻结，运行过程只能按协议执行**

- **发现**：成功判据要求至少三次完整运行，并且要相对 direct-prompt baseline 比较返工率、用户决策时间和 escaped UI defects（原文 L7）；Q3 也专门要求避免“代码能跑”冒充成功（原文 L14）。但原文尚未规定 baseline 的任务样本、prompt、输入、环境、顺序、指标口径和失效运行的判定。
- **影响**：若 baseline 在运行中漂移，或只挑选对 skill 有利的案例，三次比较就无法区分流程收益与任务难度、参与者熟悉度或环境变化。用户决策时间和 escaped defect 还可能因人工补救而被低估，形成“有数字但不可复核”的毕业证据。
- **建议**：Wave 0 先建立并由 Human gate 冻结 baseline protocol：同一批任务/输入和等价 direct-prompt，对每次 paired run 预先记录顺序、环境、操作者、原始输出、返工、决策时间和 escaped UI defect 定义；baseline 与 treatment 必须成对运行，不得事后重写 prompt 或删异常样本。协议偏离、环境变化、记录缺失的 run 进入 quarantine，不计入三次；是否按同协议重跑由指定复核者提出、Human 批准，不能由运行责任人自行裁定。

**观点 5：三次运行应是连续的质量门，不是事后凑出的总样本数**

- **发现**：原文只要求“至少三次完整运行”并在三个指标上改善（原文 L7），同时 Q3 要求定义 graduation criteria（原文 L14）；这还没有回答每次运行是否都必须完整、某一指标退化如何处理、异常样本能否替换，以及三次结果由谁判定。
- **影响**：如果允许先跑很多次再挑三次，或用一次成功运行覆盖两次失败运行，就会把 graduation 变成选择性汇总；返工率、决策时间和 escaped UI defects 之间的权衡也会在最后一刻才暴露，团队会把“平均改善”误读为流程稳定。
- **建议**：在 baseline gate 时预注册逐次和总体规则：每次 paired run 必须有完整证据包；单次严重 escaped UI defect、关键停止条件失效或记录不全，先 quarantine 并标注原因；不得静默替换。三次有效 run 完成后，再按预注册阈值检查三个指标及不可接受缺陷门，输出逐次结果、总体结果和偏差说明。指标冲突、样本无效或阈值需要临时调整时，必须 Human re-evaluation；在重评前状态保持 candidate/NEEDS_CONTEXT，不能升级为 graduated。

**观点 6：Human 决策点要有拒绝、暂停和降级权，不能只在表格里“待拍板”**

- **发现**：原文的 Human 拍板表把 B、C、A、T、U、P 六轮都标为“待拍板”，且“是否 conclusion”均为“否”（原文 L54–L63）；文档状态仍是 NEEDS_CONTEXT（原文 L65–L73）。这说明决策尚未发生，但没有列出每次拍板的输入、批准范围、拒绝后去向或升级路径。
- **影响**：如果 Human 只对最终结果点头，前面的范围、资源、baseline 和 Wave handoff 就会形成事实承诺；发生责任争议或数据异常时，团队可能以“流程已经跑过”为理由继续推进。更严重的风险——范围越界、指标口径变更、严重 UI 缺陷豁免、release/rollout 外溢——不能由自动脚本或单个执行者替 Human 接受。
- **建议**：把 Human gate 固定为六类决策：批准最小切片/排除项与资源账本；批准 RACI 和 Wave 0–3 handoff contract；冻结 baseline/paired-run protocol；批准每次异常的 quarantine 或同协议重跑；审阅三次运行及指标冲突后的 re-evaluation；最终批准 graduation。每个 gate 都记录证据、决策人、日期、条件和拒绝动作。无 Human 决策时保持 NEEDS_CONTEXT；违反边界或出现无法解释的指标时暂停并降级；孤立的坏 run 进入 quarantine；可修复的流程偏差按批准协议 fallback 重跑。不得把“本轮不承诺 release/rollout/version-skew”（原文 L7）解释成可以绕过这些人工闸门。

## 主力AI 整合立场（主会话，非独立视角，低权重）

`视角来源: 同会话SubAgent(低权重)`

独立观点已通过 scope、架构和 UX 三道收敛闸门。本轮把“完整生命周期”定义为一个受限、可复跑的 React/Next.js 表单/审批流垂直切片，而不是把所有框架、平台和 provider 一次性产品化。

1. **Scope manifest 固定边界。** 只纳入一个 route、一个输入/输出数据形状、一套本地组件 catalog、一个 `UI-BRIEF → UI-DESIGN → ui-flow/v1 → code → verification receipt → handoff` 链路；预算上限、owner、commit、模型/provider/config、纳入/排除项写入 manifest。目标 portfolio 的 10 个原子 skill 仍保持原子化（`zj-ui-brief`、`zj-ui-discover`、`zj-ui-direction`、`zj-ui-design-system`、`zj-ui-flow`、`zj-ui-prototype`、`zj-ui-visual-review`、`zj-ui-break`、`zj-ui-verify`、`zj-ui-handoff`），但 Experience Version 只允许这些 skill 在一个场景内工作，不扩展第二条业务路径。

2. **Wave 0–3 依赖顺序。** Wave 0（B/T/A）：冻结 scope/artifact/skill manifest、安全边界、失败 fixture、资源账本，并在锁定环境完成 direct-prompt baseline；失败则回到 scope/fixture。Wave 1（各 skill owner）：完成 10 个原子 skill 的输入、输出、禁止事项、依赖、停止条件和正常/冲突/失败 fixture，先用本地 artifact 跑通；任何未达标 skill quarantine，不阻断本地 fallback。Wave 2（A/T/O）：接入本地验证 adapter（Storybook 为首选），可选运行 json-render/A2UI/M3E 的兼容性 fixture；Figma/Superdesign、真实远程写回和正式 rollout 不进入 graduation。Wave 3（B/C/T/U/P）：执行三次 paired run 和 graduation review，不在此阶段扩展功能。

3. **三次 paired run 与毕业门槛预注册。** 每次使用同一 case 集、brief、环境 fingerprint、model/provider/config 和命令，运行 direct-prompt baseline 与 Experience Version 两条对照路径；中途人工补丁、缺 fixture、日志不完整、关键 gate 失败的 run 标为 invalid 并补跑，不得凑数。建议初始门槛：返工率相对 baseline 改善 ≥20%；用户从看到可选方向到接受/要求修改的决策时间改善 ≥15%；escaped UI defects 每次不恶化且三次汇总改善 ≥20%；任一 visual/a11y blocker、越权 action、provenance 缺失或 receipt 不完整都阻断 graduation。

4. **决策与责任。** B 是 DRI；A 维护边界/兼容；T 维护 fixture、paired-run 完整性和指标；U 维护决策时间与关键任务协议；C 审用户价值和相对 direct-prompt 的差异；P 维护 Wave handoff、预算和 Human 拍板记录。graduation packet 必须包含 scope manifest、10 个 skill manifest、adapter manifest、三次原始 run、指标表、缺陷/quarantine 清单、fallback 演练和 Human gate 签名。

5. **状态与剩余风险。** `DRAFT → READY → PILOT → GRADUATED`，任一关键指标回归、S1/S2 UI 缺陷、scope 漂移、provider/config 变更或关键 fixture 失败都降级为 `QUARANTINED`/`NEEDS_CONTEXT`；direct-prompt 与本地 artifact 是 fallback。机制可以消除输入缺失、owner 冲突、停止条件未执行、测量分母不一致和证据缺失；生成式审美、法律判断、用户价值外推和长期 provider/version skew 只能由 Human gate、隔离、定期重评和状态降级控制。本轮不承诺 release、rollout、dogfood 或长期 version-skew。

## Human 对 Agent X 的拍板

| 轮次 | 视角 | 隔离方式 | Human 拍板 | 是否 conclusion | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 | B | 同 provider 跨会话 | 待拍板 | 否 | |
| 2 | C | 同 provider 跨会话 | 待拍板 | 否 | |
| 3 | A | 同 provider 跨会话 | 待拍板 | 否 | |
| 4 | T | 同 provider 跨会话 | 待拍板 | 否 | |
| 5 | U | 同 provider 跨会话 | 待拍板 | 否 | |
| 6 | P | 同 provider 跨会话 | 待拍板 | 否 | |

## conclusion（含沉淀指令）

- **子问题结论：** Experience Version 锁定为一个 React/Next.js 表单/审批流垂直切片；通过 10 个保持原子边界的 UI skill 在单一路径内完成 brief、方向、设计系统、flow、prototype、实现、视觉/断点验证和 handoff。它是可毕业的受限试验，不是 release/rollout 或长期 provider 兼容承诺。
- **解法：** 用 scope manifest 固定 route、数据形状、skills、adapter、资源和排除项；按 Wave 0（契约与 baseline）→ Wave 1（本地 skill 闭环）→ Wave 2（Storybook 首选的本地验证 adapter，其他协议/渲染 adapter 仅兼容性 fixture）→ Wave 3（三次 paired run 与 graduation）推进。每个 skill 必须具备输入、输出、禁止事项、依赖、停止条件和失败 fixture；每次 paired run 同时运行 direct-prompt baseline，按预注册的返工率、决策时间、escaped UI defects 门槛判定。
- **remaining-risks 控制：** scope 漂移、指标口径变更、skill/adapter 失败和 provider/config 变化都触发 quarantine 或状态降级并补跑；本地 artifact 与 direct-prompt 是 fallback。生成式审美、法律判断、用户价值外推和长期 version-skew 不可由三次运行彻底消除，必须保留 Human gate、重评周期和明确的 `PILOT/QUARANTINED/NEEDS_CONTEXT` 状态。

- **沉淀指令：**
  - 改哪些 PRD / ADR / 文档：新增 Experience Version PRD（scope manifest、10 skill contract、Wave 0–3、RACI、paired-run protocol、graduation packet）和指标 ADR；把不承诺 release/rollout/version-skew 写入边界。
  - 跨子文档约束登记：`sub-01` 的 canonical artifact 是唯一恢复路径；`sub-02` 的 capability manifest/owner/precedence 决定 skill 进入 Wave 1；`sub-03` 的 adapter manifest、schema lock、fallback、removal test 决定 Wave 2；`sub-04`/`sub-05` 的安全与验证 gate 是 graduation 的硬前置。
  - 待删临时脚手架：本子文档的 briefings 和 viewpoints 过程文件，待 `zj-docs-ontology` 分类；Human 确认前保留讨论目录。
- **状态协议：** DONE_WITH_CONCERNS

