视角来源: 跨会话独立Agent

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
