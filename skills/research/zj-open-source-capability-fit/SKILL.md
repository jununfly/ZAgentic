---
name: zj-open-source-capability-fit
description: >-
  用本仓库《开源能力拟合决策模型》评估是否直接采用 / 扩展采用 / 选择性复用 /
  继续搜索某个外部开源项目，产出可复核的 R×O 证据矩阵与 A/B1/B2/B3/C/D 分类。
  带机械闸门（矩阵完整性、版本固定、证据非空、关键能力缺失→D、可控 B 边界校验），
  不是薄 prompt。Use when deciding whether to ingest/merge an external OSS capability,
  or to re-evaluate a prior OSS-fit decision after upstream change. For a full selection
  report (problem framing → options → evidence → fit → ownership risk → gates → recommendation),
  call `zj-tech-research-report` and let it reference this skill's output; this skill only
  produces the fit verdict and decision record, not the narrative report.
argument-hint: "<目标需求描述，或一个已填好的 capability_fit 输入 JSON 路径>"
---

# zj-open-source-capability-fit

把本仓库《开源能力拟合决策模型》从**方法论文档**操作化成**带机械闸门的决策仪器**。
它不是薄 prompt：所有计算与判定由 `scripts/capability_fit.py` 确定性执行，闸门不过就拒绝给出
自信分类——任何结论都可被第三 Agent 凭决策记录复核。

> 模型来源（自创或外部 ingest）对本 skill 的计算逻辑与机械闸门**不产生增量价值**——
> 本 skill 完全由 `docs/agreements/open-source-capability-fit-decision-model.md` 的模型定义驱动，
> 与模型出自何处无关。

## 与兄弟技能的边界

- **`zj-tech-research-report`**（消费方）：负责"技术选型 / 开源选型"的**完整报告**
  （问题框定→选项→证据→语义拟合→所有权风险→验证闸门→建议）。本报告中的
  **capability-fit 判定环节**由本技能产出（R×O 矩阵 + A/B/C/D），report 引用本技能结论，
  不重做判定逻辑。本技能**不写报告**，只给决策仪器与决策记录。
- **`zj-research` / `zj-code-research`**（上游证据）：本技能要求矩阵单元带一手证据
  （固定版本代码 / 文档 / 可复现实验）；证据采集交给这两个技能，本技能只消费其结论。
- 本技能是**决策仪器**，不是方法论本体。模型定义唯一真源在
  `docs/agreements/open-source-capability-fit-decision-model.md`（SSOT），本文件不复述定义。

## 工作流

### 0. 范围闸门
确认本次是要**对外部 OSS 做拟合判定**（ingest/merge 决策、或上游变更后重评旧判定）。
若是写选型报告 → 调 `zj-tech-research-report` 并让其引用本技能；若是采证 → 调 `zj-research`。

### 1. 拆解 R 与固定 O（对齐模型 §递归评估流程 1–2）
- 把目标拆成可独立验收的需求 `R`，每项标 `priority`(must/want/nice) 与 `critical`。
- 固定每个候选 `O` 的版本（模型：能力结论必须来自固定版本）。

### 2. 填 R×O 证据矩阵（对齐模型 §3）
为每个 `(R, O)` 单元填 `coverage / semantic_match / composability / status / evidence`：
- `status` ∈ {native, adapted, unknown, unsupported}
- `evidence`：固定版本代码路径 / 文档章节 / 可复现实验（满足态必须有，闸门 G4）

### 3. 估 E 与适配层范围
- 填 `cost[O]` 六分量（初始开发 / 集成 / 持续维护 / 上游变化适配 / 运行运维 / 安全与治理）。
- 填 `adaptation[O].scope`：适配层触碰的类目，只允许"可控 B 薄层"，触碰"主体能力"触发降 C/D。

### 4. 跑仪器（机械闸门 + 计算）
```sh
# 把命令中的 <skill-dir> 替换为本 skill 目录的绝对路径，
# 例如 skills/research/zj-open-source-capability-fit
python3 <skill-dir>/scripts/capability_fit.py init --out fit_input.json

# 评估 + 产出决策记录
python3 <skill-dir>/scripts/capability_fit.py assess \
    --input fit_input.json --record decision_record.md

# 仅查闸门
python3 <skill-dir>/scripts/capability_fit.py validate --input fit_input.json
```
脚本输出每候选的**推荐分类 + 逐条依据 + 闸门状态**；任一硬闸门(G1–G4)未过退出码为 1，
提醒不要盲信。

### 5. 拍板与归档（对齐模型 §决策记录要求 + 完成标准）
Human/Agent 在决策记录「最终拍板」段填写：选定组合 C / 缺口 G / E / PoC 结论 / 最终分类 /
理由 / 风险 / 退出路径 / 重评触发条件。完成后做**完成标准自检**：第三方 Agent 仅凭本记录
能否复核分类依据并区分证据 vs 假设。

## 结构性闸门（机械校验，不是自觉约定）
由 `scripts/capability_fit.py` 在 `assess`/`validate` 中强制：G1 矩阵完整 / G2 需求字段 /
G3 版本固定 / G4 证据非空（**硬闸门**，不过则退出码 1、拒绝自信分类）；G5 未知项 PoC 为
**就绪度提示、不阻塞**（仅附理由，不影响退出码）。完整判定条件与后果见
`references/model-application.md` §3。

关键口径：模型 `D = 继续搜索`（搜索循环回环态，**非终态否决**）；`B` 细分 B1/B2/B3；
"可控 B = 可移除薄层"，适配层触碰主体能力则降 C/D。详见
`references/model-application.md`。

## References
- `references/model-application.md` — 输入 schema 映射 + 计算规则 + 闸门清单（指向 SSOT，不复制）。
- `references/decision-record-template.md` — 决策记录骨架（对齐模型决策记录要求 + 完成标准）。
- `scripts/capability_fit.py` — 确定性计算与闸门仪器（stdlib，零新依赖）。
- `tests/test_capability_fit.py` — 回归守卫（stdlib unittest，`python3 tests/test_capability_fit.py`）。
- 模型 SSOT — `docs/agreements/open-source-capability-fit-decision-model.md`。
