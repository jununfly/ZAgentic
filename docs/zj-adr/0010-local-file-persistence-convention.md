---
doc-kind: adr
authority: zj-grill-with-docs
status: accepted
issue: "221"
---

# 会本地落盘的 skills 统一用相对路径 + 隔离目录（升华 #169）

## Context

`zj-roadmap-driven` 的 carrier JSON 曾把 `md_file` 恒存绝对路径，macOS↔Windows 经 Git 共享时把对方机器路径当相对路径、在仓库根造垃圾目录并乒乓漂移（#169 已单点修复）。#221 指出这是更普遍问题的症状：凡会本地落盘"生成"文件的 skill，若默认用绝对路径、或把产物撒进 `docs/` 等共享文档区，会同时踩两个坑——机器相关绝对路径写进可 git 跟踪文件 → 跨机漂移；生成文件混入正式文档区 → 污染。

全量重梳：实际 **11 个** skill 会本地落盘（原 issue 的"待确认清单"严重不全）。真正雷区：绝对路径硬编码进 home（`zj-storage-analyzer`→`~/Desktop`、`zj-research`→`~/.cache`）、默认撒进 cwd（`zj-open-source-capability-fit`）、散落用户项目未声明（`zj-discuss`/`zj-doc-collab` 的 `briefings/`、roadmap 的 md/lease）。`/docs/plans/` 本就是成熟的 Process 暂存区（见 `docs/prds/codebase-docs-capability.md` 与 `check-docs-dangling-refs.py` 的 `RETIRED_NAMESPACES`）。

## Decision

升华 #169 为跨 skill 通用约定（范围：仅**持久化产物**，不含纯临时态/`/tmp`）：

1. **引用一律相对路径**，绝不存绝对路径；解析基准 = carrier/技能目录（normpath）。
2. **落点按使用场景二分**：项目输出产物落 `<project-root>/tmp/skills-outputs/<skill>/<topic>/`（gitignored）；过程/计划类（roadmap、wayfinder map）落 `docs/plans/<skill>/...`（git 跟踪、close-out 后清理，语义写入 `zj-docs-ontology`）；**非项目输出必须主动询问 Human** 落点，绝不默认 `~/`、`~/Desktop`、cwd、仓库根。
3. **解析以 carrier/技能目录为基准**做 normpath；遇异机绝对路径 fail-loud（#169 机制保留）。
4. **单向耦合**：计划（`docs/plans/`、roadmap）瞬态，决策（ADR）持久；依赖方向只能 `计划 → 决策 → 代码`，**禁止** `代码/长期文档 → 计划`。`check-docs-dangling-refs.py` 对来自持久产物、指向 `docs/plans/` 的入站引用报警（WARN-first）。roadmap 节点成熟为决策时抽取成 ADR。
5. **轻量 guard**：扩展 `scripts/check-skill-runtime-closure.py`（`TARGET_PROJECT_ROOTS` 加 `tmp/`；新增 WARN 模式捕获 skill 内绝对 home/cwd 默认）。WARN-first，待 11-skill 迁移清空后可视情升级 ERROR（符合本仓库校准纪律）。
6. `zj-research` 的 `~/.cache` 编译器缓存排除出约定（属临时态），代码注释标明"缓存非产物"。

## Consequences

- 跨机共享产物/配置不再污染、不再乒乓；生成文件不混进 `docs/`，引用可审计、清理可定位。
- roadmap 的 `ROADMAP.md` 进 `docs/plans/`（保留"用户直接看/改项目内计划"体验）；`docs/plans/` 清理纪律需 skill 与人工遵循。
- 11 个 skill 中 `zj-storage-analyzer`、`zj-open-source-capability-fit`、`zj-discuss`/`zj-doc-collab` 需代码迁移（见附录）；其余已合规或属调用方指定。
- guard 当前 WARN（不阻断 required CI）；升级 ERROR 前须先清空现有 WARN。
- `.gitignore` 增 `tmp/`、`skills-outputs/`；`zj-docs-ontology` 写明 `docs/plans/` 暂存语义与清理纪律。

## 迁移清单（附录，独立 PR，feat/chore 分离）

状态图例：✅ 已完成（代码已改）｜✅ 已合规（无需改）｜⬜ 待实施（未改代码）

| Skill | 当前落点 | 处置 | 状态 |
|-------|----------|------|------|
| zj-roadmap-driven | carrier 同目录 | md→`docs/plans/`；余物→`<proj>/tmp/skills-outputs/roadmap-driven/`；保留 #169 相对+fail-loud | ⬜ 待实施（仅约定，代码未改） |
| zj-composer | `skills-outputs/zj-composer/` | 视为项目=ZAgentic，迁 `<ZAgentic>/tmp/skills-outputs/composer/`（或保留，已合规） | ✅ 已合规（无需改） |
| zj-discuss | subdoc 旁 `briefings/` | → `<proj>/tmp/skills-outputs/discuss/<topic>/` | ✅ 已完成（2026-10-27） |
| zj-doc-collab | subdoc 旁 `briefings/` | → `<proj>/tmp/skills-outputs/doc-collab/<topic>/` | ✅ 已完成（2026-10-27） |
| zj-research | `~/.cache` + 调用方 | 缓存 exempt（注释）；报告按项目输出落点 | ✅ 已合规（缓存豁免 + 调用方指定） |
| zj-code-research | 调用方 | 项目输出 → `<target>/tmp/skills-outputs/code-research/<topic>/` | ✅ 已合规（调用方指定） |
| zj-tech-research-report | 调用方 | 有目标项目→项目输出；无→问 Human | ✅ 已合规（调用方指定） |
| zj-open-source-capability-fit | 默认 cwd | 改为必填 `--out` + 缺失时报错问 Human | ✅ 已完成（2026-10-27） |
| zj-systematic-research | 调用方 | 同 research 家族 | ✅ 已合规（调用方指定） |
| zj-storage-analyzer | `~/Desktop` | 删默认 → 问 Human（非项目输出） | ✅ 已完成（2026-10-27） |
| zj-ui-core | 用户选/`--out` | 非项目输出 → 问 Human | ✅ 已合规（设计即问 Human） |

## Amendment (2026-10-27)

- **Guard 已升级 ERROR**：第 5 条原计划"WARN-first，待迁移清空后升级 ERROR"——实际在清空全部违例后已执行升级。`scripts/check-skill-runtime-closure.py` 的 `SKILL_ABS_HOME_DEFAULT` 与 `scripts/check-docs-dangling-refs.py` 的 `plan-coupling` 现均为 **ERROR**，且当前 0 违例（两脚本 exit 0，required CI 不红）。`RE_ABS_HOME_DEFAULT` 正则已收窄，仅抓 home **输出目录**，放过 `HOME = expanduser("~")` 这类扫描根/安全边界误报。
- **迁移清单状态**：上表 4 项代码迁移已完成（zj-discuss / zj-doc-collab / zj-open-source-capability-fit / zj-storage-analyzer），其余 6 项经核查属"已合规"或"调用方指定、无需改"。唯一残留开放项是 `zj-roadmap-driven` 的 md→`docs/plans/` 代码改动，约定已定、代码待实施。
