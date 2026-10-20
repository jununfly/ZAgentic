<!-- ROADMAP_SECTION_START -->
## ZJ Roadmap

> 数据文件: `ui-agent-skills-roadmap.json` | 最后更新: 2026-10-20 19:47:12

[~][Y+] 1. UI Agent Skills 全生命周期落地路线
├── [x][Y+] 1-1. 范围闸门与 Experience Version manifest
│   ├── [x][Y+] 1-1-1. 冻结 Experience Version scope manifest、in-scope/out-of-scope 与成功标准
│   ├── [x][Y+] 1-1-2. 锁定 React/Next.js 表单或审批流样例、角色、状态、环境和责任人
│   ├── [x][Y+] 1-1-3. 预注册 direct-prompt baseline、返工/决策时间/escaped defect 指标与毕业门槛
│   └── [x][Y+] 1-1-4. 建立 Wave 0 资源、许可证、fixture、owner 与风险账本
├── [x][Y+] 1-2. Canonical artifact 契约与 ui-flow/v1
│   ├── [x][Y+] 1-2-1. 定义六类 canonical artifact 的 schema、字段 owner、source 与 requiredness
│   ├── [x][Y+] 1-2-2. 实现 UI-BRIEF/UI-DESIGN 的文档编辑、patch/diff、unknown/source 语义
│   ├── [x][Y+] 1-2-3. 定义 ui-flow/v1 的 screen/component/state/action/intent/acceptance 与迁移规则
│   └── [x][Y+] 1-2-4. 完成字段保留、semantic round-trip、离线恢复、schema lock 与 golden fixtures
├── [x][Y+] 1-3. Skill capability manifest 与 resolver 编排
│   ├── [x][Y+] 1-3-1. 定义十个 skill 的 capability manifest、输入输出、禁止事项、依赖和停止条件
│   ├── [x][Y+] 1-3-2. 实现唯一 owner、precedence、resolver、plan hash 与冲突冻结机制
│   ├── [x][Y+] 1-3-3. 实现 lease、幂等键、失败阶梯、NEEDS_CONTEXT/quarantine/degraded 状态
│   └── [x][Y+] 1-3-4. 持久化 plan、decision、revision 与 handoff 的可恢复编排记录
├── [x][Y+] 1-4. Trust boundary、provenance 与 deny-first policy
│   ├── [x][Y+] 1-4-1. 建立 component/action catalog allowlist、effect intent 与 unknown 语义
│   ├── [x][Y+] 1-4-2. 实现 policy→approval→sandbox lease→executor 单入口的 deny-first 信任链
│   ├── [x][Y+] 1-4-3. 实现 provenance、asset-manifest.json、secret redaction 与许可证 quarantine
│   └── [x][Y+] 1-4-4. 覆盖未注册组件/危险 action、凭据网络截图泄露、远程写回失败的 deny fixtures
├── [x][Y+] 1-5. Deterministic verification、fixture 与 receipt
│   ├── [x][Y+] 1-5-1. 冻结 fixture-manifest、verification-matrix 与 browser/environment fingerprint
│   ├── [x][Y+] 1-5-2. 实现 baseline 与 degraded 双 lane、固定字体/网络回放/时钟/seed
│   ├── [x][Y+] 1-5-3. 实现 DOM/ARIA、focus、contrast、overflow、响应式、motion 与状态硬门禁
│   └── [x][Y+] 1-5-4. 定义 verification receipt、聚合状态、stale/revalidation_required 与无法归因 quarantine
├── [x][Y+] 1-6. 十个 UI skills 的契约化本地闭环
│   ├── [x][Y+] 1-6-1. 创建十个公共 skill 目录、SKILL.md 模板、递归索引、README 与术语登记
│   ├── [x][Y+] 1-6-2. 实现 zj-ui-brief、zj-ui-discover、zj-ui-direction、zj-ui-design-system
│   ├── [x][Y+] 1-6-3. 实现 zj-ui-flow、zj-ui-prototype、zj-ui-visual-review、zj-ui-break
│   ├── [x][Y+] 1-6-4. 实现 zj-ui-verify、zj-ui-handoff 及其 receipt/handoff 产物
│   └── [x][Y+] 1-6-5. 接通本地 resolver 与十个 skill 的正常/冲突/失败 fixture 闭环
├── [~][X+] 1-7. AdapterBoundary 与 adapter 生命周期
│   ├── [x][X+] 1-7-1. 对 Storybook、json-render、A2UI、M3E Canvas 等候选固定版本并完成 capability-fit 证据账本
│   ├── [x][X+] 1-7-2. 定义 AdapterBoundary v1、manifest、schema lock、mapping、owner、fallback 与 removal test
│   ├── [x][X+] 1-7-3. 实现 Storybook active 本地验证 adapter：stories、a11y、viewport、interaction、docs
│   ├── [ ][X+] 1-7-4. 为 json-render/A2UI/M3E 建立 opt-in projection/协议/输入兼容性 golden fixtures
│   └── [!][X+] 1-7-5. 验证 adapter 删除、断网、远程服务失败时的本地恢复、degraded/disabled/quarantine
├── [!][Y+] 1-8. Experience Version 表单/审批 sample flow
│   ├── [!][Y+] 1-8-1. 为表单/审批 Experience Version 固化 PRD、角色状态、canonical artifact 与 fixture
│   ├── [!][Y+] 1-8-2. 打通对话输入与 UI-BRIEF.md 编辑 diff → Human 接受 patch → 下一步 plan
│   ├── [!][Y+] 1-8-3. 完成 direction cards、token/catalog、flow/action/intent 与组件选择的人机协作
│   ├── [!][Y+] 1-8-4. 从 ui-flow/v1 生成本地 prototype/preview，并演练 effect approval 与安全边界
│   └── [!][Y+] 1-8-5. 演练远程 adapter 关闭、素材 quarantine、未知字段与本地静态 preview fallback
├── [!][Y+] 1-9. 三次 paired run 与 graduation gate
│   ├── [!][Y+] 1-9-1. 按同一 case/environment/config 预注册 paired run、无效运行规则与原始日志留存
│   ├── [!][Y+] 1-9-2. 执行第 1 次 paired run：direct-prompt 与 skills path 并行并生成 receipt
│   ├── [!][Y+] 1-9-3. 执行第 2、3 次 paired run 并完成视觉/a11y/interaction/人工审阅闭环
│   ├── [!][Y+] 1-9-4. 聚合指标、剩余风险与 fallback 演练，形成 graduation packet 或 pilot/quarantine 结论
│   └── [ ][Y+] 1-9-5. 持久化/重放实测闸门回写（G-19..G-25）
└── [!][X+] 1-10. 长期文档、维护治理与 rollout 决策
    ├── [!][X+] 1-10-1. 将稳定契约、决策、风险与验收标准迁移到 docs 权威页，保留讨论过程待 Human 审核
    ├── [!][X+] 1-10-2. 同步新 skill 的 bucket README、top-level README、递归发现与 ZJ-CONTEXT.md
    ├── [!][X+] 1-10-3. 建立 skill/adapter owner、维护预算、RTO/RPO、版本重评与容量/WIP 治理
    └── [!][X+] 1-10-4. 输出 rollout、pilot、kill-switch、adapter 移除与后续 revalidation 决策
<details><summary>阻塞链：17 个节点被阻塞</summary>

- 1-10. 长期文档、维护治理与 rollout 决策 ← e18: 1-9. 三次 paired run 与 graduation gate [ ]
- 1-10-1. 将稳定契约、决策、风险与验收标准迁移到 docs 权威页，保留讨论过程待 Human 审核 ← e69: 1-9-4. 聚合指标、剩余风险与 fallback 演练，形成 graduation packet 或 pilot/quarantine 结论 [ ]
- 1-10-2. 同步新 skill 的 bucket README、top-level README、递归发现与 ZJ-CONTEXT.md ← e49: 1-10-1. 将稳定契约、决策、风险与验收标准迁移到 docs 权威页，保留讨论过程待 Human 审核 [ ]
- 1-10-3. 建立 skill/adapter owner、维护预算、RTO/RPO、版本重评与容量/WIP 治理 ← e50: 1-10-2. 同步新 skill 的 bucket README、top-level README、递归发现与 ZJ-CONTEXT.md [ ]
- 1-10-4. 输出 rollout、pilot、kill-switch、adapter 移除与后续 revalidation 决策 ← e51: 1-10-3. 建立 skill/adapter owner、维护预算、RTO/RPO、版本重评与容量/WIP 治理 [ ]
- ... 另有 12 个节点被阻塞未列出

</details>


### 下一步可开工（ready 前 3）

- 1-7-4. 为 json-render/A2UI/M3E 建立 opt-in projection/协议/输入兼容性 golden fixtures [ ]
- 1-9-5. 持久化/重放实测闸门回写（G-19..G-25） [ ]
<!-- ROADMAP_SECTION_END -->
