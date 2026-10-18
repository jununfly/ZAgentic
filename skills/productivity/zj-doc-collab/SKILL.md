---
name: zj-doc-collab
description: Base skill providing the generic substrate for document-backed multi-agent collaboration — a shared document set as SSOT plus per-agent scoped private memory, with a parameterized structural non-degradation gate. Reference this when building a zj-* skill where multiple Agents/SubAgents must collaborate over a shared document set (align goals/progress, share context, each keeping scoped memory). Not user-query triggered on its own; consumed by other skills.
source: zagentic

---

# zj-doc-collab

A **base skill** providing the generic substrate for *document-backed multi-agent
collaboration*: multiple Agents / SubAgents cooperate on **a shared set of
documents** — aligning on goals/progress, sharing context, each maintaining its
own **scoped private memory** layered on the shared context.

This is the reusable primitive behind `zj-discuss` (and any future skill that
needs structured multi-perspective collaboration). `zj-discuss` is one
*specialization* — its "contribution shape" is a structurally-misaligned viewpoint
on a sub-problem plus a conclusion state protocol; any future carrier-plugin
consumer (e.g. a skill whose carrier is a message channel instead of markdown
files) is another.

> 本文件只定义**通用协作契约**，不含任何消费者（如 zj-discuss）的特有词汇（角色池、
> 结论状态枚举、沉淀指令等）。消费者语义一律在各自 skill 内定义。

## Mental model

```
shared document set (SSOT: goal + progress + context)
  └─ multiple Agents / SubAgents, each:
        read shared context + its own scoped private memory
        → contribute (a viewpoint / a decision / a delta)
  └─ coordination primitives: goal-align / progress-track / context-share
  └─ structural gate enforces non-degradation (isolation integrity)
```

## What this base skill owns (generic)

- **Lifecycle contract (P0–P4)**: scope gate → decompose → prepare roles →
  independent discussion → synthesize → dispose. The *shape* is generic; the
  *carrier* (markdown files / message channel / …) is a consumer plugin point.
- **6 generalized hard rules** (see `references/base-contract.md`): read original;
  structurally different roles; anti-echo-chamber + load-bearing warning;
  convergence; executable conclusion; non-degradation ladder.
- **Role-selection mechanism**: recommend base set + optional by trigger signal →
  Human confirms/locks → declared required set. The *mechanism* is generic; the
  *role pool* lives in the consumer's role-matrix.
- **Generic gate framework** (`scripts/gate_core.py`): source-marker validation,
  preview-label requirement, non-degradation check, evidence/placeholder
  detection — all **parameterized** by the consumer's vocabulary.
- **Generic launch-pack engine** (`scripts/launch_pack_core.py`): parse declared
  role set → render one pack per role from a parameterized template (per-role
  executor command, role-method path, gate script name).
- **scoped-memory model**: shared context (documents) = SSOT; per-agent private
  overlay layered on top.
- **Sibling-boundary pattern**: thin orchestration, reference not reimplement,
  selective external reuse (C), veto runtimes/routers (see base-contract.md).

## What consumers own (specific — plugin points)

| Plugin point | 消费者提供 | 例（zj-discuss） |
| --- | --- | --- |
| **Carrier** | 共享文档的载体与布局 | `discussions/<slug>/` markdown 文件 |
| **Role pool** | 角色语义 SSOT + 每角色 gated method | 13 份 role-methods |
| **Domain gate invariants** | 通用闸门之外的领域不变量 | 结论状态协议 + 沉淀指令 + 每角色 N 闸门 |
| **Per-role executor command** | 每角色视角的执行命令模板 | `zj-discuss-view --role X <path>` |
| **Conclusion semantics** | 收敛结论的状态枚举 | `DONE`/`DONE_WITH_CONCERNS`/`BLOCKED`/`NEEDS_CONTEXT` |

## How a consumer uses this base

1. 在自身 SKILL.md `reference` zj-doc-collab（薄编排，不重复实现通用件）。
2. 提供角色池（role-matrix）+ 载体布局。
3. 接线闸门：调用 `gate_core` 并传入自身词汇；追加领域不变量。
4. 接线启动包：调用 `launch_pack_core` 并传入每角色执行命令模板。
5. 特有行为自带测试；本基础自带通用测试。

### 最小接线示例

消费者脚本把基础 skill 的 `scripts/` 加入 `sys.path`，再 import 通用件、传入自身词汇：

```python
import sys
from pathlib import Path

# 与消费者同父的基础 skill（skills/productivity/ 或安装位平铺布局）
_BASE = Path(__file__).resolve().parents[2] / "zj-doc-collab" / "scripts"
if str(_BASE) not in sys.path:
    sys.path.insert(0, str(_BASE))

from gate_core import (
    check_viewpoint_marker,
    check_non_degradation,
    split_sections,
)

# 消费者自有词汇（基础只给默认值，不绑定任何消费者）
ALLOWED_MARKERS = {"跨会话独立Agent", "同会话SubAgent(低权重)"}
PREVIEW_LABEL = "⚠ 非独立"
CLAIMED_STATUS = {"DONE", "DONE_WITH_CONCERNS"}

def gate_viewpoint(body, role):
    # 委托通用件做标注校验，消费者只叠加领域层（状态枚举/沉淀/per-role N 闸门）
    errs = check_viewpoint_marker(
        body, role,
        allowed_markers=ALLOWED_MARKERS,
        preview_marker="同会话SubAgent(低权重)",
        preview_label=PREVIEW_LABEL,
    )
    if not errs:
        errs += check_non_degradation(
            body,
            has_cross_session_anchor=("跨会话独立Agent" in body),
            cross_session_marker="跨会话独立Agent",
            claimed_statuses=CLAIMED_STATUS,
        )
    return errs
```

启动包生成同理——消费者调用 `launch_pack_core.generate`，传入每角色执行命令模板（基础从不硬编码消费者命令）：

```sh
python3 <consumer-skill>/scripts/<consumer-launch>.py <sub-doc> \
    --matrix <consumer-skill>/references/role-matrix.md \
    --out <讨论文件夹>/briefings
# 消费者脚本内部：
#   generate(subdoc, roles, out, matrix,
#            executor_cmd_template="zj-discuss-view --role {key} {subdoc}")
```

## Scripts

- `scripts/markdown_sections.py` — fence-aware Markdown 分节器（通用）。
- `scripts/gate_core.py` — 参数化结构性闸门原语。
- `scripts/launch_pack_core.py` — 参数化启动包引擎。

## Tests

- `tests/` — 通用件独立测试，证明机制在隔离下正确（消费者词汇作默认值验证等价性）。

## References

- `references/base-contract.md` — 6 条泛化硬规则 + 生命周期 + 兄弟边界模式（通用，无消费者词汇）。

## 兄弟边界（通用，沉淀自 zj-discuss，上移至基础）

> 边界原则：**引用而非重做。** 消费者做薄编排层，凡兄弟技能/基础已覆盖的能力一律调用，
> 不在消费者内重实现（防逻辑漂移）。

- 防御式辩护（如 `zj-steelman`）与协作式结构错位视角**不变式互斥**：视角角色不得内置
  defend 逻辑；对「提案是否站得住」类子问题，改调辩护技能。
- 压缩契约（如 `zj-handoff`）⊇ 启动包契约：引用不重复，仅追加消费者专属两行头。
- 治理/分类（如 `zj-docs-ontology`）由 Human 确认闭环完成；消费者阶段只吐指针，绝不自行分类/迁移。
- **否决项（不再复议）**：会话编排运行时 / router / suite 化 —— 会让适配层拥有主体方法
  状态。启动包生成器是这条红线的产物边界：它只写文件，不发起会话。
