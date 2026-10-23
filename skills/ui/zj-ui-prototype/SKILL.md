---
name: zj-ui-prototype
description: >-
  S6 BUILD：从 ui-flow/v1 生成可交互的本地 preview 或实现切片，只用 catalog 内组件；
  任何代码执行、网络、凭据、远程写回都先出 effect intent，经 policy / approval / sandbox 才执行。
  Use when flow 已成型，需要把人能看见、能点的 preview 做出来，而不是直接改生产代码。
  确定性实现见 `skills/ui/zj-ui-core/scripts/ui_stages.py` 的 `run_prototype`。
argument-hint: "<ui-flow/v1 路径与 preview 输出目录>"
metadata:
  status: implemented
source: zagentic
---

# zj-ui-prototype

S6 · BUILD · `emit`（只产出显式声明的非 canonical 产物 `preview`）

> capability manifest、输入输出、禁止事项、停止条件与失败 fixture id
> 已冻结；可执行实现落在 `skills/ui/zj-ui-core/scripts/ui_stages.py` 的 `run_prototype`（复用
> `ui_skill_core.py` 的 deny-first / unknown 四元组 / 幂等 commit 原语），由
> `tests/ui-agent-skills/fixtures/skills/FF-PROTO-*` 验收。

## Capability Manifest

```json
{
  "skill_id": "zj-ui-prototype",
  "manifest_version": "0.1.0",
  "stage": "S6",
  "owner_scope": "emit",
  "writes": ["preview"],
  "reads": ["ui-flow/v1", "UI-DESIGN.md"],
  "input": [
    {"name": "ui-flow/v1", "type": "revision", "required": "yes", "source": "S5"},
    {"name": "component catalog", "type": "revision", "required": "yes", "source": "S4"},
    {"name": "effect intent", "type": "object", "required": "conditional", "source": "policy-gate"}
  ],
  "output": [
    {"name": "preview / implementation slice", "type": "artifact", "artifact_kind": "preview", "atomic": false},
    {"name": "effect intent request", "type": "object", "artifact_kind": "non-canonical", "atomic": false}
  ],
  "forbidden": [
    "直接使用 catalog 外的组件",
    "绕过 policy / approval / sandbox 执行 effect",
    "把 json-render 投影变成 SSOT",
    "写入任何 canonical artifact"
  ],
  "dependencies": [
    "S5 revision",
    "policy → approval → sandbox lease → executor 单入口"
  ],
  "required_capabilities": ["local-preview-runtime", "effect-intent-generator"],
  "stop_conditions": [
    {"condition": "未注册组件或危险 action", "action": "STOP", "next": "deny，不生成实现"},
    {"condition": "远程 adapter 不可用", "action": "STOP", "next": "退回本地静态 preview，不得伪造成功"},
    {"condition": "effect 未获批", "action": "WAIT_HUMAN", "next": "零副作用"}
  ],
  "owner": "prototype owner",
  "precedence": 60,
  "failure_fixtures": ["FF-PROTO-01", "FF-PROTO-02", "FF-PROTO-03"],
  "human_gate": "required"
}
```

## 职责与边界

`owner_scope=emit`：本 skill **不拥有任何 canonical artifact 的写锁**。`writes` 里声明的
`preview` 是规范允许显式声明的非 canonical 产物，不是 schema 中的第六类 artifact。
实现切片与 preview 都从这里出去；`UI-BRIEF.md` / `UI-DESIGN.md` / `ui-flow/v1` 一律只读。

- **effect 不等于做事**：先出 `effect intent`（目标、参数摘要、权限、可撤销性、数据分类），
  再走 approval，未获批就停。
- **catalog 是边界**：catalog 外组件一律 deny，不用"临时补一个"绕过。
- **不冒充 SSOT**：json-render 只是可移除投影，删掉它项目仍要能维护。

## 停止条件与 Human gate

- 未注册组件 / 危险 action → `deny`，不生成实现。
- 远程不可用 → 本地静态 preview fallback，**不得伪造成功**。
- effect 未获批 → `WAIT_HUMAN`，零副作用。
- `human_gate=required`：任何不可逆或外部写入都要人签。

## 失败 fixture

- `FF-PROTO-01` 正常：本地 preview 可交互，只用 catalog 内组件。
- `FF-PROTO-02` 冲突：未注册组件 → deny，不生成实现。
- `FF-PROTO-03` 失败：远程 adapter 不可用 → 本地 fallback，且不声称远程成功。

## 交接

- 上游：S5 的 `ui-flow/v1`、S4 的 catalog。
- 下游：S7 `zj-ui-visual-review` 对 preview 做 inspect 与截图；回退目标是 S5 revision。
- adapter 侧失败 → 退回本地 preview，不换 owner。
