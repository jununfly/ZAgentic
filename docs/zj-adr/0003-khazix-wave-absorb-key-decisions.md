# khazix-skills 吸收 wave: 4 个可重用元决策

khazix wave (6 节点 13 决策) 已闭环, 5 个 skill (zj-hv-analysis / zj-leader / zj-neat-freak / zj-aihot / zj-storage-analyzer) 全部 adopt 落库. 决策全量记录在 git 历史 (61a264f..84f7797) + 已删除的 `docs/plans/roadmap-khazix-wave.json` 中. 本 ADR 抽出 **4 个有跨 wave 可重用价值** 的元决策 — 当未来再从第三方 skill 仓吸收内容时, 这些决策点可作为判断依据.

抽出标准同 ADR 0002: (1) 决定未来工作方向, (2) 看似自明但实际是判断选择, (3) 未来读者会问"为什么这样".

## 决策 1 — Scope 纪律: 显式排除不并入的源 skill

**Wave 级决策** (用户在 scope 选择时显式排除).

6 个源 skill 只并入 5 个: `khazix-writer` (公众号写作风格) 被显式排除. 排除依据是 ADR 0002 决策 3 的互补元规则 — 与仓内现有 skill 无明确互补点 (受众/产物形态均不匹配), 而非质量原因.

**为什么显式排除而非默认全收**: wave 的默认引力是"来都来了". 显式排除 + 记录排除理由, 让"没收的"和"收的"一样可追溯, 未来想收时有判断起点, 不想收时不会被人反复提议.

## 决策 2 — 第三方品牌 skill 也统一 zj- 前缀, 授权条款随正文保留

**1-4 (zj-aihot) 命名决策**.

aihot 是第三方品牌 (aihot.virxact.com 匿名只读 API), 仍统一加 `zj-` 前缀 (name 字段改 `zj-aihot`, 其余逐字). MIT 许可覆盖指令文件; 数据用途的商用限制条款写在 skill 正文内, 随正文逐字保留. LICENSE / install.sh / manifest.sha256 全量随迁.

**为什么不保留原名**: 前缀的 value 在"仓内命名空间不碰撞 + invocation 路由一致" (见 ZJ-CONTEXT `zj- naming`). 为个别第三方破例会让前缀规则出现判断灰区; 品牌归属由正文内容自证, 不依赖目录名.

## 决策 3 — 附属文件全量随迁, 不裁剪

**Wave 级决策**.

adopt 的附属文件全量随迁, 包括 neat-freak 的 `evals/` (~80 fixture)、aihot 的 `install.sh` / `manifest.sha256` / `agents/openai.yaml`. 保持 skill 完整自含, 不做"看起来用不上"的删减.

**为什么不裁剪**: 裁剪判断本身就是预测"哪些用不上", 错判成本 (skill 缺件、eval 不可复跑、manifest 校验失败) 高于多占的目录体积. 已知代价: verbatim 原则下, 源仓的失配引用也随迁 (例: zj-hv-analysis 的 description 引用未并入的 khazix-writer / wechat-title, 保留原文不改).

## 决策 4 — unrelated(source) 配对形式 + 按域分桶

**5 个 skill-pair 一致的配对与归置决策**.

基线无同意图 skill 时, 配对形式记 `unrelated(source)`, 策略直接走 adopt (无冲突可消解). 桶归属按域判断: 方法论/工程治理 (hv-analysis, leader, neat-freak) → `engineering/`; 系统工具/资讯查询 (aihot, storage-analyzer) → `misc/`.

**为什么 unrelated 也要过配对流程**: 直接 cp 进仓会跳过两道判断 — (1) 与现有 skill 是否真的不同域 (zj-hv-analysis 与 zj-research 同域但方法/产物不同, 判定不合并; zj-leader 与 zj-to-spec 意图相近但受众不同), (2) 落在哪个桶. 配对记录 (roadmap decision 数组) 是这两道判断的留痕, 未来"为什么这两个没合并"可查.

## 写给未来

- 这 4 条是 khazix wave (首次纯第三方源、全 unrelated 配对) 验证过的, 下次吸收 wave 可直接引用.
- 与 ADR 0002 的关系: 0002 管"A↔B 对齐"的通用动词与流程, 本 ADR 管"第三方源吸收"的特化判断, 两者叠加使用.
