# UI-DESIGN.md — User Profile Edit Form（EV-v0.1 · Wave 0 表单样例）

> 上游：`form/UI-BRIEF.md` · `revision: 8638ddaf1200f3d217098ed49ad2940cf4983c7a082f7094b25d1a0060eee53d`
> Owner：zj-ui-direction（S3，唯一写 owner）；本文件为 S3 选定方向后的 canonical 方向落点。
> 状态：draft / 本地 canonical，未进入 effect（生产代码归 1-8-4/1-8-5）。

## direction_choice（Human 选定，2026-10-21）
- **selected**: `card-a · Clean Minimal`
- 选定人：zj（Human gate 解除，原 WAIT_HUMAN → RESOLVED）
- 理由/provenance：`zagentic/ui-kit v0`（internal, license: proprietary）；选中依据 = 后台型个人资料编辑强调可读与信任，中性灰阶 + 系统字体 + comfortable 密度最贴合。无外部未授权引用，不触发 FF-DIR-03 quarantine。

## 选定方向约束（供 S4 token/catalog 与 S5 flow 消费）
- 色板：中性灰阶（#FFFFFF / #F7F8FA / #1F2933），主色 #2563EB，危险 #DC2626
- 字体：system-ui 栈；标题 600 / 正文 400
- 密度：comfortable（控件间距 16–24px，行高 1.6）
- 动效：仅焦点环 + 轻量淡入，无大位移
- 取舍已记录（见 design-collab.md §1 card-a）

## 关联 artifact
- 方向卡候选：`form/design-collab.md` §1（card-a/b/c 全列）
- token/catalog：`form/design-collab.md` §2（已对齐 card-a 中性色板）
- flow 六义：`form/ui-flow.v1.md`
