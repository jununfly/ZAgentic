# ZAgentic 产品形态：从 pstack-claude 对照中演进

> 本文件是复杂问题「结合 pstack-claude 与 ZAgentic 的方法论比较，判断 ZAgentic 是否需要更好的产品形态并确定演进路径」的主文档（MASTER）。其余文档各对应一个独立子问题，由 `zj-discuss` 方法论维护。

## 核心问题

- **问题陈述：** 在 ZAgentic 已具备可组合 skill、推荐路径、证据链与治理机制的前提下，是否应从“技能目录 + 文本路由 + 人工组装”演进为更明确的产品形态；若应演进，目标产品契约、系统边界和验证路径分别是什么？
- **为什么现在要解决：** pstack-claude 展示了“全局入口路由 → 方法流水线 → 并行执行 → 验证复盘”的强产品形态，而 ZAgentic 更强调独立 skill、Human authority、证据、治理和可移除组合。上轮固定版本报告覆盖 58 个 skill，拟合结果为 B1=29、C=20、D=9、A=0；可借鉴价值真实存在，但整体复制 pstack runtime 会引入第二 authority/runtime。若不先确认产品形态，继续 merge skill 可能积累重复 owner、隐式路由和相互冲突的自治策略。
- **成功判据：** 对两项目形成事实与解释分离的比较；识别 ZAgentic 当前用户组装成本；至少比较三种严肃候选并作出目标形态决策；写出输入、输出、状态、失败出口、Human 决策点和边界；给出可逆最小纵切 PoC、成功阈值、停止条件与回退路径；把耐久结论交给长期文档治理，不把讨论文件夹当长期 authority。

## 解决思路（整合叙事）

先用统一维度比较 pstack-claude 与 ZAgentic 的产品单元、路由、组合、执行、验证、复盘、authority、状态和宿主假设；再从用户旅程出发比较保持现状、可解释组合器、有限状态薄编排层和强 router/runtime。最终推荐必须同时满足用户组装成本下降、证据和 Human authority 可审计、组件可移除以及不引入第二 runtime。结论将以最小可逆纵切验证，随后由 `zj-docs-ontology` 分类并沉淀到长期 PRD/ADR/设计文档。

## 文档索引

| 子文档 | 独立子问题 | 状态 | 解法摘要 |
| --- | --- | --- | --- |
| [sub-01-design-philosophy-and-methodology.md](./sub-01-design-philosophy-and-methodology.md) | 用统一框架比较 pstack-claude 与 ZAgentic 的设计哲学、方法论及可迁移边界 | 🔲 观点完成，待 Human 拍板 | 初步倾向：迁移阶段化方法、验收契约、证据包和薄适配；拒绝宿主 runtime 直引 |
| [sub-02-target-product-form-and-evolution.md](./sub-02-target-product-form-and-evolution.md) | 为 ZAgentic 选择目标产品形态、演进边界与最小验证路径 | 🔲 观点完成，待 Human 拍板 | 初步推荐：可解释组合方案生成器 + 既有 skill/roadmap 执行，先不引入强 router/runtime |

状态图例：🔲 进行中 · ✅ 已结论

## 跨子文档约束

> 各子文档在结论阶段登记彼此冲突、依赖与共享前提，集中在此，避免解法互相打架。

- 子文档 1 只能产出比较、设计张力和可迁移/不可迁移清单，不预先决定最终产品形态。
- 子文档 2 必须把上轮逐 skill capability-fit 报告作为约束输入，不重复生成 58 项 merge 排名。
- 任一候选方案都不得引入与 ZAgentic 现有 Human authority、证据协议和文档治理并列的第二 authority/runtime。
- 产品形态结论必须先由可逆 PoC 验证，技能 merge 属于后续执行规划，不替代产品验证。
- 当前两篇子文档的角色观点与结构闸门已完成；结论状态仍为 `NEEDS_CONTEXT`，须由 Human 逐轮拍板后才能转为 `DONE` 或 `DONE_WITH_CONCERNS`。

## 本文件夹的性质与处置契约

本文件夹是复杂问题「ZAgentic 产品形态从 pstack-claude 对照中演进」求解之前的过程性质权威依据，不是长期文档。

- `MASTER.md`：核心问题、解决思路、文档索引与跨子文档约束。
- 其余文档：各独立子问题的讨论与解法。

**处置：** 问题解决后须调用 `zj-docs-ontology` 对本组文档分类沉淀——可长期复用内容（权威结论、决策、约束）拆解进 `docs/` 对应权威页；过程性讨论、briefings 和证据按删除候选处理；沉淀完成且 Human 确认后删除本文件夹。

## 复盘度量（可选，删除前填）

```json
<待终局前运行 metrics.py 后填入>
```
