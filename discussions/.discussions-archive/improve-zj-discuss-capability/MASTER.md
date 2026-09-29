# 改进 zj-discuss / zj-discuss-view 的能力与体验（meta 讨论）

> 本文件是复杂问题「如何改进 zj-discuss / zj-discuss-view 的能力与体验，并以一次真实使用发现 bug」的 **主文档（MASTER）**。
> 本文件夹由 `zj-discuss` 方法论维护——这是一次 **meta 使用**：用 zj-discuss 本身来讨论改进 zj-discuss。

## 核心问题

- **问题陈述：** zj-discuss / zj-discuss-view 作为项目级 `skills/` 方法论文档，存在
  (a) AI 未自动触发 / 可发现性差；(b) Phase 2 仍需人肉开 N 会话派发角色（human 补位重）；
  (c) 准备阶段角色简介未自动带出（bug1）；(d) 质量护栏 / 体验 / 处置闭环待打磨。
  需要给出可落地改进方案，并借本次真实使用暴露 bug。
- **为什么现在要解决：** 本次实际触发失败（Skill 工具不索引项目级 `skills/` 目录）已直接证实 (a)；
  用户希望减 human 补位、提高产出质量。
- **成功判据：** 产出一份含可执行沉淀指令的改进方案（触发 / 分发 / 质量体验三块），
  并登记本次使用发现的所有 bug。

## 解决思路（整合叙事）

> 初始为分解阶段概览；每个子文档 conclude 后增量更新；全部 conclude 后由终局合成重写为整合叙事。

本次 meta 讨论本身即一次真实跑通，**结论已翻转此前误判**：

- **触发失败**根因落在宿主 `Skill` 索引边界（只索引 `~/.workbuddy/skills/`，不索引项目级 `skills/`），非方法论缺陷 → 改进走双通路（user-level 注册/软链 + `Glob **/skills/**/SKILL.md` 项目级 fallback）。
- **「用 Agent 工具 fresh-context 派发替代人肉开 N 会话」被证伪**：它在 zj-discuss 独立性阶梯里属 **same-session 低权重层**，不满足非降级锚点，且踩中「否决项（会话编排运行时）」。r1-closure 节点 1-4 的 κ=0.667 是在 same-session 条件下取得，仅作方法可行性预验，不作自动化授权。
- **并发隔离**靠「每角色独立文件 + 单写者串行合并」消除竞态；但 `check_subdoc.py` 仅扫单文件，须扩展为 glob/dir 合并扫描。
- **质量护栏**暴露 **2 个阻断级假阳性 bug，均已修**：(a) conclusion 段首规则说明句被误判为违规（狼来了）；(b) `EVIDENCE_RE` 只认 `原文 Lxx` 裸形式、拒收主流 `原文 <file> Lxx` 写法——meta-run 实测 sub-02 B 观点3/4 因此被拒，且若不改会在生产中造成 mass false rejection → 闸门被关（正是 SKILL 自警的失效模式）。其余断点：沉淀指令未进闸门、删除不可逆无 RPO 兜底（待实现）。
- **bug1**（准备阶段角色简介未自动带出）根因 = 准备阶段清单与 role-matrix 是两条数据通路（AI 自由文本 vs `launch_pack.py` 的 `load_role_pool`），修复 = 把准备阶段改为 `launch_pack.py --prep` 脚本驱动（单一数据源）。

## 文档索引

| 子文档 | 独立子问题 | 状态 | 解法摘要 |
| --- | --- | --- | --- |
| [sub-01-trigger-dispatch.md](./sub-01-trigger-dispatch.md) | 触发机制与自动派发（减 human 补位） | ✅ 已结论 | 触发走双通路；Agent 工具派发证伪为 same-session、踩否决项；并发靠分文件+串行合并 |
| [sub-02-quality-experience.md](./sub-02-quality-experience.md) | 质量护栏与体验打磨（含 bug1） | ✅ 已结论 | bug1=脚本驱动准备清单；check_subdoc 假阳性已修+证据正则放宽+沉淀指令入闸；删除前持回执并 git 提交 |

状态图例：🔲 进行中 · ✅ 已结论

## 跨子文档约束

> 各子文档在结论阶段登记彼此冲突 / 依赖 / 共享前提，集中在此，避免解法互相打架。

- **否决项语义已核实（关键）：** Agent 工具 fresh-context 派发 = 会话编排运行时，确踩「否决项（会话编排运行时 / router / suite）」红线。子1 的「减 human 补位」目标与独立性闸门存在**结构性张力**——是否放宽阶梯（新增「tool-spawned fresh-context = cross-session 等价层」）是待 zj 决策的 open question，而非已解决的问题。
- **派发与体验耦合：** 子1 触发改进（Glob 项目级 fallback）覆盖子2「启动摩擦」一部分；但派发仍保留 Human 拍板闸门，子2 的 launch pack 体验改善聚焦于 `--prep` 强制带简介。
- **护栏修复共享：** 子2 发现的 check_subdoc 假阳性 / EVIDENCE_RE 过窄 / 沉淀指令入闸，同时惠及所有 zj-discuss 使用方（含子1），属全局修复。

## 本文件夹的性质与处置契约

本文件夹是复杂问题「改进 zj-discuss」**求解之前的过程性质权威依据**，不是长期文档。

- `MASTER.md`：核心问题 + 解决思路 + 文档索引（本组入口）。
- 其余文档：各独立子问题的讨论与解法（一事一议）。

**处置：** 问题解决后须调用 `zj-docs-ontology` 对本组文档分类沉淀——可长期复用内容
（权威结论 / 决策 / 约束）拆解进 `docs/` 对应权威页，过程性讨论与证据按删除候选处理；
**沉淀完成且 Human 确认后删除本文件夹**。

> 在删除前，本文件夹即该复杂问题的完整解决方案（进行态 / 已结论态）。

## 复盘度量（可选，删除前填）

> 问题解决、调用 `zj-docs-ontology` 沉淀前，运行下方命令把本讨论的压缩比等度量算出来贴在此处：

```sh
python3 <skill-dir>/scripts/metrics.py <本讨论文件夹路径>
```

```json
<在此粘贴 metrics.py 输出>
```

## AI 上下文 digest（可选，voice-only）

```text
<在此粘贴本讨论的 voice-only digest：zj-discuss 的立场/语气简述，或留空>
```
