# ZAgentic 产品形态：从 pstack-claude 对照中演进

> 本文件是复杂问题「结合 pstack-claude 与 ZAgentic 的方法论比较，判断 ZAgentic 是否需要更好的产品形态并确定演进路径」的主文档（MASTER）。其余文档各对应一个独立子问题，由 `zj-discuss` 方法论维护。

## 核心问题

- **问题陈述：** 在 ZAgentic 已具备可组合 skill、推荐路径、证据链与治理机制的前提下，是否应从“技能目录 + 文本路由 + 人工组装”演进为更明确的产品形态；若应演进，目标产品契约、系统边界和验证路径分别是什么？
- **为什么现在要解决：** pstack-claude 展示了“全局入口路由 → 方法流水线 → 并行执行 → 验证复盘”的强产品形态，而 ZAgentic 更强调独立 skill、Human authority、证据、治理和可移除组合。上轮固定版本报告覆盖 58 个 skill，拟合结果为 B1=29、C=20、D=9、A=0；可借鉴价值真实存在，但整体复制 pstack runtime 会引入第二 authority/runtime。若不先确认产品形态，继续 merge skill 可能积累重复 owner、隐式路由和相互冲突的自治策略。
- **成功判据：** 对两项目形成事实与解释分离的比较；识别 ZAgentic 当前用户组装成本；至少比较三种严肃候选并作出目标形态决策；写出输入、输出、状态、失败出口、Human 决策点和边界；给出可逆最小纵切 PoC、成功阈值、停止条件与回退路径；把耐久结论交给长期文档治理，不把讨论文件夹当长期 authority。

## 解决思路（整合叙事）

先把 pstack-claude 与 ZAgentic 放入同一比较框架：pstack 的复利来自阶段化任务推进、连续工作流、并行候选、验收和复盘；ZAgentic 的长期优势来自可拆卸 skill、证据协议、Human authority、文档治理和可移除组合。两者的可迁移边界由输入输出、状态、权限、语义 owner、宿主依赖、证据、删除和回退字段表达。

终局产品形态确定为“可解释组合方案生成器（Composer）+ 既有 skill/roadmap 执行”。Composer 是意图到 Plan 的方案生成能力：它读取用户目标、约束和能力目录，输出带选择理由、顺序、依赖、验收和缺口说明的 Plan；能力未命中但有可信候选时给出建议，无可靠建议时逐行输出 `required skill：简短地描述缺失skill的形状`。Plan 是由 Composer skill 内置版本化模板生成的可审查方案契约，经过 Human 审查后才交给既有执行链。

首个可逆 PoC 只覆盖外部仓库研究和工具组合设计，产物写入 `skills-outputs/` 下的版本化 Markdown Plan，不修改 skill 定义，不自动执行不可逆动作。PoC 的机械验收使用固定 fixture、场景 oracle、Plan schema/provenance、安全硬门槛和删除实验层后的原路径回归；时间、交互步骤、人工修改和恢复次数只作描述性观测，人工组装基线不作为客观因果基线。强 router/runtime、hooks、transcript/model sheet、宿主 runtime 状态和 shipping glue 暂不进入默认路径。

终局后进入 `zj-docs-ontology`：提案阶段分类长期设计、ADR、入口说明、研究证据和讨论过程；只执行 Human 确认的沉淀与删除；讨论目录在沉淀完成且确认后删除。
## 文档索引

| 子文档 | 独立子问题 | 状态 | 解法摘要 |
| --- | --- | --- | --- |
| [sub-01-design-philosophy-and-methodology.md](./sub-01-design-philosophy-and-methodology.md) | 用统一框架比较 pstack-claude 与 ZAgentic 的设计哲学、方法论及可迁移边界 | ✅ 已结论 | 吸收阶段化方法、验收契约、证据包和复盘；拒绝宿主 runtime 直引，确立 Composer/Plan authority 边界 |
| [sub-02-target-product-form-and-evolution.md](./sub-02-target-product-form-and-evolution.md) | 为 ZAgentic 选择目标产品形态、演进边界与最小验证路径 | ✅ 已结论 | 采用可解释 Composer + 版本化 Plan；以固定 fixture、场景 oracle、安全硬门槛和删除后回归验证，不以人工基线提速作硬门槛 |

状态图例：🔲 进行中 · ✅ 已结论

## Human 拍板议题（跨子文档，一事一议）

> 这里把两个子文档的角色意见合并为不重复的决策对象。每次只处理一个 `HD-*`；Human 拍板后回填对应子文档的 Human 表与本表状态，再进入下一题。

| ID | 一事一议 | 来源 | 当前建议 | 依赖 | 状态 |
| --- | --- | --- | --- | --- | --- |
| `HD-1` | **产品单元与唯一 authority：** skill/workflow、证据协议、组合器、执行链各自谁拥有语义、状态和权限？ | 子文档 1 Q1/Q3/Q5；子文档 2 Q1/Q3 | skill/workflow 继续拥有能力语义；证据/决策协议继续拥有可审计事实；组合器负责生成可解释 Plan，并在能力不足时给出建议或逐行列出 `required skill：<缺失 skill 形状>`；组合器不拥有执行权限或长期治理 authority。 | 无；这是后续议题的前置约束 | ✅ 已确认（2026-10-08） |
| `HD-2` | **pstack 机制的迁移边界：** 哪些原则吸收，哪些宿主假设拒绝？ | 子文档 1 Q2–Q5 | 吸收阶段化工作流、验收契约、证据包、复盘记录；逐项采用“直接迁移 / 薄适配验证 / 拒绝迁移”；拒绝全局 router、hooks、transcript/model sheet、宿主 runtime 状态和 shipping glue。 | HD-1 | ✅ 已确认（2026-10-08） |
| `HD-3` | **目标产品形态：** 保持目录、可解释组合器、有限状态薄编排层、强 router/runtime 四选一或分阶段？ | 子文档 2 Q1–Q2 | 采用“可解释组合方案生成器 + 既有 skill/roadmap 执行”；组合器 skill 内置版本化 Plan 模板；找不到能力时先给建议，无法建议时逐行输出 `required skill：<缺失 skill 形状>`；强 router/runtime 暂不进入默认路径。 | HD-1、HD-2 | ✅ 已确认（2026-10-08） |
| `HD-4` | **最小纵切契约：** 首个 PoC 做什么、写什么、何处必须 Human 批准？ | 子文档 2 Q3–Q4 | 用“外部仓库研究”和“工具组合设计”两任务；只生成 `skills-outputs/` 下版本化 Markdown Plan，不改 skill 定义、不自动执行不可逆动作；Human 审查后才进入既有执行链。 | HD-3 | ✅ 已确认（2026-10-08） |
| `HD-5` | **继续/停止阈值：** 如何判断 PoC 值得继续、修改或删除？ | 子文档 2 Q5；T/S/U 观点 | 不把“相对人工组装提速”或“执行成功率不低于人工基线”当作客观硬门槛；固定 fixture 只做描述性观测。机械门槛改为：Plan 契约和 provenance 完整、能力缺口格式正确、场景 oracle 通过、authority bypass/未声明副作用/未批准写入或外联/秘密明文泄露均为 0，删除实验层后原路径回归通过。 | HD-4 | ✅ 已确认（2026-10-08） |
| `HD-6` | **耐久沉淀与退出：** 通过后改哪些长期文档，失败后删什么？ | 两个子文档 conclusion 的沉淀指令 | 通过后由 `zj-docs-ontology` 把产品契约/ADR/入口说明沉淀到长期文档；失败则删除实验适配层、保留原路径；Human 确认后删除 `discussions/` 与 briefings。 | HD-1–HD-5 | ✅ 已确认（2026-10-08） |

### HD-1 的补充契约

- **能力命中：** 组合器从现有 skill/workflow 中生成候选组合，并说明选择理由、依赖、顺序和验收要求。
- **能力未命中但可判断：** 组合器给出建议，说明建议来源、适配边界和是否需要后续 capability-fit / research。
- **能力未命中且无可靠建议：** 组合器不得用模糊的“暂不支持”代替缺口，必须逐行输出一组缺口，每行遵循：`required skill：简短地描述缺失skill的形状`。
- **Plan 模板 owner：** Plan 模板内置在组合器 skill 中，作为该 skill 的版本化资源；每份 Plan 应记录模板版本，模板变更不得静默改变既有 Plan 的解释。

### Human 对 `HD-1` 的确认记录

- **日期：** 2026-10-08
- **决定：** 接受“组合器 = 意图到 Plan 的方案生成能力；Plan = 组合器 skill 内置模板生成的可审查方案契约”这一产品单元划分。
- **authority 边界：** skill/workflow 拥有能力语义；证据/决策协议拥有可审计事实；组合器只拥有建议、解释和 Plan 生成；既有执行链拥有批准后的执行与副作用；长期治理仍由现有文档 authority 负责。
- **缺口协议：** 能力无可靠建议时，组合器逐行输出 `required skill：简短地描述缺失skill的形状`。
- **Plan 模板：** 模板由组合器 skill 内置并版本化，Plan 必须记录模板版本。

### Human 对 `HD-2` 的确认记录

- **日期：** 2026-10-08
- **决定：** 接受阶段化工作流、验收契约、证据包、复盘记录作为可迁移的方法机制。
- **迁移规则：** 每项机制按“直接迁移 / 薄适配验证 / 拒绝迁移”分类，并记录输入输出、依赖、证据、删除和回退路径。
- **边界：** 不直接迁移全局 router、hooks、transcript/model sheet、宿主 runtime 状态和 PR shipping glue；这些宿主假设不能成为 ZAgentic 的第二 authority/runtime。

### Human 对 `HD-3` 的确认记录

- **日期：** 2026-10-08
- **决定：** 接受“可解释组合方案生成器 + 既有 skill/roadmap 执行”的目标产品形态。
- **产品边界：** 组合器负责从用户意图、约束和能力目录生成带理由的 Plan；Plan 使用组合器 skill 内置的版本化模板；能力缺口按已确认的建议/`required skill：...` 协议输出。
- **明确暂缓：** 有限状态薄编排层和强 router/runtime 不进入默认产品路径，除非后续独立 PoC 证明其不会形成第二 authority/runtime。

### Human 对 `HD-4` 的确认记录

- **日期：** 2026-10-08
- **决定：** 接受首个可逆 PoC 的范围和契约。
- **任务白名单：** 外部仓库研究、工具组合设计。
- **产物边界：** 只生成 `skills-outputs/` 下带版本的 Markdown Plan；不修改 skill 定义。
- **Human 闸门：** Plan 生成后由 Human 审查，批准后才进入既有执行链。
- **副作用边界：** PoC 不自动执行不可逆动作。

### HD-5 的测量修正

- **撤回的指标：** “方案生成时间相对人工组装基线下降至少 30%”和“执行成功率不低于人工基线”不再作为客观验收门槛；人工基线受任务、操作者和路径差异影响，无法稳定证明因果改进。
- **保留的观测：** 在固定 fixture、固定 skill 索引和固定输入约束下记录 wall-clock、主动交互步骤、人工修改次数、拒绝/重试次数、失败恢复次数和 Plan 采纳情况；报告中位数、分布和异常，不把它们包装成普遍提速结论。
- **机械通过条件：** Plan schema/provenance 完整；每个能力选择有理由；缺口按 `required skill：...` 输出；固定场景 oracle 通过；authority bypass、未声明副作用、未批准写入或外联、秘密明文泄露均为 0；删除实验层后原路径回归通过。
- **产品判断：** 是否值得继续属于 Human 对固定场景证据和实际使用反馈的产品判断，不伪装成一个由人工基线推导出的客观因果结论。

### Human 对 `HD-5` 的确认记录

- **日期：** 2026-10-08
- **决定：** 接受修订后的继续/停止判定。
- **撤回：** 不把相对人工组装提速或人工基线执行成功率作为客观硬门槛。
- **保留观测：** 在固定 fixture 下记录时间、交互步骤、人工修改、拒绝/重试、恢复和 Plan 采纳情况；这些数据只作描述性材料。
- **机械通过条件：** Plan schema/provenance 完整；能力选择有理由；缺口按 `required skill：...` 输出；固定场景 oracle 通过；authority bypass、未声明副作用、未批准写入或外联、秘密明文泄露均为 0；删除实验层后原路径回归通过。

### Human 对 `HD-6` 的确认记录

- **日期：** 2026-10-08
- **决定：** 接受长期沉淀与退出路径。
- **通过路径：** 调用 `zj-docs-ontology` 提案并执行确认后的沉淀，把产品契约、Plan 模板 owner、authority 边界和入口说明放入长期设计/ADR/入口文档。
- **失败路径：** 删除 Composer 实验适配层和临时 Plan 产物，保留原有 skill/roadmap 路径；保留必要失败证据供治理审计。
- **过程材料：** ontology 沉淀完成、Human 确认后，删除本讨论目录和 `briefings/`；在此之前它们仍是本问题的过程性质权威依据。

**终局状态：** `HD-1` 至 `HD-6` 全部确认；两个子文档进入 `DONE`，下一步执行文档治理提案与长期沉淀。

## 跨子文档约束

> 各子文档在结论阶段登记彼此冲突、依赖与共享前提，集中在此，避免解法互相打架。

- 子文档 1 只能产出比较、设计张力和可迁移/不可迁移清单，不预先决定最终产品形态。
- 子文档 2 必须把上轮逐 skill capability-fit 报告作为约束输入，不重复生成 58 项 merge 排名。
- 任一候选方案都不得引入与 ZAgentic 现有 Human authority、证据协议和文档治理并列的第二 authority/runtime。
- 产品形态结论必须先由可逆 PoC 验证，技能 merge 属于后续执行规划，不替代产品验证。
- 两篇子文档的角色观点、结构闸门和六项 Human 拍板均已完成；讨论结论为 `DONE`，长期沉淀和过程材料删除按 `zj-docs-ontology` 提案与确认执行。

## 本文件夹的性质与处置契约

本文件夹是复杂问题「ZAgentic 产品形态从 pstack-claude 对照中演进」求解之前的过程性质权威依据，不是长期文档。

- `MASTER.md`：核心问题、解决思路、文档索引与跨子文档约束。
- 其余文档：各独立子问题的讨论与解法。

**处置：** 问题解决后须调用 `zj-docs-ontology` 对本组文档分类沉淀——可长期复用内容（权威结论、决策、约束）拆解进 `docs/` 对应权威页；过程性讨论、briefings 和证据按删除候选处理；沉淀完成且 Human 确认后删除本文件夹。

## 复盘度量（可选，删除前填）

```json
{
  "discussion_slug": "zagentic-product-form-evolution-from-pstack",
  "roles_used": ["A", "B", "C", "R", "S", "T", "U"],
  "viewpoint_count": 10,
  "open_questions_total": 2,
  "open_questions_closed": 2,
  "closure_rate": 1.0,
  "raw_volume_chars": 20923,
  "solution_volume_chars": 814,
  "compression_ratio": 25.703931203931205,
  "recomputable": true
}
```
