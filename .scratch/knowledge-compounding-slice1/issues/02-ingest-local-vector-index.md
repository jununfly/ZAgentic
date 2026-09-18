# 02 — Ingest 摄入与本地向量索引（FR-001）

**Status:** ready-for-agent
**Blocked by:** 01 — 起 utopia 持久层地基
**Source:** ZKnowledgeCompounding/docs/prds/知识复利工具_spec_slice1.md (FR-001, Implementation Decisions: 私有材料底座 / 格式支持)

## What to build

在 ZAgentic 的 **`zj-deep-research` skill**（新建）中实现 Ingest 模块。它能吃进用户的私有材料——本地文件/目录，或资料库节点——支持 **md / html / csv** 三种主要格式；对材料切块，每块带上**页级元数据**（来源、页码/段落、标题路径等），并在本地建立**向量索引**。

索引必须**跨次复用**：本次建好的索引，下一次研究任务可以直接挂载，不必重建。这是「复利起点」——知识体第一次被沉淀为可被检索的结构。

## Acceptance criteria

- [ ] 给定一组私有材料（md/html/csv 混合或单一），Ingest 产出本地向量索引
- [ ] 索引中每个 chunk 携带页级元数据，可被检索结果回带（人能追溯到原文位置）
- [ ] 索引持久化在本地；第二次任务挂载同一索引时无需重建即可检索
- [ ] 资料库节点作为输入源时，能被同等摄入并建索引
- [ ] 整个摄入过程数据不出域（本地索引，无外部上传）

## Key interfaces / decisions (from spec)

- **落地形态**：ZAgentic 的 `zj-deep-research` skill 演化，复用 skill→agent 路径，不单建服务
- **私有材料底座**：本地向量索引（切块 + 页级元数据），跨次复用、数据不出域
- **格式支持**：md / html / csv 三种主要格式

## Out of scope

- 联网检索（属于 T03 Retrieve 的「私有库 + 联网」中的联网部分）
- 报告生成、引用校验（T03 / T04）
- 回流与 query（T05 / T06）
- 跨设备同步索引（FR-014，后续切片）
