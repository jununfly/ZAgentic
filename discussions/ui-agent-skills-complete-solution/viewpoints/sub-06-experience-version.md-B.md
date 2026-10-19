视角来源: 跨会话独立Agent

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
