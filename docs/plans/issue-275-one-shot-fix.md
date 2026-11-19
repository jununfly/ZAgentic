# Issue #275 一步到位修复方案（草案）

> 状态：draft，未跟踪，等 zj 确认后再走分支+PR。
> 关联：issue #275（zj-docs-ontology 作用对象模型错位 + 三处实现缺陷）。
> 本方案**不延续 legacy 判例的条条框框**：凡与修复目标冲突的既有裁决/断言/命名惯例，一律列入「Legacy 冲突与待改进项」一并处理，不为兼容旧口径而打折。

## 0. 一句话结论

把 zj-docs-ontology / zj-docs-architecture 从「路径子串 + CWD 相对 + 隐式边界」改成「**显式声明 + 单一解析基准 + 证据可注入**」，一次改掉 3 个实现缺陷、2 个 design 缺口，并同步修订 8 处与之冲突的 legacy 约定。全部修复以设计原则 4 为北极星：产物不止是过门禁的绿报告，而是让 docs system 向「**可导航、可推理、Human & AI readiness 的知识网络**」演进——map 即 ontology 声明面，报告即图快照来源。

## 1. 设计原则（替代 legacy 判例）

1. **一切影响验收判定的事实必须显式声明**：作用对象、页面角色、moves、witness 路径——不靠路径子串、CWD、prompt 措辞推断。
2. **单一真相源 + 单一解析基准**：同一事实不允许两个声明来源（沿 #264 的既有原则），同一路径不允许两个解析基准（本方案新增）。
3. **信号与错误分级固定**：机械可判 = ERROR；需 Human 确认 = pending + signal，escalation 决策权交给 consumer（CI/step-gate）——与 #264 platform-layer C 同一模式。**Carve-out（反向核查裁决 ②，2026-11-19）**：分级细分为两类——**声明失真 / 体系冲突类**（显式声明与事实不符，如悬边；或事实冲击体系完整性，如无任何证据的文件消失）= ERROR；**声明缺失类**（应声明而未声明、且不与任何事实冲突，如无 role、孤儿页）= signal + 一次性补声明提示。缺失是"待补信息"不是"错误事实"，与 Fix 3 pending_moves 同构；`UNDECLARED_RETIREMENT` 属冲突类，ERROR 不变。
4. **ontology × 知识图谱组合驱动持续治理**：把 docs system 持续维护成一张可导航、可推理、Human & AI readiness 的知识网络——ontology 提供实体/属性/关系的类型层，知识图谱提供实例层的链接与追溯，二者组合让文档不再只是目录树，而是可以机械校验、可以沿图导航、人机都能读的知识资产。

## 2. 修复项

### Fix 1：作用对象一等声明（Acceptance 1、2）

**现状**：`scope` 只指 pass topic（gitignored 产物目录），作用对象边界靠 prompt 措辞推断；SKILL.md description 过度承诺。

**改法**：
- CLI 新增 `--object <declaration>`：作用对象**始终由 Human 指定目录**；未指定时缺省 = `{repo-root}/docs/`，并在报告里注明 derived（原则 1：缺省值可推导，但必须显式可见，不可静默）。
- report 顶层新增两个字段，彻底拆开二义：
  - `object_of_governance`：本次治理的作用对象边界（显式传入或 derived）。
  - `pass_topic`：原 `scope`（checklist 产物目录）。
- report 新增 `capability_boundary` 块：声明「本 pass 覆盖 = governance layer；product-domain model / 拆解重组 = 不在本 skill 能力内」。
- 新诊断 `CAPABILITY_NOT_COVERED`（signal，非 ERROR）：当报告检测到请求特征是「实体/属性/关系/规则拆解重组」类时触发，指向应使用/新建的能力（zj-codebase-design 或新建 ontology-design skill），**禁止用治理层跑绿掩盖**。触发是启发式（关键词/句式特征匹配），**只产 signal、不参与任何验收判定**——不违反原则 1（原则 1 约束的是影响验收的事实）。

**对应 Acceptance**：1（报告可见"作用对象 = ?"）、2（显式不覆盖声明）。

### Fix 2：witness 路径单一基准（Acceptance 5-A，缺陷 A）

**现状**：`emit_checklist:329` 写 `case_dir` 前缀相对路径；`inspect_checklist:387-388` 对非绝对路径再拼一次 → `<case_dir>/<case_dir>/...`；`architecture_witness():633-634` 用第三个基准（repo root）解析相对路径。测试全用绝对 `--out` 绕过了缺陷分支，`test_checklist.py:146` 还把错路径断言成预期。

**改法（一步到位，不留兼容分支）**：
- emit 的 Step 5 artifact **只写纯文件名** `architecture-validator.txt`（相对 case_dir 的规范形式，checklist.json 可移植、不绑机器）。
- inspect 唯一解析规则：相对路径一律 `case_dir / artifact`。**删除** `architecture_witness()` 的 root 基准分支，`--arch-witness` 相对路径同样按 case_dir 解析。
- 报告中展示 resolved 绝对路径，便于人工核对。
- 回归测试（双向验）：
  - 相对 `--out` + 绝对 `--out` 两种情况下，emit 声明路径 == inspect 解析路径（新断言）。
  - 按声明路径放 witness → 无 `EXEC_STEP5_ARTIFACT_MISSING`；不放 → 仍报 ERROR。
  - **改掉** `test_checklist.py:146` 的旧断言。

### Fix 3：moves 可注入 + rename 机械可区分（Acceptance 5-B，缺陷 B）

**现状**：Python API 层 `report(proposal=)` 支持 moves 豁免，但 `main():855` 调用根本不传 → `moves` 恒 `[]`；`--proposal` 只是打印开关；`UNDECLARED_RETIREMENT` 的错误消息让用户"add a moves entry"，而 CLI 无任何途径——错误消息指向一条不存在的路。合规 `git mv` 只能靠无内容 stub 过门禁。

**改法**：
- CLI 自动检测 rename：`git status --porcelain=v1 -z` 的 `R` 记录 + `git diff --name-status -M HEAD` 的 `R` 记录，合并进 report 新字段 `pending_moves`。
- 判定规则三级：
  1. HEAD 消失路径命中 `proposal.moves`（已确认）→ 完全豁免（沿用现有 API 路径）。
  2. 命中 `pending_moves`（git 检出、未确认）→ 降级为 `RENAME_AWAITING_CONFIRMATION`（**signal**，非 ERROR），提示 Human 在 proposal 里确认。
  3. 无任何 rename 证据的消失 → `UNDECLARED_RETIREMENT`（ERROR，不变）。
- **删除** "留无内容 stub 过门禁" 的 workaround 语义：rename 不再需要 tombstone stub；stub 既非 tombstone 也无 `retired-to`，本来就不是 rename 的准确表达。

### Fix 4：页面角色显式声明（Acceptance 4，缺陷 C）

**现状**：`validate_architecture_docs.py:227` 用 `"/architecture/" in path` 抓 entry，任何含该子串的 supporting 派生视图被强套 primary 契约（`ta-/ba-/pa-` 前缀、doc-kind、authority-id 1:1），一次十余条 ERROR。

**改法（改判定入口，不只是改子串）**：
- map entry 增加显式字段 `role: primary | supporting`：**map 条目级是唯一合法声明位置**（map 是本 skill 的判定真相源，原则 2 不允许第二声明来源）；页面 frontmatter `page-role` **一律不认**，出现即 signal `ROLE_DECLARATION_OUT_OF_MAP`（一次性提示迁移进 map）。
- `map_entries()` 只认 map 条目的显式 `role:` 声明；**整体删除** `"/architecture/" in path` 判定。
- 契约适用范围：primary 契约只作用于 `role: primary`；`role: supporting` 完全豁免；**无声明 = `PAGE_ROLE_UNDECLARED`（signal，一次性提示补声明），不套契约**——按原则 3 carve-out（声明缺失类 = signal），fail-open 避免把 supporting 视图误伤成 ERROR 墙。
- `ta-/ba-/pa-` 文件名前缀**降级**为 primary 页的命名惯例（可机械校验），不再是契约入口——契约入口是 role 声明。
- **原则 4 对齐**：`role:` 声明本质是给页面打 ontology 类型（primary = 知识网络的权威节点，supporting = 派生视图节点）；map 即 ontology 的类型层声明面，图实例层见 Fix 7。

### Fix 5：one-home-per-fact 机械信号（Acceptance 3）

**改法**：
- report 新增 `duplicate_fact_scan`（signal 级）：对 map 覆盖页面做 heading + n-gram 重叠粗筛（复用 doc-slop 的 n-gram 代理指标经验），命中「N 页重复同一事实且无 authority 归属」→ `FACT_NO_SINGLE_HOME`（signal）。
- 新诊断 `PARALLEL_ONTOLOGY_SUSPECTED`（signal）：机械触发判据——**同时满足**以下两条才触发，不做模糊推断：(a) 检测到 **map 覆盖范围之外**的目录存在新增/活跃变更的文档（归属判定用 map 覆盖范围，不用路径前缀——与 L4 反前缀裁决一致）；(b) 该目录下文档的 heading 与 map 覆盖页面的 heading 集合存在主题词重叠（n-gram 命中 ≥ 阈值）。直接针对 #275 实证的"往新目录堆文档制造并行第二套体系"。

### Fix 6：输出区锚定（附带，防 CWD 漂移）

**现状**：`DEFAULT_OUT = tmp/skills-outputs/...` 是 CWD 相对路径——从不同目录启动，产物落不同地方，SKILL.md 声明路径随之漂移。

**改法**：`--out` 缺省锚定到 `{repo-root}/tmp/skills-outputs/zj-docs-ontology`（repo root 已是 CLI 第一参数，锚定零成本），CWD 不再是隐变量。

### Fix 7：map 升级为 ontology 声明面 + graph_snapshot（原则 4 的实例层落地）

**现状**：map 已是判定真相源（Fix 4 的 role 声明所在），但 entry 之间没有关系声明——页面间的引用（派生自、被取代、支撑）只存在于正文措辞里，机械不可导航；报告只产契约判定，不产任何图结构，Human / AI 想按图导航 docs 只能重新爬全树，「可推理」无从谈起。

**改法**：
- map entry 新增可选 `relations:` 声明：typed edge（起步只收三类：`derived-from` / `supersedes` / `supports`，指向其他 entry 的 id 或路径）。
- 校验两级（对齐原则 1 / 原则 3）：
  - 声明的边指向不存在的页面 = **ERROR**（显式声明失真，机械可判）；
  - 页面孤儿（无任何入边且非 primary 入口）= **signal**（`ORPHAN_PAGE`），提示补导航关系，不做强制。
- report 新增 `graph_snapshot` 块：**nodes = map entries**（含 `role` / authority-id 属性），**edges = `relations` 声明**；**constraints 独立成块**（authority 1:1 等规则约束——约束是规则不是边，混进 edges 会让 AI consumer 无法区分"关系"与"规则"）；固定 JSON schema 带 `schema_version`。知识图谱实例层从这里长出来——**不另建并行 ontology 目录**，与 Fix 5 的 `PARALLEL_ONTOLOGY_SUSPECTED` 同一防线。
- Human & AI readiness：graph_snapshot 是机器可载入的，AI consumer 直接用它做导航/推理（沿 `supersedes` 找最新权威版本、沿 `derived-from` 追溯来源）；Human 侧导航索引渲染属 consumer 责任，不在本 skill 范围。
- 单一真相源：图快照**从 map 派生**，不新增第二个声明来源（原则 2）；L7 的「audit 不升格为门禁」边界对 Fix 7 同样适用——除悬边 ERROR 外全部为 signal。

## 3. Legacy 冲突与待改进项（明确列出，随本方案一并处理）

| # | Legacy 项 | 冲突点 | 处置 |
|---|-----------|--------|------|
| L1 | `test_checklist.py:146` 把 case_dir 前缀路径断言为预期 | 把缺陷钉成契约 | 删改，换 emit==inspect 一致性断言 |
| L2 | `architecture_witness()` root 基准解析 | 与 inspect 的 case_dir 基准构成双基准 | 统一为 case_dir 单基准 |
| L3 | Ruling v7 "proposal-named moves only; hash-pairing rejected" | 与"git mv 合法操作必须可豁免"冲突 | 修订为：git 原生 rename 检测自动进 `pending_moves`（signal），Human 确认后豁免；无证据消失仍 ERROR。这不是 hash-pairing（不靠内容哈希配对），是 git 原生证据 |
| L4 | `ta-/ba-/pa-` 前缀作契约入口 | 前缀本身就是"路径形状当类型声明" | 降级为 primary 命名惯例，契约入口改 `role:` 显式声明 |
| L5 | SKILL.md:3 description "governance of one codebase's documentation system" 过度承诺 | 承诺 > 能力 | 重写为能力边界声明：治理层 + 显式不覆盖清单 |
| L6 | `scope` 一词二义（pass topic vs 作用对象） | 工具无法核对作用对象 | 拆为 `object_of_governance` + `pass_topic` 两字段 |
| L7 | 本仓「doc-slop 不得升格为门禁」边界（`test_it_stays_an_audit_list_not_a_gate`） | Fix 5 新增机械扫描可能被读作越界 | 定位为 **signal + consumer escalation**（同 #264 platform-layer C 模式），不新增 ERROR、不改 exit code 语义；在测试里显式钉住"扫描只产 signal" |
| L8 | tombstone-stub workaround 语义 | stub 既非 tombstone 也无 `retired-to`，为满足观察边界而存在 | 删除；rename 走 pending_moves，retire 语义回归 tombstone/`retired-to:` 本义 |
| L9 | DEFAULT_OUT CWD 相对 | 声明路径随启动目录漂移 | 锚定 repo-root（Fix 6） |

## 4. 实施切片（TDD，每片先红后绿）

| PR | 内容 | 验证 |
|----|------|------|
| PR1 | Fix 2 + 3 + 6（工具正确性：路径单基准、moves 注入、输出锚定） | 新增回归测试双向验（缺陷态红/修复态绿）；修 L1/L2 断言 |
| PR2 | Fix 1（CLI 表面积 + SKILL.md 重写，L5/L6） | report schema 测试 + SKILL.md 契约测试 |
| PR3 | Fix 4 + 5（跨 skill：zj-docs-architecture + zj-docs-ontology，L4/L7） | 子串判定删除后双向验：supporting 视图零 ERROR、primary 页契约仍生效；`PAGE_ROLE_UNDECLARED` / `ROLE_DECLARATION_OUT_OF_MAP` / `PARALLEL_ONTOLOGY_SUSPECTED` 三 signal 触发双向验（命中红→补声明/迁移绿、误报噪声回归） |
| PR4 | Fix 7（ontology 声明面 + graph_snapshot） | map schema 测试：悬边红/补声明绿；孤儿页 signal 双向验；graph_snapshot 按 schema_version 快照稳定 |

**门禁注意事项**（本仓硬坑）：
- 两个 skill 都属 `codebase-docs` 桶，桶计数不变（无增删 skill），但 `docs/architecture/ta-skill-bucket-codebase-docs.md` 的条目描述如引用旧判定机制需同步。
- closure-lint 是 required 且无条件触发；PR 后 ~55s 刷新，红先判分支是否落后 main。
- 改 skill 后三副本按 `git archive + rsync` 删-重装同步（不用 link-skills.sh）。
- 测试一律 anaconda3 python3，串行跑。
- 本方案文件本身留在 `docs/plans/` 不入 doc-map（plan-coupling ADR 0010 约定）。

## 5. 风险点

1. **Fix 3 的 signal 级 rename 提示**可能被 CI consumer 忽略 → 与 #264 一致，由 step-gate 决定 escalation；如需强制，consumer 侧把 signal 当 gate。
2. **Fix 4 fail-open**（无 role 声明不套契约）短期可能漏检未声明的新 primary 页 → `PAGE_ROLE_UNDECLARED` signal 提示补声明（已按原则 3 carve-out 裁决为声明缺失类，非 ERROR）；CI consumer 可先把它当 gate 观察一段时间。frontmatter 残留 `page-role` 的存量页面会集中触发 `ROLE_DECLARATION_OUT_OF_MAP`，首轮治理需批量迁移进 map。
3. **Fix 5 n-gram 粗筛**有噪声（记忆：原始百分比≠slop 严重度）→ 只报重复事实对 + 指向页，不做百分比评分。
4. **L3 ruling 修订**需在 ADR 或 SKILL.md 里留 amendment 记录，避免"已修复缺陷仍写成现状"的腐化。
5. **Fix 7 relations 声明有维护成本**：起步只收 3 类边 + 孤儿只报 signal，避免 map 变成没人维护的装饰图；graph_snapshot schema 变更必须走 `schema_version`，防止 consumer 断裂。
6. **原则 4 的边界**：本方案只落「类型层声明（role）+ 实例层边（relations）+ 图快照」三件事；完整的 ontology 设计（实体/属性/规则建模）仍属 Fix 1 `capability_boundary` 显式不覆盖清单，走 zj-codebase-design / ontology-design skill，**不用治理层跑绿掩盖**。
