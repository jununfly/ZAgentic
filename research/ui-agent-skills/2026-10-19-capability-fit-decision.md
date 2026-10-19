# 开源能力拟合决策记录

> 由 `zj-open-source-capability-fit` 依据 [开源能力拟合决策模型](../../docs/agreements/open-source-capability-fit-decision-model.md) 生成。

## 目标需求 R

为 ZAgentic 的界面开发 skills 选择可拆分、可组合、可复核的外部 OSS 能力，而不把任何外部项目误用为全生命周期平台

- **R1** [关键] 候选提供一个边界清晰、可由 Agent 调用或作为工程 seam 使用的可复用能力 — 验收: 能指出一个独立职责、输入、输出和调用入口
- **R2** [关键] 候选产出可检查、可传递或可回滚的结构化 artifact/output — 验收: 至少有 spec、文档、截图、代码、测试结果或明确的设计记录
- **R3** [关键] 候选可以通过薄适配层接入 ZAgentic，而不接管本仓库的产品语义和 SSOT — 验收: 适配范围限于身份/查询/状态/来源转换，主体能力可移除
- **R4** [关键] 候选具有可固定版本、可审计的源码/许可证/外部依赖责任边界 — 验收: 能记录 commit、许可证、升级风险和退出路径
- **R5** [want] 候选直接补足至少一个界面生命周期缺口：设计方向、协议渲染、原型输入、动效、实现或验证 — 验收: 在一个垂直切片中能观察到质量或效率改善
- **R6** [want] 候选支持跨会话反馈、跨项目复用或跨框架迁移中的至少一种 — 验收: artifact、组件、prompt、renderer 或规则能被下一次工作复用

## 候选 a2ui · A2UI (cbaa5ee62c737b50d0695c1e5794d0f648b61dca)

- **推荐分类**: `C`
- 关键需求覆盖率: 50% · 平均有效拟合度: 0.86 · 总所有权成本 E: 101

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 0.95 | 0.95 | https://raw.githubusercontent.com/a2ui-project/a2ui/cbaa5ee62c737b50d0695c1e5794d0f648b61dca/README.md |
| R2 | native | 1.0 | 1.0 | 0.95 | 0.95 | https://raw.githubusercontent.com/a2ui-project/a2ui/cbaa5ee62c737b50d0695c1e5794d0f648b61dca/README.md |
| R3 | adapted | 0.95 | 0.95 | 0.95 | 0.86 | https://raw.githubusercontent.com/a2ui-project/a2ui/cbaa5ee62c737b50d0695c1e5794d0f648b61dca/README.md |
| R4 | native | 0.95 | 0.95 | 0.95 | 0.86 | https://raw.githubusercontent.com/a2ui-project/a2ui/cbaa5ee62c737b50d0695c1e5794d0f648b61dca/README.md |
| R5 | native | 0.9 | 0.85 | 0.9 | 0.69 | https://raw.githubusercontent.com/a2ui-project/a2ui/cbaa5ee62c737b50d0695c1e5794d0f648b61dca/README.md |
| R6 | native | 0.95 | 0.95 | 0.95 | 0.86 | https://raw.githubusercontent.com/a2ui-project/a2ui/cbaa5ee62c737b50d0695c1e5794d0f648b61dca/README.md |

### 依据
- 关键需求缺口且 E=101>E_MID -> C

## 候选 claude-frontend-design · Claude Code frontend-design plugin (ef7bfdca55d906929fe6b782025b93758c325074)

- **推荐分类**: `B`
- 关键需求覆盖率: 25% · 平均有效拟合度: 0.73 · 总所有权成本 E: 64

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 0.95 | 0.95 | https://raw.githubusercontent.com/anthropics/claude-code/ef7bfdca55d906929fe6b782025b93758c325074/plugins/frontend-design/README.md |
| R2 | native | 0.9 | 0.95 | 0.9 | 0.77 | https://raw.githubusercontent.com/anthropics/claude-code/ef7bfdca55d906929fe6b782025b93758c325074/plugins/frontend-design/skills/frontend-design/SKILL.md |
| R3 | adapted | 0.9 | 0.9 | 0.95 | 0.77 | https://raw.githubusercontent.com/anthropics/claude-code/ef7bfdca55d906929fe6b782025b93758c325074/plugins/frontend-design/.claude-plugin/plugin.json |
| R4 | adapted | 0.8 | 0.8 | 0.85 | 0.54 | https://raw.githubusercontent.com/anthropics/claude-code/ef7bfdca55d906929fe6b782025b93758c325074/plugins/frontend-design/skills/frontend-design/SKILL.md |
| R5 | native | 0.95 | 0.95 | 0.95 | 0.86 | https://raw.githubusercontent.com/anthropics/claude-code/ef7bfdca55d906929fe6b782025b93758c325074/plugins/frontend-design/skills/frontend-design/SKILL.md |
| R6 | adapted | 0.7 | 0.8 | 0.85 | 0.48 | https://raw.githubusercontent.com/anthropics/claude-code/ef7bfdca55d906929fe6b782025b93758c325074/plugins/frontend-design/README.md |

### 依据
- 关键需求存在部分缺口但 E=64<=E_MID -> B

## 候选 taste · Taste Skill (b9ca2fd8047f4c72d7da90ebc1c1203e57c72cd2)

- **推荐分类**: `B`
- 关键需求覆盖率: 25% · 平均有效拟合度: 0.80 · 总所有权成本 E: 63

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 0.95 | 0.95 | https://raw.githubusercontent.com/Leonxlnx/taste-skill/b9ca2fd8047f4c72d7da90ebc1c1203e57c72cd2/skills/taste-skill/SKILL.md |
| R2 | native | 0.95 | 0.95 | 0.9 | 0.81 | https://raw.githubusercontent.com/Leonxlnx/taste-skill/b9ca2fd8047f4c72d7da90ebc1c1203e57c72cd2/README.md |
| R3 | adapted | 0.85 | 0.9 | 0.9 | 0.69 | https://raw.githubusercontent.com/Leonxlnx/taste-skill/b9ca2fd8047f4c72d7da90ebc1c1203e57c72cd2/skills/taste-skill/SKILL.md |
| R4 | native | 0.95 | 0.95 | 0.95 | 0.86 | https://raw.githubusercontent.com/Leonxlnx/taste-skill/b9ca2fd8047f4c72d7da90ebc1c1203e57c72cd2/README.md |
| R5 | native | 0.95 | 0.95 | 0.95 | 0.86 | https://raw.githubusercontent.com/Leonxlnx/taste-skill/b9ca2fd8047f4c72d7da90ebc1c1203e57c72cd2/skills/taste-skill/SKILL.md |
| R6 | native | 0.85 | 0.85 | 0.9 | 0.65 | https://raw.githubusercontent.com/Leonxlnx/taste-skill/b9ca2fd8047f4c72d7da90ebc1c1203e57c72cd2/README.md |

### 依据
- 关键需求存在部分缺口但 E=63<=E_MID -> B

## 候选 json-render · json-render (72568f990e5502c4d3115691facb8ca928a5c9fc)

- **推荐分类**: `C`
- 关键需求覆盖率: 50% · 平均有效拟合度: 0.88 · 总所有权成本 E: 93

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 0.95 | 0.95 | https://raw.githubusercontent.com/vercel-labs/json-render/72568f990e5502c4d3115691facb8ca928a5c9fc/README.md |
| R2 | native | 1.0 | 1.0 | 0.95 | 0.95 | https://raw.githubusercontent.com/vercel-labs/json-render/72568f990e5502c4d3115691facb8ca928a5c9fc/README.md |
| R3 | adapted | 0.95 | 0.95 | 0.9 | 0.81 | https://raw.githubusercontent.com/vercel-labs/json-render/72568f990e5502c4d3115691facb8ca928a5c9fc/README.md |
| R4 | native | 0.95 | 0.95 | 0.95 | 0.86 | https://raw.githubusercontent.com/vercel-labs/json-render/72568f990e5502c4d3115691facb8ca928a5c9fc/README.md |
| R5 | native | 0.95 | 0.9 | 0.95 | 0.81 | https://raw.githubusercontent.com/vercel-labs/json-render/72568f990e5502c4d3115691facb8ca928a5c9fc/README.md |
| R6 | native | 1.0 | 0.95 | 0.95 | 0.90 | https://raw.githubusercontent.com/vercel-labs/json-render/72568f990e5502c4d3115691facb8ca928a5c9fc/README.md |

### 依据
- 关键需求缺口且 E=93>E_MID -> C

## 候选 m3e-canvas · M3E Canvas (627e42321bcf080979da87f40a17dcd432425a95)

- **推荐分类**: `C`
- 关键需求覆盖率: 25% · 平均有效拟合度: 0.78 · 总所有权成本 E: 85

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 0.9 | 0.90 | https://raw.githubusercontent.com/lnkiai/m3e-canvas/627e42321bcf080979da87f40a17dcd432425a95/README.md |
| R2 | native | 0.95 | 0.95 | 0.9 | 0.81 | https://raw.githubusercontent.com/lnkiai/m3e-canvas/627e42321bcf080979da87f40a17dcd432425a95/README.md |
| R3 | adapted | 0.8 | 0.8 | 0.9 | 0.58 | https://raw.githubusercontent.com/lnkiai/m3e-canvas/627e42321bcf080979da87f40a17dcd432425a95/README.md |
| R4 | native | 0.95 | 0.95 | 0.9 | 0.81 | https://raw.githubusercontent.com/lnkiai/m3e-canvas/627e42321bcf080979da87f40a17dcd432425a95/README.md |
| R5 | native | 0.95 | 0.95 | 0.95 | 0.86 | https://raw.githubusercontent.com/lnkiai/m3e-canvas/627e42321bcf080979da87f40a17dcd432425a95/README.md |
| R6 | native | 0.9 | 0.9 | 0.9 | 0.73 | https://raw.githubusercontent.com/lnkiai/m3e-canvas/627e42321bcf080979da87f40a17dcd432425a95/README.md |

### 依据
- 关键需求缺口且 E=85>E_MID -> C

## 候选 emil-skills · Emil Kowalski skills (2d228630ba1446365f614a108cb8252f1feda202)

- **推荐分类**: `B`
- 关键需求覆盖率: 25% · 平均有效拟合度: 0.78 · 总所有权成本 E: 60

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 0.95 | 0.95 | https://raw.githubusercontent.com/emilkowalski/skills/2d228630ba1446365f614a108cb8252f1feda202/README.md |
| R2 | native | 0.9 | 0.95 | 0.9 | 0.77 | https://raw.githubusercontent.com/emilkowalski/skills/2d228630ba1446365f614a108cb8252f1feda202/skills/break-ui/SKILL.md |
| R3 | adapted | 0.9 | 0.9 | 0.95 | 0.77 | https://raw.githubusercontent.com/emilkowalski/skills/2d228630ba1446365f614a108cb8252f1feda202/README.md |
| R4 | adapted | 0.9 | 0.9 | 0.9 | 0.73 | https://raw.githubusercontent.com/emilkowalski/skills/2d228630ba1446365f614a108cb8252f1feda202/README.md |
| R5 | native | 0.95 | 0.95 | 0.95 | 0.86 | https://raw.githubusercontent.com/emilkowalski/skills/2d228630ba1446365f614a108cb8252f1feda202/skills/animate/SKILL.md |
| R6 | native | 0.8 | 0.85 | 0.9 | 0.61 | https://raw.githubusercontent.com/emilkowalski/skills/2d228630ba1446365f614a108cb8252f1feda202/README.md |

### 依据
- 关键需求存在部分缺口但 E=60<=E_MID -> B

## 候选 uupm · UI UX Pro Max (56ea9cf174ed86786187daa9de0e6247cb0747e4)

- **推荐分类**: `B`
- 关键需求覆盖率: 25% · 平均有效拟合度: 0.85 · 总所有权成本 E: 57

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 0.95 | 0.95 | https://raw.githubusercontent.com/nextlevelbuilder/ui-ux-pro-max-skill/56ea9cf174ed86786187daa9de0e6247cb0747e4/README.md |
| R2 | native | 0.95 | 0.95 | 0.95 | 0.86 | https://raw.githubusercontent.com/nextlevelbuilder/ui-ux-pro-max-skill/56ea9cf174ed86786187daa9de0e6247cb0747e4/README.md |
| R3 | adapted | 0.9 | 0.9 | 0.95 | 0.77 | https://raw.githubusercontent.com/nextlevelbuilder/ui-ux-pro-max-skill/56ea9cf174ed86786187daa9de0e6247cb0747e4/README.md |
| R4 | native | 0.95 | 0.95 | 0.9 | 0.81 | https://raw.githubusercontent.com/nextlevelbuilder/ui-ux-pro-max-skill/56ea9cf174ed86786187daa9de0e6247cb0747e4/README.md |
| R5 | native | 0.95 | 0.95 | 0.95 | 0.86 | https://raw.githubusercontent.com/nextlevelbuilder/ui-ux-pro-max-skill/56ea9cf174ed86786187daa9de0e6247cb0747e4/README.md |
| R6 | native | 0.95 | 0.95 | 0.95 | 0.86 | https://raw.githubusercontent.com/nextlevelbuilder/ui-ux-pro-max-skill/56ea9cf174ed86786187daa9de0e6247cb0747e4/README.md |

### 依据
- 关键需求存在部分缺口但 E=57<=E_MID -> B

## 候选 oil-ui · Oil UI (feb1f95e8cec48bb8ba35181cb66f94f23b1b6fc)

- **推荐分类**: `B`
- 关键需求覆盖率: 25% · 平均有效拟合度: 0.82 · 总所有权成本 E: 58

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 0.95 | 0.95 | https://raw.githubusercontent.com/oil-oil/oil-ui/feb1f95e8cec48bb8ba35181cb66f94f23b1b6fc/README.md |
| R2 | native | 0.95 | 0.95 | 0.9 | 0.81 | https://raw.githubusercontent.com/oil-oil/oil-ui/feb1f95e8cec48bb8ba35181cb66f94f23b1b6fc/README.md |
| R3 | adapted | 0.9 | 0.9 | 0.95 | 0.77 | https://raw.githubusercontent.com/oil-oil/oil-ui/feb1f95e8cec48bb8ba35181cb66f94f23b1b6fc/README.md |
| R4 | native | 0.95 | 0.95 | 0.95 | 0.86 | https://raw.githubusercontent.com/oil-oil/oil-ui/feb1f95e8cec48bb8ba35181cb66f94f23b1b6fc/README.md |
| R5 | native | 0.95 | 0.95 | 0.95 | 0.86 | https://raw.githubusercontent.com/oil-oil/oil-ui/feb1f95e8cec48bb8ba35181cb66f94f23b1b6fc/README.md |
| R6 | native | 0.85 | 0.85 | 0.9 | 0.65 | https://raw.githubusercontent.com/oil-oil/oil-ui/feb1f95e8cec48bb8ba35181cb66f94f23b1b6fc/README.md |

### 依据
- 关键需求存在部分缺口但 E=58<=E_MID -> B

## 候选 superdesign · Superdesign skill (f9f05cd988c247dce6c072eaf9ac6b162f2ffc4b)

- **推荐分类**: `D`
- 关键需求覆盖率: 25% · 平均有效拟合度: 0.72 · 总所有权成本 E: 108

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 0.9 | 0.90 | https://raw.githubusercontent.com/superdesigndev/superdesign-skill/f9f05cd988c247dce6c072eaf9ac6b162f2ffc4b/README.md |
| R2 | native | 1.0 | 0.95 | 0.9 | 0.85 | https://raw.githubusercontent.com/superdesigndev/superdesign-skill/f9f05cd988c247dce6c072eaf9ac6b162f2ffc4b/README.md |
| R3 | adapted | 0.8 | 0.8 | 0.85 | 0.54 | https://raw.githubusercontent.com/superdesigndev/superdesign-skill/f9f05cd988c247dce6c072eaf9ac6b162f2ffc4b/README.md |
| R4 | adapted | 0.75 | 0.8 | 0.8 | 0.48 | https://raw.githubusercontent.com/superdesigndev/superdesign-skill/f9f05cd988c247dce6c072eaf9ac6b162f2ffc4b/README.md |
| R5 | native | 0.95 | 0.95 | 0.9 | 0.81 | https://raw.githubusercontent.com/superdesigndev/superdesign-skill/f9f05cd988c247dce6c072eaf9ac6b162f2ffc4b/README.md |
| R6 | native | 0.95 | 0.9 | 0.85 | 0.73 | https://raw.githubusercontent.com/superdesigndev/superdesign-skill/f9f05cd988c247dce6c072eaf9ac6b162f2ffc4b/README.md |

### 依据
- 关键需求 R4 有效拟合度=0.48<0.5 -> 继续搜索(D)

## 候选 storybook · Storybook (064c650498ad8411c74984ee3188a64be8bd0f20)

- **推荐分类**: `C`
- 关键需求覆盖率: 25% · 平均有效拟合度: 0.83 · 总所有权成本 E: 91

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | native | 1.0 | 1.0 | 0.95 | 0.95 | https://raw.githubusercontent.com/storybookjs/storybook/064c650498ad8411c74984ee3188a64be8bd0f20/README.md |
| R2 | native | 0.95 | 0.95 | 0.95 | 0.86 | https://raw.githubusercontent.com/storybookjs/storybook/064c650498ad8411c74984ee3188a64be8bd0f20/README.md |
| R3 | adapted | 0.95 | 0.95 | 0.9 | 0.81 | https://raw.githubusercontent.com/storybookjs/storybook/064c650498ad8411c74984ee3188a64be8bd0f20/README.md |
| R4 | native | 0.95 | 0.95 | 0.9 | 0.81 | https://raw.githubusercontent.com/storybookjs/storybook/064c650498ad8411c74984ee3188a64be8bd0f20/README.md |
| R5 | native | 0.9 | 0.85 | 0.9 | 0.69 | https://raw.githubusercontent.com/storybookjs/storybook/064c650498ad8411c74984ee3188a64be8bd0f20/README.md |
| R6 | native | 0.95 | 0.95 | 0.95 | 0.86 | https://raw.githubusercontent.com/storybookjs/storybook/064c650498ad8411c74984ee3188a64be8bd0f20/README.md |

### 依据
- 关键需求缺口且 E=91>E_MID -> C

## 候选 figma-guide · Figma MCP server guide (f2789420e7e8b4e2465dfeb1e12e1fc6a31397e5)

- **推荐分类**: `D`
- 关键需求覆盖率: 0% · 平均有效拟合度: 0.55 · 总所有权成本 E: 130

### R × O 证据矩阵

| 需求 | 状态 | 覆盖 | 语义 | 组合 | 有效拟合 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | adapted | 0.8 | 0.85 | 0.8 | 0.54 | https://raw.githubusercontent.com/figma/mcp-server-guide/f2789420e7e8b4e2465dfeb1e12e1fc6a31397e5/README.md |
| R2 | adapted | 0.85 | 0.9 | 0.85 | 0.65 | https://raw.githubusercontent.com/figma/mcp-server-guide/f2789420e7e8b4e2465dfeb1e12e1fc6a31397e5/README.md |
| R3 | adapted | 0.7 | 0.75 | 0.75 | 0.39 | https://raw.githubusercontent.com/figma/mcp-server-guide/f2789420e7e8b4e2465dfeb1e12e1fc6a31397e5/README.md |
| R4 | adapted | 0.65 | 0.7 | 0.7 | 0.32 | https://raw.githubusercontent.com/figma/mcp-server-guide/f2789420e7e8b4e2465dfeb1e12e1fc6a31397e5/README.md |
| R5 | native | 0.9 | 0.9 | 0.85 | 0.69 | https://raw.githubusercontent.com/figma/mcp-server-guide/f2789420e7e8b4e2465dfeb1e12e1fc6a31397e5/README.md |
| R6 | native | 0.95 | 0.9 | 0.85 | 0.73 | https://raw.githubusercontent.com/figma/mcp-server-guide/f2789420e7e8b4e2465dfeb1e12e1fc6a31397e5/README.md |

### 依据
- 关键需求 R3 有效拟合度=0.39<0.5 -> 继续搜索(D)
- 关键需求 R4 有效拟合度=0.32<0.5 -> 继续搜索(D)

## 最终拍板 (Agent，待 sealed ledger 重跑确认)

- 选定组合 C 与能力缺口 G: 由 ZAgentic 自有核心持有 `ui-brief/v1`、`UI-DESIGN.md`、`ui-flow/v1`、选择/审查记录、验证 receipt；以 `taste`/`oil-ui`/`uupm`/`emil-skills` 的方法或 B1 adapter 补足视觉和动效；以 `a2ui`/`json-render`/`m3e-canvas`/`storybook` 作为按项目启用的 B1 adapter；`superdesign` 和 `figma-guide` 暂不进入核心路径。G 是没有候选覆盖的统一编排、artifact SSOT、跨阶段证据链、权限/退出和全生命周期 release gate。
- 自有责任 E 及成本估计: 核心自有架构与 15 个核心/adapter skill 预计首轮 8–12 人周；持续责任包括 schema 兼容、skill discovery/README 注册、浏览器验证运行时、截图与证据保留、外部版本重评、许可证和素材 provenance。脚本单候选 E 仅用于相对排序，不可视为实际人周。
- PoC 结论: 先做单一 React/Next.js 项目的“自然语言 brief → 三个方向比较 → 用户选一个 → `UI-DESIGN.md` + `ui-flow/v1` → 一个表单/审批流实现 → Storybook/browser/a11y/break 验证”垂直切片；在此切片上分别试跑 json-render 与 A2UI，并用 M3E 导入/导出一套两屏移动 flow。没有完成这三个对照，不进入长期 adapter 维护。
- 最终分类 (A/B1/B2/B3/C/D): `C`（自有架构为主体）+ 外部 unit capability 采用 `B1`（adapter/plugin，不维护 fork）；`superdesign` 与 `figma-guide` 在当前证据下保持 `D`/继续搜索或仅作外部 connector 候选。该拍板解释了脚本对若干候选给出 `B` 的原因：它们可复用，但不能单独承担本目标的关键闭环。
- 采用理由: 外部项目的强项高度互补且职责正交：Taste/Oil/UUPM 解决方向与审美，Emil 解决动效/原型/极端数据，A2UI/json-render 解决受约束的声明式 UI，M3E 解决非专家的结构化输入，Storybook 解决组件验证；没有一个项目应拥有 ZAgentic 的阶段编排和产品语义。
- 主要风险: 外部项目版本/协议快速变化；远程 Figma/Superdesign 产生不可控服务依赖；不同 artifact 之间转换会丢失状态/意图；视觉截图会受浏览器/字体/网络影响；生成式 UI 的未注册组件、危险动作和数据泄露需要 catalog/approval/sandbox；素材许可和生成内容 provenance 不能靠 README 推断。
- 退出路径: 所有核心 artifact 为本地 Markdown/JSON，外部适配器只写可重建的缓存和转换结果；删除任一 adapter 后仍可通过对话和本地文档完成设计、实现和验证；若某 adapter 连续两个版本改变 schema、三次 PoC 无法达到阈值或维护 E 超过 80，则停用并回到自有 `ui-flow/v1`。
- 重新评估触发条件: A2UI v1 稳定发布；json-render catalog/spec 或 renderer 发生 breaking change；M3E/Figma 的导入导出格式改变；外部 skill 许可证/数据边界改变；浏览器验证在 CI 中不稳定；首个真实项目的用户选择耗时、返工率或验证通过率未达到 `solution-blueprint.md` 的 graduation criteria。

**完成标准自检**: 是（本记录可复核固定版本、R×O 矩阵、脚本闸门、E、缺口、PoC、采用/退出与重评条件）；但正式技术报告仍否，因为本轮 sealed ledger 未生成，当前证据 URL 尚未转换为 sealed Evidence ID，且脚本成本是相对估计而非实测人周。
