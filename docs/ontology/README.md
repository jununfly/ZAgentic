# ZAgentic 文档化系统 · 统一本体 + 知识图谱

`docs/` 是 ZAgentic 代码库（技能集合）的**文档化系统**。本目录是这套系统的
**统一本体（实体/属性/关联/规则）+ 知识图谱（KG）** 的家——注意：这里不再是
"两套 ontology"，而是**一份**本体的两个 concern 模块（详见 [`ONTOLOGY.md`](./ONTOLOGY.md)
第 0 节）：

- **Module G（治理层）**：文档系统自身的分类/权威/生命周期契约
  （`doc-kind` 词表、`authority` 层级、`docMapBinds` 1:1 绑定、`MAP_*` 检查）。
  由可移植技能 `skills/codebase-docs/zj-docs-ontology` 实现。
- **Module P（产品域层）**：ZAgentic 作为技能集合产品的领域模型
  （`Platform`/`SkillBucket`/`Skill`/`Pipeline`/`Validator`）。ZAgentic 本地实现。

四个工程目标由这份统一本体承载：

| # | 目标 | 这里怎么落地 |
| --- | --- | --- |
| 1 | 语义统一，消除歧义 | [`ONTOLOGY.md`](./ONTOLOGY.md) 与 [`ontology.schema.json`](./ontology.schema.json) 固定术语与权威锚点（`authority-id`）；两模块共用一份词汇，不再有"ontology 命名撞车"。 |
| 2 | 支持推理与约束校验 | [`validate.py`](./validate.py) 一次跑 Module G（`MAP_*` 由组合进来的治理脚本覆盖）+ Module P 全部规则。 |
| 3 | 让 Agent/Human 懂业务 | 实体与关联即"业务词汇表 + 关系网"：`Skill→SkillBucket→Platform`、`ArchitectureView→Design→ADR` 两条主线。 |
| 4 | 可复用、可设计、增删改保持新鲜度 | 图谱由 [`extract.py`](./extract.py) 从**活代码树**重生成；改动后重跑校验立即暴露漂移。 |

## 文件职责

| 文件 | 模块 | 角色 | 何时改 |
| --- | --- | --- | --- |
| `ONTOLOGY.md` | G+P | 人类可读概念主干（T-Box）：实体/属性/关联/规则，含两层结构说明 | 术语或约束本身演进时 |
| `ontology.schema.json` | G+P | 机器可读本体 + 规则清单（单一真相源，每条标 `module`） | 与 ONTOLOGY.md 同步 |
| `extract.py` | P | 从 `skills/`、`personal/`、`docs/` 生成知识图谱（A-Box），支持 `--repo` | 无需手改；随活树自动产出 |
| `validate.py` | G+P | 推理 + 约束校验（组合治理脚本覆盖 Module G），支持 `--repo` | 无需手改 |
| `tests/test_ontology.py` | P | 产品域集成测试（图谱规模 + Module P 规则） | 改动抽取/校验时 |
| `graph.json` | — | 生成的图谱实例（**不提交**，按需再生） | 运行 extract 时产出 |

## 工作流（保鲜核心）

```bash
# 1) 再生图谱（增删改技能/文档后第一步；或直接让 validate 自动重生）
python3 docs/ontology/extract.py > docs/ontology/graph.json

# 2) 推理 + 约束校验（一次覆盖 Module G + Module P；CI / pre-commit 钩子）
python3 docs/ontology/validate.py                      # 自动从活树生成图谱并校验
python3 docs/ontology/validate.py docs/ontology/graph.json   # 或校验已落盘图谱

# 3) 产品域集成测试
python3 docs/ontology/tests/test_ontology.py
```

- **新增技能**：放入 `skills/<bucket>/<name>/` → 重跑 → 若缺 frontmatter 或桶未注册，`rule.every-skill-discoverable` 报红。
- **新增文档**：frontmatter 声明 `doc-kind`/`authority`/`authority-id`；主视图须满足 `rule.stable-authority-id`。
- **改桶结构**：`rule.bucket-reorg-is-adr-bearing` 要求先有 ADR；否则 `rule.bucket-inventory-consistent` 抓出文档与活树不一致。
- **改 doc-map（docs/README.md）**：务必遵守 `rule.G1-docmap-binding`——每个 `authority-id` 用独立 bullet 绑到恰好一页，且描述性文字/表格中不要夹带 markdown 链接（否则绑定探测器会把游离链接折进前一个 id）。
- **人工评审项**（契约/夹具，如 `rule.contract-before-graduation`、`rule.immutable-fixtures`）由 reviewer 依据 `designs/ui-agent-skills/` 下对应规格核对，不进自动校验。

## 设计原则

> **图谱是派生事实，活代码树是唯一真相源。** 本体（本目录）只在术语/约束演进时改；
> 日常增删改只动代码树 + 重跑脚本，即可让文档系统长期保持高新鲜度，且 Agent 与 Human
> 都能从同一套实体/关联读懂业务。Module G 的治理逻辑由可移植技能 `zj-docs-ontology`
> 单一拥有，本仓库通过组合调用复用，不重复实现（治理契约明确容忍技能间不跨目录 import）。

> 部署二分：Module G 随技能便携（可装到任意代码库），Module P 留在本仓库
> `docs/ontology/`。`validate.py` 通过组合调用 `docs_governance.py --validate`
> 把两个模块的检查并入同一次运行——对使用者而言是"一个命令、一份报告"。
