# zj-discuss — 架构文档（Architecture）

> 长期权威页。产品定义见 `product.md`，完整行为规格见 `design.md`。
> 角色语义唯一真源：`skills/productivity/zj-discuss/references/role-matrix.md`。

## 1. 组件图

```
                       zj-discuss  (生命周期 owner / 编排器)
                       ├─ references/master-template.md   MASTER 骨架
                       ├─ references/subdoc-template.md   子文档骨架(角色数无关)
                       ├─ references/role-matrix.md       ★ 角色候选池 + 推荐启发式 (SSOT)
                       └─ 议程引擎 (固定议程 F1–F5 + 动态议程决策函数)
                              │ 为每个角色生成 briefing
                              ▼
       跨会话独立 Agent（每角色一个会话）── 加载 zj-discuss-view --role X
                                              └─ Read 原文 → 写 ## Agent viewpoints
                       └─ 阶段 2：zj-docs-ontology（分类/迁移/删除，Human 确认闭环）
```

| 组件 | 职责 | 边界 |
| --- | --- | --- |
| `zj-discuss` | 分解、准备阶段角色推荐、生成 briefing、动态议程编排、合成回卷、阶段 2 指针 | 不做兄弟技能已覆盖的能力；不建会话运行时 |
| `zj-discuss-view` | companion：在**独立会话**按指派角色写独立视角 | 只写视角，不合成、不编排 |
| `role-matrix.md` | 角色候选池 + 推荐启发式 + 收敛规则 | 角色语义唯一真源，其他文件只引用 |
| 模板 | MASTER / 子文档骨架 | 子文档视角区块按声明集动态生成 |
| 议程引擎 | 固定议程（底线）+ 动态议程（自适应编排） | 动态议程不得删减固定阶段 |

## 2. 生命周期状态机

```
[Phase 0 范围闸门] → (是复杂问题?) → 否: 走 steelman/grilling/直接chat
        │ 是
        ▼
[Phase 1 分解 + 准备] → 候选分解(SubAgent) → 角色选取(Human) → 建 discussions/<slug>/
        │                  + MASTER + 子文档 stub
        ▼
[Phase 2 每子文档独立讨论] → 生成 briefing → 跨会话 Agent 写视角 → Human 拍板
        │                     ↺ 动态议程可增聚焦轮/协调轮 (不删固定阶段)
        ▼
[Phase 3 合成回卷] → 增量更新 MASTER 索引 → 终局重写解决思路
        ▼
[Phase 4 处置契约] → 阶段 1 完成；待 Human 触发 zj-docs-ontology
        ▼
[Phase 2(治理) zj-docs-ontology] → 分类 → 沉淀 → Human 确认 → 删除文件夹
```

## 3. 文件结构（求解期产物）

```
discussions/<self-explain-slug>/        # 仓库根，无 discuss- 前缀
  MASTER.md                             # 核心问题 + 解决思路 + 文档索引 + 跨子文档约束 + 处置契约
  sub-01-<slug>.md                      # 独立子问题 + 待讨论问题 + 各角色视角 + 拍板 + conclusion
  sub-02-<slug>.md
  ...
  briefings/                            # transient 脚手架，阶段 2 删除候选
    sub-01-<slug>-briefing-<role>.md
```

> `discussions/` 为仓库自定义分类，未跟踪时按 zj-docs-ontology 的 target-defined 处理，
> 不纳入受管文档图谱。

## 4. 角色池与选取机制

- **候选池**（base + 可选）：B 技术经理 / C 产品专家 / A 架构师（base ✅）；
  T 测试·质量 / S 安全 / O 运维·SRE / D 数据 / L 法律·合规 / F 财务·成本 /
  U 用户研究·UX / R 学术·研究 / P 流程·组织 / E 伦理·社会（⚪ 候选）。
- **准备阶段推荐**：base 永远推荐；子问题命中某信号（如含验收标准→T、涉权限→S）
  则追加；向 Human 呈现「推荐角色（带一句话简介+理由）」+「其他可选（带一句话简介）」，
  Human 调整后锁定为**声明必需集**。
- **声明必需集驱动收敛**：覆盖即停，角色数量与映射不写死。

## 5. 议程引擎

- **固定议程 F1–F5**：定义核心问题 / 角色确认分发 / 各角色独立有效观点 /
  Human 逐轮拍板 / 合成共识沉淀。**不可跳过**。
- **动态议程**：状态评估（开放问题闭合度 / 观点有效性 / 张力 / 收敛）→ 决策下一轮
  （聚焦轮 / 协调轮 / 重开真隔离会话 / 继续剩余角色 / 触发合成）。借鉴动态规划/
  自适应控制的「依状态决定下一步」思想，只在固定框架内加深覆盖，不为凑数加视角。

## 6. 兄弟技能边界（引用而非重做）

| 兄弟技能 | 边界 |
| --- | --- |
| `zj-steelman` | 防御式辩护（判 Strong/Adequate/Weak）；discuss-view 是协作式结构错位，不变式互斥，禁止共享实现 |
| `zj-handoff` | briefing := handoff 压缩契约 + discuss 专属两行头；discuss 不重造压缩逻辑 |
| `zj-docs-ontology` | 阶段 2 只吐 `<conclusion>+<suggested-category>+<pointer>`，绝不运行 docs_governance.py |
| `zj-grilling` | 进入 discuss 前用于锐化核心问题 framing |

## 7. 决策模型分类（本仓库自创方法论 SSOT）

> 模型定义见本仓库 `docs/agreements/open-source-capability-fit-decision-model.md`（自创方法论 SSOT）。

全局分类 = **C（选择性复用）**：gstack 作组件来源（启动包形态、`--all`、跨 provider 评审范式、
状态协议、轻量度量注册表、digest 的 voice 部分），zj-discuss 方法体系为自有主体。
**否决** 运行时编排器 / suite-化（触发约束 1 → D）。

> 具体边界（R5）与度量 schema（R4）见 `design.md` §8 / §9。
