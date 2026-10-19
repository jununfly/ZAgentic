# T 视角：测试 / 质量

视角来源: 跨会话独立Agent

## **观点 1**

**发现**：原文把“未注册 component/action 被阻断或进入 unknown”与 approval、sandbox、来源记录并列为成功判据（原文 L7），并把它们组合方式列为 Q1（原文 L12），但没有定义可判定的状态转移或绑定关系。若只做若干布尔开关，测试无法区分“已注册但意图不符”“批准过但权限已变更”和“未知能力”。

**影响**：信任链可能出现绕过：攻击者用已注册 component 触发未声明 action，或复用另一 intent 的 approval；并发请求还可能在审批前后各看到不同 catalog。结果会把“UI 看起来安全”误当成执行安全，无法用质量证据证明 Q1 已满足。

**建议**：把一次执行建模为可审计的拒绝默认状态机：`catalog allowlist(version/hash) -> intent(action + target + data class) -> capability boundary -> approval(token, scope, expiry, intent hash) -> sandbox(policy) -> execute -> provenance`。实现可自动化的 fixture：未注册 component、未注册 action、component/action 不匹配、空 intent、intent 字段超长或未知字段、过期/重复/跨 intent approval、catalog 版本漂移、两次并发执行。每个 fixture 断言“阻断或显式 unknown”、无副作用、审计事件包含决策点和 catalog/intent/approval/sandbox 标识；正例断言仅能调用 allowlist 中且与 intent 完全匹配的 capability。CI 应固定 catalog fixture hash，并重复运行并发用例，确保结果确定且 approval 不能 replay。

## **观点 2**

**发现**：原文明确要求代码执行、MCP、网络、Figma 写回和凭据使用都需要 approval/sandbox/来源记录，并要求敏感截图默认不上传（原文 L7）；Q2 又要求对凭据、远程写回、网络 URL、敏感截图提供“默认拒绝且可审计的例外”（原文 L13）。这些对象的失败面不同，但原文成功判据尚未拆成可观察断言。

**影响**：一条“已批准”可能被错误地当成全局许可：例如允许读取某个 API 的凭据却同时允许任意 URL 外传，或允许 Figma 读操作却放行写回；日志、MCP 返回值和截图也可能泄漏 secret。远程写回的失败还可能是部分成功，造成不可逆副作用和难以回归的 flaky 测试。

**建议**：为每类高风险 capability 建立独立 policy fixture 和审计字段：凭据使用只能取得短时、最小 scope 的引用，secret 不进入 prompt、日志、截图或 artifact；网络默认无 egress，仅允许 catalog 中的 scheme/host/path，重定向、DNS 变化和非 HTTPS 均重新判定；Figma/MCP 写回必须有目标、变更摘要、幂等键和一次性 approval，sandbox 失败或 approval 缺失时在网络调用前阻断。提供可复现的失败 fixture：无 approval、错误 scope、过期 token、任意 URL、恶意 redirect、敏感截图 upload、MCP/tool 未注册、Figma 写回中途断网、同一幂等键并发提交。验收断言包括：外部服务未收到请求（或收到可验证的 dry-run）、凭据值不出现在任何输出、截图被拒绝/脱敏、审计记录可关联 intent 与 policy 决策；对超时、空响应、重试和并发重复提交做回归测试。

## **观点 3**

**发现**：原文要求未知许可证素材不进入默认产物、并在 Q3 中要求记录 license、credit、source、replacement 和责任人（原文 L7、L14）；但没有定义“记录完成”的最小 schema，也没有说明生成内容、导入素材和开源依赖如何统一验证。

**影响**：同一资产可能在 UI 中被采用，却无法追溯来源、许可证或替换责任；缺少 manifest 的素材会在打包、截图或 Figma 写回时悄悄扩散。许可证字段为空、未知、互相冲突或来源 URL 失效时，若测试只检查字段存在，就会把无效 provenance 当成合规证据。

**建议**：将 `asset manifest` 设为产物门禁，至少包含 `asset_id`、类型（导入/生成/依赖）、内容 hash、source/原始 URL、license 标识与状态、credit、replacement、owner、引入时间、生成模型/提示词或依赖版本、允许的使用范围；manifest hash 随构建和写回记录。建立可执行规则：`license=unknown/missing`、source 缺失、hash 不匹配、owner/replacement 缺失时只能进入 quarantine/unknown，不得进入默认产物；生成资产也必须有 provenance，不能因“模型生成”跳过。测试覆盖空 manifest、字段类型错误、重复 asset_id、hash 改变、许可证冲突、失效 source、替换后旧引用、同一资产并发登记；正例验证 manifest 能从产物反查到 owner 和 source，负例验证默认构建、上传和写回均阻断并留下原因。

## **观点 4**

**发现**：原文的独立性边界是“什么可以生成、执行、上传或采用”，并要求“即使外部服务全部关闭，本地安全与版权边界仍可独立验证”（原文 L6）；成功判据还要求“失败 fixture 能证明阻断”（原文 L7）。这要求测试套件不能把远程 API、Figma 或网络可用性当作前置条件。

**影响**：如果测试依赖真实 MCP、网络或 Figma，断网时只能报环境失败，不能证明默认拒绝；如果只测 happy path，回归可能表现为“功能不可用”而不是“越界被阻断”。这会掩盖空输入、异常输入、极值、并发和部分失败下的安全退化。

**建议**：提交一组离线、版本固定的 failure fixtures 作为 CI 的最低门槛，并让 fixture 记录 `input -> expected decision -> side effects -> audit evidence`：catalog miss、intent/capability mismatch、无/过期/跨请求 approval、sandbox violation、credential leak、network/screenshot/Figma/MCP default deny、unknown license/missing manifest、外部服务关闭、超时/重试/部分写回和并发竞态。测试必须检查零副作用或明确 quarantine，而不只检查异常类型；为每个 fixture 提供可复现命令、固定时间/随机种子和预期审计事件。将正例、负例、边界和回归 fixture 纳入同一矩阵，任何 policy、catalog schema、manifest schema 或 adapter 变更都强制重跑，避免用人工截图或“测试通过”文字替代可回放证据。

## **观点 5**

**发现**：原文 Q1–Q3 同时涉及能力授权、外部副作用和 provenance（原文 L12-L14），但成功判据只给出了结果方向，没有规定失败后的可观测性、撤销性和验收分层（原文 L7）。质量上必须证明的不只是“被拒绝”，还包括拒绝发生在副作用之前、原因可解释且不会因重试变成允许。

**影响**：缺少统一事件链时，测试可能分别通过 catalog、审批和 manifest 的单测，却无法证明端到端链路没有跨层漏洞；拒绝后自动重试、降级到 unknown、缓存旧 approval 或恢复网络连接，都可能把安全策略变成时间相关的 flaky 行为。故障定位也无法区分用户未批准、策略拒绝、素材不合规和外部服务不可用。

**建议**：定义最小端到端验收契约：每次请求生成不可伪造的 execution id，并按顺序记录 catalog decision、intent hash、capability decision、approval decision、sandbox decision、provenance/manifest decision、external side-effect result；事件不得含 secret，且拒绝事件必须带稳定 error code。为每个 Q1/Q2/Q3 规则各保留至少一个正例和一个失败 fixture，断言决定顺序、零越界副作用、重试/并发下的幂等性、approval 撤销后的立即拒绝和 catalog/manifest 版本可回溯。把这套矩阵作为 release gate：单测验证 schema，属性/边界测试验证空异常极值，集成测试验证真实 side-effect adapter 被 mock/spy 到未调用，离线回放验证审计证据完整；任何失败先标为阻断性质量回归，不以人工批准或更新 fixture 规避。
