# 子问题：生成 UI、动作、凭据与素材 provenance 的信任边界

## Agent viewpoints

### 视角：A（架构师 / 约束）

视角来源: 跨会话独立Agent

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

