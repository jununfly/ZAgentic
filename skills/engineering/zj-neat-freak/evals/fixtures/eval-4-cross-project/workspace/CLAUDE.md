# workspace 规范

公司项目工作空间。

- 文件夹名全部英文、小写、连字符（kebab-case）
- 每个项目必须有自己的 CLAUDE.md；AGENTS.md 必须是指向 CLAUDE.md 的软链，永远只编辑 CLAUDE.md
- 项目 `.gitignore` 必须包含 `.env`
- 上下游项目的接入文档必须两边对齐：上游改协议，下游 integration 文档同步改
