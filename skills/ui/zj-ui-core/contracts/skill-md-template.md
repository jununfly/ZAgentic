# UI skill 的 SKILL.md 模板（1-6-1）

> **这份文件是模板的单一事实源。** `skills/ui/zj-ui-*/SKILL.md` 的骨架必须与它同形；
> 新增第 11 个 UI skill 时先改这里，再复制成形，不要凭记忆手写。
>
> 归属路线图节点 1-6-1。上游契约：`skill-capability-manifest.md`（16 字段、
> 阶段责任卡、fixture→owner 矩阵）、`/docs/designs/ui-agent-skills/ui-agent-skills-canonical-schema.md`（六类 canonical
> artifact）、`/docs/designs/ui-agent-skills/ui-agent-skills-ui-flow-v1-contract.md`（六义）。
>
> 机械守卫：`tests/test_ui_agent_skills_layout.py`（目录、frontmatter、16 字段、stage 唯一、
> fixture 归属、四份索引与术语登记是否同步）。

---

## 1. 为什么正文里要放 JSON 块

16 个字段必须逐字出现在 SKILL.md（1-3-1 §7 对 1-6 的硬要求），同时要能被 resolver 与静态
测试机器读取。两个约束一起排除了两个直觉方案：

- **塞进 YAML frontmatter**：`scripts/validate-skill-frontmatter.py` 对 top-level 字段做白名单，
  16 个新键会全部报 `unknown top-level field`，等于让每个新 skill 出生就红。
- **另放 `manifest.yaml` 旁挂文件**：违反"SKILL.md 必须包含 16 字段"，且漂移时没有任何东西会喊。

所以：正文 `## Capability Manifest` 标题下的一个 ```` ```json ```` 块，键名与 1-3-1 §1 表
**完全一致、不增不减**（测试断言 16 个键的集合相等，多一个少一个都失败）。16 个键按顺序是：

```
skill_id, manifest_version, stage, owner_scope, writes, reads, input, output,
forbidden, dependencies, required_capabilities, stop_conditions, owner,
precedence, failure_fixtures, human_gate
```

## 2. 骨架

```markdown
---
name: zj-ui-<stage>
description: >-
  <S<n> <STAGE>：一句话职责。Use when <触发场景>。
  当前为契约骨架（1-6-1），可执行实现未落地。
argument-hint: "<这个 skill 期待的人类输入>"
metadata:
  status: contract-skeleton
  implemented_in: <1-6-2 | 1-6-3 | 1-6-4>
source: zagentic
---

# zj-ui-<stage>

S<n> · <STAGE> · <write|read|emit> owner of `<artifact>`

> **状态：契约骨架（1-6-1）。** 本文件冻结 capability manifest、输入输出、禁止事项、停止条件
> 与失败 fixture id；可执行实现归 `<节点>`，fixture 运行归 1-6-5。实现落地前不要把本 skill
> 当作可用能力。

## Capability Manifest

```json
{ ... 16 个字段 ... }
```

## 职责与边界

<做什么 / 不做什么 / 与上下游的分界线>

## 停止条件与 Human gate

<逐条列出 manifest.stop_conditions 与 human_gate 的触发语义>

## 失败 fixture

<FF-XXX-01 正常 / FF-XXX-02 冲突 / FF-XXX-03 失败，各一行说明期望终态；id 与 1-3-1 §4 一致>

## 交接

<上游拿到什么、交给谁、交接失败怎么办（不自动改派）>
```

## 3. 填写规则

1. **`writes` 不得为空**（1-3-1 §1）。`owner_scope=emit` 的 skill（S6）写的是显式声明的
   非 canonical 产物 `preview`，这是 §1.3 允许的唯一例外，必须在正文说明，不能留空数组。
2. **`reads` 不含自身 `writes`**：同一 skill 自己刚写的 artifact 不算"读依赖"，上游关系写进
   `dependencies`。
3. **`stage` 一 skill 一阶段**：十个 skill 对应 S1..S10，永不并列。`precedence` 取 stage 序号 ×10。
4. **`failure_fixtures` ≥3 且 id 必须在 1-3-1 §4 矩阵里**：正常 / 冲突 / 失败各一，禁止自造 id。
5. **`forbidden` 不得为空数组**——"没有禁止事项"是不可接受声明。
6. **`owner` 写人类责任岗**（brief/contract owner 等），不是 skill 名。
7. **frontmatter 只放 `name` / `description` / `argument-hint` / `metadata` / `source`**；
   `description` 不得含尖括号，且不得声称已实现的能力。
8. **状态标记不可省**：`metadata.status=contract-skeleton` 与正文状态块同时存在，直到对应
   实现节点把它改成 `implemented`。这是本仓库"不把未完成伪装成已完成"的落地形式。

## 4. 同步清单（新建 skill 时必须一起改）

| 位置 | 改什么 | 谁守 |
| --- | --- | --- |
| `skills/ui/<skill>/SKILL.md` | 本模板成形 | `tests/test_ui_agent_skills_layout.py` |
| `skills/ui/README.md` | `](./<skill>/SKILL.md)` + 一行描述 | 同上 |
| `README.md`（top-level） | `](./skills/ui/<skill>/SKILL.md)` + 一行描述；桶数量描述 | 同上 |
| `skills/engineering/zj-guide/SKILL.md` | 路由条目 + Scope 里的桶清单 | 递归校验器 `validate_guide_coverage` |
| `AGENTS.md` | bucket 清单 | 同上（人工） |
| `ZJ-CONTEXT.md` | `Skill bucket` 词条 + 新术语 | `tests/test_ui_agent_skills_layout.py` |
| `scripts/validate-zagentic-plugin.py` | `PUBLIC_BUCKETS`（仅新桶时） | 递归校验器自身 |
| `scripts/list-skills.sh` + `scripts/zagentic-skills-list` | `categories`（仅新桶时）+ 重新生成清单 | 人工 + 安装脚本 |
