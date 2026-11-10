# 横比模型：操作化映射（非 SSOT）

本文件是《产品项目图式横比模型》到本技能仪器之间的**可操作映射**，用于约束输入与产出形状。
权威方法论定义在源仓库 `docs/agreements/product-project-graphical-cross-comparison-model.md`
（`authority-id: agreement.product-project-graphical-cross-comparison-model`），仅源仓库维护、
不随 skill 安装；相关判决见 ADR 0012（场景锚定）与其 Amendment（上下文条目旁挂）。
本文件不复制模型本体，也不替代 agreement 的变更流程。

运行时闭包：安装态只有本技能目录。本文件与 `scripts/cross_compare.py` 自包含，
不读取源仓库 docs；文中提到的 SSOT 路径仅供 Human 交叉核对。

## 1. 图定义与 ID

对任一产品项目 `P_i`，横比 item 是一张独立有向图：

```text
Graph_i = (V_i, S_i, D_i, X_i, RC_i)
V_i = F_i union T_i,  |V_i| >= 1
```

| 元素 | 记号 | 定义 | ID 前缀 |
| --- | --- | --- | --- |
| 产品特性节点 | F | 用户可感知、可独立陈述与验收的功能或价值单元 | `F::` |
| 技术能力节点 | T | 实现侧可独立陈述与验收的能力单元 | `T::` |
| 竖切片超边 | S | 把一个可观察端到端场景连成一组 F 与 T | `S::` |
| 依赖边 | D | 语义恒为 requires：实现 from 需要 to | `D::` |
| 横切路径 | X | 在多条竖切片中重复出现的体验路径 | `X::` |
| 图内关系约束 | RC | kind 为 mutually-exclusive 或 ordering，不进有向依赖图 | `RC::` |
| 上下文条目 | CTX | 旁挂清单，**不属于 Graph_i 元组** | `CTX::` |
| 场景 | SC | 固定场景集中的可观察场景 | `SC::` |
| 差异条目 | DE | 场景乘项目一条，唯一结论载体 | `DE::` |

节点属性：`id` / `statement` / `acceptance` / `evidence-ref`（可为空）/ `semantic-owner`（可选）/
`indivisible`（可选）。元素级不承载供给状态；供给判定只发生在差异条目上，参照系是场景。

跨项目引用写作 `<project-id>::<element-id>`。ID 一旦发布不复用、不重命名。
`valid_id` 校验前缀与 `::` 结构；跨图允许同名（项目私有命名空间），图内不允许重复。

## 2. 上下文条目（不是图元素）

四类 kind：`constraint`（非功能约束）/ `data-contract`（数据契约）/ `external-dep`（外部依赖）/
`actor`（参与主体）。`scope: domain` 归固定场景集所有、由 Human 给定；`scope: project` 归各自
`Graph_i`、Stage 2 收集。

它们**不进 V、不进 S.members、不进有向依赖图、不进 RC.members，也不进摘要指标分母**。
理由：原子化判据对它们失效；`S.members` 是 V 的子集；SCC、依赖闭包与扇入在异构图上语义崩坏。
差异条目用 `context-refs` 引用、`context-verdicts` 逐条判定，才能表达「能力结构相同但上下文条件不同」。

## 3. bundle JSON 形状

agreement 的机器可读 SoT 最小形状以 YAML 给出，本仪器**直接消费该 YAML 形态**（一等输入，
与 SSOT 字面一致）。JSON 是 YAML 1.2 的合法实例：同一份 bundle 换成 `.json` 即可在
无 PyYAML 的环境零依赖运行，两种形态语义必须完全一致（由 `tests/test_cross_compare.py`
的等价性断言钉死）。脚本按文件扩展名分派，不靠内容猜测。顶层：

```text
schema                      固定为 zj-graphical-cross-comparison/bundle/v1
scene-set                   id / version-pin / source / derived-from-graphs:false / scenes / context-entries
graphs[]                    每项目一张：project / version-pin / nodes / slice-edges /
                            cross-cutting-paths / dependency-edges / relation-constraints /
                            context-entries / undeclared-relations / orphan-nodes
scene-mapping[]             slice -> scene，带 ruling-ref 与 ruling-by
equivalence-rulings[]       场景内等价裁决，须引用双方 acceptance
optional-scene-pool-review  Human 盲区核对留痕
difference-entries[]        场景乘项目一条，见第 4 节
report-sections[]           固定八节，每节标注 sources
summary-metrics-usage       必须为 display-only
```

关键形状约定：

- `slice-edges[].scenario` 是对象，含 `start` / `end` / `observable` 三个非空字符串。
- `slice-edges[].members` 是 SoT 数组；Mermaid 投影的中间节点不得写入 `nodes`。
- `dependency-edges[].relation` 缺省即 requires；出现其它值即判非法。
- `undeclared-relations[]` 每条须含 `ruling-by` 与 `effective-version`；二者为空 = 未裁决。
- `context-verdicts[].ref` 集合必须与 `context-refs` 完全一致。
- `report-sections[]` 的 `sources` 子集为 `evidence` / `human-ruling` / `assumption`。

最小合法样例见 `tests/fixtures/valid-bundle.yaml`，它与 `tests/fixtures/valid-bundle.json`
语义等价；空模板由脚本 init 生成，输出形态随 `--out` 扩展名（`.yaml` / `.json`），
`--out` 必填、不默认任何路径。`init` 与 `report --out` 不会在缺少 PyYAML 时静默改投 JSON，
而是明确报错并提示改用 `.json`。

## 4. 两套枚举，不得混用

供给四态，参照系是**场景**，不是我方架构：

| 状态 | 判据 | 仪器校验 |
| --- | --- | --- |
| native | 至少一条竖切片映射到该场景、成员完备、有一手材料证据 | evidence-refs 非空 |
| adapted | 有覆盖证据但需适配，须点明适配对象与证据 | evidence-refs 非空 + adaptation-target |
| unsupported | 一手材料中有显式否定陈述 | negative-statement-ref 非空 |
| unknown | 既无覆盖证据也无否定陈述，只进缺口清单 | verification-plan 非空，不进定量部分 |

上下文三态是另一套枚举：`satisfied`（有证据成立）/ `violated`（显式否定证据）/
`unknown`（两者皆无，须附最小验证计划）。`context-verdicts` 不改变 `verdict`，
它补的是「两个项目都 native，但一个数据不出域、另一个依赖第三方 LLM API」这一类差异。

## 5. 复核条件 CHK-01..12

| 条件 | 后果 | 仪器 |
| --- | --- | --- |
| CHK-01 版本与 ID | 不得签发报告 | 机械 |
| CHK-02 竖切片合法 | 拒绝该边 | 机械 + Human 判原子化 |
| CHK-03 未决关系 | 不得进入 Stage 3 | 机械验留痕；未裁决关系一律 error（fail-closed），不再降级为 warning，Human 裁决内容 |
| CHK-04 场景集外部性 | 不得签发报告 | 机械验形状，Human 验来源 |
| CHK-05 场景内等价 | 该节点对不写共有语义 | 机械验引用，Human 裁决等价 |
| CHK-06 状态判据 | 该条目退回 | 机械 |
| CHK-07 可选场景集 | 退回 Stage 2-f | 机械验留痕，Human 做核对 |
| CHK-08 孤儿节点 | 就绪度提示，不阻塞 | 机械（WARN） |
| CHK-09 报告结构 | 不得签发报告 | 机械验八节与来源标注，Human 验可复核性 |
| CHK-10 上下文条目 | 该条目退回 | 机械验 scope / kind / 证据与旁挂 |
| CHK-11 场景映射裁决 | 该映射退回 | 机械验 ruling-ref / ruling-by 留痕与 slice / scene 引用合法性，Human 裁决内容 |
| CHK-12 差异条目基数 | 不得签发报告 | 机械验每条 DE 的 scene 引用固定场景集、project 匹配某图，且 (scene, project) 对集合恰为 \|scenes\|×\|projects\| 全集（缺 / 重 / 溢一律 error），Human 裁决内容 |

任何条件不满足时产出仍可保留为**过程材料**，但不得标注为已完成的横比报告。
仪器对「零语义操作」「证据真伪」「语义等价」这类不可形式化的部分一律只验留痕，不做推断；
这是 fail-closed 的一部分，不是覆盖率缺口被静默接受。

## 6. 摘要指标（不参与结论）

```text
证据绑定覆盖率 = 已绑定固定版本证据的图元素数 / 全部图元素数
竖切片覆盖率   = 被至少一条 S 连接的节点数 / 全部节点数
共享度         = 出现在 >=2 条 S 中的节点数 / 全部节点数（X 不计入）
SCC 规模分布   = D 有向图上每个环的节点数分布（只有环算「不可单独交付」）
最大依赖闭包   = max over v of |closure(v) 并上 {v}|
扇入分布       = 各节点入度分布
未决存量       = 登记簿中裁决人为空的条目数
```

分母只含 V / S / D / X / RC，**上下文条目不计入**。无向连通分量不进入本模型：忽略 requires
的方向会把可独立交付的依赖方与共享底座绑成一团，系统性虚增工作量单元。
所有指标只作清单摘要，不得用于排序、裁决、回灌或确定优先级；仪器输出恒带
`not_for_conclusion: true` 与 `usage: display-only`。

## 7. 报告固定结构（缺节即 CHK-09 不过）

1. 图清单与版本 pin（含 domain 级上下文条目清单）
2. 场景映射表与映射裁决记录
3. 差异条目清单（逐条：场景 / 项目 / 供给四态 / 支撑切片 / 节点集 / 证据 / 映射裁决 /
   上下文引用与三态判定 / 验证计划）
4. 可选场景集核对留痕
5. 场景内语义等价裁决记录（含双方 acceptance 引用）
6. 摘要指标（标注「不参与结论」）
7. 与母模型的可选回灌素材（明确母模型侧接口待定义）
8. 完成标准自检（第三方 Agent 能否仅凭报告复核每条差异，并区分证据 / Human 裁决 / 假设）

每节须标明其中每条陈述属于三类来源中的哪一类；Human 裁决不得写成证据，假设不得写成裁决。

## 8. 与母模型的可选回灌接口

差异条目中 native / adapted 的能力，以及 unsupported 的明确缺口，可作为母模型后续建立
R 乘 O 矩阵的**素材**。母模型是否接纳、如何拆解为单位能力、如何计算缺口与成本、如何判定
A / B / C / D，均由母模型自己定义。本技能不声明该接口已存在，不重做判定，
也不把横比结论写成采用结论。

## 9. 不变量速查

1. 每元素有稳定 ID，以及固定版本证据绑定或显式证据状态。
2. 竖切片成员列表是 SoT，Mermaid 只是投影。
3. unknown 不等于 unsupported。
4. 各图独立建成，不互相引用、不预先对齐；跨项目对齐只经场景映射发生。
5. 未决关系必须登记；未裁决时按 unknown 处理，不进差异条目的定量部分。
6. 摘要指标不参与结论。
7. 固定场景集只描述场景，不规定节点或模块。
8. 上下文条目不进 V、不进 S.members、不进有向依赖图；domain 级同样不规定实现划分。
9. 单字母 C 只用于引用母模型的 Compose 项；本模型的图内关系约束写 RC、复核条件写 CHK-nn。
