# Design Collaboration — User Profile Edit Form（EV-v0.1 · Wave 0 表单样例）

> 上游：`form/UI-BRIEF.md` · `revision: 8638ddaf1200f3d217098ed49ad2940cf4983c7a082f7094b25d1a0060eee53d`（S2 已锁定）
> 本文件 = S3 方向卡(非 canonical) + S4 token/catalog(draft) 的协作产物，**均 draft / 本地 canonical，未进入 effect**。
> 方向 choice 落 `UI-DESIGN.md` 需 Human 选定（WAIT_HUMAN），本节点不替人选、不默认取第一。

## 1. Direction Cards（S3 · zj-ui-direction，2–3 张可比候选）

每张卡含：色彩 / 字体 / 密度 / 动效 / 适用场景 / 取舍 / 参考来源(license)。

### card-a · Clean Minimal
- 色彩：中性灰阶背景（#FFFFFF / #F7F8FA），文本 #1F2933，主色 #2563EB，危险 #DC2626
- 字体：system-ui 系统字体栈；标题 600 / 正文 400
- 密度：comfortable（控件间距 16–24px，行高 1.6）
- 动效：仅焦点环 + 轻量淡入，无大位移
- 适用场景：后台型个人资料编辑，强调可读与信任
- 取舍：视觉存在感弱，品牌辨识度低
- 参考来源：`zagentic/ui-kit v0`（internal, license: proprietary）—— 无外部未授权引用，不触发 quarantine

### card-b · Structured Professional
- 色彩：白底 + 蓝色主色 #2563EB + 浅灰分隔 #E5E7EB；状态色复用主色/危险
- 字体：Inter（fallback system-ui）；标题 700、半粗引导
- 密度：compact（间距 12–16px，信息密度高）
- 动效：微交互（提交按钮 loading 态、字段校验抖动）
- 适用场景：企业工具，强调结构清晰与操作反馈
- 取舍：紧凑导致小屏略拥挤
- 参考来源：`zagentic/ui-kit v0`（internal, license: proprietary）

### card-c · Soft Friendly
- 色彩：暖白 #FFFDF9 + 柔和强调 #F59E0B + 圆角大色块
- 字体：rounded 字体栈（Nunito fallback system-ui）
- 密度：airy（大留白，间距 24–32px）
- 动效：弹性过渡、hover 抬升
- 适用场景：消费类产品，强调亲和力
- 取舍：专业感弱，密集表单效率低
- 参考来源：`zagentic/ui-kit v0`（internal, license: proprietary）

## 2. Token / Catalog（S4 · zj-ui-design-system draft）

| token | value | purpose | source / license |
| --- | --- | --- | --- |
| color.bg | #FFFFFF | 页面背景 | zagentic/ui-kit v0 / proprietary |
| color.surface | #F7F8FA | 卡片/输入容器 | zagentic/ui-kit v0 / proprietary |
| color.text | #1F2933 | 主文本 | zagentic/ui-kit v0 / proprietary |
| color.primary | #2563EB | 主操作/焦点 | zagentic/ui-kit v0 / proprietary |
| color.danger | #DC2626 | 错误/危险操作 | zagentic/ui-kit v0 / proprietary |
| font.family | system-ui stack | 正文字体 | zagentic/ui-kit v0 / proprietary |
| font.heading.weight | 600 | 标题字重 | zagentic/ui-kit v0 / proprietary |
| space.scale | 4 / 8 / 12 / 16 / 24 | 间距栅格 | zagentic/ui-kit v0 / proprietary |
| radius.base | 8px | 控件圆角 | zagentic/ui-kit v0 / proprietary |

> Provenance：全部 token 源自内部 `zagentic/ui-kit v0`，license=proprietary，无外部模板套用、无未知 license 引用（FF-DIR-03 不触发）。

## 3. Direction Choice（Human gate · RESOLVED，2026-10-21）

- 候选：card-a / card-b / card-c（并列，precedence 无法自动消解）
- **已选定**：`direction_choice = card-a · Clean Minimal`（zj 指定）
- 落点：`form/UI-DESIGN.md.direction_choice`（S3 唯一写 owner，已写入）
- human_gate：WAIT_HUMAN → RESOLVED

## 4. Provenance Summary（退出判据追踪）
- 方向选择候选 + gate：✅ 3 张卡可比、各自 license 已注、choice=card-a（RESOLVED，已落 UI-DESIGN.md）
- token/catalog：✅ 全表带 source/license
- flow/action/intent：见 `form/ui-flow.v1.md`
- 理由/provenance：✅ 内部来源统一标注，无 quarantine
