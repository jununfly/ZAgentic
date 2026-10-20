---
name: zj-ui-core
description: >-
  UI 链的契约基座（S0，不参与 S1..S10 阶段链）：canonical schema 校验、deny-first 拒绝、
  unknown 四元组保留、原子提交与幂等键、WCAG contrast 计算，以及 S1..S4 的确定性实现。
  Use when 需要验证 ui/* 技能的行为是否被机械守住，或运行失败 fixture。
  不是可调用阶段，不要用它产出 brief 或 design。
argument-hint: "<fixture 目录，或留空查看已实现阶段>"
metadata:
  status: implemented
  implemented_in: 1-6-2
source: zagentic
---

# zj-ui-core

S0 · BASE · `read` owner（不写任何 canonical 字段）

> **状态：已实现（1-6-2）。** 本技能是 `skills/ui/` 的代码载体，不是链上的一个阶段：
> 它没有 `writes`，也不出现在 S1..S10 的顺序里。S1..S4 的确定性实现都在 `scripts/`，
> S5..S10 于 1-6-3 / 1-6-4 接入同一套原语。

## Capability Manifest

```json
{
  "skill_id": "zj-ui-core",
  "manifest_version": "0.1.0",
  "stage": "S0",
  "owner_scope": "read",
  "writes": [],
  "reads": ["UI-BRIEF.md", "UI-DESIGN.md"],
  "input": [
    {"name": "stage request（结构化）", "type": "object", "required": "yes", "source": "agent"}
  ],
  "output": [
    {"name": "stage result envelope", "type": "object", "artifact_kind": "non-canonical", "atomic": false}
  ],
  "forbidden": [
    "解析自然语言：对话→结构化由 agent 完成",
    "执行 effect：网络访问、凭据使用、远程写回",
    "替调用方补默认值（缺失必须变 unknown 四元组）",
    "让 adapter 扩写 component catalog"
  ],
  "dependencies": [
    "canonical artifact schema（1-2-1）",
    "deny-first / unknown 四元组语义（1-2-2）"
  ],
  "required_capabilities": [
    "schema-validation",
    "unknown-quartet-preservation",
    "idempotent-commit",
    "contrast-computation"
  ],
  "stop_conditions": [
    {"condition": "字段未注册或类型不符", "action": "STOP", "next": "REJECTED，零写入，列出字段与建议 owner"},
    {"condition": "必填缺口", "action": "STOP", "next": "转 unknown 四元组 + NEEDS_CONTEXT"},
    {"condition": "幂等键重放但内容不同", "action": "STOP", "next": "REJECTED，不覆盖既有 revision"}
  ],
  "owner": "ui/contract owner",
  "precedence": 5,
  "failure_fixtures": [],
  "human_gate": "none"
}
```

## 为什么需要这个基座

十个阶段技能都把同一批语义写在自己的 SKILL.md 里：unknown 不能压空、未注册字段不能静默丢弃、
缺失必填要转 `NEEDS_CONTEXT`、revision 要原子提交。这些句子**散文可以写任意多遍**，但只有一处
实现时它们才可能被机械证伪。把实现拆成十份，就是让"unknown"在第十份里悄悄退化成可空字符串。

因此：**语义只实现一次，阶段技能只声明契约。**

## 模块

| 文件 | 职责 |
| --- | --- |
| `scripts/ui_skill_core.py` | schema 表、状态优先级、deny-first、unknown 四元组、`commit()` 幂等提交、WCAG contrast、result 信封 |
| `scripts/ui_stages.py` | S1..S4 的 runner：`run_brief` / `run_discover` / `run_direction` / `run_design_system` |
| `scripts/run_fixture.py` | fixture 跑批：`--recursive` 扫目录，逐条比对 expected，非零退出即失败 |

## 三条不变量（改代码前先读）

- **deny-first**：未注册字段一律 `REJECTED` 并列出字段名，绝不静默丢弃。camelCase 笔误若被丢弃，
  文档就会以"已补齐"的样子继续往下走。
- **unknown 四元组**：`{path, raw, reason, source}` 必须完整。`raw` 允许是 `null`（"确实什么都没说"
  是信息），但键不能消失，也不能换成猜测值。
- **原子提交 + 幂等键**：`commit()` 以 `(artifact_kind, idempotency_key)` 去重；同键重放内容相同 →
  写入次数不增，内容不同 → `REJECTED`，不覆盖。

## 状态优先级

`REJECTED > BLOCKED > QUARANTINED > HUMAN_REVIEW_REQUIRED > NEEDS_CONTEXT > OK`

一次运行命中多条时取最严重的那个，避免轻度发现掩盖硬失败。

## 怎么用

```bash
python scripts/run_fixture.py <fixture-dir>            # 单条
python scripts/run_fixture.py <root> --recursive       # 全部
python scripts/run_fixture.py --list-stages            # 本 build 已实现的阶段
```

fixture 形态（`tests/ui-agent-skills/fixtures/skills/<FF-ID>/`）：

- `input.json`：`{fixture_id, stage, description, request}`
- `expected.json`：断言集 —— `status` / `writes` / `unknown[{path,reason}]` / `rejected_fields` /
  `quarantined` / `candidates` / `questions_max` / `artifact_present` / `artifact_expect` /
  `artifact_absent` / `revision_is_sha256`

`artifact_absent` 是防"好心补默认值"的那一条：它断言某个字段**必须不存在**，而不是等于空。

## 交接

- 上游：S1..S4 的 SKILL.md 声明契约，本技能提供实现与 fixture 跑批。
- 下游：1-6-5 的 resolver 用同一批 fixture 串链；1-6-3 / 1-6-4 往 `ui_stages.py` 追加 S5..S10。
