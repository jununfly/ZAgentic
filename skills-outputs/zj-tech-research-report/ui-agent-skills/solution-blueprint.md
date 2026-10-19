# ZAgentic 界面开发 Skills 方案蓝图

> 状态：Experience Version 方案，正式 technical-c4 报告见 `research/ui-agent-skills/2026-10-19-report.md`，配套证据账本已 sealed。
>
> 关键结论：采用“ZAgentic 自有 artifact/编排 + 外部 unit capability 的 B1 adapters”，不采用单一外部平台作为全生命周期底座。Superdesign/Figma MCP 暂不进入核心路径；正式报告、sealed-ledger 证据链和 capability-fit 决策记录均已发布。

## 1. 产品形态

这套能力应该表现为一个“有阶段感的界面开发助手”，而不是一个会把所有 UI 请求都接管的超级 skill。用户可以用三种方式提供输入：

1. 直接对话：“我要一个给仓库管理员使用的移动端审批页面。”
2. 编辑本地文档：修改 `UI-BRIEF.md`、`UI-DESIGN.md` 或 `ui-flow.json` 后让 Agent 继续。
3. 使用可选画布/设计工具：从 M3E Canvas、Figma 或其他工具导入结构化结果，仍回到本地 artifact。

Agent 的工作对象不是“某段 prompt”，而是一个可以 diff、选择、回滚、交接的项目包：

```text
.ui-work/
├── UI-BRIEF.md                 # 用户、目标、约束、非目标、成功标准
├── UI-DESIGN.md                # master design system + page overrides
├── ui-flow.json                # ui-flow/v1：页面、组件、状态、动作、转场
├── directions/                 # 2–3 个方向卡、比较截图、选择记录
├── prototypes/                 # 可丢弃的变体和 picker harness
├── reviews/                    # visual/motion/a11y/break reports
├── assets/manifest.json        # 来源、许可证、credit、替换点
└── handoff.md                  # 当前阶段、决策、证据、下一步
```

核心原则是：外部项目可以生成或渲染这些文件，但不能夺走它们的语义所有权。

## 2. Skill 组合与开发建议

状态说明：`新开发` 表示应由 ZAgentic 自己拥有；`选择性复用` 表示只吸收方法、模板或规则；`B1 adapter` 表示外部能力可替换，不维护 fork；`暂缓` 表示只保留 connector/研究入口。

| Skill | 状态 | 所属 bucket | 责任边界 | 主要参考/复用 | 关键输入 → 输出 |
| --- | --- | --- | --- | --- | --- |
| `zj-ui-orchestrator` | 新开发 | `engineering/` | 识别生命周期阶段、调用顺序、Human gate、冲突和停止条件；不做具体设计 | `zj-composer`、ZAgentic stage skills | 请求/项目状态 → stage plan + next action |
| `zj-ui-brief` | 新开发 | `engineering/` | 把模糊需求变成 user/job/baseline/goals/non-goals/constraints/acceptance | `frontend-design`、`zj-tech-research-report` brief | 对话或 `UI-BRIEF.md` → `ui-brief/v1` |
| `zj-ui-discover` | 新开发 | `engineering/` | 读取现有 UI、tokens、组件、路由、截图、数据和已有设计规则，建立基线 | Superdesign replica、Figma context | repo + URL → inventory + baseline replica |
| `zj-ui-direction` | 新开发 + 方法复用 | `engineering/` | 生成 2–3 个真正不同、可解释、可比较的视觉方向；等待用户选择 | `frontend-design`、Taste、Oil UI | brief + baseline → direction cards + comparison page |
| `zj-ui-design-system` | 新开发 + 数据适配 | `engineering/` | 维护 `UI-DESIGN.md`、tokens、page override、anti-pattern、content voice | UUPM 检索/规则、Superdesign design-system、Taste token sheet | direction choice → design system artifact |
| `zj-ui-flow` | 新开发 | `engineering/` | 拥有页面/组件/状态/动作/转场/空错加载态的本地契约 | A2UI/json-render 的结构启发 | brief + design system → `ui-flow/v1` + state matrix |
| `zj-ui-prototype` | 新开发 | `engineering/` | 在生产代码外构造 2–3 个交互变体、picker、用户选择和清理 | Emil `prototype`、Oil UI、M3E | flow + tokens → prototype harness + selected variant |
| `zj-ui-implement` | 新开发 | `engineering/` | 按项目技术栈把选定 flow 实现为真实代码，复用已有组件/令牌 | Figma implementation rules、ZAgentic `zj-implement` | selected flow + repo → production diff + notes |
| `zj-ui-assets` | 新开发 | `engineering/` | 管理图片/视频/图标/生成素材的来源、许可证、credit、fallback | Taste assets/credits | direction + asset needs → manifest + local references |
| `zj-ui-motion` | 新开发 + 规则复用 | `engineering/` | 判断是否需要动、目的、工具、属性、曲线、时长、打断和 reduced motion | Emil `animate`/`animation-vocabulary` | interaction intent → motion decision + implementation |
| `zj-ui-motion-review` | 新开发 + 规则复用 | `engineering/` | 只审查已有 motion 的感觉、性能、频率和无障碍 | Emil `review-animations`/`improve-animations` | diff/app → findings table + receipt |
| `zj-ui-visual-review` | 新开发 | `engineering/` | 多尺寸浏览器截图、布局/对比度/focus/overflow/reduced-motion 检查和最多三轮 critique | Taste `inspect`/screenshots、Storybook viewport/a11y | running app → screenshots + review report |
| `zj-ui-break` | 新开发 + 规则复用 | `engineering/` | 注入长文本、空/一条/大列表、多语言、缩放和错误状态；不直接改组件 | Emil `break-ui` | fixture/story → break report + dev-only toggle |
| `zj-ui-components` | 新开发 + B1 Storybook adapter | `engineering/` | 把组件、状态、stories、文档和设计 token 固化为可回归单元 | Storybook docs/a11y/actions/viewport | flow + components → stories + component matrix |
| `zj-ui-verify` | 新开发 | `engineering/` | 编排 unit/interaction/visual/a11y/responsive/break gates，生成 machine receipt | Storybook addons、browser runner | stories + app → verification receipt |
| `zj-ui-handoff` | 新开发 | `productivity/` | 压缩决策、证据、未知项、未完成项和下一步，支持跨会话继续 | `zj-handoff`、research receipt | all artifacts → `handoff.md` |
| `zj-ui-a2ui` | B1 adapter | `engineering/` | 将 `ui-flow/v1` 的声明式子集映射到 A2UI，并验证 catalog/event/data binding | A2UI | ui-flow → A2UI messages/PoC receipt |
| `zj-ui-json-render` | B1 adapter | `engineering/` | 将 component/action schema 映射到 json-render catalog/registry/spec | json-render | ui-flow → catalog/spec/React PoC |
| `zj-ui-m3e` | B1 adapter | `engineering/` | M3E Canvas screens/theme/flow 与 `ui-flow/v1` 往返转换 | M3E Canvas | canvas export → ui-flow + prompt/share |
| `zj-ui-figma` | 暂缓，外部 connector | `engineering/` | 读取 Figma context/variables/screenshot/Code Connect；不让远程服务成为核心 | Figma MCP guide | Figma node → imported context + provenance |

## 3. 统一 artifact contract

第一版不要尝试兼容 A2UI 和 json-render 的全部字段，而是定义小而深的本地契约：

```json
{
  "schema": "ui-flow/v1",
  "project": "approval-console",
  "source": [{"kind": "conversation", "ref": "UI-BRIEF.md#goal"}],
  "designSystem": {"ref": "UI-DESIGN.md", "version": "local"},
  "screens": [{
    "id": "request-detail",
    "purpose": "review and approve one request",
    "viewport": [390, 844],
    "states": ["loading", "ready", "empty", "error", "success"],
    "elements": [{
      "id": "approve",
      "component": "Button",
      "props": {"label": "Approve"},
      "actions": [{"event": "press", "intent": "approve-request"}]
    }]
  }],
  "acceptance": [{"id": "keyboard-focus", "threshold": "all interactive elements visibly focusable"}],
  "unknowns": []
}
```

字段纪律：

- `source` 记录它为什么存在，避免只有视觉没有意图。
- `component` 必须来自项目 catalog；未注册组件进入 `unknown`，不能直接执行。
- `actions` 记录 intent，不直接嵌入任意代码；执行层另有 approval/sandbox 边界。
- `states` 默认要求 loading/empty/error/success 中至少适配实际业务需要的集合。
- `acceptance` 与 `reviews` 分开：一个是预期，一个是结果。
- 所有 adapter 必须是可逆转换；丢失字段必须产生 warning，而不是静默吞掉。

## 4. 端到端 Experience Version

选一个真实但小的 React/Next.js 项目和一个“表单/审批流”垂直切片：

1. 用户写一句话或编辑 `UI-BRIEF.md`。
2. `zj-ui-brief` 补齐用户、任务、信息、约束、非目标和验收；只在关键缺失时提问。
3. `zj-ui-discover` 读取现有组件/token/路由并生成 baseline。
4. `zj-ui-direction` 生成三个差异明确的方向，用户通过比较页选择一个。
5. `zj-ui-design-system` 落盘 token、排版、颜色、状态语气和 page override。
6. `zj-ui-flow` 生成两屏、五种状态、两个动作的 flow。
7. `zj-ui-prototype` 构建生产代码外的变体并等待用户确认。
8. `zj-ui-implement` 只实现选定变体，生成一个组件 story。
9. `zj-ui-visual-review` 在 390/768/1440 宽度截图，跑对比度、focus、overflow、reduced motion。
10. `zj-ui-motion`/`zj-ui-motion-review` 只处理确有目的的 motion。
11. `zj-ui-break` 切换 worst-case fixture，检查长名、错误、空态、长按钮、1000 条数据。
12. `zj-ui-components`/`zj-ui-verify` 生成 stories、验证 receipt 和 `handoff.md`。

## 5. 开发顺序

### Wave 0：契约和测试夹具（优先级 P0）

- `ui-brief/v1`、`ui-flow/v1`、`ui-review/v1`、`ui-verification-receipt/v1` schema。
- skill capability manifest：触发条件、输入、输出、禁止事项、依赖、artifact owner。
- 一个固定 demo project 和不变的验收 fixture。
- `UI-BRIEF.md`、`UI-DESIGN.md`、`ui-flow.json`、`handoff.md` 模板。

退出条件：第三方 Agent 只读模板和 manifest 能判断下一步、读取产物和拒绝越界动作。

### Wave 1：核心设计闭环（P0）

实现 `zj-ui-brief`、`zj-ui-discover`、`zj-ui-direction`、`zj-ui-design-system`、`zj-ui-prototype`。

退出条件：同一个 brief 能得到三个不收敛的方向；用户选择可记录；删除 prototype 不影响生产代码；设计系统可被第二次会话加载。

### Wave 2：实现和质量闭环（P0）

实现 `zj-ui-flow`、`zj-ui-implement`、`zj-ui-visual-review`、`zj-ui-motion`、`zj-ui-break`、`zj-ui-components`、`zj-ui-verify`、`zj-ui-assets`。

退出条件：一个页面在 390/768/1440、键盘、reduced motion、长文本/空态/错误态下有可复核 receipt；失败时能指出是哪个 claim/threshold 没过。

### Wave 3：外部适配器（P1）

依次验证 `zj-ui-json-render`、`zj-ui-a2ui`、`zj-ui-m3e`、`zj-ui-storybook`；Figma connector 只在有真实 Figma 项目、seat 和额度时进入 PoC。

每个 adapter 必须提供：版本锁、输入输出映射、丢失字段 warning、外部依赖失败 fallback、删除 adapter 后的回退路径、最小 golden fixture。

### Wave 4：编排和推广（P1/P2）

实现 `zj-ui-orchestrator`、`zj-ui-handoff`，补 CLI/对话入口、README 注册、递归发现、skill validation、跨会话 resume、可选安装清单。

## 6. 质量指标与 graduation criteria

Experience Version 的门槛（不是“代码合并即完成”）：

| 指标 | 阈值 | 测量 |
| --- | --- | --- |
| 方向差异度 | 三个方向中至少两个在布局/字体/色彩/关键素材中有两个独立差异轴 | direction card + screenshot review |
| 用户可选性 | 用户能在 10 分钟内指出喜欢/不喜欢的方向和理由 | 选择记录 + brief follow-up |
| artifact 可恢复性 | 新会话只读本地 artifacts 后能继续 90% 以上的设计决策 | resume fixture |
| 实现闭环 | 选定方向能生成可运行页面和至少 1 个 story | demo project command |
| 视觉底线 | 390/768/1440 无 blocker；键盘 focus、contrast、reduced-motion 有证据 | visual/a11y receipt |
| 数据韧性 | worst-case fixture 至少覆盖长文本、空、错、1 条、1000 条、多语言 | `zj-ui-break` report |
| 外部可移除 | 删除每个 adapter 后核心 artifact 和本地流程仍可读/可编辑 | adapter removal test |

Promote to `usefulness-validation` only if the same slice beats the current direct-prompt baseline in rework rate, user decision time and escaped UI defects across at least three runs. `dogfood`/`release` 的 rollout、rollback、version skew 不属于本轮；进入这些阶段时再补版本策略。

## 7. 安全、版权与责任边界

- 模型不能直接执行未注册 component/action；动态 UI 只生成 catalog 内的数据。
- 外部 MCP/CLI 的凭据、网络、写回 Figma 和代码执行必须显式审批，并记录来源。
- 所有下载/生成素材写入 manifest，含 source URL、作者、license、credit 和替换点；未知许可证不进入默认产物。
- 浏览器检查服务只访问本地项目和明确允许的 URL；截图可能含敏感数据，默认不上传。
- adapter 不能写入核心 artifact 的不可逆字段；不能通过复制外部服务生成的代码绕过本仓库 review/verify gate。
- 退出外部项目时，保留本地 Markdown/JSON、截图和结果摘要；不把远程 ID 作为继续工作的唯一索引。

## 8. 仓库落位与验收清单

实现时每个 public skill 都必须：

- 放到正确的 `skills/` bucket，有 `SKILL.md`、必要的 `agents/openai.yaml`、references/templates 与测试。
- 在 bucket README 和根 README 各有 name-linked one-line entry，并通过递归 discovery。
- 新领域术语先加入 `ZJ-CONTEXT.md`，再进入 merge 流程。
- 复用 `zj-writing-for-agents` 的 progressive disclosure 和 `zj-write-a-skill` 的结构约束。
- 采用 skill-pair 工作流时，按仓库规则依次执行 `zj-steelman`、`zj-dry-run`、`zj-debrief`；提交前使用 `./scripts/zj-git`。
- 每个 skill 至少有一个“可以失败”的 fixture：缺输入、外部服务不可用、schema 不兼容、截图不稳定、敏感数据、用户未选择时都必须停在明确边界。

