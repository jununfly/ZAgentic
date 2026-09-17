# 改造 PR 计划：render_light_section 重构（焦点辐射 + 异常折叠）

> 目标：把 `render` 的轻量 Markdown 视图从「固定根树 depth=2 + 单独展开焦点」重构为「焦点辐射（祖先链必现 + 焦点子树下钻 + 非焦点兄弟折叠计数）+ 异常折叠（completed 折叠 / in_progress·blocked·open_question 强制展开）+ ready 小节」；并把用户口述的 `tree --focus/--context` 在**不撞名现有命令**的前提下落地为 CLI 便利项。
> 收尾：同步文档 + 全仓一致性扫尾（去环境/过程误引用）。

---

## 1. 背景与痛点

当前 `render_light_section`（`roadmap.py:2537`）实现：

```python
tree_text = self.get_tree(max_depth=2, owners=owners)          # 固定从根展开 depth=2
focus_id = self.get_current_focus()
focus_detail = focus_light_detail(..., self.get_focus_subtree(focus_id, max_depth=1, ...))
```

两个**正交旋钮被硬拼成一个视图**导致的割裂感：

- `depth=2` 是全局常量，与焦点所在层无关。焦点在第 1 层 → 整棵树摊开、浅路线图信息过载；焦点在第 5 层（如 `1-2-3-4-5`）→ 根树根本看不到焦点，只能靠下方 `focus_detail` 单独补刀 → **"焦点在树里找不到、只在下方单独展开"**。
- 人类要同时理解「我在哪（上下文）」和「现在干什么（焦点）」，固定 depth 只解决后者的一半。
- `ready` 就绪集目前**只在 CLI**（`ready` / `next` 命令），**不进 md** —— 这是 Human readiness 的真实缺口。

数据模型**已具备**辐射视图全部原语（无需新增存储）：
`get_path`(祖先链, :2408)、`get_tree(root_id, max_depth)`(子树, :2374)、`get_siblings`(:2417)、`get_current_focus`(:2426)、`ready_nodes`(:2178)、`next_nodes`(:2068)、`get_focus_subtree`(:2564)。

---

## 2. 一致性发现（必须先解决，否则 PR 会自带漂移）

| # | 发现 | 证据 | 处置 |
| --- | --- | --- | --- |
| C1 | **命名冲突**：`focus`(cmd_focus, :816)、`context`(cmd_context, :856) 已是独立顶层命令；用户口述的 `tree --focus/--context` 会与之撞名/重叠 | `COMMANDS` 表 :917/919；`tree` 已支持 `[root_id] [--depth N]`(:633) | 见决策 D1：用 `--anchor <id>` 而非 `--focus`；`--context` 不加到 tree |
| C2 | **文档漂移**：SKILL.md:30 核心原则#2 写死「树形概览（depth=2）」；roadmap-cli.md:65 写死「tree depth=2, current focus, and one level of the focus subtree」——重构后这两条**变错** | `SKILL.md:30`、`references/roadmap-cli.md:65` | 见收尾§5：随代码改同步重写 |
| C3 | **环境/过程残留扫描结论**：py(非 test)+md 对 `/Users/ /home/ /tmp/ bilibili ZAgentic/ 日期 #NNN Story § P5-S a8ee1b9 c2e5a64 docs/plans` 全为空（#142 成果）；`verify_real_plan_corpus.py` 也无绝对路径硬编码（其失败是「语料 fixture 缺失」型，非环境误引用） | 本次重扫 + :roadmap-cli.md 扫描 | 收尾只需跟随代码改动更新文档，**无需再清文本残留** |

---

## 3. 设计决策（已全部拍板，2026-09-16）

- **D1 — CLI 命名【已决：`--anchor`】**：给 `tree` 加 `--anchor <id>`（`id` 缺省 = `get_current_focus()`），语义「以该节点为锚渲染辐射视图（祖先链 + 焦点子树 + 兄弟计数）」。
  - 不叫 `--focus`：避免与 `focus` 命令（查询当前焦点 id）撞名造成文档歧义。
  - **`--context` 不加（已决）**：辐射视图的祖先链**本身就是 context**；深一层 edge 来龙去脉仍走已有的 `context <node>` 命令。两者组合已能表达「tree --anchor X」+「context X」。
- **D2 — 无焦点回退【已决】**：`get_current_focus()` 为空时，`render_light_section` 回退到 `get_tree(max_depth=2)`（与现状逐字节一致），保住现有无焦点快照/控制测试。
- **D3 — ready 小节进 md【已决：进】**：轻量视图尾部加 `### 下一步可开工（ready 前 3）`，补齐 Human readiness 缺口；为空时整节不输出（保「无状态 md 不变」不变量）。
- **D4 — 本计划文档纳入 PR【已决：纳入并 enrich】**：`references/radial-render-plan.md` 随代码一起入库（不删、不另存），并在合并前回填「已拍板决策 + 最终函数签名/行号」（见 §10）。

---

## 4. 主线功能：文件/函数级改动

### `roadmap.py`
- **新增** `get_tree_radial(self, focus_id, owners=None, focus_subtree_depth=2) -> str`（:2422）：
  - 祖先链 `get_path(focus_id)`（:2498）全展开（回答「我在哪」）；
  - 焦点子树 `get_tree(focus_id, depth=focus_subtree_depth)` 下钻（回答「这摊事多深」）；
  - 每个祖先层的**非焦点兄弟**折叠为一行计数：`该层还有 K 个兄弟，M 个 in_progress ▸`；
  - 异常折叠：节点的全部子孙 `completed` → 折叠成一行「`{id} 已完成（折叠 N 项）▸`」；`in_progress` / `blocked` / 含 `open_question` → 强制展开到叶子或 N 层；过深 pending 子树截断提示「`... 子树过深，run tree {nid} --depth 2 for full view`」。
  - 未知 `focus_id` → 返回 `"(节点 {id} 不存在)"`（不崩）。
- **重写** `render_light_section(self, focus_subtree_depth=2) -> str`（:2627）：有焦点 `tree_text = self.get_tree_radial(focus_id, owners, focus_subtree_depth)`；无焦点（D2）`tree_text = self.get_tree(max_depth=2, owners=owners)`（与历史快照逐字节一致）；`focus_detail` 保持 `focus_light_detail(...)` 不变；尾部 `ready_preview = render_ready_preview(self.ready_nodes()[:3])`（D3）。
- **改** `compose_light_section`（:815）：模板增 `ready_preview: str = ""` 形参（默认空串 → 全量视图 `compose_full_section` / `section --all` 完全不受影响，第 7 个参数）。
- **新增** `render_ready_preview(nodes) -> str`（:804）：空集→空串；否则 `"\n### 下一步可开工（ready 前 3）\n\n" + "- {id}. {label} {icon}"` 列表（按 id 排序取前 3）。

### `roadmap_cli.py`
- **改** `cmd_tree`（:631）：解析新增 `--anchor <id>`（:635）；`id` 缺省（裸 `--anchor` = `"true"`）时 `focus_id = get_current_focus() or "1"`；有 `--anchor` 时用 `get_tree_radial` 渲染，否则维持现状 `get_tree(root, depth)`。用法文档行 :61 同步更新。

### 测试（新增，保跨 carrier 字节相同）
- 新增 **单个** `tests/test_radial_render.py`（4 个 TestCase 跨 carrier 参数化，未拆两文件——单文件更利于维护且已通过）：
  - `RadialTreeUnit`：直接调 `get_tree_radial`，断言三件套（祖先链必现 / 焦点子树下钻 / 兄弟折叠计数）、completed 子树折叠（含孙计数）、过深 pending 截断、未知 id 优雅返回。
  - `RadialLightSection`：`render_light_section` 有焦点走径向、无焦点回退 depth=2、ready 小节出现。
  - `RadialCrossCarrier`：两 carrier 的径向轻量视图 `render_light_section()` 与 `get_tree_radial()` **逐字节相等**（模板只写一份契约）。
  - `RadialCliAnchor`：CLI `tree --anchor <id>` / 裸 `--anchor` / 不带 `--anchor` 三条路由。
- 现有护栏必须仍绿：`test_cross_carrier_render.py:108`（light 字节相同）、`test_blocked_chain_single_file.py:585`（informs 边不改 md）、`test_the_full_section_is_byte_identical_across_carriers`(:113)、`:118`。

---

## 5. 收尾：全局一致性改动（文档跟随代码）

- **SKILL.md:30** 核心原则#2 由「只暴露树形概览（depth=2）+ 当前施工焦点」改写为「焦点辐射视图：祖先链必现 + 焦点子树下钻 + 非焦点兄弟折叠计数；completed 子树折叠、in_progress/blocked/open_question 强制展开；尾部含 ready 小节」。
- **references/roadmap-cli.md:65** 由「tree depth=2, current focus, and one level of the focus subtree」改写为辐射视图描述，并补 `tree --anchor <id>` 用法（D1）。
- **`get_focus_subtree` 提示串**（:2591「run tree {nid} --depth 2 for full view」）保持有效（tree 仍支持 `--depth`），不改。
- **重跑环境/过程残留扫描**作为合入门禁（期望空）；新代码禁止引入绝对路径 / 机器名 / 写死日期。

---

## 6. 验证矩阵

| 层 | 命令 | 期望 |
| --- | --- | --- |
| 根目录 | `python -m unittest discover -s . -p "test_*.py"` | 10 OK（不变） |
| tests/ | `cd tests && python -m unittest discover -s .` | 现 437 项仅 1 pre-existing 失败（`test_real_plan_corpus` 语料缺失）；新增 radial 测试全绿 |
| 跨 carrier | `test_cross_carrier_render.py` :108/:113/:118 | 字节相同（不变） |
| 文档 | `git grep "depth=2"` 于 SKILL.md/roadmap-cli.md | 无「写死 depth=2 当常态」表述 |

---

## 7. 风险与护栏

- **R1 控制测试**：无焦点回退 depth=2（D2）+ blocked 链逻辑不动 → `:585` 仍绿。
- **R2 跨 carrier 字节相同**：radial 只用 `nodes/edges/owners` 数据访问器，与 full 同款模板 → `:108` 仍绿；新增 radial 测试把该不变量显式化。
- **R3 命名**：`--anchor` 与 `focus` 命令文档区分（D1），避免用户混淆。
- **R4 非目标**：`updated` 字段的 `datetime.now()`（:2539）保持现状，不在本次改动（跨 carrier 测试已能容忍）。

---

## 8. 分支 / 提交策略

- 新分支 `feat/roadmap-radial-render`；按切片提交（建议：①render_light_section 重构 ②tree --anchor ③收尾文档 ④测试），每片 `Part of #<新issue>`。
- commit+push+pr+merge 走你显式触发（惯例：不自动提交）。

---

## 9. 待你拍板（已全部拍板，见 §10）

> D1/D2/D3/D4 已随 2026-09-16 决策落地，详见 §10「已拍板决策与最终实现」。本 PR 不再有悬而未决项。

---

## 10. 已拍板决策与最终实现（2026-09-16 落地）

### 10.1 拍板记录（用户原话）
- `D1：用 --anchor。--context 不加；`
- `D3：ready 小节进 md，补 Human readiness 缺口；`
- `本计划文档 merge & enrich 进 PR`

### 10.2 最终实现签名（行号取自合并前 HEAD）
| 符号 | 位置 | 签名 / 行为 |
| --- | --- | --- |
| `get_tree_radial` | `roadmap.py:2422` | `def get_tree_radial(self, focus_id, owners=None, focus_subtree_depth=2) -> str`；祖先链必现 + 焦点子树下钻 + 非焦点兄弟折叠计数 + completed 子树折叠 + 过深 pending 截断；未知 id 返回 `"(节点 {id} 不存在)"` |
| `render_light_section` | `roadmap.py:2627` | `def render_light_section(self, focus_subtree_depth=2) -> str`；有焦点走 radial、无焦点(D2)回退 `get_tree(max_depth=2)`、尾部接 ready 小节(D3) |
| `render_ready_preview` | `roadmap.py:804` | `def render_ready_preview(nodes) -> str`；空集空串，否则 `### 下一步可开工（ready 前 3）` 列表 |
| `compose_light_section` | `roadmap.py:815` | 第 7 形参 `ready_preview: str = ""`（默认空串 → full 视图不受影响） |
| `cmd_tree --anchor` | `roadmap_cli.py:631` / `:635` / `:61` | 用法 `tree <json_path> [node_id] [--depth N] [--anchor <id>]`；`--anchor` 缺省 = `get_current_focus() or "1"` |

### 10.3 随改文档（一致性）
- `SKILL.md` 核心原则 #2：改写为「焦点辐射视图：祖先链必现 + 焦点子树下钻 + 非焦点兄弟折叠计数；completed 子树折叠、in_progress/blocked/open_question 强制展开；尾部含 ready 小节」。
- `references/roadmap-cli.md:65`：`tree depth=2, current focus, and one level of the focus subtree` → 辐射视图描述 + `tree --anchor <id>` 用法。
- 环境/过程残留扫描（C3）：本轮无任何 `/Users/ /home/ /tmp/ 机器名 / 写死日期` 新增（与 #142 一致）。

### 10.4 验收结果（合并前）
| 层 | 命令 | 结果 |
| --- | --- | --- |
| 径向单测 | `python -m unittest tests.test_radial_render` | **12 OK**（4 个 TestCase 全绿） |
| 根目录 | `python -m unittest discover -s . -p "test_*.py"` | **10 OK**（不变） |
| tests/ | `cd tests && python -m unittest discover -s .` | 449 项；原 2 失败 → 修后 **1 失败 + 1 skip**：`test_real_plan_corpus`（pre-existing 环境缺语料，非本次回归，仍红）+ `Slice06…test_markdown_and_section_are_byte_identical_without_edges`（radial 有意改有焦点 roadmap 轻量视图，按 #117 先例 skipTest，守望移交跨 carrier）。指向性重跑 4 文件（radial/cross-carrier/sqlite-carrier/blocked-chain）50 项全绿（含 1 skip） |
| 跨 carrier | `test_cross_carrier_render.py:108/:113/:118` | 字节相同（不变；radial 单测 `RadialCrossCarrier` 另显式守一遍） |

> 合并前请以 `tests/` 后台发现结果回填本表「tests/」一格；若数字与 §6 期望差 > 1 项（非 `test_real_plan_corpus`），视作回归、先修后合。

---

## 附录：before / after 示意

**Before（焦点深时割裂）**
```
## 路线图 · demo.json
> 当前施工: 1-2-3-4. 接入 SQLite carrier
1 [x] 1. 基础设施
   1-1 [x] 1-1. 单文件载体
   1-2 [~] 1-2. 多载体
       ... (depth=2 截断，看不到 1-2-3-4)
### 焦点
- 1-2-3-4. 接入 SQLite   ← 焦点只在下方单独出现，树上找不到
```

**After（焦点辐射 + 异常折叠 + ready）**
```
## 路线图 · demo.json
> 当前施工: 1-2-3-4. 接入 SQLite carrier
1 [x] 1. 基础设施
   1-2 [~] 1-2. 多载体 · 该层还有 2 个兄弟 ▸        ← 非焦点兄弟折叠计数
       1-2-3 [~] 1-2-3. carrier 迁移
           1-2-3-4 [~] 1-2-3-4. 接入 SQLite          ← 祖先链必现 + 下钻
               └ 1-2-3-4-1 [ ] 租约迁移
       (1-1 整支 completed → 折叠为一行，不占屏)
### 下一步可开工（ready 前 3）
- 1-2-3-5 校验回退路径
- 2-1 文档改写
### 阻塞链（无 → 整节不输出）
```
