# S 视角：安全 / 威胁建模

视角来源: 跨会话独立Agent

## 观点 1

**发现**：原文成功判据要求未注册 component/action 被阻断或进入 `unknown`，并要求代码执行、MCP、网络、Figma 写回和凭据使用具备 approval、sandbox、来源记录（原文 L7）；Q1 又要求把 catalog、intent、approval、sandbox、capability boundary 组合成最小信任链（原文 L12）。当前没有声明这些检查的先后顺序、绑定对象或失效条件。

**影响**：攻击入口不只来自用户输入，也包括 skill 生成的 component/action、MCP 参数和网络目标；若 approval 只批准“意图”而不绑定 catalog 版本、具体 action、参数、目标、凭据范围和有效期，就会形成 confused-deputy，导致一个合法批准被改造成任意代码执行、远程写回或数据外传。sandbox 若没有明确 capability boundary，也不能证明它真的限制了文件、网络和凭据访问。

**建议**：把执行建模为不可跳过的状态机：`catalog 注册且版本固定 → intent 与 action/参数匹配 → capability boundary 计算 → 显式 approval（action、参数摘要、目标、凭据 scope、TTL）→ 最小 sandbox → 产生带 source/approval/sandbox 证据的结果`。任何未注册、`unknown`、intent 不匹配、审批过期/范围不符、sandbox 初始化失败或证据缺失都硬阻断；给出一个失败 fixture：未注册 action、已批准 action 被替换参数、审批过期和 sandbox 禁止能力各自必须得到非执行结果。

## 观点 2

**发现**：Q2 明确把凭据、远程写回、网络 URL、敏感截图列为默认拒绝并要求可审计例外（原文 L13）；成功判据还明确要求敏感截图默认不上传（原文 L7）。但原文尚未定义凭据从哪里取得、网络出口如何限制、截图如何分类，也没有给出例外的受益者、目的地和数据范围。

**影响**：这是可真实到达的泄露路径：恶意或被污染的 URL 可诱导网络请求，action/MCP 可把环境变量或凭据 broker 的结果带入外部调用，Figma 写回可把本地敏感内容持久化到第三方，截图则可能在像素中暴露 token、个人数据或内部 UI。只记录“调用过网络”不能证明没有泄露；一次未经授权的 egress 就足以破坏本地安全边界。

**建议**：凭据只能经短时、最小 scope 的 broker 按已批准 action 注入，禁止出现在 prompt、日志、截图和产物中；sandbox 默认无网络、无任意文件读取，URL 仅允许按协议/域名/路径/方法/响应大小建立 allowlist，远程写回必须单独 approval。截图先做敏感区域检测和脱敏，默认只保存在本地；例外审批必须记录操作者、目的、字段级范围、目的地、时间窗、撤销状态和脱敏结果。设置硬阻断阈值：未经该例外记录的凭据读取、网络 egress、Figma/远程写回或敏感截图上传任一发生，运行失败且不得生成成功产物；用“secret in DOM/环境变量、外部 URL、未批准 Figma 写回、含 token 的截图”四个失败 fixture 验证。

## 观点 3

**发现**：Q3 要求素材、生成内容和开源依赖记录 `license、credit、source、replacement、责任人`（原文 L14）；成功判据要求未知许可证素材不进入默认产物（原文 L7）。这同时覆盖输入素材、模型生成物、依赖包和最终导出物，但当前没有规定 provenance 是逐项记录还是仅在项目级记录，也没有规定许可证冲突时的决策。

**影响**：若 provenance 只在最终产物写一句来源，无法追溯一个组件中的单个图标、字体、依赖或生成图片，责任人也无法证明自己有再分发权。未知许可证、不可验证来源或互相冲突的 copyleft/商业限制会把默认产物变成不可发布或不可审计的交付物；生成内容也可能携带参考素材、第三方模型条款或用户输入的隐私风险。

**建议**：为每个输入/生成/依赖/导出项建立不可变 provenance manifest，至少包含稳定 ID、类型、hash、source URL 或仓库与版本、license/SPDX（未知则明确 `unknown`）、credit、replacement、责任人、引入时间和允许用途；生成内容额外记录生成工具/模型版本与是否使用受限输入。默认产物只允许 license 可验证且用途兼容的条目；`unknown`、缺 source/责任人、hash 不一致或许可证冲突必须阻断，保留替换候选并要求人工审批后才能例外采用。验收 fixture 应包含未知许可证图片、缺 credit 的字体、版本漂移依赖和许可证冲突依赖，均不得进入默认输出。

## 观点 4

**发现**：原文把“失败 fixture 能证明阻断”列为成功判据（原文 L7），但待讨论问题仅描述了策略层问题（原文 L10），当前子文档结论仍为“待讨论”，状态为 `NEEDS_CONTEXT`（原文 L67）。因此，威胁是否真实可达、缓解是否生效，还没有可重复的负向证据或发布闸门。

**影响**：没有负向 fixture 时，系统可能只在 happy path 中记录 catalog/approval/sandbox/provenance；一旦出现未知 action、参数混淆、sandbox 降级、凭据进入日志、敏感截图上传、未许可素材或远程写回，测试无法区分“被拒绝”与“悄悄完成”。这会把安全控制退化成文档承诺，且无法证明入口、出口和信任边界已完整覆盖。

**建议**：建立按入口—边界—出口组织的失败 fixture 矩阵，并把阻断设为发布前硬闸门：未注册/未知 action、intent 或 approval 不匹配、sandbox/capability boundary 失效、未批准凭据读取、非 allowlist 网络 URL、未批准远程写回、敏感截图上传、缺失或冲突 provenance 任一 fixture 失败即阻断，不得以 warning 或降级成功绕过。每次执行应输出可审计的拒绝原因、规则版本、输入摘要 hash 和“未执行/未上传/未写回”证据；只有全部负向 fixture 阻断、正向最小权限 fixture 成功、且无高危泄露事件时，才允许将状态从 `NEEDS_CONTEXT` 推进为可交付结论。
