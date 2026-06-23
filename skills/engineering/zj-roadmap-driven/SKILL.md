---
title: "zj-roadmap-driven"
description: "路线图驱动开发——以地图导航形式，帮助 Agent 正确理解全貌，始终与 Human 保持地图颗粒度对齐"
triggers:
  - 路线图
  - roadmap
  - 地图导航
  - 规划路线
  - 树形结构
  - 复利系统
---

# zj-roadmap-driven — 路线图驱动开发

**目标：** 在复杂任务场景中，用路线图（树形节点 + 决策记录）作为 Agent 和 Human 的共享心智模型。避免持续对话导致的目标偏离——每一步都在地图上留下足迹。

**核心原则：**
1. **JSON 是唯一真相源**——所有数据（节点、决策、备注、模式）只存在于 JSON。Agent 必须通过 CLI 读写，禁止直接编辑文件。
2. **Markdown 是轻量渐进式视图**——只暴露树形概览（depth=2）+ 当前施工焦点。Human 一眼看清进度，不占满上下文。
3. **每个节点有编号**（1, 1-1, 1-1-1, …），方便 Human 和 Agent 快速定位
4. **每个节点有状态 checkbox**（[ ] / [~] / [x] / [!]），一眼识别进度
5. **决策随节点落盘**（JSON 中），形成可追溯的决策历史。md 只展示焦点节点的决策。

## 工作流

```
Human 提方向 → Agent 建 roadmap JSON → Agent 渲染轻量 section 到 md
    ↓
Agent 每做一个决策 → 调用 `decide` 写入节点 → 调用 `render` 更新 md
    ↓
Human 看 md 里的树 + 当前焦点 → 确认或纠正 → Agent 继续
    ↓
Agent 完成一个子任务 → 调用 `update` 打勾 → 调用 `render` 更新 md
    ↓
Agent 需要全貌 → 调 `tree` / `decisions` / `section`（全量）按需获取
```

**关键规则：**
- **Agent 每次完成实质工作后，必须 `render` 更新 md 文件。** 这是 Human 看到进度的唯一窗口。
- **Agent 做任何方向性决策前，先 `decide` 记录。** 决策不落盘 = 没发生。
- **Human 随时可以通过 `tree` + `decisions` 了解全貌，无需翻对话历史。**
- **Agent 禁止直接 Read/Edit md 的路线图 section。** 只能通过 CLI 操作 JSON，再 render 输出。

## 数据结构

### 节点字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 编号，如 `1`, `1-1`, `1-1-1` |
| `label` | string | 节点名称 |
| `status` | string | `pending` / `in_progress` / `completed` / `blocked` |
| `mode` | string | `explore`（探索） / `exploit`（深挖） |
| `parent` | string\|null | 父节点 id，根节点为 null |
| `children` | list | 子节点 id 列表 |
| `decisions` | list | 决策记录 `[{q, answer, note}]` |
| `notes` | string | 自由备注 |

### 状态图标

| 状态 | 图标 | 含义 |
|------|------|------|
| `pending` | `[ ]` | 待处理 |
| `in_progress` | `[~]` | 施工中 |
| `completed` | `[x]` | 已完成 |
| `blocked` | `[!]` | 被阻塞 |

### 模式含义

| 模式 | 标签 | 含义 |
|------|------|------|
| `explore` | `[X+]` | 子树还在探索中——方向、范围、优先级未定 |
| `exploit` | `[Y+]` | 子树方向已确定——正在深入施工 |

树形输出中每个节点格式为：`[状态图标][模式标签] 编号. 名称`

### 节点命名规范

节点名称必须**自解释**（self-explainable）：只看名称就知道要做什么。完整且准确的范围和内容，应结合父节点作为语境背景。

- ✅ `文章处理后端流水线`、`数据库层异步IO重构`、`用户认证OAuth2集成`
- ❌ `优化`、`重构`、`修复`、`处理`、`完成`

**Agent 使用 `add` / `update --label` 创建或修改节点名称时，必须检查名称是否自解释。** 发现通用词警告用户但可继续。

### 修改节点名称的安全流程

当 `update --label` 改变节点名称，且**语义发生偏移**（核心名词变了，不只是措辞润色）时，Agent 必须先询问：

> "`node({id}. {旧name})` 将更新为 `node({id}. {新name})`，是否要新建 sub-node 对应偏差，避免跟踪遗漏？"

用户确认后：

1. 如果回答"是"：执行 `update --label` 后立即 `add` 一个子节点，label = 旧名称，status = `pending`
2. 如果回答"否"：直接执行 `update --label`，不做额外操作

**语义偏移 vs 措辞润色：**
- 偏移（触发）：`文章+视频处理` → `文章处理`（范围缩小）、`日志系统` → `文档系统`（主体替换）
- 润色（不触发）：`文章处理` → `文章处理流水线`（细化措辞）

### 父子状态自动同步

修改节点状态（`update --status`）、新增子节点（`add`）、删除节点（`delete`）后，系统自动向上同步父节点状态：

- **全部子节点 completed → 父节点自动设为 completed**
- **任意子节点非 completed → 父节点不得为 completed**（自动降级为 `in_progress`）

级联冒泡：同步到父节点后，继续向上检查祖父节点，直到根节点。

### JSON Demo

参见 `demos/roadmap_demo.json`——基于「AI-Native 个人可复利工具系统」的实际路线图。

### Markdown Section Demo

参见 `demos/ZJ_ROADMAP_section_demo.md`——由 `roadmap.py` 从 JSON 自动渲染的标准输出。

## 确定性操作

所有操作通过 `roadmap_cli.py` 执行。每个命令输入确定 → 输出确定。

**Python 依赖：** 无第三方依赖，仅需 Python 3.8+ 标准库。

### 初始化

```bash
# 创建新路线图
python roadmap_cli.py init <json_path> --title "项目名称" [--description "描述"] [--md-file "关联的md文件.md"]
```

### 节点 CRUD

```bash
# 添加子节点
python roadmap_cli.py add <json_path> <parent_id> "<label>" [--status pending] [--mode explore]

# 更新节点属性（只更新传入的字段）
python roadmap_cli.py update <json_path> <node_id> --status completed
python roadmap_cli.py update <json_path> <node_id> --label "新标签" --notes "备注内容"

# ⚠️ 修改 label 前先读「修改节点名称的安全流程」

# 删除节点及所有子节点
python roadmap_cli.py delete <json_path> <node_id>

# 查看节点详情 (JSON)
python roadmap_cli.py get <json_path> <node_id>
```

### 决策记录

```bash
# 为节点添加决策
python roadmap_cli.py decide <json_path> <node_id> "问题" "答案" ["备注"]

# 列出所有决策（或指定节点）
python roadmap_cli.py decisions <json_path>
python roadmap_cli.py decisions <json_path> <node_id>
```

### 渲染

```bash
# 轻量 Markdown section → 写入关联的 md 文件（给人看的）
# 内容：树形 depth=2 + 当前焦点节点（决策+备注）
python roadmap_cli.py render <json_path>

# 全量 Markdown section → stdout（调试用）
# 内容：树形全展开 + 全部决策表 + 当前焦点详情
python roadmap_cli.py section <json_path>

# 关联 md 文件
python roadmap_cli.py link <json_path> <md_file>
```

### 导航

```bash
# 树形视图
python roadmap_cli.py tree <json_path>
python roadmap_cli.py tree <json_path> <node_id>    # 从指定节点开始
python roadmap_cli.py tree <json_path> <node_id> --depth 3

# 从根到节点的路径
python roadmap_cli.py path <json_path> <node_id>

# 兄弟节点
python roadmap_cli.py siblings <json_path> <node_id>

# 当前施工点（第一个 in_progress 的叶子节点）
python roadmap_cli.py focus <json_path>
```

### 验证与统计

```bash
# 数据完整性验证
python roadmap_cli.py validate <json_path>

# 统计信息
python roadmap_cli.py stats <json_path>
```

## Agent 使用示例

```
# 场景：Human 说「把文章处理后端走通」

# 1. 先在路线图上定位
python roadmap_cli.py tree roadmap.json 1-1-1
# 输出:
# [~][Y+] 1-1-1. 技术文章处理
# ├── [x][Y+] 1-1-1-1. URL → 存原文
# ├── [~][Y+] 1-1-1-2. 叠加摘要处理
# ├── [ ][Y+] 1-1-1-3. 自动打标签
# └── [ ][Y+] 1-1-1-4. 定时批处理

# 2. 添加新节点
python roadmap_cli.py add roadmap.json 1-1-1 "文章处理后端流水线" --status in_progress

# 3. 记录决策（JSON 内）
python roadmap_cli.py decide roadmap.json 1-1-1-5 "后端用什么？" "Python + FastAPI" "轻量够用"

# 4. 施工完成后更新状态 → 父节点自动同步
python roadmap_cli.py update roadmap.json 1-1-1-5 --status completed --notes "API: POST /articles/convert"

# 5. 更新 Human 的 md 视图（轻量：树+焦点）
python roadmap_cli.py render roadmap.json

# 6. 调试时查看全量（stdout）
python roadmap_cli.py section roadmap.json
```

## Script 路径

Skill 脚本位于 skill 目录本身，Agent 运行时按 skill 目录计算路径：

```
<skill_dir>/roadmap.py        # 核心库
<skill_dir>/roadmap_cli.py    # CLI 入口
```

Agent 在 Skill 加载后，用 `$SKILL_DIR` 或绝对路径定位脚本。

## 与 zj-grill-me 配合

`zj-roadmap-driven` 是 `zj-grill-me` 的搭档：
- `zj-grill-me` 负责逐层拷问，到达决策树叶子节点
- `zj-roadmap-driven` 负责把每层决策沉淀到路线图 JSON + md section
- 两者交替：grill 一个 Q → roadmap 记录决策 → grill 下一个 Q

## Notes

- JSON 是唯一真相源。所有数据操作必须通过 CLI，**禁止 Agent 直接 Read/Edit JSON 或 md 的路线图 section。**
- md section 由 `render` 命令完全重写，手动修改会被覆盖。
- `render` 输出轻量视图（树 depth=2 + 焦点），`section` 输出全量视图（stdout，调试用）。
- 删除节点会递归删除所有子节点，操作前确认。
- 如果路线图 JSON 不存在，Agent 应先用 `init` 创建。
- 无 `import` 命令。md 不能反导回 JSON。
