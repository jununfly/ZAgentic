# C 角色独立观点：用户价值与生态可采用性

视角来源: 跨会话独立Agent

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
