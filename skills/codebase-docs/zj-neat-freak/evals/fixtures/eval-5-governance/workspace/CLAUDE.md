# workspace 规范

个人项目工作空间，所有项目落在本目录的子文件夹里。

## 命名与结构

- 文件夹名全部英文、小写、连字符（kebab-case）：`pdf-tools` 而不是 `PDF_Tools`
- 根目录不允许裸放文件（本 CLAUDE.md 除外）
- 每个有可运行代码的项目必须有自己的 CLAUDE.md（含目的、技术栈、启动命令）

## CLAUDE.md 与 AGENTS.md 同源

CLAUDE.md 与 AGENTS.md 必须同源：新建 CLAUDE.md 后立刻 `ln -s CLAUDE.md AGENTS.md`。
两份独立且不一致的，合并到 CLAUDE.md 再改软链。永远只编辑 CLAUDE.md。

## 红线

- 密钥、token 不进代码；项目 `.gitignore` 必须包含 `.env`、`.env.local`
- 运行时数据目录不进 git（如 `legacy-crm/data/`、`pdf-tools/output/`）

## 项目清单

| 项目 | 说明 |
|---|---|
| pdf-tools | PDF 批处理工具 |
| legacy-crm | 客户管理系统（Rails） |
| link-shortener | 短链服务 |
