<!-- ROADMAP_SECTION_START -->
## ZJ Roadmap

> 数据文件: `ui-agent-skills-roadmap.json` | 最后更新: 2026-10-20 19:18:23

[~][Y+] 1. UI Agent Skills 全生命周期落地路线
    ├── [~][X+] 1-7. AdapterBoundary 与 adapter 生命周期
    │   ├── [~][X+] 1-7-1. 对 Storybook、json-render、A2UI、M3E Canvas 等候选固定版本并完成 capability-fit 证据账本
    │   ... 该层还有 4 个兄弟，0 个 in_progress ▸
    ... 该层还有 9 个兄弟，0 个 in_progress ▸
<details><summary>阻塞链：20 个节点被阻塞</summary>

- 1-10. 长期文档、维护治理与 rollout 决策 ← e18: 1-9. 三次 paired run 与 graduation gate [ ]
- 1-10-1. 将稳定契约、决策、风险与验收标准迁移到 docs 权威页，保留讨论过程待 Human 审核 ← e69: 1-9-4. 聚合指标、剩余风险与 fallback 演练，形成 graduation packet 或 pilot/quarantine 结论 [ ]
- 1-10-2. 同步新 skill 的 bucket README、top-level README、递归发现与 ZJ-CONTEXT.md ← e49: 1-10-1. 将稳定契约、决策、风险与验收标准迁移到 docs 权威页，保留讨论过程待 Human 审核 [ ]
- 1-10-3. 建立 skill/adapter owner、维护预算、RTO/RPO、版本重评与容量/WIP 治理 ← e50: 1-10-2. 同步新 skill 的 bucket README、top-level README、递归发现与 ZJ-CONTEXT.md [ ]
- 1-10-4. 输出 rollout、pilot、kill-switch、adapter 移除与后续 revalidation 决策 ← e51: 1-10-3. 建立 skill/adapter owner、维护预算、RTO/RPO、版本重评与容量/WIP 治理 [ ]
- ... 另有 15 个节点被阻塞未列出

</details>


### 当前施工：1-7-1. 对 Storybook、json-render、A2UI、M3E Canvas 等候选固定版本并完成 capability-fit 证据账本

**决策：**
- Q: capability-fit 如何对候选分群评估？ → 按 adapter 架构角色分两群：A 群=active 本地验证面(Storybook)，B 群=opt-in 投影/协议/输入兼容(json-render/A2UI/M3E)；不能用统一 R 集套所有候选，否则 Storybook 会被误判 D。

### 下一步可开工（ready 前 3）

- 1-9-5. 持久化/重放实测闸门回写（G-19..G-25） [ ]
<!-- ROADMAP_SECTION_END -->
