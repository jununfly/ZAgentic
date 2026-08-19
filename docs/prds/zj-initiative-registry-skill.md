# zj-initiative-registry Skill

## 1. 产品定义

`zj-initiative-registry` 是一个 ZAgentic Skill，用于管理由用户指定的 GitHub Registry 仓库承载的跨仓库 Initiative 导航。它让 Human 和多台设备上的多个 Agent 共享同一份 Initiative、Spec 和 Plan 索引，并通过 Git history、branch 和 pull request 保留变更审计。

Registry 的数据协议由 [ZInitiatives Registry Protocol](https://github.com/jununfly/ZInitiatives/blob/main/docs/prds/initiative-registry-protocol.md) 定义；本 Spec 只定义 Skill 的用户体验、工作流、实现边界和验收标准。

## 2. 目标场景

- Human 在多台设备上使用多个 Agent，仍能定位同一 Initiative 的 Spec 和 Plan。
- 用户指定一个 GitHub repository 作为 Registry 的共享事实源。
- Agent 可以从 Registry 找到某个 Initiative 的 PRD 和执行 roadmap，再进入对应项目继续工作。
- 不同 Agent 可以通过分片 manifest 和 Git branch/PR 并行维护不同 Initiative。
- Registry 变更可以在没有共享本地文件系统的设备之间同步。

## 3. 非目标

- 不替代 `zj-roadmap-driven` 管理 Plan 内部的节点、决策、状态和 focus。
- 不自动决定仓库是否构成独立 Initiative，也不自动决定 Spec/Plan 的归属。
- 不把 GitHub token、SSH key 或其他凭证写入 Registry、日志或生成物。
- 不自动修改 Initiative 仓库中的 PRD 或 Plan 内容。
- 不聚合每个 Plan 的运行时状态为一个伪精确的全局进度。

## 4. 用户 Interface

Skill 支持以下操作：

```text
bootstrap --registry-repo <github-url>
register initiative|spec|plan
remove initiative|spec|plan
validate --registry-repo <github-url>
check-drift --registry-repo <github-url>
closeout-check --registry-repo <github-url>
sync --registry-repo <github-url>
show <initiative-or-spec-or-plan-id>
```

自然语言请求“初始化全局 Initiative 注册表”“登记这个 PRD”“同步跨设备项目导航”“检查 Registry 漂移”“找到某个 Initiative 当前 Plan”应触发本 Skill。

`--registry-repo` 的解析顺序为：命令显式参数、当前项目的本地配置、用户级配置；都不存在时要求 Human 提供 GitHub URL。当前已配置的 Registry 是 `https://github.com/jununfly/ZInitiatives`。

## 5. 数据与生成物

分片 manifest 是 Registry 的维护输入，完整文件是确定性生成物：

```text
ZInitiatives/
├── registry/
│   ├── initiatives/
│   ├── specs/
│   └── plans/
├── generated/
│   ├── global-initiative-registry.json
│   ├── global-initiative-registry.md
│   └── global-initiative-registry.mmd
├── schemas/
└── scripts/
```

`global-initiative-registry.json` 必须包含 schema version、生成来源仓库和 commit SHA。生成物不能被 Agent 手工重排；修改必须回到对应 manifest 后重新编译。

Initiative、Spec、Plan 的字段和三层关系以 Registry Protocol 为准。跨设备共享的路径使用 GitHub repository URL 加 repository-relative path；禁止写入任何设备的绝对路径。

## 6. 维护工作流

### Bootstrap

Skill 检查用户提供的 GitHub URL，确认仓库可读；在仓库不存在 Registry 结构时创建模板、schema、维护规则和校验入口。初始化完成的判据是 Registry 仓库包含合法配置、至少一个可解析的生成文件，并且本地验证通过。

### Register

Skill 读取目标 Initiative 仓库的说明和目标文件，提出 Initiative/Spec/Plan 归属建议。首次注册、归属变化、合并或退休必须经过 Human 确认；确认后只修改相应分片 manifest，重新生成全部派生文件并输出 semantic diff。

### Validate

Skill 执行本地 schema 校验、三层关系校验、ID 唯一性校验、路径存在性校验、生成物一致性校验，并对每个 Plan 调用其声明的 roadmap engine 验证器。注册引用损坏是 error；仓库中存在未登记的 PRD 或 Plan 默认是 warning。

### Check drift

Skill 对已登记的 Initiative 仓库执行只读检查，报告被删除的引用、未登记的 PRD/Plan、仓库迁移、默认分支变化和 Spec/Plan 归属失效。漂移报告不自动修改 Registry。

### Closeout check

Skill 对已登记的 roadmap Plan 执行只读 closeout 检查。Plan 的全部节点完成时，Skill 提醒 Human 将临时材料沉淀为 durable 文档、更新必要的 Registry 导航并重新生成校验；Plan 被阻塞时，Skill 提醒 Human 先完成决策。checkout 或源文件不可用时报告 warning，不推断完成。该检查不删除 Registry 条目、不压缩历史，也不修改 Initiative 仓库。

### Sync and publish

默认流程为 fetch 最新默认分支、创建 scoped branch、修改 manifest、编译、验证、提交、push 和创建 pull request。push 前必须再次确认 remote 没有移动；检测到非 fast-forward 或远端变化时停止并要求重新同步。Human 明确授权时才允许直接提交默认分支；禁止 force-push。

## 7. 本地 checkout Adapter

Registry 只保存远程仓库和仓库内路径。本地设备通过 git checkout map 将 Initiative ID 映射到本地目录。checkout map 属于设备私有配置，必须 gitignore。找不到本地 checkout 时，Skill 可以读取 GitHub 远程文件、提示 Human clone，或在明确授权后执行 clone。

## 8. 与其他 Module 的关系

```text
zj-initiative-registry
└── resolves Initiative → Spec → Plan

zj-roadmap-driven
└── manages the selected Plan's nodes, decisions, status and focus
```

GitHub Registry 是共享导航事实源；各 Initiative 仓库拥有自己的 Spec 和 Plan 内容；`zj-roadmap-driven` 拥有 Plan 的执行状态。Registry Skill 通过 Adapter 连接 GitHub、文件系统和 roadmap validator，不让任何上游数据模型泄漏到调用方。

## 9. 验收标准

1. Human 提供 `https://github.com/jununfly/ZInitiatives` 后，Skill 能在一台新设备完成 bootstrap，并生成合法 Registry。
2. 两台设备可以读取同一 Registry，并解析到同一个 Initiative、Spec 和 Plan。
3. 两个 Agent 同时修改不同 Initiative 时可以通过 branch/PR 合并，不覆盖彼此的 manifest。
4. 同一 manifest 发生远端更新时，Skill 会停止并报告冲突，不执行隐式覆盖。
5. 生成的 JSON、Markdown 和 Mermaid 只由 manifest 确定性编译得到。
6. 删除或移动已登记文件会被 `validate` 或 `check-drift` 报告。
7. 每个 Plan 的执行状态仍能通过 `zj-roadmap-driven` 独立验证。
8. 测试和日志不会泄露 GitHub 凭证或设备绝对路径。
9. 已完成或被阻塞的 Plan 会触发明确的 Human closeout 或 decision reminder，且检查保持只读。

## 10. 分阶段交付

### Phase 0：协议和 bootstrap

实现 Registry Protocol schema、模板、bootstrap、compile 和 validate；使用 ZInitiatives 完成一条 Initiative → Spec → Plan 闭环。

### Phase 1：注册与漂移

实现 register、remove、show、check-drift 和 semantic diff；覆盖跨仓路径存在性、未登记文件 warning 和损坏引用 error。

### Phase 2：多设备 Git 协作

实现 scoped branch、PR 发布、远端移动检测和 checkout map；用两台设备和多个 Agent 验证并发维护。

### Phase 3：持续治理

增加 Registry CI、协议版本迁移、Initiative 生命周期和跨 Initiative 依赖图；不把 Plan 的运行时状态复制到 Registry。
