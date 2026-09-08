# notesapp

个人笔记应用（Next.js）。

## 技术栈

- Next.js 15 + TypeScript
- 认证：NextAuth（GitHub OAuth）
- 数据库：SQLite（开发），计划迁移 PostgreSQL

## 启动

```bash
pnpm install
pnpm dev
```

## 待办

- [ ] SQLite → PostgreSQL 迁移（进行中）
- [ ] 列表页性能问题排查（首屏 3s+）
