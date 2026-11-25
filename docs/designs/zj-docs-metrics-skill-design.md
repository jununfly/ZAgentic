---
doc-kind: design
authority: primary
authority-id: design.docs-metrics-skill
---

# zj-docs-metrics 设计文档（与实现对齐）

> 本页描述 `skills/codebase-docs/zj-docs-metrics/` **实际实现的设计**。所有断言对应
> `scripts/docs_metrics.py` 的真实控制流、`references/health-contract.md` 的契约、以及
> `tests/test_docs_metrics.py` 钉死的行为。它**不是**操作指南；调用步骤见 skill 自身 `SKILL.md`。

## 1. 定位：measurement 是独立于 correctness 的第三轴

skill 链里有三种正交主张，本 skill 只拥有第三种：

| 主张 | 归属 skill | 诊断族 | 性质 |
|---|---|---|---|
| "地图是对的"（map correctness） | `/zj-docs-ontology` | `MAP_*`、`RETIRE_*`、`UNMAPPED_PAGE`、typed relations（`derived-from`/`supersedes`/`supports`）、Module D | correctness |
| "结构是对的"（structure correctness） | `/zj-docs-architecture` | `PAGE_*`、`SOURCE_TARGET_*`、`ADR_UNACCEPTED`、`AUTHORITY_ID_*`/`AUTHORITY_MAP_BINDING`、概念图 `CONSIST_*`/`CONCEPT_CYCLE` | correctness |
| "页面是活的"（measurement） | **本 skill** | `BUDGET_EXCEEDED`、`FRESHNESS_DRIFT`、`NAV_ORPHAN`、`MAP_ONLY` | advisory |

实现上本 skill **不发任何 correctness 诊断、借不到任何门禁权威**（`health-contract.md`
「Status in the skill chain」）。它的 verdict 是给 Human 的离群点（outlier），不是缺陷裁定。
这条边界是设计的根：`measure()` 的返回类型是 `list[dict[str, str]]`（离群点表），不是
错误码集合，也没有 `proposed_actions`/`mutations` 之类写动作概念。

> **[现状]（2026-11 refresh，对齐两个邻居 skill 重构后）** 上表诊断族已据磁盘现状更新：architecture 在 #288–#294 概念图层新增 `CONSIST_UNDOC`/`CONSIST_ORPHAN_DOC_CLAIM`/`CONSIST_OWNER_MISMATCH`/`CONCEPT_CYCLE`/`AUTHORITY_MAP_BINDING`（`validate_architecture_docs.py:469`）；ontology 新增 `UNMAPPED_PAGE`、typed-relation 图上的 `ORPHAN_PAGE`（`docs_governance.py:817`）、Module D `ONTOLOGY_*`（`validate_ontology_model.py:149`）。**关键：architecture 的 `SOURCE_*` 现状仅 `SOURCE_TARGET_MISSING`/`SOURCE_TARGET_OUTSIDE`（存在性/越界，`validator-contract.md:98-104`），不含任何时间新鲜度码**——见 §10 的归属空洞。

> **[定稿]（本轮锁定的定位与功能边界）** 本 skill 一句话定义 = **对一个仓库「活页集合」做纯拓扑 + 纯物理属性的 advisory 度量器：刻意零语义判定、零门禁、零跨-skill 契约依赖**。由此推出一条**硬功能判据**：一个指标能否只读「活页本身 + 普通 markdown 链接图 + 文件物理属性」就算出来？能 → 核心功能；需要**复制**邻居 skill 的契约语法才能算 → 定位冲突点。据此功能集分两层——
> - **核心（纯自包含）**：`BUDGET_EXCEEDED`（物理行数）、`NAV_ORPHAN`、`MAP_ONLY`（链接图拓扑）。
> - **条件保留（best-effort 消费者）**：`FRESHNESS_DRIFT`——它依赖 architecture 拥有的 `## Source map` fact source，故只能以「非权威消费者」身份存在，定性见 §10.3。
>
> 硬判据同时是**准入闸门**：未来任何新 meter，只要需要读邻居契约，默认不进本 skill（除非重定性为消费者级 advisory）。

> **[命名定稿]（本轮，细节全收口）** skill 由 `zj-doc-health` 改名 **`zj-docs-metrics`**，并入 `zj-docs-` 家族（对齐 `zj-docs-ontology`/`zj-docs-architecture`）。两条硬依据：① `health`/「Health check」在组内已被 `zj-docs-ontology` 的 **L1** 占用（`SKILL.md:3`/`:22`/`:100`）且语义正交（那是 correctness，本 skill 是 advisory）；② 本 skill 的魂是**反 health 裁定**——契约拒绝「机械 health-score gate」（`health-contract.md:21`、`governance-contract.md:369-372`），且全仓（README / ZJ-CONTEXT / 3 个 roadmap design，如 `zj-roadmap-visual-review-technical.md:408`）拿 `zj-doc-health` 举证「不做 health 门禁」，名实相反。
>
> **命名映射**（根名统一复数 `docs_metrics`，因单次调用 = 整仓一批 docs）：
> - skill 目录 / 调用串：`zj-doc-health` → **`zj-docs-metrics`**
> - opt-in 配置：`docs/doc-health.json` → **`docs/docs-metrics.json`**（你定，接受 `docs/docs-` 重复换复数一致；本仓无既有该文件，作废成本 0）
> - 引擎脚本：`scripts/doc_health.py` → **`scripts/docs_metrics.py`**
> - 测试文件：`tests/test_doc_health.py` → **`tests/test_docs_metrics.py`**（**保留 `test_` 前缀**：本仓 CI 靠 `unittest discover -p` 收集，丢前缀会静默漏跑）
> - meter 码（U3，与本改名合并为同一 PR）：`ORPHAN_PAGE` → **`NAV_ORPHAN`**、`ZERO_INDEGREE` → **`MAP_ONLY`**
>
> **改名沿革注**：上列旧名为**改名前的有意保留**（记录从 `zj-doc-health` 家族词迁移而来的对照）；文档其余部分的 `zj-doc-health`/`doc_health.py`/`test_doc_health.py`/`doc-health.json`/`ORPHAN_PAGE`/`ZERO_INDEGREE` 均已随本次执行统一为新标识符。
>
> **执行状态**：本文档所述改名已落地于 feature 分支 `feat/zj-docs-metrics-rename`（`git mv` 目录/脚本/测试、码常量化 `NAV_ORPHAN`/`MAP_ONLY`、config→`docs-metrics.json`、SKILL.md/README/zj-guide/ZJ-CONTEXT 同步；3 个 roadmap 引用按 D4 保留旧名加注）。17 项回归测试全绿。
>
> **调用粒度定稿**：单次调用 = 整仓一批 docs（`parser.add_argument("repo")`、`root.rglob("*.md")`、输出恒为跨页 outlier 表；`NAV_ORPHAN`/`MAP_ONLY` 是图级指标故必然批处理）。**不加 `--scope`**——改名不得悄悄扩语义面。

## 2. 顶层控制流（`main()`，`docs_metrics.py:184`–`:207`）

```
python3 scripts/docs_metrics.py <repo> [--config <path>]
   │
   ├ root = args.repo.resolve()                    # 绝对化，相对路径全部以此为基准
   ├ load_config(root, args.config)                # → (config_path, config)
   │     ├ config_path is None  → 打印 status:"opt-in"，return 0     # 没配置 = 不度量（:191–:194）
   │     └ isinstance(config,str)→ 打印 status:"config-error"，return 1（:195–:198）
   ├ outliers = measure(root, config)              # 唯一有副作用外观的函数，实际纯读
   └ 打印 status:"measured" + mode:"read-only-report" + outliers
         return 1 if outliers else 0              # （:207）
```

三条不变式贯穿：

1. **只读**：脚本无任何写文件/`git` 写/mkdir 调用；`test_the_tool_never_writes`
   （`test_docs_metrics.py:133`–`:141`）用 `rglob` 全量比对 measure 前后的 `(path, mtime_ns, bytes)`，
   钉死「零写入」。
2. **opt-in 优先**：无配置文件即 `status:"opt-in"` + exit 0，绝不猜测参数、绝不为未采纳本套
   skill 的仓库产生物。
3. **report-only**：`outliers` 是提议面。修复由 Human 路由到归属 skill——预算改写/重挂到
   `/zj-docs-ontology`，过期声明到页面 owner，退役候选到退役路径（`SKILL.md` Workflow 第 3 步）。

## 3. 配置面与可移植边界（`load_config`，`:172`–`:181`）

- 默认路径 `root/docs/docs-metrics.json`；`--config <path>` 覆盖（`explicit` 时 `candidate = Path(explicit)`）。
- 文件不存在（`not candidate.is_file()`）→ 返回 `(None, None)` → opt-in。
- 文件存在但 JSON 解析或读取失败 → 捕获 `(ValueError, OSError)` → 返回 `(candidate, f"unreadable config: {error}")`，
  即 **config 槽位放字符串**作为错误哨兵，`main()` 据此走 `config-error`。
- 设计要点（`health-contract.md`「Output and exit codes」）：`config-error` **也 exit 1**——「读不懂的参数化」绝不能伪装成
  「健康检查通过」。这与 opt-in（exit 0）刻意相反：未配置是「没被邀请」，坏配置是「被邀请但无法履约」。

配置 schema（自由字典，本 skill 不定义第二套语法，只读这三类键）：

```json
{
  "budgets":  [ {"glob": "docs/prds/*.md", "max_lines": 120} ],
  "freshness": {"max_age_days": 30},
  "orphans":  true
}
```

三类键各自独立可选：缺 `budgets`/`freshness`/`orphans` 只是对应 meter 不跑，不报错。

## 4. 两个核心谓词：`living_markdown` 与 `resolve`

几乎所有 meter 都建立在「哪些页面算活页」与「一条链接指向仓内何处」这两个谓词上。

### 4.1 `living_markdown(root)`（`:89`–`:100`）——活页集合

```
对 root.rglob("*.md") 排序后逐个：
   parts = relative(root, md).split("/")
   若任一 part ∈ EVIDENCE_NAMES 或 ∈ PROCESS → 跳过（非活页）
   否则 → 收集 md.resolve()
```

- `EVIDENCE_NAMES = {"artifacts","evidence","evaluations","fixtures","skills-outputs","test-results"}`
  (`:24`)；`PROCESS = ("plans","zj-retros")`（`:25`）。判定是**路径分段级**（任一段命中即排除），
  不是前缀级——`skills-outputs/sweep/note.md` 因首段命中被排除（`test_evidence_surfaces_are_not_link_sources`，
  `test_docs_metrics.py:126`–`:130`）。
- **`resolve()` 是 load-bearing**：函数返回的是 `md.resolve()` 而非 rglob 原路径。docstring（`:90`–`:93`）
  说明：在 temp/工作目录位于符号链接后的系统上，未解析的 rglob 路径永远不等于 `resolve()` 产出的路径，
  链接图会**静默清空**。故入站/出站比较全部在已解析路径空间内进行。
- 语义后果：证据面与过程面**既不作为被度量对象、也不作为链接源**（`SKILL.md` Boundaries、
  `health-contract.md`「NAV_ORPHAN / MAP_ONLY」）——它们是冻结或瞬态的，不是「活引用」。
- **此活页定义刻意独立于 `/zj-docs-ontology` 的 map-coverage 判定**：两者「哪些页算数」可以不一致，
  这是设计而非缺陷——统一它会把这套 opt-in、零跨 skill import 的工具耦合到 ontology 的 preset 词汇，
  破坏可移植边界。契约已钉死此点（`health-contract.md`「Status in the skill chain」）。

### 4.2 `resolve(root, value, base)`（`:39`–`:47`）——链接目标解析

- 跳过外部/锚点：以 `http://`、`https://`、`mailto:`、`#` 开头 → 返回 `None`。
- 切掉 `#fragment`，从 `base`（调用方传入的页面所在目录）拼接后 `.resolve()`。
- **可移植性守卫**：`candidate.relative_to(root)` 抛 `ValueError`（即解析后跑到仓外）→ 返回 `None`。
  函数只判定「在不在仓内」，**不判定存不存在**——存在性交由调用方按需 `is_file()` 过滤。
- **[现状/风险]（2026-11 refresh）** 此 `resolve()` 与 architecture 的 `path_from()`（`validate_architecture_docs.py:124`）**已分叉**：后者支持 `/` 前缀绝对路径，本函数不支持；一个以 `/src/...` 书写的 `## Source map` 条目，architecture 判合法，本 skill 的 freshness 会按 `page.parent` 拼出错误目标或被丢弃。

## 5. 作用域细节：`measure()` 的 scope 与 map（`:103`–`:169`）

`measure()` 开头确立两个基准（`:105`–`:107`）：

```
is_git = (root/".git").exists()
docs   = root/"docs"
scope  = docs if docs.is_dir() else root
```

**作用域差异是刻意实现事实，须记录**：

| Meter | 遍历基准 | 依据 |
|---|---|---|
| `BUDGET_EXCEEDED` | `root.glob(pattern)`（pattern 是**仓根相对**） | `:114`，规则自带 glob，不受 scope 影响 |
| `FRESHNESS_DRIFT` | `living_markdown(scope)` | `:129` |
| `NAV_ORPHAN`/`MAP_ONLY` | 节点来自 `living_markdown(scope)`；map 另指 `root/docs/README.md` | `:144`–`:145` |

- orphans 的「地图」固定是 `docs/README.md`（若存在），并从参与判定的 `pages` 中剔除（`:145`）——
  地图自身不是被度量页，只作为入站来源之一被单独统计。
- `is_git` 在 `measure()` 入口算一次并向下传给 `mtime()`，整趟度量用同一时间源判定。

## 6. 四个 meter 的精确语义

### 6.1 `BUDGET_EXCEEDED`（`:109`–`:123`）

对每条 `budgets` 规则，`glob` 与 `max_lines` 任一缺失/类型不符（`not pattern or not isinstance(cap,int)`）
→ **静默跳过该规则**（`:112`–`:113`，不报错，符合「工具不猜参数」）。否则对每个匹配且 `.md` 结尾的文件，
`len(text.splitlines())` 物理行数 > `max_lines` → 记 outlier，detail 含实际行数、上限、命中规则
（`{lines} lines > max {cap} (rule: {pattern})`）。用**物理行**而非词数：确定、可被未来 linter 复核
（`health-contract.md`「BUDGET_EXCEEDED」）。

### 6.2 `FRESHNESS_DRIFT`（`:125`–`:140`）

前置：`freshness` 必须是 dict 且 `max_age_days` 非 `None`（`:127`），否则整个 meter 不跑。`max_age = float(max_age_days)*86400`。

对 `living_markdown(scope)` 每页调 `source_map_targets(root, page)`（`:50`–`:72`）：

```
用 HEADING_RE (?m)^##\s+(.+)$ 找所有二级标题
定位标题文本 .strip().lower() == "source map" 的那段
   section = 该标题末尾 → 下一标题开头（无下一标题则到文末）
   无 "## Source map" 段 → 返回 []（页被跳过）
targets：LINK_RE.findall(section) + INLINE_PATH_RE.findall(section)
   按 value 去重 → resolve(root, value, page.parent) → 只保留 target.is_file()
```

- **[现状更正]（2026-11 refresh）** 旧声称「本 skill 不定义第二套 mapping 语法」是对**意图**的描述，非现状：本 skill 实际自带一份 `## Source map` 解析（`source_map_targets`，`docs_metrics.py:50`–`:72`），与 architecture 的 `source_paths()`（`validate_architecture_docs.py:264`–`:266`）是**两份平行实现**：inline 正则口径不同——本 skill 的 `INLINE_PATH_RE` 匹配任意反引号内容（`docs_metrics.py:22`）vs architecture 只认带扩展名的路径形态（`validate_architecture_docs.py:17`）；本 skill 用 `HEADING_RE` 重扫标题定位段，architecture 用 `section()` helper；`/` 前缀处理不同（见 §4.2）。因本 skill 零跨 skill import，architecture #67 这类改 base 的 breaking change 有 `LinkBaseTest` 守自家，却无任何测试拉住本 skill 的 freshness 不失准。
- 同时认 markdown 链接 `[..](..)`（`LINK_RE`）与行内反引号内容（`INLINE_PATH_RE`）两种声明形式（注：与 architecture 的 inline 口径**已分叉**，见上）。
- 漂移判定：`newest_source = max(mtime(t) for t in targets)`；`page_time = mtime(page)`；
  当 `newest_source - page_time > max_age` → outlier，detail 报「最新源比页面新 N 天」。
- **无 `## Source map` 段的页直接跳过**（`:131`–`:132`，`targets` 空 → `continue`）：没声明源就无法断言新鲜度
  （`test_a_page_without_a_source_map_is_skipped`，`test_docs_metrics.py:94`–`:98`）。

### 6.3 `NAV_ORPHAN` / `MAP_ONLY`（`:142`–`:168`）

前置 `config.get("orphans") is True`（`:143`，注意严格 `is True`，非真值——只有布尔 true 才跑）。

构造以**活页为节点**的入站链接图（此处链接源只用 `LINK_RE`，**不含行内 code path**，与 6.2 不同）：

```
pages = living_markdown(scope) 去掉 map_path
inbound = {p: set() for p in pages}；map_inbound = set()
map 的每条 markdown 链接 → resolve 命中 pages 内某页 → 加入 map_inbound
每个 page 的每条 markdown 链接 → resolve 命中 pages 内且 target != self → inbound[target].add(page)
逐 page 判定：
   map_cites = page in map_inbound
   cited     = bool(inbound[page])
   not map_cites and not cited  → NAV_ORPHAN   （连地图都不知道它存在）
   map_cites     and not cited  → MAP_ONLY （被地图索引、但无活页引用）
```

- 自引用被排除（`target != md`，`:156`），否则页面会因链接自己而「被引用」。
- `MAP_ONLY` 是**advisory 且常为正常**（入口页常只被地图索引）——这正是它只在 `orphans:true`
  时才度量的理由（`health-contract.md`「NAV_ORPHAN / MAP_ONLY」）。
- 两码路径都用 `relative(root, page)`（已解析路径回写为仓相对 POSIX 路径，`:35`–`:36`），
   故报告里是 `docs/prds/a.md` 这种形态（`test_map_only_is_reported`，`test_docs_metrics.py:108`–`:113`）。
- **`NAV_ORPHAN`（旧名 `ORPHAN_PAGE`）与 ontology 的 `ORPHAN_PAGE` 不同图、可共存**：改名已消除旧同名；ontology 的是 `## Source map` 条目在
  **typed relation edge**（`derived-from`/`supersedes`/`supports`）图上的可达性缺陷（`docs_governance.py:817`–`:832`），
  本 skill 的是**普通 markdown 链接图**上的导航孤岛（码 `NAV_ORPHAN`）。边不同、无共享权威，同一页可被两者各报一次而互不矛盾，
  清掉一个不清掉另一个。

## 7. 时间源降级规则（`mtime`，`:75`–`:86`）

度量新鲜度的时间基准**按运行环境降级**，是本 skill 唯一的外部进程依赖：

```
若 is_git:
   git -C <path.parent> log -1 --format=%ct -- <path.name>
   成功且有输出 → 用 commit time（float(stdout 首行)）
   失败/空      → 落到 mtime
否则: 直接用 path.stat().st_mtime
```

- 偏好 git commit time 的原因：**checkout 与 rebase 不会重置内容年龄**，文件 mtime 会（`health-contract.md`「FRESHNESS_DRIFT」时间源段）。
- 回退文件 mtime 保证工具在**纯目录/测试 fixture**（无 git）里仍可用——单测正是靠 `os.utime` 设 mtime 来驱动
  freshness（`test_docs_metrics.py:81`–`:82`）。
- 每个文件用其**自身父目录**作为 `git -C` 仓库根，命令只取 `--format=%ct`（提交时间戳），是只读查询。

## 8. 输出契约与退出码

输出恒为一段 JSON（`json.dumps(..., indent=2)`；`measured` 分支额外 `ensure_ascii=False`，`:206`）。

| status | 触发条件 | 关键字段 | exit |
|---|---|---|---|
| `opt-in` | 无配置文件 | `config:null`、`message`、`outliers:[]` | 0 |
| `config-error` | 配置文件存在但不可读/非法 JSON | `config`（相对路径）、`message`、`outliers:[]` | 1 |
| `measured` | 正常度量 | `config`、`mode:"read-only-report"`、`outliers` | `1`（有 outlier）/ `0`（干净） |

每个 outlier 恒为 `{code, path, detail}` 三键，`code` 限于 §6 的四值之一。测试逐条覆盖三态退出码
（`CommandLineTest`，`test_docs_metrics.py:144`–`:183`）。

## 9. 关键设计取舍

- **度量与裁定分离**：verdicts 是 advisory outlier 而非 ERROR，门禁权归本 skill 之外的仓库 CI；
  这样「页面健康」的判断权留给有上下文的 Human，工具不越权裁定语义。
- **opt-in 与 config-error 的反向退出码**：未配置=没被邀请→exit 0；坏配置=被邀请但无法履约→exit 1。
  二者都返回空 `outliers`，但退出码刻意不同，防止「无法度量」冒充「度量通过」。
- **复用架构层单一 mapping 语法（[目标]，现状见 §6.2/§10）**：意图是 freshness 只消费 `## Source map` 段、不另立声明格式、杜绝第二真相源；但现状是本 skill 自带一份**平行**解析，二者已分叉——对齐方案见 §10 未决项 U1。
- **活页边界即度量边界**：证据面/过程面从「被度量」「链接源」两端同时排除，使链接图只反映活文档拓扑。
- **`resolve()` load-bearing**：路径解析一致性是链接图正确性的前提，否则符号链接环境下图静默为空。
- **物理行 + 时间源降级**：都是「确定、可移植、可在无 git 环境自测」取向的具体落点。

## 10. 2026-11 refresh：对齐邻居现状后的定位与重设计未决项

> 本节据 `zj-docs-ontology`（#275/#281/#282/#286 四层 + Module D + typed relations）与 `zj-docs-architecture`（#285/#286/#287/#288–#294 切片让渡 + 概念图 + `#67` Source map base）重构后的磁盘现状，重述本 skill 的定位、最强差异化，以及重设计必须正面处理的张力。`[现状]` = 磁盘事实可验；`[目标]/[新增]/[未决]` = 重设计意图，需另立执行 plan。

### 10.1 定位不变 + 最强差异化 [现状]

本 skill 仍是 correctness 之外的 measurement 第三轴：`measure()` 返回离群点表（`docs_metrics.py:103`），全程只读、无错误码、无 `proposal`/`mutation`。最强差异化是 **ontology 主动让渡的能力缺口的承接者**——`governance-contract.md:369-372` 把「page size budget / freshness scoring / orphan scoring」整体列为 **rejected default**，理由「目标仓库无 manifest、无统一 source-map 时间戳，任何 score 都是凭空捏造」「carried as a capability gap」；本 skill 用 opt-in `docs/docs-metrics.json`（`docs_metrics.py:173`）补 manifest、消费 `## Source map` + git commit-time（`docs_metrics.py:50-86`）补时间源，正是对该缺口的承接。它也是组内唯一**零跨 skill import、无 `BASE_RULES` 生成块**的成员（已核：`docs_metrics.py` 仅 import 标准库）。与 `zj-neat-freak` 不重叠：neat-freak 是写动作收尾（改文档/记忆/清场），本 skill 是 read-only 度量。裁定：保留独立。

### 10.2 freshness 归属空洞 [现状]

`governance-contract.md:169-172` 现状**仍**写「Freshness…是 architecture 层的 concern（`SOURCE_*`）」；但 architecture 的 `SOURCE_*` 现状仅 `SOURCE_TARGET_MISSING`/`SOURCE_TARGET_OUTSIDE`（存在性/越界，`validator-contract.md:98-104`），**无任何「页面比源陈旧 N 天」的时间码**。即：ontology 把 freshness 推给 architecture、architecture 只做链接完整性、时间新鲜度无人拥有——这正是本 skill 该占的缝。但契约须显式切开「时间度量 vs 结构存在性」，否则与 `:169` 的归属声明直接打架。

### 10.3 freshness 定性收口：best-effort 消费者 [定稿]

见 §4.2 与 §6.2：本 skill 实际维护了第二份 `## Source map` 解析，与 architecture `source_paths()` 在 inline 正则、`/` 前缀、section 定位三处分叉，且因零跨 skill import 而无测试拉住其漂移。**本轮定稿的解法是在定位层收口所有权，而非在实现层追平**：

> `## Source map` 这个 fact source 归 **architecture**；metrics 只是它的 **best-effort 消费者**，不主张等同 architecture 的严格 source 集。

据此，**U1 收敛到 (b)**——理由从「省实现」升级为「定位自洽」：metrics 所有 verdict 本就是 advisory outlier，freshness 报「页面时间戳比它声明的某源旧 N 天」这种粗粒度提示，精度天花板由「消费者 + 零 import」这个定位决定，**不由解析对齐程度决定**。被否方案留痕：**(a) 锁定镜像** 会让 metrics 事实上声称持有 `## Source map` 权威，越界；**(c) 删 freshness** 会让本 skill 退化为「budget + orphan 两个 lint」，丢掉最能落地的 capability-gap 承接面，独立性反站不住。

（注：`§6.2` 描述的「第二份平行解析」是实现事实，本节把它**重新定性**为「消费者可接受的精度代价」，不再要求与 architecture 逐字对齐；`/` 前缀与 inline 正则差异仍记录在 §4.2/§6.2 供 review，但不再列为待修 bug。）

### 10.4 重设计张力 C/D [目标/未决]

- **C 同名码（已消歧）**：本 skill 旧码 `ORPHAN_PAGE`/`ZERO_INDEGREE` 已改名 `NAV_ORPHAN`/`MAP_ONLY`，与 ontology 的 `ORPHAN_PAGE`（`docs_governance.py:817`）不再同名；`health-contract.md`「NAV_ORPHAN / MAP_ONLY」段已降级为「改名沿革 + 不同图」说明。→ [已决，随改名 PR 落地]。
- **D capability-gap 授权与归属矛盾未写进本 skill 契约**：`:369-372` 缺口承接、`:169-172` 时间/存在切分只在邻居侧，本 skill `health-contract.md` 未引用。`[目标]` 把 §1 定位、§10.3 freshness 定性一并补入 → [未决 U4]。

### 10.5 决策汇总（与正文 §10.1–§10.4 两处收口）

下列 U1–U5（含改名 + U3）决策均已收口，并已随 PR #295 / #296 落地到代码与契约正文，无待执行的后续 plan：

- **U1** freshness 第二份解析 → **[已决：(b) best-effort 消费者]**，见 §10.3；定性已随 PR #296 回写 `health-contract.md`「FRESHNESS_DRIFT」段。(a)/(c) 作为被否方案留痕。
- **U2** freshness 与 architecture `SOURCE_*` 切分为「时间 vs 存在性」 → **[已决]**，并入 §1 [定稿] 功能边界 + §10.3 所有权表述；所有权切分已随 PR #296 写进 `health-contract.md`「FRESHNESS_DRIFT」段。
- **U5** 三轴表/码族与邻居现状对齐 → **[已决]**：§1 表已就地更新（PR #295），`health-contract.md`「Status」段码族已同步 `SOURCE_TARGET_*`/`CONSIST_*`/`UNMAPPED_PAGE`（PR #296）。
- **改名 + U3**（**[已决：随 PR #295 落地 `338db6c`，squash 合并、分支已删]**）：skill→`zj-docs-metrics`、config→`docs/docs-metrics.json`、引擎→`docs_metrics.py`、测试→`test_docs_metrics.py`、meter 码→`NAV_ORPHAN`/`MAP_ONLY`；**D1** 脚本/测试文件名同步改、**D2** 上述码名、**D3** `graph.json` 重跑生成、**D4** 3 个 roadmap 引用**保留旧名加注**，均已执行。调用粒度维持整仓 batch、不加 `--scope`。17 回归测试全绿、0 dangling。
- **U4** 把 §1 定位、§10.3 freshness 定性、`:369-372` capability-gap 授权回写进 `health-contract.md` → **[已决：随 PR #296 落地 `4f823e4`]**（Diff 1+2+3 全量回写，Status 段码族一并对齐现状）。

---

## 11. 典型应用场景（反验定位与功能边界）

> 本节用场景反向检验 §1 的定位与功能边界是否成立，**非实测读数**——下列命中情况均为设计推演，未经在当前仓库实跑 metrics 验证。每场景标注对应 meter、为何归 metrics、以及为何不归 ontology/architecture/neat-freak。

**正向场景（与四个 meter 一一对应）**

- **文档膨胀** → `BUDGET_EXCEEDED`：某 PRD/design 从「一个有界问题」写成什么都往里塞。Human 设 `docs/prds/*.md: 120`，取超预算清单。归 metrics：纯物理行数、零语义；neat-freak 要读内容才判，ontology/architecture 不管长度。
- **导航孤岛 / 孤儿页** → `NAV_ORPHAN`：重构把某页从 `docs/README.md` 摘了没删，或新建页既没进 map 又无人链 →「没人知道它存在」。归 metrics：普通 markdown 链接图，与 ontology 的 typed-relation `ORPHAN_PAGE` 不同图、可同页各报一次而互不矛盾。
- **索引了但零引用** → `MAP_ONLY`：map 链某页、但无第二页引用它。对 entry-point 正常、对本应被引用的细节页是信号；advisory 且仅 `orphans:true` 才跑。
- **源变了页面没跟上** → `FRESHNESS_DRIFT`（**best-effort 消费者**）：某页声明 `## Source map` 指向 `src/**`，代码改了、页 60 天没动 → 报「最新源比页新 N 天」提示复核。归 metrics：填 §10.2 的归属洞——architecture `SOURCE_*` 只管目标存在/越界、不判时间陈旧。

**工作流 / 结构性场景（反验「独立存在」）**

- **交接前 / 季度体检，metrics 作路由输入**：跑一次得 outlier 表，再分发——预算改写/重挂 → `/zj-docs-ontology`，过期声明 → 页面 owner，清残留 → `/zj-neat-freak`。这是 `SKILL.md`「Report, don't fix」的具象，也是 metrics 不并入别人的理由（它产**提议面**）。
- **跨仓库可移植的轻量度量**：装进任意新仓库只需 Human 提交 `docs/docs-metrics.json`，单目录拷走即用。归 metrics：组内唯一零 `BASE_RULES`、零跨 skill import（§10.1）；architecture/ontology 搬动需带 `skill-conventions` 词汇体系。
- **（可选）非阻塞 CI advisory 信号**：Human 自愿把 health 接进 CI 产 PR 评论，但不设 required check（opt-in + `exit 1 only when outliers`）。契合契约拒绝「默认机械 health-score gate」，仅在人想要非阻塞数据时供之。

**反场景（划界——这些不该由 metrics 接）**

- 「这页写得对不对 / 全不全」→ 语义判断，归 Human（advisory measurement 不判语义）。
- 「authority-id 冲突、map 绑定、lifecycle 退役」→ correctness，归 ontology/architecture。
- 「把文档/规则/记忆与代码同步、清会话残留」→ 写动作收尾，归 neat-freak。

**场景结论**：膨胀/孤岛/零引用三场景全纯自包含，兑现「纯拓扑+物理」定位；freshness 场景印证它必须按 §10.3 定性为 best-effort 消费者才自洽；路由面与可移植性两场景，是 metrics 既「不该并入邻居」又「不必做成大而全」的双重独立理由。

---

## 12. 有意不实现 / 实现边界（勿静默加）

- **不定义第二套 source mapping**：freshness 只认 `## Source map`（`:57`），其它表达映射的方式一律不支持。
- **`orphans` 严格 `is True` 门控**（`:143`）：truthy 字符串（如 `"true"`）不会启用该 meter——避免隐式类型猜测。
- **bad rule 静默跳过**：budgets 条目 glob/max_lines 非法只跳过该条（`:112`–`:113`），不影响其它规则与整体度量。
- **零 outlier ≠ 页面正确**：`health-contract.md`「What a clean run does not mean」明确——干净只说明
  Human 设定的阈值当前满足，页面质量/完整/正确属另外两个 skill 与阅读者。设计文档同样据此拒绝把本 skill
  的 exit 0 当质量背书。
- **不与 `/zj-docs-ontology` 统一「活页」谓词、也不合并本 skill `NAV_ORPHAN` 与 ontology `ORPHAN_PAGE`**：见 §4.1 与 §6.3——统一会把
  opt-in、零跨 skill import 的度量器耦合进 ontology 的 preset 词汇与确定性账本（`confirmation_id=sha256`），
  破坏其可移植与无门禁权威边界。此点已在契约「Status in the skill chain」「NAV_ORPHAN / MAP_ONLY」
  两段钉死，**勿以"消除重复"为名合并两端**。
