# 01 — 起 utopia 持久层地基（FR-012）

**Status:** ready-for-agent
**Blocked by:** None — can start immediately
**Source:** ZKnowledgeCompounding/docs/prds/知识复利工具_spec_slice1.md (FR-012, Implementation Decisions: 持久层选型 / 存储格式)

## What to build

把 **utopia** 作为知识复利工具 Slice 1 的持久层跑起来：自托管、双时态（bitemporal）、带权限，Apache-2.0 许可。建立 **OKF 格式**（目录 + markdown + YAML frontmatter）的导入能力，并启用 **openwiki 式自动维护**（新增/变更文档时自动更新索引与关联）。数据主权必须留在用户本地，不依赖任何外部 SaaS。

这是整个 Slice 1 的地基：后续 research-agent 产出的报告、回流的元认知、zj 的主动 query，全部读写这一层。从 Phase 0 起就运行它，避免后期迁移。

## Acceptance criteria

- [ ] utopia 以自托管方式启动，给定本地 URL 可访问（不依赖外部托管）
- [ ] 一个 OKF 文档（目录 + `*.md` + `frontmatter.yaml`）可被导入 utopia，导入后能通过内容/元数据检索到
- [ ] 双时态能力可用：同一事实的新旧版本可被区分与回溯
- [ ] 权限模型存在且最小可用（至少区分「写入者 / 读取者」两类角色）
- [ ] 自动维护生效：新增一个 OKF 文档后，索引自动包含它，无需手工重建
- [ ] 整个链路无任何外部 SaaS 依赖（数据主权在用户手）

## Key interfaces / decisions (from spec)

- **持久层选型**：utopia（双时态 + 权限 + 自托管，Apache-2.0），从 Phase 0 起运行
- **存储格式**：OKF（目录 + md + YAML frontmatter），可移植、数据主权在用户手
- **许可**：Apache-2.0（与 utopia 一致，避免传染式 copyleft）

## Out of scope

- 多 Agent 协同 / promote（FR-013，后续切片）
- 多人多设备同步（FR-014，后续切片）
- 双轨数据模型 / GAM / 元认知三层（FR-011，Phase 2）
- 任何 UI 编辑器（双链编辑器等）
