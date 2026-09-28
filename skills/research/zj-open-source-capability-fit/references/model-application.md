# 模型应用指南 (zj-open-source-capability-fit)

> 本文件是《开源能力拟合决策模型》的**应用映射**，不是模型副本。
> 模型本体与权威定义见
> [docs/agreements/open-source-capability-fit-decision-model.md](../../../docs/agreements/open-source-capability-fit-decision-model.md)
> （ingested from `jununfly/ZInitiatives`，状态：已接受）。
> 任何与模型本体的分歧一律回到 SSOT，不在本文件改写定义。

本指南把模型的七个环节映射到 `scripts/capability_fit.py` 的输入与计算，确保操作化忠实于模型。

---

## 1. 输入 schema 映射 (JSON)

`capability_fit.py assess --input <file.json>` 接受如下结构：

| 字段 | 模型环节 | 说明 |
| --- | --- | --- |
| `goal` | 目标 | 一句话描述 R 要满足什么 |
| `requirements[]` | `R` 需求集合 | 每项含 `id` / `statement` / `priority`(must\|want\|nice) / `critical`(bool) / `acceptance` |
| `candidates[]` | `O₁…Oₙ` | 每项含 `id` / `name` / `url` / **`version`(固定版本，闸门 G3 强制)** / `license` |
| `matrix[O][R]` | `R × O` 证据矩阵 | 每格含 `coverage` / `semantic_match` / `composability`(∈[0,1]) / `status`(native\|adapted\|unknown\|unsupported) / `evidence` / `notes` |
| `cost[O]` | `E` 总所有权成本 | 六分量：`initial_dev` / `integration` / `maintenance` / `upstream_adapt` / `ops` / `security_gov` |
| `adaptation[O]` | 可控 B 边界判定输入 | `scope`(适配层触碰的类目) / `mode`(B 细分) / `responsibility_uncontrolled` / `poc_plan` |

生成空白模板：`python3 scripts/capability_fit.py init --out <path.json>`。

---

## 2. 计算规则映射

### 两判定量 (模型 §"两个判定量")
- **有效拟合度** = `coverage × semantic_match × composability`（每因子先 clamp 到 [0,1]）。
- **总所有权成本 E** = 六分量之和。
- 任何关键能力缺失，都不能由非关键能力的高覆盖率抵消（见 §3 关键缺口检测）。

### 缺口与组合 (模型 §核心模型)
- `G = R - C`：未被满足的关键需求比例由 `must_coverage` 报告；具体缺口在决策记录里逐格列出。
- 矩阵单元状态区分 `native / adapted / unknown / unsupported`，只有 `native` 或 `adapted` 且有效拟合度 ≥ `FIT_OK`(0.9) 才计为满足（`evidence` 非空，闸门 G4）。

### 决策分类 (模型 §决策分类 + §可控 B 边界)
推荐分类由脚本给出**可复核依据**，最终分类由 Human/Agent 拍板（模型：优先顺序非强制结论，偏离须记录理由）：

| 触发条件 | 推荐 |
| --- | --- |
| 关键需求 unsupported / unknown / 有效拟合度 < `FIT_FAIL`(0.5) | **D**（继续搜索，搜索循环回环态，非终态否决） |
| 适配层触碰主体能力(禁止类目) 且 (责任不可控 或 E>`E_HIGH`) | **D** |
| 适配层触碰主体能力(禁止类目) 但责任可控 | **C** |
| 关键需求存在部分缺口(0.5≤fit<0.9) 且 E≤`E_MID` | **B**(有适配层) / **C** |
| 关键需求存在部分缺口 且 E>`E_MID` | **C** |
| 关键完整、无适配层、E≤`E_LOW` | **A**（直接采用） |
| 缺口小且可控、E≤`E_MID`、声明 `mode` | **B1/B2/B3**（按 mode 细分） |
| 缺口小且可控、E≤`E_MID`、未声明 `mode` | **B**（须声明 mode 细分） |
| 成本 E>`E_MID` | **C**（自有架构为主体） |

`B` 细分（模型 §扩展采用进一步区分）：
- `B1`：`mode ∈ {adapter, plugin, sidecar}`，不维护 fork
- `B2`：`mode = upstream-contrib`，承担贡献被拒/延迟风险
- `B3`：`mode = fork`，维护长期 fork 并吸收上游

### 可控 B 边界 (模型 §可控 B 的边界)
`adaptation.scope` 只允许下列**薄层**类目（`ALLOWED_ADAPT`），触碰下列**主体能力**类目（`FORBIDDEN_ADAPT`）即触发降 C/D：

- 允许薄层：身份映射 / 查询适配 / 状态转换 / claim·lease 等小型协调语义 / 来源与可追溯适配
- 禁止主体能力：存储和同步基础设施 / 完整检索或记忆流水线 / ACL 和权限系统 / 完整工作流或任务平台

---

## 3. 机械闸门 (脚本强制，不靠自觉)

| 闸门 | 校验 | 不过的后果 |
| --- | --- | --- |
| G1 矩阵完整 | 每个 `R × O` 单元齐全 | 拒绝分类 (`BLOCKED`) |
| G2 需求字段 | 每项有 `priority` 与 `critical` | 拒绝分类 |
| G3 版本固定 | 候选 `version` 非空（模型：固定每个候选版本） | 拒绝分类 |
| G4 证据非空 | 满足态(native/adapted)单元 `evidence` 非空（模型：结论须来自一手资料） | 拒绝分类 |
| G5 未知项 PoC | 未知单元须有 `poc_plan`（模型：未知项消除或有可接受验证计划） | **就绪度提示**（不阻塞，附理由；要退出 D 进实施须补 PoC） |

`assess` 在任一硬闸门(G1-G4)未过时退出码为 1，提醒不要盲信推荐分类。

---

## 4. 递归与停止 (模型 §递归评估流程 / §搜索与停止规则)
脚本对**单轮**给定 R 与 O 做评估与分类。若推荐为 `D`，按模型回到第 2 步引入新候选重评；停止规则（关键需求均有固定版本证据 / 未知项已消或有计划 / G·E·风险·退出路径明确 / 分类判据一致 / 验收与止损已定义）由 `decision-record-template.md` 的「完成标准自检」承载。
