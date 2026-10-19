
 # 子问题：生成 UI、动作、凭据与素材 provenance 的信任边界

## 上下文

- **所属主文档：** [../MASTER.md](./MASTER.md)
- **本子问题独立性：** 聚焦“什么可以生成、执行、上传或采用”，不讨论视觉方向、skill 路由或 adapter 可用性；即使外部服务全部关闭，本地安全与版权边界仍可独立验证。
- **成功判据：** 未注册 component/action 被阻断或进入 unknown；代码执行、MCP、网络、Figma 写回和凭据使用需要 approval/sandbox/来源记录；未知许可证素材不进入默认产物；敏感截图默认不上传；失败 fixture 能证明阻断。
- **声明必需角色集：** B,C,A,T,S,L

## 待讨论问题（scope 草案）

- Q1：catalog、intent、approval、sandbox 和 capability boundary 如何组合成最小信任链？
- Q2：凭据、远程写回、网络 URL、敏感截图如何默认拒绝并提供可审计的例外？
- Q3：素材、生成内容和开源依赖如何记录 license、credit、source、replacement 和责任人？

## Agent viewpoints（独立视角 — 须跨会话独立 Agent）

### 视角：B（技术经理 / 可落地）
`视角来源: 跨会话独立Agent`



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

### 视角：C（产品专家 / 用户价值·生态竞品）
`视角来源: 跨会话独立Agent`



C 的产品判断：这不是把安全提示叠加到 UI agent 上，而是把“可放心采用的动作”做成产品能力。目标用户是需要让 agent 生成 UI、调用动作、接触素材或写回 Figma 的产品/设计/工程协作者；他们真实购买的不是更多自动化，而是可预期的结果、可撤销的副作用和能交接给组织的 provenance。优先级应按不可逆损害排序：凭据泄露、远程写回、敏感截图上传和版权不明资产是 P0；可恢复的本地生成体验优化才是 P1。

**观点 1**

- **发现**：原文 L6 将边界限定为“什么可以生成、执行、上传或采用”，原文 L7 要求未注册 component/action 被阻断或进入 `unknown`，并要求代码执行、MCP、网络、Figma 写回和凭据使用同时具备 approval、sandbox、来源记录；Q1（原文 L12）则明确要求 catalog、intent、approval、sandbox、capability boundary 组成最小信任链。当前 scope 还没有说明用户如何理解这条链，也没有定义“catalog 不认识”时的产品状态。
- **影响**：如果这些机制只是后台策略，用户会把安全拒绝误判为 agent 不稳定，转而使用更宽松的竞品或手工绕过；如果每一步都弹窗，又会使低风险生成不可用。可采用性取决于一次可读的执行预览，而不是安全名词数量。
- **建议**：将最小信任链落成一个可展示的 `execution_intent`：`catalog_id@version`、请求动作、输入/输出、所需 capability、风险级别、是否需要 approval、sandbox 配置、来源和 intent hash。catalog 只允许签名且版本固定的 component/action；未注册项不执行，进入 `unknown` 队列并显示原因。默认低风险本地生成走预批准 sandbox，高风险 capability 逐项批准；验收用三类用户路径：已注册低风险动作一键完成、未注册动作明确阻断、同一 intent hash 重放结果一致。相对“全自动黑箱”生态工具，这个预览/回执是可解释差异点；若用户仍无法在 10 秒内判断“会不会上传或写回”，该价值主张即被反例推翻。

**观点 2**

- **发现**：原文 L7 将代码执行、MCP、网络、Figma 写回和凭据使用并列为需要 approval/sandbox/来源记录的能力，Q2（原文 L13）还要求凭据、远程写回、网络 URL、敏感截图默认拒绝并提供可审计例外；但没有把用户同意的范围与 capability 绑定起来。
- **影响**：一次“允许”若可被后续动作复用，就会把用户对一次 Figma 写回误扩大成任意远程写入、把一个 URL 误扩大成任意网络访问，形成生态上最难解释的权限事故。相比设计工具常见的插件授权、CI 常见的 secret scope，agent 若没有动作级边界，组织用户会选择不接入凭据和远程能力，核心价值被削弱。
- **建议**：把 approval 设计为一次性的、可撤销的 capability token，而不是全局开关：`credential_ref` 只能指向不可导出的短时引用；网络只允许 exact host/path/method 的 allowlist，DNS/redirect 重新校验；Figma 写回必须列出目标文件、节点范围、变更摘要和幂等键；截图默认本地，先做敏感区域检测/遮罩，上传需单独批准并记录用途、目的地、保留期。每次例外生成审计回执（用户、intent hash、capability、时间、sandbox、来源、结果），并提供撤销。P0 失败 fixture 至少包括“无 token 访问凭据”“allowlist 外 URL”“redirect 到外站”“未批准的写回”“含敏感区域截图上传”；任一未产生网络/写回/凭据副作用才算通过。

**观点 3**

- **发现**：原文 L7 明确规定未知许可证素材不得进入默认产物，Q3（原文 L14）要求记录 license、credit、source、replacement 和责任人；原文 L6 又强调即使外部服务关闭，本地版权边界仍必须独立验证。当前没有定义生成内容、第三方素材、开源依赖和人工替换之间的统一交付格式。
- **影响**：没有统一 manifest，用户在 demo 阶段可能觉得“能生成”已经完成，但上线、交付客户或回滚时无法回答素材从何而来、能否商用、谁负责替换。生态上，素材库的 attribution 要求与开源依赖的 SBOM/许可证清单都要求可追溯；一个只记录最终 PNG 的 agent 无法与这些协作流程接轨。未知 license 默认放行会把低频但高代价的合规风险转嫁给最终用户。
- **建议**：每个产物携带不可缺省的 `asset_manifest`，逐项记录 `asset_id`、内容 hash、类型、source URL/仓库 commit、creator/provider、license SPDX 或 `unknown`、credit 文案、生成模型/版本（若适用）、prompt/transform 摘要、replacement、责任人和审核状态。`unknown` 或许可证冲突的资产进入 quarantine，不进入默认导出/写回；导出前显示缺口并支持用 manifest 中的 replacement 替换，替换后重新计算 hash 和 intent。将 manifest 作为 UI、Figma 写回和压缩包的同一 provenance 载体；验收 fixture 包括无 license、不可访问 source、要求 attribution 但缺 credit、替换后 hash 未更新四种情况。若用户能在交付前一眼看到“可用/待替换/责任人”，该机制才有相对手工整理清单的实际价值。

**观点 4**

- **发现**：原文成功判据（L7）要求“失败 fixture 能证明阻断”，并将敏感截图默认不上传、未知许可证素材不进默认产物、未注册 component/action 阻断或进入 `unknown` 写成可验证结果；但没有定义失败体验、回归集或用户可见的证据。
- **影响**：没有失败 fixture，团队只能演示 happy path，无法证明默认拒绝仍有效；一次策略变更就可能悄悄放开网络、凭据或资产入口。产品优先级也会失真：安全边界发生回归的代价远高于某个组件生成慢几百毫秒，因此应先锁定负向契约再优化体验。
- **建议**：建立版本化 `trust-boundary-fixtures/` 作为发布闸门，每个 fixture 包含输入 intent、catalog 版本、期望状态（`allow`/`approval_required`/`unknown`/`deny`/`quarantine`）、应出现的审计字段和“不得发生”的副作用；至少覆盖未注册 action、sandbox 外代码、无凭据 token、越界 URL/redirect、未批准 Figma 写回、敏感截图上传、未知 license、缺 source/credit、manifest hash 不一致。CI 用网络 mock、凭据 mock、Figma mock 和文件系统快照证明零副作用，UI 测试另验拒绝原因、修复入口和回执下载。发布门槛是所有 P0 fixture 通过，任何 capability 放宽必须新增 fixture；可证伪条件是任一失败用例能在无真实外部服务时仍证明副作用发生，此时不得宣称信任边界完成。

**覆盖判断**

- Q1（原文 L12）：观点 1 给出 catalog allowlist → intent hash → approval → sandbox → capability boundary 的用户可见信任链。
- Q2（原文 L13）：观点 2 给出凭据、网络、远程写回、截图的默认拒绝、最小例外和审计机制。
- Q3（原文 L14）：观点 3 给出 asset manifest、license/credit/source/replacement/owner 和 quarantine；观点 4 给出失败 fixture 作为可持续验证机制。
- 目标用户、采用理由、优先级、生态参照和可证伪性均已明确：产品价值是可预期、可撤销、可交付的 agent 动作；若预览不能让用户快速判断副作用，或 P0 fixture 能观察到未授权副作用，则该方案不具备可采用性。

### 视角：A（架构师 / 约束）
`视角来源: 跨会话独立Agent`





**观点 1**

- **发现：** 原文 ## 待讨论问题（scope 草案）Q1 与原文 L7 已经要求 catalog、intent、approval、sandbox、来源记录共同构成阻断条件，但尚未定义它们的先后关系、绑定对象和 fail-closed 规则。
- **影响：** 若只在 UI 层检查 catalog，调用方仍可能绕过 UI 直接执行 action；若 approval 不绑定具体 intent、catalog 版本和参数哈希，批准一次就可能被重放到另一动作。这样“未注册 action 被阻断”无法成为跨入口不变式，后续接入 MCP、代码执行或 Figma 写回时会出现策略漂移。
- **建议：** 固化一个版本化的 `CapabilityRequest` 信任链：`catalog allowlist(version, component/action, capability)` → `intent(action, target, params_digest, purpose)` → `policy decision` → `approval(request_digest, actor, scope, expiry)` → `sandbox lease(capabilities, egress, credential_refs)`。只有 allowlist 中的条目才能生成 intent；unknown 条目进入 `unknown` 并拒绝执行，不能自动降级或按名称猜测。执行器只接受由策略引擎签发且与 intent、catalog 版本、参数哈希一致的短时 lease，并把每次 decision/approval/lease 写入审计记录。

**观点 2**

- **发现：** 原文 L6 明确将本子问题限定为“什么可以生成、执行、上传或采用”，且要求即使外部服务关闭仍可独立验证；原文 Q1 还要求回答 capability boundary，但当前正文没有区分纯生成与副作用动作。
- **影响：** 把生成 UI、读本地素材、执行代码、网络请求、凭据读取和远程写回放在一个通用工具接口里，会使向后兼容变成隐式放权：旧调用只要能调用工具，就可能获得新 capability。外部适配器关闭时若仍允许“模拟成功”，会掩盖真实边界和审计缺口。
- **建议：** 将能力拆成稳定的 `plan`（纯数据、无副作用）与 `effect`（执行/上传/写回）两类接口；`effect` 必须携带由 catalog 声明的 capability 集合和 sandbox lease，缺少任一项即拒绝。旧 API 只能映射到最小只读 plan；新增 capability 必须新增 catalog 条目和显式 schema 版本，不能通过扩大旧枚举或“兼容默认值”放权。外部服务不可用时只允许返回可验证的 plan/blocked 状态，不返回假成功。

**观点 3**

- **发现：** 原文 Q2 与 L7 同时点名凭据、网络、MCP、Figma 写回和敏感截图，但没有规定默认拒绝的粒度、例外的生命周期，或截图与网络上传是否共享同一 provenance。
- **影响：** 仅弹一次“允许联网”会把域名、方法、数据范围和上传动作混成长期权限；环境变量中的全局凭据也会让 sandbox 失去最小权限边界。敏感截图一旦进入网络队列或日志，事后撤销无法消除泄露；Figma 写回若可重试而无幂等键，还可能产生重复远程副作用。
- **建议：** 以 capability token 分离 `credential.read(ref)`、`network.egress(host, method, data_class)`、`screenshot.capture(classification)`、`remote.write(target)`，默认全部 deny。例外必须由 intent 明确声明目标、数据分类、目的、期限和负责人，经 approval 后注入短时、单用途凭据引用；凭据值不得进入 prompt、manifest、日志或截图。网络经 egress proxy 执行 host allowlist 与数据分类检查，敏感截图默认只在本地保存并脱敏，上传需单独 approval；Figma 写回带 `request_digest/idempotency_key`、审计事件和可撤销/回滚状态。所有拒绝和例外均记录 policy version、reason、actor 与 timestamp。

**观点 4**

- **发现：** 原文 Q3 要求素材、生成内容和开源依赖记录 `license、credit、source、replacement、责任人`，而原文 L7 要求未知许可证素材不进入默认产物；这要求 provenance 成为产物装配的输入契约，而非交付后的备注。
- **影响：** 如果 manifest 可选或只记录 URL，复制、裁剪、模型生成、依赖升级和替换都会丢失责任链；“未知许可证”可能通过缓存、组合组件或默认占位图重新进入产物。不同生产路径各自定义字段还会使长期审计和自动替换不可演进。
- **建议：** 定义版本化 `asset-manifest.json`，每个 asset/dependency 至少包含稳定 `asset_id`、类型、内容哈希、source/provider、license/SPDX 或 `unknown`、credit、replacement、owner、生成模型/提示词（如适用）、限制、审批事件和父产物引用；manifest 本身随产物签名并纳入构建输入。装配器只接受 `approved` 或明确 `generated` 且 provenance 完整的条目；`unknown` 自动 quarantine，不进入默认产物。旧 manifest 缺字段只能经过显式迁移或人工责任人补录，不能以默认许可补齐；替换必须保留旧 asset_id、原因和时间线。

**观点 5**

- **发现：** 原文 L7 已给出可观察的成功判据（未注册 component/action 阻断、代码/MCP/网络/Figma/凭据需 approval/sandbox/来源记录、未知许可证与敏感截图默认拒绝），并明确要求“失败 fixture 能证明阻断”；原文 L12-L14 又分别提出 Q1-Q3 的信任链、例外和 provenance 问题。
- **影响：** 没有跨入口失败 fixture，策略可能只在 happy path 生效；尤其无法发现 catalog 漏洞、approval 与参数脱钩、sandbox capability 超范围、秘密泄漏到日志、敏感截图上传和 unknown license 穿透装配器。随着 schema 或 policy 版本升级，旧 fixture 失效后还可能造成静默放宽。
- **建议：** 建立版本化 deny-first fixture 套件并纳入 CI/发布闸门：`unregistered_component`、`unknown_action`、`missing_intent`、`approval_digest_mismatch/expired`、`sandbox_capability_escalation`、`credential_in_prompt_or_log`、`network_host_not_allowlisted`、`sensitive_screenshot_upload_without_approval`、`remote_write_without_idempotency`、`unknown_license_asset_in_default_output`、`manifest_missing_owner/source`。每个 fixture 断言“无副作用、返回明确 deny/unknown、写入最小审计事件”；再用一组最小 allow fixture 证明合法链路。fixture 绑定 catalog/policy/manifest schema 版本，策略变更必须更新预期并做兼容性回归。

**观点 6**

- **发现：** 原文 L6 要求安全与版权边界可在外部服务关闭时独立验证，原文 L70-L72 预留 PRD/ADR、跨子文档约束和临时脚手架清理，但当前结论仍为“待讨论”，尚未指定唯一契约归属。
- **影响：** 若 catalog、policy、asset manifest 和审计格式分别散落在 UI、skill、adapter 文档中，新增组件或 provider 会复制规则并产生冲突；外部服务恢复、schema 演进或迁移旧产物时，系统可能出现“本地检查通过、远程执行不守约”的双重事实源。
- **建议：** 在 ADR 中指定四个稳定边界：catalog registry 是能力声明唯一来源，policy engine 是 allow/deny 唯一来源，executor 是 lease 校验唯一入口，asset manifest 是产物 provenance 唯一来源；adapter 只能申请已声明 capability，不能自行扩权。为四类契约定义版本、向后兼容策略和迁移命令，并提供 offline policy/effect simulator，使无网络、无凭据、无 Figma 服务时仍能运行上述失败 fixture。将这些约束登记到跨子文档接口清单，避免后续 skill 路由或 adapter 生命周期引入隐式旁路。

### 视角：T（测试 / 质量）
`视角来源: 跨会话独立Agent`



**观点 1**

**发现**：原文把“未注册 component/action 被阻断或进入 unknown”与 approval、sandbox、来源记录并列为成功判据（原文 L7），并把它们组合方式列为 Q1（原文 L12），但没有定义可判定的状态转移或绑定关系。若只做若干布尔开关，测试无法区分“已注册但意图不符”“批准过但权限已变更”和“未知能力”。

**影响**：信任链可能出现绕过：攻击者用已注册 component 触发未声明 action，或复用另一 intent 的 approval；并发请求还可能在审批前后各看到不同 catalog。结果会把“UI 看起来安全”误当成执行安全，无法用质量证据证明 Q1 已满足。

**建议**：把一次执行建模为可审计的拒绝默认状态机：`catalog allowlist(version/hash) -> intent(action + target + data class) -> capability boundary -> approval(token, scope, expiry, intent hash) -> sandbox(policy) -> execute -> provenance`。实现可自动化的 fixture：未注册 component、未注册 action、component/action 不匹配、空 intent、intent 字段超长或未知字段、过期/重复/跨 intent approval、catalog 版本漂移、两次并发执行。每个 fixture 断言“阻断或显式 unknown”、无副作用、审计事件包含决策点和 catalog/intent/approval/sandbox 标识；正例断言仅能调用 allowlist 中且与 intent 完全匹配的 capability。CI 应固定 catalog fixture hash，并重复运行并发用例，确保结果确定且 approval 不能 replay。

**观点 2**

**发现**：原文明确要求代码执行、MCP、网络、Figma 写回和凭据使用都需要 approval/sandbox/来源记录，并要求敏感截图默认不上传（原文 L7）；Q2 又要求对凭据、远程写回、网络 URL、敏感截图提供“默认拒绝且可审计的例外”（原文 L13）。这些对象的失败面不同，但原文成功判据尚未拆成可观察断言。

**影响**：一条“已批准”可能被错误地当成全局许可：例如允许读取某个 API 的凭据却同时允许任意 URL 外传，或允许 Figma 读操作却放行写回；日志、MCP 返回值和截图也可能泄漏 secret。远程写回的失败还可能是部分成功，造成不可逆副作用和难以回归的 flaky 测试。

**建议**：为每类高风险 capability 建立独立 policy fixture 和审计字段：凭据使用只能取得短时、最小 scope 的引用，secret 不进入 prompt、日志、截图或 artifact；网络默认无 egress，仅允许 catalog 中的 scheme/host/path，重定向、DNS 变化和非 HTTPS 均重新判定；Figma/MCP 写回必须有目标、变更摘要、幂等键和一次性 approval，sandbox 失败或 approval 缺失时在网络调用前阻断。提供可复现的失败 fixture：无 approval、错误 scope、过期 token、任意 URL、恶意 redirect、敏感截图 upload、MCP/tool 未注册、Figma 写回中途断网、同一幂等键并发提交。验收断言包括：外部服务未收到请求（或收到可验证的 dry-run）、凭据值不出现在任何输出、截图被拒绝/脱敏、审计记录可关联 intent 与 policy 决策；对超时、空响应、重试和并发重复提交做回归测试。

**观点 3**

**发现**：原文要求未知许可证素材不进入默认产物、并在 Q3 中要求记录 license、credit、source、replacement 和责任人（原文 L7、L14）；但没有定义“记录完成”的最小 schema，也没有说明生成内容、导入素材和开源依赖如何统一验证。

**影响**：同一资产可能在 UI 中被采用，却无法追溯来源、许可证或替换责任；缺少 manifest 的素材会在打包、截图或 Figma 写回时悄悄扩散。许可证字段为空、未知、互相冲突或来源 URL 失效时，若测试只检查字段存在，就会把无效 provenance 当成合规证据。

**建议**：将 `asset manifest` 设为产物门禁，至少包含 `asset_id`、类型（导入/生成/依赖）、内容 hash、source/原始 URL、license 标识与状态、credit、replacement、owner、引入时间、生成模型/提示词或依赖版本、允许的使用范围；manifest hash 随构建和写回记录。建立可执行规则：`license=unknown/missing`、source 缺失、hash 不匹配、owner/replacement 缺失时只能进入 quarantine/unknown，不得进入默认产物；生成资产也必须有 provenance，不能因“模型生成”跳过。测试覆盖空 manifest、字段类型错误、重复 asset_id、hash 改变、许可证冲突、失效 source、替换后旧引用、同一资产并发登记；正例验证 manifest 能从产物反查到 owner 和 source，负例验证默认构建、上传和写回均阻断并留下原因。

**观点 4**

**发现**：原文的独立性边界是“什么可以生成、执行、上传或采用”，并要求“即使外部服务全部关闭，本地安全与版权边界仍可独立验证”（原文 L6）；成功判据还要求“失败 fixture 能证明阻断”（原文 L7）。这要求测试套件不能把远程 API、Figma 或网络可用性当作前置条件。

**影响**：如果测试依赖真实 MCP、网络或 Figma，断网时只能报环境失败，不能证明默认拒绝；如果只测 happy path，回归可能表现为“功能不可用”而不是“越界被阻断”。这会掩盖空输入、异常输入、极值、并发和部分失败下的安全退化。

**建议**：提交一组离线、版本固定的 failure fixtures 作为 CI 的最低门槛，并让 fixture 记录 `input -> expected decision -> side effects -> audit evidence`：catalog miss、intent/capability mismatch、无/过期/跨请求 approval、sandbox violation、credential leak、network/screenshot/Figma/MCP default deny、unknown license/missing manifest、外部服务关闭、超时/重试/部分写回和并发竞态。测试必须检查零副作用或明确 quarantine，而不只检查异常类型；为每个 fixture 提供可复现命令、固定时间/随机种子和预期审计事件。将正例、负例、边界和回归 fixture 纳入同一矩阵，任何 policy、catalog schema、manifest schema 或 adapter 变更都强制重跑，避免用人工截图或“测试通过”文字替代可回放证据。

**观点 5**

**发现**：原文 Q1–Q3 同时涉及能力授权、外部副作用和 provenance（原文 L12-L14），但成功判据只给出了结果方向，没有规定失败后的可观测性、撤销性和验收分层（原文 L7）。质量上必须证明的不只是“被拒绝”，还包括拒绝发生在副作用之前、原因可解释且不会因重试变成允许。

**影响**：缺少统一事件链时，测试可能分别通过 catalog、审批和 manifest 的单测，却无法证明端到端链路没有跨层漏洞；拒绝后自动重试、降级到 unknown、缓存旧 approval 或恢复网络连接，都可能把安全策略变成时间相关的 flaky 行为。故障定位也无法区分用户未批准、策略拒绝、素材不合规和外部服务不可用。

**建议**：定义最小端到端验收契约：每次请求生成不可伪造的 execution id，并按顺序记录 catalog decision、intent hash、capability decision、approval decision、sandbox decision、provenance/manifest decision、external side-effect result；事件不得含 secret，且拒绝事件必须带稳定 error code。为每个 Q1/Q2/Q3 规则各保留至少一个正例和一个失败 fixture，断言决定顺序、零越界副作用、重试/并发下的幂等性、approval 撤销后的立即拒绝和 catalog/manifest 版本可回溯。把这套矩阵作为 release gate：单测验证 schema，属性/边界测试验证空异常极值，集成测试验证真实 side-effect adapter 被 mock/spy 到未调用，离线回放验证审计证据完整；任何失败先标为阻断性质量回归，不以人工批准或更新 fixture 规避。

### 视角：S（安全 / 威胁建模）
`视角来源: 跨会话独立Agent`



**观点 1**

**发现**：原文成功判据要求未注册 component/action 被阻断或进入 `unknown`，并要求代码执行、MCP、网络、Figma 写回和凭据使用具备 approval、sandbox、来源记录（原文 L7）；Q1 又要求把 catalog、intent、approval、sandbox、capability boundary 组合成最小信任链（原文 L12）。当前没有声明这些检查的先后顺序、绑定对象或失效条件。

**影响**：攻击入口不只来自用户输入，也包括 skill 生成的 component/action、MCP 参数和网络目标；若 approval 只批准“意图”而不绑定 catalog 版本、具体 action、参数、目标、凭据范围和有效期，就会形成 confused-deputy，导致一个合法批准被改造成任意代码执行、远程写回或数据外传。sandbox 若没有明确 capability boundary，也不能证明它真的限制了文件、网络和凭据访问。

**建议**：把执行建模为不可跳过的状态机：`catalog 注册且版本固定 → intent 与 action/参数匹配 → capability boundary 计算 → 显式 approval（action、参数摘要、目标、凭据 scope、TTL）→ 最小 sandbox → 产生带 source/approval/sandbox 证据的结果`。任何未注册、`unknown`、intent 不匹配、审批过期/范围不符、sandbox 初始化失败或证据缺失都硬阻断；给出一个失败 fixture：未注册 action、已批准 action 被替换参数、审批过期和 sandbox 禁止能力各自必须得到非执行结果。

**观点 2**

**发现**：Q2 明确把凭据、远程写回、网络 URL、敏感截图列为默认拒绝并要求可审计例外（原文 L13）；成功判据还明确要求敏感截图默认不上传（原文 L7）。但原文尚未定义凭据从哪里取得、网络出口如何限制、截图如何分类，也没有给出例外的受益者、目的地和数据范围。

**影响**：这是可真实到达的泄露路径：恶意或被污染的 URL 可诱导网络请求，action/MCP 可把环境变量或凭据 broker 的结果带入外部调用，Figma 写回可把本地敏感内容持久化到第三方，截图则可能在像素中暴露 token、个人数据或内部 UI。只记录“调用过网络”不能证明没有泄露；一次未经授权的 egress 就足以破坏本地安全边界。

**建议**：凭据只能经短时、最小 scope 的 broker 按已批准 action 注入，禁止出现在 prompt、日志、截图和产物中；sandbox 默认无网络、无任意文件读取，URL 仅允许按协议/域名/路径/方法/响应大小建立 allowlist，远程写回必须单独 approval。截图先做敏感区域检测和脱敏，默认只保存在本地；例外审批必须记录操作者、目的、字段级范围、目的地、时间窗、撤销状态和脱敏结果。设置硬阻断阈值：未经该例外记录的凭据读取、网络 egress、Figma/远程写回或敏感截图上传任一发生，运行失败且不得生成成功产物；用“secret in DOM/环境变量、外部 URL、未批准 Figma 写回、含 token 的截图”四个失败 fixture 验证。

**观点 3**

**发现**：Q3 要求素材、生成内容和开源依赖记录 `license、credit、source、replacement、责任人`（原文 L14）；成功判据要求未知许可证素材不进入默认产物（原文 L7）。这同时覆盖输入素材、模型生成物、依赖包和最终导出物，但当前没有规定 provenance 是逐项记录还是仅在项目级记录，也没有规定许可证冲突时的决策。

**影响**：若 provenance 只在最终产物写一句来源，无法追溯一个组件中的单个图标、字体、依赖或生成图片，责任人也无法证明自己有再分发权。未知许可证、不可验证来源或互相冲突的 copyleft/商业限制会把默认产物变成不可发布或不可审计的交付物；生成内容也可能携带参考素材、第三方模型条款或用户输入的隐私风险。

**建议**：为每个输入/生成/依赖/导出项建立不可变 provenance manifest，至少包含稳定 ID、类型、hash、source URL 或仓库与版本、license/SPDX（未知则明确 `unknown`）、credit、replacement、责任人、引入时间和允许用途；生成内容额外记录生成工具/模型版本与是否使用受限输入。默认产物只允许 license 可验证且用途兼容的条目；`unknown`、缺 source/责任人、hash 不一致或许可证冲突必须阻断，保留替换候选并要求人工审批后才能例外采用。验收 fixture 应包含未知许可证图片、缺 credit 的字体、版本漂移依赖和许可证冲突依赖，均不得进入默认输出。

**观点 4**

**发现**：原文把“失败 fixture 能证明阻断”列为成功判据（原文 L7），但待讨论问题仅描述了策略层问题（原文 L10），当前子文档结论仍为“待讨论”，状态为 `NEEDS_CONTEXT`（原文 L67）。因此，威胁是否真实可达、缓解是否生效，还没有可重复的负向证据或发布闸门。

**影响**：没有负向 fixture 时，系统可能只在 happy path 中记录 catalog/approval/sandbox/provenance；一旦出现未知 action、参数混淆、sandbox 降级、凭据进入日志、敏感截图上传、未许可素材或远程写回，测试无法区分“被拒绝”与“悄悄完成”。这会把安全控制退化成文档承诺，且无法证明入口、出口和信任边界已完整覆盖。

**建议**：建立按入口—边界—出口组织的失败 fixture 矩阵，并把阻断设为发布前硬闸门：未注册/未知 action、intent 或 approval 不匹配、sandbox/capability boundary 失效、未批准凭据读取、非 allowlist 网络 URL、未批准远程写回、敏感截图上传、缺失或冲突 provenance 任一 fixture 失败即阻断，不得以 warning 或降级成功绕过。每次执行应输出可审计的拒绝原因、规则版本、输入摘要 hash 和“未执行/未上传/未写回”证据；只有全部负向 fixture 阻断、正向最小权限 fixture 成功、且无高危泄露事件时，才允许将状态从 `NEEDS_CONTEXT` 推进为可交付结论。

### 视角：L（法律 / 合规）
`视角来源: 跨会话独立Agent`



**观点 1**

- **发现**：原文成功判据要求“未注册 component/action 被阻断或进入 unknown”，并要求代码执行、MCP、网络、Figma 写回和凭据使用具备 approval、sandbox、来源记录（原文 L7）；Q1 又明确要求组合 catalog、intent、approval、sandbox 和 capability boundary（原文 L12）。当前文本没有定义谁可以批准、批准绑定哪些对象、批准多久有效，也没有定义 catalog 缺失或版本漂移时的法律状态。
- **影响**：如果 approval 只是一次泛化的“允许运行”，就无法证明用户同意的是特定 component/action、数据范围、目标环境和远程写回；越权执行可能构成未授权处理、违反服务条款或内部授权制度。catalog、intent、sandbox 任一缺失时继续执行，会把合规责任从系统闸门转嫁给最终用户。
- **建议**：为每次执行生成不可变授权记录：`catalog_id + component/action 版本 + intent 摘要 + 输入/输出数据分类 + capability 列表 + sandbox policy + 审批主体/时间/有效期/撤销状态 + provenance`。批准必须绑定这组内容，不能跨版本或跨目标复用；unknown、未注册、版本不匹配、能力超出 intent 或无 sandbox 时硬阻断。把“阻断”定义为默认法律状态，把人工例外定义为一次性、最小权限、可撤销且可审计的授权。

**观点 2**

- **发现**：Q2 直接把凭据、远程写回、网络 URL、敏感截图列为待决边界（原文 L13）；成功判据同时要求凭据使用、网络和 Figma 写回有 approval/sandbox/来源记录，并要求敏感截图默认不上传（原文 L7）。原文没有给出例外的允许条件，也没有区分秘密、个人信息、客户机密和普通素材。
- **影响**：原始凭据进入 prompt、日志、截图或第三方网络请求，可能造成秘密泄露、个人信息跨境传输、保密义务违约及供应商条款违约；未限定 URL 的外连还可能把用户输入或生成素材送入未审查的处理者。Figma 等远程写回若无目标、范围和回滚证据，可能形成未经授权的变更。仅记录“用户点过批准”不足以证明告知、目的限定和最小化。
- **建议**：建立四类默认拒绝策略：凭据只能由短时、最小权限、不可回显的 broker 注入，禁止出现在 prompt/日志/截图；网络仅允许已登记的域名/URL、目的、数据类别和地区，保存请求/响应摘要与来源，不在不明 URL 上自动跟随重定向；Figma 写回必须显示目标文件、变更 diff、操作者、审批、sandbox 和回滚点；含 PII、客户机密、令牌或内部界面的截图只在本地处理，例外须先分类、脱敏、限定接收方和保留期并重新审批。缺少任一条件即阻断，不以 warning 放行。

**观点 3**

- **发现**：Q3 要求素材、生成内容和开源依赖记录 `license、credit、source、replacement、责任人`（原文 L14）；成功判据明确要求未知许可证素材不得进入默认产物（原文 L7）。原文尚未规定许可证如何验证、依赖如何覆盖传递依赖、生成内容的输入权利如何记录。
- **影响**：把“找得到来源”误当成“有权使用”会漏掉商业使用限制、署名/NOTICE、copyleft 传染、模型或素材服务商的输出条款，以及第三方输入的隐私和版权风险。未知许可素材一旦进入默认产物，后续发布者很难证明已尽审查义务，可能触发下架、赔偿、源码提供或客户合同违约。
- **建议**：为每个素材/依赖建立 provenance manifest，至少包含唯一 ID、来源 URL 或仓库、固定版本/commit/hash、获取时间、许可证原文或 SPDX 标识、用途/地域/商业使用限制、credit/NOTICE 要求、是否修改、替换候选、责任人和审查状态；生成内容另记模型/服务版本、prompt 或输入摘要、输入素材许可、输出条款和人工审查人。对未知、冲突或无法验证的许可证进入 quarantine，不进入默认产物；对 copyleft、不可商用、署名义务或供应商条款不明的项进入人工法律审批，并在 SBOM/NOTICE 中可追溯。

**观点 4**

- **发现**：原文把“失败 fixture 能证明阻断”列为成功判据（原文 L7），但 Q1–Q3 仍标为 scope 草案（原文 L10-L14），结论与解法也尚待讨论（原文 L65-L73）；因此目前没有可复核的失败样例、阈值或例外审计格式。
- **影响**：没有负向测试就无法证明默认拒绝真的发生，也无法在事故、客户审计或许可争议中证明系统按政策执行。若把不确定性作为“可继续生成”，会出现合规漏放；若只阻断最终发布而允许中间产物带出敏感数据或受限素材，阻断点又来得太晚。
- **建议**：至少固化以下失败 fixture，并把“阻断”作为验收结果：未注册 action；catalog 版本与 intent 不匹配；代码/MCP 访问凭据但无 broker、approval 或 sandbox；访问未 allowlist 的 URL；Figma 写回无目标确认、diff 或 approval；含 PII/秘密的截图尝试上传；许可证缺失/unknown/冲突；依赖无固定版本或无法生成 provenance。机械阈值为：任一必需字段缺失、任一能力超出已批准 intent、任一来源/许可证状态为 unknown、任一敏感数据跨边界无显式例外，均不得执行、上传或进入默认产物；只能进入 quarantine/unknown 并要求指定责任人批准。每次失败保存规则 ID、输入分类、命中的能力、阻断时间、审批状态和修复/替换记录，作为审计证据。

## 主力AI 整合立场（主会话，非独立视角，低权重）

`视角来源: 同会话SubAgent(低权重)`

独立观点已通过 scope、架构和 UX 闸门。本题采用 deny-first 的本地信任链：catalog → intent → policy → approval → sandbox lease → executor → provenance；`plan` 与 `effect` 分离，外部服务关闭仍能离线验收。

1. 建立版本化 capability catalog，统一拦截 CLI/MCP/Figma/自动化入口。未注册 component/action 为 `unknown` 且不可执行；effect 必须携带 intent、参数摘要、policy decision、approval digest、sandbox lease 和幂等键，执行器是唯一副作用入口。

2. 凭据、网络、截图和远程写回默认 deny。例外按 capability token 精确限定 host/path/method、数据分类、文件根、进程、时间窗和最小 credential scope；secret 只通过短时 broker 引用，禁止进入 prompt、产物、日志和截图。敏感截图默认本地保存，上传需脱敏、二次 approval、hash/retention 审计。

3. `asset-manifest.json` 是素材/生成内容/开源依赖的 provenance SSOT，记录 asset hash、source、license/SPDX 或 unknown、credit、replacement、owner、生成模型/依赖版本、approval。unknown license/source/owner 缺失自动 quarantine，不进入默认产物；替换保留旧 asset_id 时间线。

4. 建立 offline deny-first fixture 与最小 allow fixture：未知组件/action、approval mismatch/expired、sandbox escalation、credential leak、未 allowlist URL、敏感截图上传、无幂等远程写回、unknown license 等均断言无副作用、稳定 reason code 和审计记录。policy/catalog/manifest 变更必须重跑，失败回退全量 deny 或本地预览/导出。

## Human 对 Agent X 的拍板

| 轮次 | 视角 | 隔离方式 | Human 拍板 | 是否 conclusion | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 | B | 同 provider 跨会话 | 待拍板 | 否 | |
| 2 | C | 同 provider 跨会话 | 待拍板 | 否 | |
| 3 | A | 同 provider 跨会话 | 待拍板 | 否 | |
| 4 | T | 同 provider 跨会话 | 待拍板 | 否 | |
| 5 | S | 同 provider 跨会话 | 待拍板 | 否 | |
| 6 | L | 同 provider 跨会话 | 待拍板 | 否 | |

## conclusion（含沉淀指令）

- **子问题结论：** 任何生成、执行、上传、写回或采用动作都必须经过统一的 deny-first trust chain；catalog、policy、executor 和 asset manifest 分别是能力声明、allow/deny、副作用入口和 provenance 的唯一事实源。
- **解法：** 将 plan/effect 分离，未注册能力进入 unknown；effect 以 intent digest、approval、sandbox lease、credential/network/screenshot token 和幂等键执行。资产以 manifest 绑定 hash/source/license/credit/replacement/owner，unknown 进入 quarantine。离线 failure fixture 必须证明未发生副作用和审计链完整。
- **remaining-risks 控制：** 生成式 UI 的安全语义、法律/许可证判断、远程条款和用户误批准不能由 schema 彻底消除；通过 Human approval、最小权限、脱敏、quarantine、fallback、短时凭据、审计和定期合规复核控制。任何策略或 catalog 不可用时 fail closed，不模拟成功。
- **沉淀指令：**
  - 改哪些 PRD / ADR / 文档：新增 Trust Boundary/Capability Policy ADR、asset provenance schema、credential/network/screenshot policy 和 offline fixture catalog。
  - 跨子文档约束登记：`sub-01` 定义 provenance/receipt 的 artifact owner；`sub-02` 不得绕过 executor；`sub-03` adapter 只能申请既有 capability；`sub-05` 的 verification receipt 需承接 decision/audit 证据。
  - 待删临时脚手架：本子文档 briefings 和 viewpoints 过程文件，待 `zj-docs-ontology` 分类；Human 确认前保留讨论目录。
- **状态协议：** DONE_WITH_CONCERNS

