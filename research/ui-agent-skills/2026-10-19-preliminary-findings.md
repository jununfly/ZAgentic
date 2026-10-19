# 界面开发 Agent skills 生态调研（预备证据版）

> 研究时间：2026-10-19（Asia/Shanghai）
>
> 证据状态：本轮 `zj-research` GitHub collection 被未认证 API 配额阻断，尚未生成 sealed ledger。因此本文只记录已经按固定 commit 阅读的一手仓库文件，不能作为已通过 `zj-tech-research-report` 发布闸门的正式报告，也不把 GitHub Stars 当作能力评分。待 collection 恢复后，应将本文中的 source URL 映射到 sealed Evidence ID，并重建正式 Report IR。

## 决策问题与假设

目标不是选择一个“最强 UI 生成器”，而是在 ZAgentic 中设计一套可组合技能，让程序员能够从模糊想法出发，完成：

```text
想法/需求 → 设计方向 → 设计系统 → 页面/流程原型 → 交互与状态 → 代码实现
→ 浏览器/截图反馈 → 无障碍/响应式/极端数据 → 组件文档与回归 → 交付维护
```

当前阶段按 `experience-version` 处理：先做一条可丢弃的端到端垂直切片，验证 Agent 能否把一份自然语言 brief 变成一个可选择、可审阅、可实现、可回归的界面交付物。暂不把跨团队发布、企业权限、完整 Figma 替代品或通用低代码平台纳入第一阶段。

## 固定版本来源

以下 commit 由公开 Git 引用解析得到，并作为本轮语义阅读的固定版本；正式报告仍需以 `zj-research` sealed ledger 的 revision 与 Evidence ID 为准。

| 候选 | 固定 commit | 角色假设 |
| --- | --- | --- |
| [a2ui-project/a2ui](https://github.com/a2ui-project/a2ui/tree/cbaa5ee62c737b50d0695c1e5794d0f648b61dca) | `cbaa5ee62c737b50d0695c1e5794d0f648b61dca` | Agent-to-UI 声明式协议、catalog、renderer、composer |
| [anthropics/claude-code](https://github.com/anthropics/claude-code/tree/ef7bfdca55d906929fe6b782025b93758c325074) | `ef7bfdca55d906929fe6b782025b93758c325074` | `frontend-design` 官方插件/skill 容器 |
| [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill/tree/b9ca2fd8047f4c72d7da90ebc1c1203e57c72cd2) | `b9ca2fd8047f4c72d7da90ebc1c1203e57c72cd2` | 视觉方向、真实图片、浏览器检查、截图自评 |
| [vercel-labs/json-render](https://github.com/vercel-labs/json-render/tree/72568f990e5502c4d3115691facb8ca928a5c9fc) | `72568f990e5502c4d3115691facb8ca928a5c9fc` | 受 catalog 约束的 Generative UI、spec、renderer、MCP |
| [lnkiai/m3e-canvas](https://github.com/lnkiai/m3e-canvas/tree/627e42321bcf080979da87f40a17dcd432425a95) | `627e42321bcf080979da87f40a17dcd432425a95` | 可点击画布/流程/主题到 Agent prompt |
| [emilkowalski/skills](https://github.com/emilkowalski/skills/tree/2d228630ba1446365f614a108cb8252f1feda202) | `2d228630ba1446365f614a108cb8252f1feda202` | 动效构建、动效审查、原型分支、极端数据 |
| [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/tree/56ea9cf174ed86786187daa9de0e6247cb0747e4) | `56ea9cf174ed86786187daa9de0e6247cb0747e4` | 规则/数据驱动的设计系统和栈适配 |
| [oil-oil/oil-ui](https://github.com/oil-oil/oil-ui/tree/feb1f95e8cec48bb8ba35181cb66f94f23b1b6fc) | `feb1f95e8cec48bb8ba35181cb66f94f23b1b6fc` | 多方向并排比较、选择、截图复审 |
| [superdesigndev/superdesign-skill](https://github.com/superdesigndev/superdesign-skill/tree/f9f05cd988c247dce6c072eaf9ac6b162f2ffc4b) | `f9f05cd988c247dce6c072eaf9ac6b162f2ffc4b` | 外部设计 Agent / canvas / design system CLI |
| [storybookjs/storybook](https://github.com/storybookjs/storybook/tree/064c650498ad8411c74984ee3188a64be8bd0f20) | `064c650498ad8411c74984ee3188a64be8bd0f20` | 组件孤立开发、文档、a11y/viewport/interaction 测试 |
| [figma/mcp-server-guide](https://github.com/figma/mcp-server-guide/tree/f2789420e7e8b4e2465dfeb1e12e1fc6a31397e5) | `f2789420e7e8b4e2465dfeb1e12e1fc6a31397e5` | Figma MCP/Plugin 的连接和交付流程参考，非本地 OSS runtime |

## 关键发现

### 1. 视觉设计能力不是一个 prompt，而是“方向选择 + 约束 + 复审”闭环

`frontend-design` 明确要求先根据主题提出视觉方向，形成颜色、字体、布局和原则的 compact token system，再检查是否落入通用 AI 默认审美，最后实现；它还把响应式、键盘 focus、可访问对比度和 reduced motion 设为质量底线。来源：[SKILL.md](https://raw.githubusercontent.com/anthropics/claude-code/ef7bfdca55d906929fe6b782025b93758c325074/plugins/frontend-design/skills/frontend-design/SKILL.md)。

Taste Skill 把这一步进一步程序化：从 20 个研究方向中抽取多个候选，要求先建立“只有这个产品拥有的素材清单”，再选择一个方向；实现后用真实浏览器在三个宽度检查，并基于截图最多三轮修复。它还把图片来源、许可证、credit 和“不要伪造证明素材”纳入流程。来源：[README](https://raw.githubusercontent.com/Leonxlnx/taste-skill/b9ca2fd8047f4c72d7da90ebc1c1203e57c72cd2/README.md)、[design-taste-frontend/SKILL.md](https://raw.githubusercontent.com/Leonxlnx/taste-skill/b9ca2fd8047f4c72d7da90ebc1c1203e57c72cd2/skills/taste-skill/SKILL.md)。

Oil UI 的独特增量是“并排比较页”：多种方向在同一页面切换桌面/移动尺寸，用户选择后把选择语句交给 Agent 继续迭代。它把“premium/clean”拆为可观察的字体、留白、色彩面积、构图与一个记忆点，而不是让 Agent 自由发挥。来源：[README](https://raw.githubusercontent.com/oil-oil/oil-ui/feb1f95e8cec48bb8ba35181cb66f94f23b1b6fc/README.md)。

**拟合结论：** 这三者适合抽取方法和检查点，不适合整仓库合并。应新开发 `zj-ui-direction`，保留“多方向、可选择、可复审、可记录”的产品形态；素材搜索、浏览器 inspector、第三方服务和研究数据库作为可拔插适配器。

### 2. UI 风格/设计系统需要“检索数据 + 解释规则 + 可落盘覆盖”，不能只靠模型记忆

UI UX Pro Max 将产品类型、风格、颜色、字体、图表、UX 指南和技术栈分成可搜索数据集，并用 BM25、行业规则、anti-pattern 和 checklist 生成可落盘的 design system；其 README 还明确支持 master + page override 的持久化模式。来源：[README](https://raw.githubusercontent.com/nextlevelbuilder/ui-ux-pro-max-skill/56ea9cf174ed86786187daa9de0e6247cb0747e4/README.md)。

Superdesign 则把 design system 放在项目 `.superdesign/design-system.md`，在重设计已有页面时先制作“当前状态 replica”，再在外部 canvas 中分支 draft；它要求把用户选择、分支、设计上下文和后续迭代连起来。来源：[README](https://raw.githubusercontent.com/superdesigndev/superdesign-skill/f9f05cd988c247dce6c072eaf9ac6b162f2ffc4b/README.md)。

**拟合结论：** 本仓库应拥有自己的 `UI-DESIGN.md`/`ui-design-system.md` 规范和 master/page override 结构。可以选择性复用 UUPM 的数据组织与检索模式，不能把其数据目录当成 ZAgentic 的架构真源；外部设计 Agent 输出必须被转译成可审阅的本地 artifact。

### 3. 生成式 UI 的关键不是生成代码，而是受信 catalog 和稳定 spec

A2UI 将 Agent 输出定义为声明式 JSON，客户端通过受信 component catalog 映射到原生组件；它强调安全边界、跨框架、增量更新、数据绑定和事件系统。仓库同时提供协议核心、Agent SDK、多个 renderer，并提供 Composer 让人通过可视编辑器生成 JSON。它当前仍处于 public preview，README 标注 v0.9 协议族、v1.0 release candidate、实现仍会变化。来源：[README](https://raw.githubusercontent.com/a2ui-project/a2ui/cbaa5ee62c737b50d0695c1e5794d0f648b61dca/README.md)。

json-render 把同一思想进一步工程化：用 `defineCatalog` 定义组件 props schema、动作和描述，再用 `defineRegistry` 绑定真实组件；相同 spec 可流式渲染到 React/Vue/Svelte/Solid/React Native 等目标，并提供 state adapter、devtools、codegen、YAML 和 MCP 包。来源：[README](https://raw.githubusercontent.com/vercel-labs/json-render/72568f990e5502c4d3115691facb8ca928a5c9fc/README.md)。

**拟合结论：** 本仓库不应把 A2UI 或 json-render 当作全套 skills 的底座。应先新开发一个最小、框架无关的 `ui-spec`/`ui-flow` 文档契约：组件、布局、状态、动作、tokens、验收和来源。然后以 B1 adapter 方式分别接 A2UI 或 json-render 做 PoC，比较真实项目中的语义匹配和退出成本。两者都不能替代视觉方向与工程验证。

### 4. 画布是“把不会写 UI 的人变成能提供结构化约束的人”的入口

M3E Canvas 在浏览器中拖拽 Material 3 Expressive parts、连接 screens、预览点击/滑动流程、编辑主题，最后输出可复制给 Claude Code、Codex 或其他 coding tool 的 prompt；设计可保存、分享、导出 PNG，AI helper 只在用户提供 key 时从浏览器直连服务商。来源：[README](https://raw.githubusercontent.com/lnkiai/m3e-canvas/627e42321bcf080979da87f40a17dcd432425a95/README.md)。

Figma MCP Guide 展示了更强的“设计资产作为上下文”路径：从选中 frame 读取 design context、变量和截图，通过 Code Connect 对齐真实组件，也支持写回 canvas 和从网页生成 Figma 设计；但它依赖远程 Figma MCP、Beta/座席/调用额度和 Figma Developer Terms，不能视为本仓库可拥有的本地 capability。来源：[README](https://raw.githubusercontent.com/figma/mcp-server-guide/f2789420e7e8b4e2465dfeb1e12e1fc6a31397e5/README.md)。

**拟合结论：** 推荐新开发 `zj-ui-prototype`，把“可视画布”和“Markdown/JSON 文档编辑”统一到同一个本地 UI Flow artifact；M3E Canvas 作为 `zj-ui-prototype-m3e` 可选导入/导出适配器，Figma 作为 `zj-ui-figma` 外部 connector。真正的本地 SSOT 必须能在没有远程服务时读写、diff、回滚和继续对话。

### 5. 交互质量需要拆成构建、审查、压力测试三个不同 skill

Emil Kowalski 的 skill collection 明确把 `animate`（从是否应该动开始构建）、`review-animations`（严格审查现有动效）、`improve-animations`（全库审计）、`find-animation-opportunities`（找真正值得动的地方）、`animation-performance`（掉帧排查）、`animation-vocabulary`（把模糊要求变成专业描述）、`prototype`（隔离的多版本选择器）和 `break-ui`（极端数据破坏测试）拆开。来源：[README](https://raw.githubusercontent.com/emilkowalski/skills/2d228630ba1446365f614a108cb8252f1feda202/README.md)、[animate/SKILL.md](https://raw.githubusercontent.com/emilkowalski/skills/2d228630ba1446365f614a108cb8252f1feda202/skills/animate/SKILL.md)、[review-animations/SKILL.md](https://raw.githubusercontent.com/emilkowalski/skills/2d228630ba1446365f614a108cb8252f1feda202/skills/review-animations/SKILL.md)、[prototype/SKILL.md](https://raw.githubusercontent.com/emilkowalski/skills/2d228630ba1446365f614a108cb8252f1feda202/skills/prototype/SKILL.md)、[break-ui/SKILL.md](https://raw.githubusercontent.com/emilkowalski/skills/2d228630ba1446365f614a108cb8252f1feda202/skills/break-ui/SKILL.md)。

**拟合结论：** 不要把“审美检查”写成一个巨型 skill。至少拆成 `zj-ui-motion`、`zj-ui-visual-review`、`zj-ui-break`、`zj-ui-prototype` 四个边界；每个只拥有一种失败模式和一种可验证输出。

### 6. Storybook 更适合作为工程验证 seam，而不是视觉设计入口

Storybook 自身把 UI 组件隔离开发、文档和测试作为核心定位，并通过 addons 覆盖 a11y、actions、docs、measure、outline、viewport、design assets 等。它的能力非常适合承接 UI skills 产生的组件契约和回归样例，但不会替用户选择视觉方向，也不会代替 Agent 的需求澄清。来源：[README](https://raw.githubusercontent.com/storybookjs/storybook/064c650498ad8411c74984ee3188a64be8bd0f20/README.md)。

**拟合结论：** 新开发 `zj-ui-components`/`zj-ui-verify`，以 Storybook 为可选 B1 adapter；本仓库的 skill 只生成 stories、状态矩阵、a11y/viewport/interaction 验收，不把 Storybook runtime 复制进仓库。

## 原子化 item 与 skill 化评估

状态含义：

- `复用方法`：只吸收工作流原则、模板和检查项，由 ZAgentic 自己实现。
- `B1 adapter`：外部能力可被薄适配层包裹，主体责任仍由 ZAgentic 持有，不维护 fork。
- `新开发`：该能力属于本仓库的产品语义或 SSOT，不应交给外部项目。
- `外部参考`：对需求有启发，但不构成可执行 capability。
- `暂缓/D`：当前证据显示不适合承担该职责，保留在候选扫描表。

| ID | 原子 item | 来源能力 | skill 化评估 | 建议动作 |
| --- | --- | --- | --- | --- |
| D01 | 产品/用户/任务 brief 提炼 | frontend-design、taste、oil-ui | 高；是所有后续设计决策的输入 | 新开发 `zj-ui-brief` |
| D02 | 设计方向多选与差异性闸门 | taste、oil-ui、prototype | 高；用户需要可比较的选择，不应被一次生成绑死 | 新开发 `zj-ui-direction` |
| D03 | subject-specific idea / competitor test | taste、oil-ui | 高；补足程序员不擅长的“为什么这样设计” | 复用方法，落入 `zj-ui-direction` |
| D04 | palette/type/layout/principles token sheet | frontend-design、UUPM | 高；应形成可落盘 artifact | 新开发 `zj-ui-design-system` |
| D05 | 行业/产品类型→style/palette/type 检索 | UUPM | 中高；数据可复用，数据所有权/版本需独立 | B1 data adapter 或自建精简数据 |
| D06 | 设计系统 master + page override | UUPM、superdesign | 高；解决跨会话和页面局部变化 | 新开发本地文档契约 |
| D07 | 现有 UI 反向提取 tokens/组件/流 | superdesign、Figma MCP | 高；是改造已有项目的前置 | 新开发 `zj-ui-discover`，Figma 可选 connector |
| D08 | replica HTML / baseline capture | superdesign | 高；给外部设计工具提供稳定上下文 | 新开发并限制在 `.ui-work/replicas/` |
| D09 | A2UI declarative component catalog | A2UI | 中高；协议清晰但版本早期且不是视觉设计系统 | B1 adapter，PoC 后决定 |
| D10 | A2UI renderer/catalog validation/data binding | A2UI | 中高；适合动态界面和安全边界 | B1 adapter，ZAgentic 持有 ui-spec |
| D11 | A2UI Composer visual JSON authoring | A2UI | 中；可作为外部原型，不宜成为本地 SSOT | 外部参考/导入适配 |
| D12 | json-render catalog + Zod props | json-render | 高；对 Agent 生成的组件边界非常实用 | B1 adapter，优先 React PoC |
| D13 | json-render spec streaming/state/actions | json-render | 高；可支撑可更新的界面 | B1 adapter；只接入需要此 runtime 的项目 |
| D14 | json-render cross-framework renderer | json-render | 中；降低前期锁定，但扩大版本面 | 暂缓，先选一个 host framework |
| D15 | json-render MCP/devtools/codegen/YAML | json-render | 中；属于 runtime/tool 扩展，不是默认 skill | 作为可选插件，非核心 |
| D16 | 画布拖拽 parts、screens、links | M3E Canvas | 高；对非专家输入特别有价值 | 新开发本地 `zj-ui-prototype`，M3E 导入导出 |
| D17 | theme/palette/type/motion 一处编辑 | M3E Canvas | 高；形成可编辑的设计系统字段 | 新开发 artifact schema；可适配 M3E |
| D18 | canvas→prompt / share link | M3E Canvas、superdesign | 高；降低从设计到 Agent 的沟通成本 | 新开发 Markdown/JSON 编译器 |
| D19 | Figma get_design_context/screenshot/variables | Figma MCP | 高但外部依赖强 | `zj-ui-figma` connector，不入核心 |
| D20 | Figma write-to-canvas/Code Connect | Figma MCP | 中高；适合已有设计团队，不适合第一阶段 | 暂缓，设计外部接口 |
| D21 | art direction + real imagery + credits | taste | 高；能显著减少 AI slop 和版权风险 | 新开发 `zj-ui-assets` + direction rules |
| D22 | browser inspector at desktop/tablet/mobile | taste | 高；机器可验证的视觉底线 | 新开发 `zj-ui-visual-review`，可借鉴规则 |
| D23 | screenshot critique and bounded fix loop | taste、oil-ui | 高；把“看起来不好”转成有限修复轮次 | 新开发 `zj-ui-visual-review` |
| D24 | motion decision/build | emil `animate` | 高；应先判断“是否需要动” | 新开发 `zj-ui-motion` |
| D25 | motion review/performance/opportunity | emil collection | 高；与构建隔离，避免自审失效 | 新开发 `zj-ui-motion-review` 或作为 `visual-review` 子流程 |
| D26 | isolated multi-variant prototype picker | emil `prototype`、oil-ui | 高；保留选择权并防止污染生产代码 | 新开发 `zj-ui-prototype` |
| D27 | worst-case data toggle and break report | emil `break-ui` | 高；补足“demo data 看不出问题” | 新开发 `zj-ui-break` |
| D28 | design system generation/search/checklist | UUPM | 中高；规则库有价值，外部数据需审计 | 选择性复用 schema/检索思路 |
| D29 | component stories/docs/a11y/viewport/actions | Storybook | 高；工程回归的成熟 seam | B1 adapter `zj-ui-components` |
| D30 | visual regression / screenshot baseline | Storybook 生态 + browser tools | 高；是 release gate，不是 design ideation | 新开发 `zj-ui-verify` |
| D31 | natural-language UI copy/content states | frontend-design、taste | 高；空态、错误态、CTA 是交互的一部分 | 新开发 `zj-ui-content-states` |
| D32 | portable install/namespacing/version checks | 各 skill repo、ZAgentic 自身 | 高；必须服从本仓库发现/README/验证规则 | 新开发公共 skill packaging contract |

## 初步组合建议

推荐采用“ZAgentic 持有语义与 artifact，外部项目提供可拔插执行能力”的组合：

```text
                    ┌──────────────────────────┐
                    │ zj-ui-orchestrator        │
                    │ 路由/阶段/停止条件/交接     │
                    └────────────┬─────────────┘
                                 │
       ┌─────────────────────────┼─────────────────────────┐
       │                         │                         │
  brief & taste             design artifacts           implementation
  zj-ui-brief               UI-DESIGN.md               zj-ui-implement
  zj-ui-direction           ui-flow.json               zj-ui-components
  zj-ui-design-system       screenshots/notes           zj-ui-verify
       │                         │                         │
       └───────────────┬─────────┴──────────┬──────────────┘
                       │                    │
                 optional adapters      feedback gates
               A2UI / json-render      visual / motion / break
               M3E / Figma / Storybook  a11y / responsive / data
```

### 核心 skills（建议新开发）

| Skill | 生命周期职责 | 最小输入 | 必须产出 |
| --- | --- | --- | --- |
| `zj-ui-orchestrator` | 判断当前处于发现、设计、原型、实现、验证还是交付；串联兄弟 skills | 用户请求、项目状态、已有 artifacts | 阶段记录、下一步、停止/升级条件 |
| `zj-ui-brief` | 把模糊描述变成用户/任务/约束/非目标/成功标准 | 对话或 `UI-BRIEF.md` | `ui-brief/v1` + alignment questions |
| `zj-ui-discover` | 读取现有代码、tokens、组件、路由和截图，建立基线 | 代码库、运行页面 | baseline inventory、replica、unknowns |
| `zj-ui-direction` | 生成 2–3 个可解释、真正不同的视觉方向并等待选择 | `ui-brief/v1` | direction cards、比较页/截图、选择记录 |
| `zj-ui-design-system` | 维护全局 master + 页面 override、token 与 anti-pattern | direction choice、现有 tokens | `UI-DESIGN.md`、tokens、decision log |
| `zj-ui-flow` | 定义页面、状态、事件、转场、空/错/加载态 | brief + prototype | `ui-flow/v1`、状态矩阵、验收清单 |
| `zj-ui-prototype` | 用可丢弃多版本原型让人选择交互和布局 | flow + design system | prototype harness、variants、selection |
| `zj-ui-implement` | 将选定设计转成现有技术栈代码，复用组件和 tokens | selected prototype + repo | production diff、stories、implementation notes |
| `zj-ui-visual-review` | 浏览器多尺寸、截图、可访问性、对比度、reduced motion、视觉 critique | running app + contract | review report、screenshots、bounded fixes |
| `zj-ui-motion` | 只为有理由的 motion 做构建/审查/性能验证 | interaction intent | motion decision + code + reduced-motion proof |
| `zj-ui-break` | 用真实极端数据、空/一条/大列表、窄屏/缩放破坏 UI | component/story/fixture | break report + dev-only fixtures |
| `zj-ui-components` | 把组件、状态和设计 token 固化为可文档化、可回归的单元 | implemented components | Storybook stories 或等价 fixture |
| `zj-ui-verify` | 运行 unit/interaction/visual/a11y/responsive checks，并给出 release gate | stories + app | machine-readable receipt、evidence |
| `zj-ui-assets` | 管理真实素材、生成素材、来源、许可、替换点 | direction + asset needs | asset manifest、credits、fallback |
| `zj-ui-handoff` | 将对话、文档、设计、代码和验证结果压缩成可继续的交接 | all artifacts | handoff + next action |

### 可选 adapters（建议 B1，不维护 fork）

| Adapter | 用途 | 边界 |
| --- | --- | --- |
| `zj-ui-a2ui` | 将 `ui-flow/v1` 的可声明部分映射成 A2UI catalog/messages，验证动态 UI | 不让 A2UI 定义本仓库的 design system、权限或产品语义 |
| `zj-ui-json-render` | 将 component/action schema 映射到 json-render catalog/registry，做 React 生成式 UI PoC | 只接收受信 catalog；不把任意模型 JSON 直接变成代码 |
| `zj-ui-m3e` | 导入/导出 M3E Canvas 的 screens、theme 和 prompt | M3E 是编辑器，不是 ZAgentic artifact 的唯一真源 |
| `zj-ui-figma` | 读取 Figma frame/context/variables/screenshot，按 Code Connect/项目规则落地 | 远程服务、seat、额度、Terms 和写回权限由用户承担 |
| `zj-ui-storybook` | 生成 stories、viewport/a11y/actions 测试和 docs 入口 | Storybook 是验证/文档 runtime，不负责选风格 |

## 主要决策与暂不采用项

1. **不直接采用单一“全能 UI skill”。** UUPM、Taste、Oil UI、Superdesign 都有强方法，但它们把数据、服务、审美与执行边界混在一起；本仓库要持有可 diff 的 brief、design system、flow、decision 和 evidence。
2. **不把 A2UI 当作视觉设计协议。** A2UI 解决 Agent 如何安全地“说 UI”，不解决产品为什么使用某种风格、信息架构和可用性；它应位于生成式 UI 的传输/渲染层。
3. **不把 json-render 当成默认前端架构。** 它适合 React/多 renderer 的动态 UI 和受 catalog 约束的生成式界面，但会引入 runtime、state、版本和跨框架组合成本；先做一个项目级 PoC。
4. **不直接依赖 Figma 作为唯一交互入口。** Figma 适合有设计资产的团队，但远程 MCP 的额度、Beta、座席和服务条款是外部责任；对话 + Markdown + JSON 必须能独立完成工作。
5. **不把 screenshot 检查等同于“好设计”。** 视觉 inspector 能抓到 overflow、空洞布局、对比度和响应式问题，但仍需要方向选择、用户任务、内容真实性和人工选择。
6. **不把动效塞进一个 UI 大 skill。** 构建、审查、性能和机会发现是不同的判断任务；至少需要独立输入、输出和停止条件。

## 未决问题与 PoC

- `ui-flow/v1` 是否采用 A2UI flat component list、json-render elements map，还是 ZAgentic 自有中间表示？需要用同一表单/审批流在两个 adapter 上实现，比较状态表达、增量更新、错误恢复和退出成本。
- 浏览器验证是否使用现有宿主工具、Playwright、Taste inspector 或 Storybook test-runner？需要在一个真实项目上比较截图稳定性、可读性、无障碍覆盖和运行成本。
- M3E/Figma 的输入如何避免丢失“为什么这样设计”的语义？需要设计 `source`, `decision`, `constraint`, `confidence` 元数据，并测试从画布/截图反向回到文档是否可审阅。
- 视觉方向生成是否需要外部图片/网页搜索？需要验证无网络、无图片、许可证不明确时的退化路径，禁止把 placeholder 当成真实证明素材。
- 这些 skill 的自动触发条件如何避免互相抢占？需要为每个 skill 写 capability manifest、输入/输出 schema、禁止事项、调用优先级和冲突 resolver。

## 采集阻断记录

本轮执行：

```text
python3.13 skills/research/zj-research/scripts/research_cli.py \
  research/ui-agent-skills/2026-10-19-brief.request.json \
  --output research/ui-agent-skills/2026-10-19-ledger.response.json \
  --status-output research/ui-agent-skills/2026-10-19-collection.status.json
```

结果为 `GITHUB_RATE_LIMITED`，`collection.status.json` 明确记录 `state: collection-blocked`、`oldLedgerUsed: false`、`ledger.relationship: not-produced`。正式发布前必须在同一 brief fingerprint 下重新 collection，生成 sealed ledger，补充每个候选的 `stars`、`topicMatch`、revision 和 Evidence ID；不能用本文件的 URL 或直接 API 读取替代。

