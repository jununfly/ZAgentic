# workspace 规范

个人项目工作空间。

- 文件夹名全部英文、小写、连字符（kebab-case），如 `note-sync` 而不是 `Note_Sync`
- 每个有可运行代码的项目必须有自己的 CLAUDE.md（含目的、技术栈、启动命令）；AGENTS.md 必须是指向 CLAUDE.md 的软链（`ln -s CLAUDE.md AGENTS.md`），永远只编辑 CLAUDE.md
- 项目 `.gitignore` 必须包含 `.env`、`.env.local`——密钥不进 git 是红线
- 根目录不允许裸放文件
