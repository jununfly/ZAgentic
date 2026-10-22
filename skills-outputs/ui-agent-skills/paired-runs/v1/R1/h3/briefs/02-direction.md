# UI-DESIGN.md — direction 段落（S3）

输入：briefs/01-brief.md。三张可比方向卡，字段对齐，便于横向比较。

| 维度 | card-a 「纸面文档」 | card-b 「工作台克制」 | card-c 「高密度控制台」 |
| --- | --- | --- | --- |
| 色彩 | 米白 #FBF8F2 + 墨 #1F1B16 + 赭 #8A5A00 | 白 #FFFFFF + 墨 #0F172A + 蓝 #2F4BD8 | 深灰 #111318 + 青 #22D3EE |
| 字体 | 衬线标题 + 无衬线正文 | 单一无衬线（系统栈），字号 13/15/20/28 | 等宽数字 + 无衬线标签 |
| 密度 | 松（行高 1.9，卡片留白大） | 中（行高 1.6，表单单列 640px） | 高（行高 1.35，多列网格） |
| 动效 | 200ms 淡入 | 120ms 位移+透明度，reduced-motion 全关 | 60ms 闪变 |
| 适用 | 阅读型长文 | 表单与审批这类"逐项确认"任务 | 监控大屏 |
| 取舍 | 亲和但确认动作不显眼 | 确认动作层级清楚，代价是视觉偏素 | 信息密度高但误触风险大 |
| 参考来源 | 无外部素材（自研） | 无外部素材（自研） | 无外部素材（自研） |

## direction_choice
```json
{
  "choice": "card-b",
  "signed_by": "operator-h3",
  "signed": true,
  "reason": "两个页面的核心都是逐项确认与状态反馈，card-b 把 confirm / lock / error 三层状态放在同一视觉层级；card-a 的确认动作不够显眼，card-c 误触风险高。",
  "defaulted": false
}
```
不是按顺序取第一张：card-b 是显式选择，且未选 card-a。
license：三张卡均无外部素材，无 license 缺口，无 quarantine。
