# UI

界面交付的全生命周期链条：brief → discover → direction → design system → flow → prototype →
review → break → verify → handoff。一个 skill 一个阶段，每个 `(stage, artifact)` 恰好一个写
owner；冲突时停下问人，不自动改派，不用未知冒充成功。

上游契约在 `docs/designs/ui-agent-skills/`：`ui-agent-skills-skill-capability-manifest.md`（16 字段与阶段责任卡）、
`ui-agent-skills-canonical-schema.md`（六类 canonical artifact）、
`ui-agent-skills-ui-flow-v1-contract.md`（六义）。新增 skill 前先读
`ui-agent-skills-skill-md-template.md`。

- **[zj-ui-core](./zj-ui-core/SKILL.md)** — **S0 BASE**（不在阶段链上）：契约基座与确定性引擎 —— schema 校验、deny-first、unknown 四元组、原子提交与幂等键、WCAG contrast；S1..S4 的实现与 fixture 跑批都在它的 `scripts/`。
- **[zj-ui-brief](./zj-ui-brief/SKILL.md)** — S1 INTAKE：把对话或 UI-BRIEF.md 编辑解析成目标、用户、任务、成功标准与 unknown 四元组的 brief 草案。
- **[zj-ui-discover](./zj-ui-discover/SKILL.md)** — S2 DISCOVER：补齐 brief 缺口，输出问题清单、证据等级与 unknown，追问预算 2 次。
- **[zj-ui-direction](./zj-ui-direction/SKILL.md)** — S3 DIRECTION：生成 2–3 张可比较方向卡，由 Human 选定后才写入 UI-DESIGN.md。
- **[zj-ui-design-system](./zj-ui-design-system/SKILL.md)** — S4 DESIGN_SYSTEM：把方向固化成 tokens 与 component catalog，contrast 与注册表不合格即阻断。
- **[zj-ui-flow](./zj-ui-flow/SKILL.md)** — S5 FLOW：维护 ui-flow/v1 六义并保证 semantic round-trip，丢义即 hard fail。
- **[zj-ui-prototype](./zj-ui-prototype/SKILL.md)** — S6 BUILD：从 flow 生成本地 preview 或实现切片，只用 catalog 内组件，effect 先过 policy gate。
- **[zj-ui-visual-review](./zj-ui-visual-review/SKILL.md)** — S7 REVIEW：浏览器 inspect + 截图绑定任务与风险等级，产出可归因的 review record。
- **[zj-ui-break](./zj-ui-break/SKILL.md)** — S8 BREAK：长文本、空/错/极值、多语言加 390/768/1440 三档视口的极限与响应式验证。
- **[zj-ui-verify](./zj-ui-verify/SKILL.md)** — S9 VERIFY：DOM/ARIA、focus、contrast、reduced-motion 硬门禁与可重放 verification receipt。
- **[zj-ui-handoff](./zj-ui-handoff/SKILL.md)** — S10 HANDOFF：变更摘要、运行命令、风险、已知限制、fallback 与责任人的 handoff。

S1..S4 已实现（路线图节点 1-6-2）：契约不变，实现集中在 `zj-ui-core/scripts/ui_stages.py`，
12 条失败 fixture 落在 `tests/ui-agent-skills/fixtures/skills/` 并逐条通过。S5..S10 仍是
**契约骨架**（1-6-1）：manifest、输入输出、禁止事项、停止条件与失败 fixture id 已冻结，可执行
实现归 1-6-3 / 1-6-4，端到端串联归 1-6-5 的 resolver。
