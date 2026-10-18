# zj-composer issue #177 修复方案

## 背景
issue #177：zj-composer 的 `discover_catalog.py` / `generate_snapshot.py` 硬编码 ZAgentic 仓库布局
（`PUBLIC_BUCKETS`、`skills/<bucket>/README.md`、`skills/engineering/zj-guide/SKILL.md`、
`scripts/zagentic-skills-list`），并用 `Path(__file__).resolve().parents[4]` 反推 repo root。

**真实使用场景（已校准）**：ZAgentic 被整体安装到 Claude Code / Codex / WorkBuddy 等 Agent 应用；
调用方是 **Agent（模型）**——用户 prompt 指派，或 Agent 应用以工具形式自动调用。输出 JSON 被模型解析后编排任务。
"静默空 provenance" 在此升级为"Agent 被喂了假的空能力索引"——比误导人类更危险。

**安装布局（Q1/Q3 已确认）**：ZAgentic 中的各个 skill 作为**独立包并列在某个 skills 根下**
（`<skills_root>/<skill-name>/`），**不再是 monorepo 的 `skills/<bucket>/...` 嵌套树**；
`scripts/zagentic-skills-list` 与桶 README **不会随安装带走**（monorepo 内部产物，安装后不存在）。
推论：
1. 原 `parents[4]`（相对 monorepo 根）和所有 monorepo-index 表面在安装后都指向错误/不存在的位置。
2. 安装后在 Agent 本地**没有 ZAgentic 的集中目录** → `--root` / `ZAGENTIC_ROOT` 无价值（Q3）。
3. 稳定锚点是 **skill 包自身**（`__file__.resolve().parent.parent` = `<skills_root>/zj-composer`）。
   flat 安装下 `skills_root = parents[2]`；monorepo-dev 下向上回溯首个含 `skills/<bucket>/*/SKILL.md` 的祖先
   （根解析见 Slice 1，**绝不假设固定祖先深度**）。

**发现目标（Q2 已确认）**：
- 1st：随 ZAgentic 安装的技能（`<skills_root>/<zagentic-skill>/`）。
- 2nd：Agent 当前可使用的其他 skills/tools/plugins（`<skills_root>/` 下非 ZAgentic 的技能包，及 Agent 暴露的其他能力）。

## 设计原则
- 调用方是 Agent：**JSON 契约为主、退出码为辅**。`catalog_present` 与结构化 `diagnostics`
  （manifest 缺失 / 技能根无技能包等指引）必须进入 stdout 的 JSON payload；退出非零仍须保持（已定 `1`）。
- **root 显式解析、绝不假设固定祖先深度**：优先级 `--root` → `ZAGENTIC_ROOT` 环境变量 → 位置派生。
  位置派生以 skill 包自身为锚（`__file__.resolve().parent.parent` = 包目录），先试 `parents[2]` 是否为 flat
  技能根（含 `*/SKILL.md`），否则向上回溯首个含 `skills/<bucket>/*/SKILL.md` 的祖先作为 monorepo-dev 根。
  绝不用 `parents[4]` 或任何硬编码 monorepo 深度。`--root` 仅作非标准安装的可选 override，非首要机制。
- **frontmatter 标记分类，无中央名册**：每个 SKILL.md 在 YAML frontmatter 写入 `source: zagentic` 声明归属；
  `is_zagentic = (frontmatter.source == "zagentic")`。不再维护中央 roster / manifest 名册文件 —— 新 ZAgentic
  skill 只要带标记即自动识别，从根上消除"名册漏登记 → 静默漂移"的失败模式。
- **确定性枚举**：`skill_files` 对发现结果按目录/路径排序，并用 `path.resolve().is_relative_to(root.resolve())`
  守卫拒绝符号链接逃逸。同一 catalog root 永远产出同一份排序结果，与 cwd/符号链接无关。
- 发现枚举 `installed-flat` 下的 `<skills_root>/*/SKILL.md`，或 `monorepo-dev` 下的
  `<skills_root>/skills/<bucket>/*/SKILL.md`；monorepo-only 的 index 表面（bucket_readmes/root_readme/guide/install_list）去除。
- 布局自动探测（`detect_layout`）：先判 `*/SKILL.md` 为 `installed-flat`，否则判 `skills/<bucket>/*/SKILL.md` 为 `monorepo-dev`，
  供 ZAgentic 维护者本地跑 monorepo 与安装后 flat 共用同一套脚本。
- TDD：每切片 红-绿-重构。
- 退出码遵循仓库约定：通用错误默认 `exit 1`；`2` 已保留给 roadmap 锁超时，不复用。

## 切片

### Slice 1 — 显式 root 解析（path C.1，已落地）
- 新增 `resolve_root(explicit, env, start_script)`：
  - 优先级：`--root`（explicit）> `ZAGENTIC_ROOT` 环境变量 > 位置派生。
  - 位置派生：以脚本位置为锚（`package_dir = __file__.resolve().parent.parent`），先试 `package_dir.parent`
    （flat 安装下即 `<skills>` 根，需 `_has_direct_skill_packages` 校验含 `*/SKILL.md`）；否则向上回溯首个
    含 `skills/<bucket>/*/SKILL.md`（`_has_bucket_structure`）的祖先，作为 monorepo-dev 根。
  - **绝不假设固定祖先深度**（无 `parents[4]`，也不硬编码 `parents[2]` 为唯一解）。
- 删除 `discover_catalog.py` / `generate_snapshot.py` 的 `parents[4]` 反推。
- 不再依赖 `scripts/zagentic-skills-list` / `skills/engineering/README.md` 作为根标记（安装后不存在）。
- 测试：installed-flat 下位置派生命中 skills_root；monorepo-dev 下回溯命中；`--root` override 生效；
  脚本移出包结构 → `catalog_present:false` + 诊断。

### Slice 2 — frontmatter 标记分类 + 布局自动探测（path C.2，已落地）
- **去除中央 roster / manifest 名册文件**。分类完全由 SKILL.md frontmatter 驱动：
  - `source: zagentic` 标记 → `is_zagentic: true`；其余（无标记 / 其他 source）归为「Agent 其他可用能力」。
  - 因此 ZAgentic 各 skill 包内 SKILL.md 已统一写入 `source: zagentic`（53 个已落盘）。
- 新增 `parse_frontmatter(path, warnings)`：解析 YAML frontmatter，保留畸形条目为 warning
  （缺失 frontmatter / 非法 YAML / name 与目录名不一致 / name·description 缺失均记 warning），不崩溃。
- 新增 `detect_layout(root)`：自动判定 `installed-flat`（`<root>/*/SKILL.md`）或 `monorepo-dev`
  （`<root>/skills/<bucket>/*/SKILL.md`），无技能包返回 `None` → `catalog_present:false`。
- 去除 monorepo-only 的 `index_surfaces` / `declarations`（bucket_readmes/root_readme/guide/install_list）；
  替换为 `skills_root`、`layout`、`is_zagentic`、`frontmatter`、`declared`（inputs/outputs/dependencies/boundaries 元数据）。
- skill 记录字段：`name` / `directory` / `path` / `is_zagentic` / `frontmatter` / `declared` / `warnings`
  （原 `metadata_warnings` 已并入 `warnings`）。
- 测试：flat 下 `source:zagentic` 正确分类；非 zagentic 技能归为其他；frontmatter 畸形记 warning 不崩；
  `monorepo-dev` 回退仍工作。

### Slice 3 — 诚实失败（path C.3，已落地）
- `discover_catalog` 返回 `catalog_present: bool`：
  - `skills_root` 无技能包（layout 为 `None`）→ `catalog_present: false`（防静默漂移关键）+ `diagnostics`。
  - 定位到 skills_root 但 ZAgentic 技能 0 命中 → `catalog_present: true`、`skills=[]`（合法空，exit 0）。
- `main()` 映射：`catalog_present is False` → `sys.exit(1)` + JSON 内 `diagnostics`
  （"技能根无技能包，传 --root 指向安装技能目录"）。
  - **退出码用 `1`（非 `2`）**：仓库约定 `2` 已保留给锁超时（瞬态可重试）；本错误属默认 `exit 1` 桶，复用 `2` 会重载语义。
- `generate_snapshot`：检测 `catalog_present is False` → 拒写空 snapshot，`sys.exit(1)` + 诊断（打印到 stderr）。
- 测试：空发现 → `catalog_present:false`；generate 退出 `1` 且不落盘；定位到根但空 → `catalog_present:true`、exit 0。

### Slice 4 — 溯源完整性加固（已落地）
- 记录真实 `skills_root` 绝对路径（替代 `"root": "."`）。
- 枚举后加 `is_relative_to(skills_root.resolve())` 守卫，阻断符号链接逃逸（`skill_files`）。
- frontmatter 解析 `read_text` 包 `try/except` → 不可读文件记 warning 而非崩溃。
- snapshot 摘要 `canonical_manifest_digest` 仅对 SKILL.md 文件（相对 catalog root）做内容寻址哈希，
  替代已删除的 monorepo index 表面（无中央 manifest 后，SKILL.md 自身即唯一事实源）。
- 修复 `.replace("+00:00","Z")` hack → `datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")`。

### Slice 5 — 标准异味清理（低优先，部分落地）
- `path` / `source_reference` 冗余键已合并为单一 `path`（source_reference 删除）。
- 抽出共享 `composer_root.py` 消除两文件重复的 `parse_args`/`__main__` 样板 —— **未做**，留待后续低优先清理。

## 划出范围（建议独立 issue，不并入 #177）
- snapshot 只哈希 SKILL.md（相对 catalog root），未覆盖技能包内兄弟文件 → 溯源完整性增强，另开 issue。
- Agent 暴露的非 skill-package 形式的 tools/plugins（Agent 原生工具）枚举，若 Agent 提供统一表面则后续接入。

## 状态
- 退出码：**已定 = 1**（根无技能包 / catalog_present:false 一律 exit 1；快照拒写空 catalog 亦 exit 1）。
- 调用方模型：**已校准** —— Agent 消费 JSON，JSON 契约为主。
- 安装布局 / Q1–Q3：**已确认**（flat 独立包、无集中目录、`--root`/`ZAGENTIC_ROOT` 仅可选 override）。
- 分类机制：**已实现 = frontmatter `source: zagentic` 标记 + 布局自动探测**，无中央 roster / manifest 名册。
- 确定性：`skill_files` 排序枚举 + 符号链接逃逸守卫，cwd/符号链接无关。
- Slice 1/2/3/4：**已落地并已验证**（21 个单测 + `run_regressions.py` 全绿，快照 `catalog-v1-df316e12...` 已重生）。
- Slice 5：部分落地（`source_reference` 合并），`composer_root.py` 抽离未做（低优先）。
- **代码审计（zj-code-review）结果已闭环**：① `resolve_root` 去掉 `name=="skills"` 名称门，改纯内容判定（`_inside_monorepo_skills` 区分 monorepo，行为保持）；② 畸形 frontmatter 警告改归 per-skill `warnings`（不再混入全局 bucket）；③ `generate_snapshot` 诚实失败诊断改走 stdout JSON（与 `discover_catalog` 契约一致）；④ 隔离 `zj-git-bypass-safe-delete/SKILL.md` 的 CRLF→LF 归一化噪音（仅留 +1 `source: zagentic` marker，保留原 CRLF）；⑤ `run_regressions.py` 去重 `canonical_json_digest`（复用 `validate_plan.canonical_manifest_digest`）、`parents[4]` 固定祖先深度改为 `_repo_root()` 内容派生。
- 分支：`fix/177-composer-frontmatter-discovery`（全部改动未提交）。
