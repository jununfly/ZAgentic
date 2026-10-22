# UI-DIRECTION · 用户资料编辑表单

stage: S3 DIRECTION
reads: briefs/UI-BRIEF.md
human_gate: required

## 候选方向卡

### card-a · Calm Sheet

- 色彩：暖白 `#FBFAF8` 底，墨黑 `#1C1C1C` 文字，苔绿 `#2F6B4F` 主色
- 字体：系统无衬线，正文 16/1.6，标题 24/1.3
- 密度：宽松，字段间距 24，单列最大宽度 560
- 动效：180ms 淡入，无位移
- 适用：偏内容、低压力的个人设置
- 取舍：气质温和，但主色与错误色对比需要额外校准
- 来源 / license：in-house，自研，无外部资产

### card-b · Focused Console

- 色彩：纯白 `#FFFFFF` 底，墨黑 `#1A1A1A` 文字，电蓝 `#1F5EFF` 主色，错误红 `#B42318`
- 字体：系统无衬线，正文 15/1.55，字段标签 13/600
- 密度：紧凑清晰，字段间距 20，单列最大宽度 520
- 动效：120ms 状态过渡，遵守 reduced-motion
- 适用：表单密集、需要快速纠错的工具型界面
- 取舍：视觉冷静、反馈直接，但品牌个性较弱
- 来源 / license：in-house，自研，无外部资产

### card-c · Warm Card

- 色彩：浅米 `#F7F2EA` 底，卡片白，陶土 `#B4553A` 主色
- 字体：人文无衬线优先，回退系统字体
- 密度：中等，卡片内边距 28
- 动效：240ms 卡片抬升
- 适用：社区型产品的个人主页
- 取舍：亲和力强，但抬升动效对 reduced-motion 需额外降级
- 来源 / license：in-house，自研，无外部资产

## 选择记录（Human gate）

```json
{"selected":"card-b","signed_by":"user","signed":true,"reason":"表单纠错优先，需要最直接的校验与失败反馈"}
```

未签则 S4 不得开工；本记录为实签，故进入 design-system。

## 被丢弃项

- card-a / card-c 保留为候选，不进入默认产物；不按顺序默认取第一。
