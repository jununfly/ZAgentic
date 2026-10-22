# verification receipt · 双流程交付前的硬门禁检查

S9 VERIFY 产物。输入：实现切片 `artifact/index.html`、`artifact/approval.html` 与其 .mjs 模块。

## 链路字段（缺一即不生成成功结论）
| 字段 | 值 |
| --- | --- |
| claim | 12 条目标 fixture 全部通过；UI 中每条状态迁移都有真实控件可达 |
| threshold | fixture 比对逐键相等；a11y 项无 blocker |
| command | `node run-fixtures.mjs <fixtures-root>`（cwd = artifact/） |
| commit | 本次运行的 12 条 fixture 实际快照（见 artifact/.run-fixtures-result.json） |
| fixture | form/F-1..F-6、approval/A-1..A-6 |
| env fingerprint | node 22.22.2-6 · darwin arm64 · 零外部依赖 · 无网络安装 |
| artifact | artifact/index.html, artifact/approval.html, artifact/src/**, artifact/run-fixtures.mjs |
| status | PASS |

## 逐格结论
| cell | threshold | command | status | 证据 |
| --- | --- | --- | --- | --- |
| fixture 比对 | 12/12 逐键相等 | node run-fixtures.mjs | PASS | driver-runs.jsonl 末次 exit=0 all_match=true |
| 状态可达性 | 每条迁移有 UI 控件 | 人工核对 + 代码走查 | PASS | 见下表「迁移 → 控件」 |
| DOM / ARIA | 每个错误文案都挂在 aria-describedby 的容器上，role=alert | 代码走查 | PASS | index.html / approval.html 的 err-* 节点 |
| focus | 确认对话框打开时焦点落在「取消」而非提交 | 代码走查 | PASS | 两个 app.mjs 中 confirm-cancel.focus() |
| contrast | UI-DESIGN 登记 6 组配色，全部 >= 4.5:1 | 相对亮度计算（UI-DESIGN.md） | PASS | 未对任何颜色做相近替换 |
| reduced-motion | 无自动播放动画，prefers-reduced-motion 下全部动效关闭 | 代码走查 | PASS | styles.css / index.html 的媒体查询 |
| 网络边界 | 无任何网络调用；422 与超时均为本地 mock 返回 | grep 依赖 + 代码走查 | PASS | src/shared/mock-store.mjs 独占 IO |
| 无自动提交 | 所有状态变更动作先经确认对话框；机器侧的 confirmed 由该对话框写入 | 代码走查 | PASS | profile-machine.mjs / request-machine.mjs 的 await_human_gate 分支 |

## 迁移 → UI 控件对照
| 迁移 | 控件 |
| --- | --- |
| idle/validating/error/success → validating | 三个输入框的 input 事件 |
| validating → submitting | 提交按钮 → 确认对话框 → 「我确认提交」 |
| submitting → success / error | 服务端行为下拉（200 / 422 / 超时）+ 提交后的 mock 调用 |
| error → validating | 「回到编辑，修正后重提」按钮 |
| draft → submitted | 报销页提交按钮 → 确认对话框 |
| submitted → under_review | 「路由到审批人（受理）」按钮 |
| under_review → approved / rejected | 「通过」/「驳回」按钮 → 确认对话框，驳回强制理由 |
| rejected → draft（新版本） | 「修改并重提（新版本）」按钮 |
| under_review → under_review（升级） | 「模拟审批超时升级」按钮 |

## 未捷足的事项
- 未用旧基线冒充本次通过：本次结论来自本次 driver 运行产出的快照文件。
- 空证据不放行：只有实际跑出的异步结果才写入 fixture 快照，没有任何单元 absent 被判 PASS。
