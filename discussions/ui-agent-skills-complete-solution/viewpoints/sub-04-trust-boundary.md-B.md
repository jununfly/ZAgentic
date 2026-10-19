# B 视角：把信任边界做成可交付的工程闸门

视角来源: 跨会话独立Agent

**观点 1**

- **发现**：原文 Q1（原文 L12）要求 catalog、intent、approval、sandbox 与 capability boundary 组成“最小信任链”，但当前成功判据只写到未注册 component/action 要阻断或进入 unknown（原文 L7），没有规定决策顺序、数据结构、负责人或完成口径。
- **影响**：实现者可能把 `catalog` 当文档、把 `approval` 当 UI 按钮，导致同一个动作在 CLI、MCP、Figma 写回和自动化路径上得到不同结论；这会让排期无法锁定，也无法证明“阻断”真的发生。按一个现有执行入口估算，补齐策略对象、统一拦截器和 6 个基础测试 fixture 约需 3–5 人日；若入口不收敛，后续每增加一个 adapter 还会重复 1–2 人日的安全接线成本。
- **建议**：先交付一个版本化 `capability-catalog` allowlist，条目至少包含 `id/version/kind(input|component|action)/owner/required_capabilities/risk_class`；所有执行请求先按 `catalog id + version` 查 allowlist，查不到即 `unknown` 且不可执行。随后将请求规范化为 `intent`（目标、参数摘要、来源、调用者、请求 hash），由策略引擎按 `capability boundary -> sandbox profile -> approval policy` 顺序判定；高风险动作的 approval 必须绑定请求 hash、操作者、理由、过期时间和允许次数。验收以“同一请求经过 CLI/MCP/Figma 三入口得到同一 decision record”为准；平台安全负责人维护 catalog，执行框架负责人维护拦截器，测试负责人维护 fixture。第一阶段只覆盖本地代码执行、MCP 调用和 Figma 写回，第二阶段再扩展其他 action，失败时回退为全量 deny，而不是绕过拦截器。

**观点 2**

- **发现**：原文 Q2（原文 L13）同时涉及凭据、远程写回、网络 URL 和敏感截图；成功判据明确要求代码执行、MCP、网络、Figma 写回和凭据使用都需要 approval/sandbox/来源记录，并且敏感截图默认不上传（原文 L7）。这已经是多个不同风险面的组合，但文档尚未给出默认拒绝矩阵或例外的审计字段。
- **影响**：如果只在“网络请求”这一层做一次确认，凭据可能被注入到 prompt、日志或截图，或在 sandbox 外完成 Figma 写回；网络 URL 的域名允许也不能自动推出 HTTP 方法、路径和数据分类都安全。最低实现需要 1 个策略矩阵、1 个凭据代理和 6 个失败 fixture，约 4–6 人日；最大的风险是兼容性，回退方案应是把能力降级为本地预览/导出，而不是静默放行。
- **建议**：采用默认拒绝矩阵：无 approval 的代码执行/MCP/Figma 写回/外网访问/凭据读取一律 deny；sandbox profile 显式记录文件读写根、进程白名单、网络开关、可访问 host/path/method 和时间窗。凭据只允许通过短时、最小权限的 credential broker 取得，禁止进入 prompt、产物、日志和截图，审计只存引用 ID、调用者、用途和结果摘要。网络例外使用精确 host/path/method allowlist，并把响应数据分类为 public/internal/sensitive；敏感截图默认只本地保存，若确需上传，必须先脱敏、二次 approval、记录目标 URL、文件 hash 和 retention。必须加入可运行的失败 fixture：未知 action、缺 approval 的 MCP、sandbox 外写文件、未 allowlist 的 URL、无 credential scope、含 token 的日志/截图上传、未授权 Figma write-back；每个 fixture 都断言 `deny/unknown + reason_code + decision_record`，而不是只断言抛异常。

**观点 3**

- **发现**：原文 Q3（原文 L14）要求为素材、生成内容和开源依赖记录 license、credit、source、replacement 和责任人；成功判据还要求未知许可证素材不进入默认产物（原文 L7）。但当前没有定义 provenance 的单一载体，也没有说明生成内容与依赖如何被绑定到最终 UI 产物。
- **影响**：仅在 README 中人工记 credit 会在替换素材、重新生成或打包时丢失，最终无法回答“谁从哪里拿到、依据什么许可、出了问题谁负责”。一条漏记的未知许可证素材就可能污染默认交付；补做 manifest、构建校验和迁移已有素材约 3–5 人日，后续每个资产增加少量元数据成本，却能显著降低追责和替换成本。
- **建议**：把 `asset-manifest.json` 作为构建输入和产物索引，逐项记录 `asset_id/kind/sha256/source/source_url/retrieved_at/license/license_evidence/credit/transform/generator_or_dependency/version/replacement/owner/approval`；生成内容额外记录模型或工具、提示词 hash、生成时间和人工审核人，开源依赖绑定 lockfile 版本及许可证文件。`license=unknown` 或缺 `owner/source` 的条目进入 quarantine，不得被默认构建引用；允许例外时必须有责任人、到期日、替换项和 approval。构建器在打包前校验 manifest 与实际引用的 hash 一致，并输出可审计的 license/credit 清单。由素材负责人维护来源，法务或合规负责人维护许可证证据，构建负责人把校验设为必过门；验收 fixture 包括未知许可证素材、缺 source、缺 owner、替换后 hash 不一致和已登记生成素材，前四者必须阻断默认产物，最后一者必须能在 manifest 中追溯。

**观点 4**

- **发现**：原文成功判据已经要求“失败 fixture 能证明阻断”（原文 L7），而结论区仍是“待讨论”（原文 L65–73）；因此当前缺的不是更多原则，而是把三项 Q（原文 L12–14）排成可验收的交付路径。
- **影响**：没有明确的 done 定义，团队可能先接入远程服务或凭据，再补安全记录，形成不可逆的兼容性和审计债务。依赖顺序应是 catalog/schema → 决策拦截器 → credential/network/screenshot policy → asset manifest/build gate → adapter 接线；两名工程师加一名测试工程师约 2 个短迭代（约 8–12 人日），最关键风险是旧入口绕过统一拦截器。
- **建议**：以“最小可运行闭环”作为结项标准：每个请求产生 decision record；allowlist、intent、approval、sandbox、来源记录和 capability boundary 均可回放；默认 deny 的 7 类失败 fixture 全部通过；未知许可证资产无法进入默认构建；至少 CLI、MCP、Figma 三入口共享同一 policy evaluator。先在本地 dry-run 模式记录不放行的决策，确认误杀清单后再启用执行；若策略服务或 manifest 校验不可用，fail closed 并提供只读预览/本地导出回退。每次例外需有 owner、expiry、撤销方式和对应测试，避免“临时批准”成为永久旁路。
