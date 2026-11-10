---
name: zj-graphical-cross-comparison
description: >-
  把《产品项目图式横比模型》操作化为带机械闸门的对比仪器：以 Human 独立给定的固定场景集为公共坐标系，
  校验多张项目图 SoT、供给四态与上下文三态、CHK-01..11 复核条件，产出逐条可追溯的差异条目清单。
  Use when 需要在多个产品项目之间做场景锚定的结构横比、核对项目图与差异条目形状、
  或在签发横比报告前跑机械自检；不产出采用或拒绝裁决，不重做母模型 R 乘 O 矩阵。
argument-hint: "<横比 bundle YAML/JSON 路径，或 init 的输出路径>"
source: zagentic

---

# zj-graphical-cross-comparison

## 定位

本技能是**方法论的操作化仪器**，不是方法论本体。权威定义在源仓库
`docs/agreements/product-project-graphical-cross-comparison-model.md`（仅源仓库维护、不随 skill 安装）；
本文件与 `references/model-contract.md` 只给可操作映射与形状约束。运行时只读本技能自带文件
与调用方显式给出的 bundle，从不读源仓库 docs。

## 与兄弟技能的边界

- `zj-open-source-capability-fit`（母模型）：单候选采用裁决、R 乘 O 矩阵、A/B/C/D 分类。本技能
  不重做判定；差异条目中 native / adapted / unsupported 只是**可选单向回灌素材**，母模型侧接口待定义。
- `zj-research` / `zj-code-research`：一手材料与固定版本证据的采集方，本技能只消费其结果。
- `zj-tech-research-report`：完整选型叙述报告，不是场景乘项目的逐条差异清单。

## 范围闸门

1. 是多个产品项目在同一组场景下的结构横比？若否（单候选采用、实现层代码 diff、性能基准、
   发布后运维对比）→ 停止并转对应技能。
2. 固定场景集是否已由 Human 独立给定且带版本 pin 与来源？若否 → 先向 Human 索取；
   **不得由任何项目图归纳**，也不得用 Stage 2 的可选场景集充当最终场景集。
3. 未决关系是否都已裁决？裁决人与生效版本为空的项 fail-closed，阻塞进入 Stage 3。

## 工作流（对齐 agreement 三阶段）

- **Stage 1 每项目一张独立图**：按自己的语义建图，不互相引用、不预先对齐；登记 project 级上下文条目。
- **Stage 2 原子化解构**：F / T 节点过三条原子化判据；竖切片 S 的成员列表是 SoT；横切路径 X
  单列并写 appears_in；依赖边 D 语义恒为 requires；图内关系约束 RC 不进有向依赖图；
  可选场景集逐项目原样摘录（Agent 零语义操作）；未决关系登记簿交 Human 裁决。
- **Stage 3 场景锚定对比**：S 到场景的映射留裁决；每个场景乘项目生成一条差异条目，判供给四态
  与上下文三态；场景内等价裁决引用双方 acceptance；Human 做盲区核对留痕；按固定八节结构签发报告。

## 机械闸门

`scripts/cross_compare.py` 把复核条件中可机械验证的部分做成确定性校验，任一 ERROR 即拒绝签发报告，
产出只能作为过程材料。

| 条件 | 脚本覆盖 | 仍需 Human |
| --- | --- | --- |
| CHK-01 版本与 ID | schema、版本 pin、稳定 ID 与前缀、图内唯一 | 证据是否真来自固定版本一手材料 |
| CHK-02 竖切片合法 | 至少 1 F 加 1 T、场景三要素、成员属于 V、D 恒为 requires | 原子化判据是否真的成立 |
| CHK-03 未决关系 | 裁决人与生效版本非空、未裁决阻塞 Stage 3 | 三种裁决结果的选择 |
| CHK-04 场景集外部性 | 声明不由项目图推导、场景不含节点或模块字段 | 场景集是否真由 Human 独立给定 |
| CHK-05 场景内等价 | 双方 acceptance 引用与裁决人 | 语义等价本身 |
| CHK-06 状态判据 | 四态证据、显式否定陈述、验证计划、上下文三态逐条 | 证据真伪与适配对象判断 |
| CHK-07 可选场景集 | 核对留痕存在 | 零语义操作与盲区核对 |
| CHK-08 孤儿节点 | 计算值与登记值一致，WARN 不阻塞 | 缺口清单的验证计划 |
| CHK-09 报告结构 | 八节齐全、三类来源标注、摘要只用 display-only | 第三方 Agent 能否复核每条差异 |
| CHK-10 上下文条目 | scope / kind / 证据、旁挂不进图 | 条件本身的成立与违反判定 |

## 快速开始

```sh
# 按 ADR 0010 落项目隔离区；脚本无显式 --out 时一个文件都不写
# .yaml/.yml 与 .json 都是一等输入：前者与 agreement 的 SoT 字面一致，
# 后者是 YAML 1.2 合法实例，供无 PyYAML 环境零依赖运行
export OUT_DIR=<项目根>/tmp/skills-outputs/zj-graphical-cross-comparison/<topic>
python3 <skill-dir>/scripts/cross_compare.py init --out "$OUT_DIR/bundle.yaml"
python3 <skill-dir>/scripts/cross_compare.py validate --input "$OUT_DIR/bundle.yaml"
python3 <skill-dir>/scripts/cross_compare.py report --input "$OUT_DIR/bundle.yaml" --out "$OUT_DIR/metrics.yaml"
```

把扩展名换成 `.json` 即走等价的零依赖路径；`init` 与 `report --out` 按目标扩展名决定输出形态，
输入则按扩展名分派、不靠内容猜测。YAML 路径复用仓库既有 PyYAML，缺失时明确报错、不静默降级。
`validate` 的诊断走 stdout；`report` 的诊断走 stderr、无 `--out` 时 stdout 是纯指标 JSON，便于下游消费。

## 硬纪律

- **差异条目清单是唯一结论载体**；摘要指标只展示，不参与排序 / 裁决 / 回灌 / 优先级。
- 上下文条目（constraint / data-contract / external-dep / actor）是旁挂清单：不进 V、不进 S.members、
  不进有向依赖图，也不进摘要指标分母。
- 竖切片成员列表是 SoT，Mermaid 只是人读投影；不得把投影里的中间节点当真实节点，也不得反推成员集。
- `unknown` 是证据缺口，`unsupported` 须绑定一手材料中的显式否定陈述；二者不可混用。
- 未裁决关系一律按 unknown 处理；执行 Agent 不得自行补边、自行推断语义等价或默认「无依赖」。
- 场景集里某场景无任何项目覆盖时仍保留该行：这是**绝对参照**，不是可裁剪的空行。
- 不改 agreement 定义；契约变更须由方法论 owner 与报告消费者共同确认。

## References

- `references/model-contract.md` — SoT 形状、四态 / 三态、CHK 清单、报告八节（操作化映射，不复制本体）。
- `scripts/cross_compare.py` — 确定性闸门与摘要指标（YAML / JSON 双形态；JSON 路径仅依赖 stdlib）。
- `tests/test_cross_compare.py` — 红绿回归守卫（stdlib unittest，含 YAML / JSON 等价性断言）。
- `tests/fixtures/valid-bundle.yaml` 与 `tests/fixtures/valid-bundle.json` — 语义等价的双形态合法基线。
