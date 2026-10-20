# UI 阶段引擎契约（S0 base carrier · v0.1）

- **归属节点**：1-6-2（产品实现路线 · `exploit`）
- **实现落点**：`skills/ui/zj-ui-core/scripts/`（`ui_skill_core.py` / `ui_stages.py` / `run_fixture.py`）
- **被测对象**：`tests/ui-agent-skills/fixtures/skills/FF-{BRIEF,DISC,DIR,DS}-*/`
- **上游契约**：`ui-agent-skills-canonical-schema.md`（字段与 unknown policy）、
  `ui-agent-skills-brief-design-edit-semantics.md`（deny-first / patch / 不执行 effect）、
  `ui-agent-skills-skill-capability-manifest.md`（16 字段与 §4 fixture 矩阵）

---

## 0. 为什么要有这个引擎，而不是十份实现

十个 stage skill 的 SKILL.md 都在重复同一批句子：unknown 不能压空、未注册字段不能静默丢弃、
缺必填要转 `NEEDS_CONTEXT`、revision 要原子提交。**散文可以写十遍，但只有一处实现时它才可能被
证伪**。分散实现的实际后果不是"多写点代码"，而是第十份里 `unknown` 悄悄退化成可空字符串，
而第十份的 fixture 恰好没覆盖到那个分支。

所以本节点确立一条结构规则：

> **语义实现一次，阶段只声明契约。**

`zj-ui-core` 因此是 **S0 base carrier**：它是技能目录（含 SKILL.md，因此递归校验器与 copy 安装
天然覆盖），但 `owner_scope=read`、`writes=[]`、`precedence=5`，不参与 S1..S10 阶段链。
选它而不是 `skills/ui/_lib/` 的原因很硬：`scripts/validate-zagentic-plugin.py` 规定 bucket 的
直接子目录必须含 SKILL.md，共享库会被判 `missing SKILL.md`。

---

## 1. 分工：agent 解析，代码校验

| 步骤 | 谁做 | 产物 |
| --- | --- | --- |
| 读对话 / 读 `UI-BRIEF.md` 编辑，抽成结构化 request | agent（LLM） | `{candidate}` / `{evidence}` / `{cards}` / `{tokens}` |
| schema 校验、deny-first、unknown 四元组、原子提交、contrast | 引擎（确定性） | result envelope + artifact revision |

引擎**不做自然语言抽取**。若让代码用正则从对话里猜 `goal_users`，fixture 就退化成"我写什么它
就认什么"——测试与实现同源，等于用测试给自己发证书。

---

## 2. 状态集合与优先级

```
REJECTED > BLOCKED > QUARANTINED > HUMAN_REVIEW_REQUIRED > NEEDS_CONTEXT > OK
```

一次运行命中多条时取最严重的那个。理由：轻度发现（如待补问题）不能掩盖硬失败（如非法字段）。
`writes` 只有两种取值：`1` = 提交了一个 revision；`0` = 全程未触碰 `commit()`。

| 状态 | 含义 | 典型触发 |
| --- | --- | --- |
| `OK` | 该 stage 的职责闭合，revision 已提交 | 四类必填齐备 |
| `NEEDS_CONTEXT` | 证据/必填不足，停止并交人，零写入 | 缺 `success_criteria`；追问预算耗尽 |
| `HUMAN_REVIEW_REQUIRED` | 只能由人拍板的判断尚未签 | 方向未选定 |
| `QUARANTINED` | 某个外部参考不可归因，被排除在默认产物外 | `license: unknown` |
| `BLOCKED` | 硬规则不满足，禁止降级通过 | 未注册组件；contrast < 4.5 |
| `REJECTED` | 输入违反契约，拒绝且不留痕 | 未注册字段；unknown 四元组缺键 |

---

## 3. 四个 stage 的入口契约

| stage | 主要输入 | 必填（本 stage 负责） | 停止条件 |
| --- | --- | --- | --- |
| `brief` | `{input_revision, candidate{}}` | `goal_users` / `goal_task` / `constraints` / `success_criteria` | 缺口 → `NEEDS_CONTEXT` + 四元组，最多 2 问；未注册字段 → `REJECTED` |
| `discover` | `{brief{}, brief_revision, evidence[], question_budget}` | —（只补写 `unknown[]` 与证据） | `questions_asked > budget` → `NEEDS_CONTEXT`；改写上游已冻结字段 → `REJECTED` |
| `direction` | `{cards[], human_choice, brief_revision}` | `direction_choice` / `provenance` | 无 Human 选择 → `HUMAN_REVIEW_REQUIRED`；`license` 不可归因 → `QUARANTINED` |
| `design_system` | `{design{direction_choice,…}, tokens{}, components[]}` | `tokens` / `typography` / `color` / `component_principles` / `tradeoffs` | 未注册组件 → `BLOCKED`；contrast 不达标 → `BLOCKED`（**不得替换相近色**）；字体 `license` 不明 → `QUARANTINED` |

补充规则（都写在代码里，不靠散文）：

- **空值不是值**：`goal_users: []` 视为缺口。JSON 里"字段存在"很容易被误当成"已填"。
- **component catalog 归本仓库**：`COMPONENT_REGISTRY` 是常量；adapter 只能投影，不能扩表。
- **unknown 四元组键集固定** `{path, raw, reason, source}`，多键少键都 `REJECTED`；`raw` 允许
  `null`（"确实什么都没说"是信息），但键不能消失。
- **contrast 只算 schema 承诺的两对**：`on_surface/surface` 与 `on_primary/primary`，阈值 4.5。

---

## 4. 原子提交与幂等键

`commit(store, artifact_kind, payload, idempotency_key)`：

- `revision = sha256(canonical_json(payload))`，`canonical_json` 排序键 + 紧凑分隔符；
- 同 `(artifact_kind, idempotency_key)` 重放且内容相同 → `writes=0`，revision 不变
  （`FF-ORCH-03` 的"100 次重放 1 次有效写入"）；
- 同键但内容不同 → `REJECTED`，**不覆盖**既有 revision（幂等键不是"随便覆盖"的许可证）。

---

## 5. fixture 形态与断言语义

```
tests/ui-agent-skills/fixtures/skills/<FF-ID>/
  input.json     {fixture_id, stage, description, request}
  expected.json  断言集
```

`expected.json` 的可用断言：

| 字段 | 断言 |
| --- | --- |
| `status` / `writes` | 终态与副作用次数 |
| `unknown[{path,reason}]` | 四元组的集合（按 path+reason 排序比较），`artifact_absent` 之外的"缺什么" |
| `unknown_quartets_complete` | 每个 unknown 条目的键集恰为四键 |
| `rejected_fields` | 被拒字段名集合 |
| `quarantined` / `candidates` | 被排除的参考、可用候选 |
| `questions_max` | 追问数量上限（`≤2` 是契约，不是建议） |
| `artifact_present` | 是否有产物（`writes=0` 时必须 `false`） |
| `artifact_expect{path: value}` | 产物关键字段的点路径取值 |
| `artifact_absent[]` | 某字段**必须不存在**——防"好心补默认值"把 unknown 变成空值 |
| `revision_is_sha256` | revision 是 64 位十六进制 |

`artifact_absent` 是本契约里最容易被忽略、也最重要的一条：它断言的不是"等于空"，而是"不存在"。
少了它，`goal_task: ""` 和"没写"在 JSON 层面无法区分。

---

## 6. 与其它节点的边界

- **1-6-3 / 1-6-4**：往 `ui_stages.py` 追加 S5..S10 的 runner，复用同一套原语；不得新起一套
  unknown/commit 实现。
- **1-6-5**：resolver 用同一批 fixture 串链；本节点**不**做端到端串联（决策见 roadmap 1-6-2），
  因此这里通过不代表链能跑通。
- **1-7+（adapter）**：只能提交带 `projection_id` / `source_revision` 的投影，不得改写 canonical
  字段，也不得扩 `COMPONENT_REGISTRY`。

---

## 7. 本节点的证据（可复算）

| 证据 | 复算命令 | 结果 |
| --- | --- | --- |
| 12 条 failure fixture | `python skills/ui/zj-ui-core/scripts/run_fixture.py tests/ui-agent-skills/fixtures/skills --recursive` | 12/12 matched，退出码 0 |
| 引擎不变量 13 项 | `python -m unittest tests.test_ui_agent_skills_stage_skills` | OK |
| 布局/manifest 守卫 | `python -m unittest tests.test_ui_agent_skills_layout` | OK |

`tests/test_ui_agent_skills_stage_skills.py` 额外守四类**fixture 抽不到**的语义：100 次幂等重放
只写一次、同键改内容被拒、contrast 失败不返回替换色板、无来源证据的值不进入产物。

---

## 8. 未验证项（诚实边界）

- **对话 → 结构化 request 的质量**：由 agent 负责，本节点不测，也无法用 fixture 测。
- **`UI-BRIEF.md` / `UI-DESIGN.md` 的文件级 patch/diff**：属 1-2-2 语义，本节点只做字段级校验，
  未实现文档 diff 解析。
- **端到端链**：归 1-6-5；本节点四条 stage 各自闭合，不代表 `brief → … → handoff` 能跑通。
- **contrast 只覆盖两对**：`on_surface/surface`、`on_primary/primary`。更多语义色对（link、
  disabled、focus ring）未纳入，1-6-4 的 verify 阶段需补。
