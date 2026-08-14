# taskflow

团队任务管理工具，个人使用。

## 技术栈

- 语言 / 框架：TypeScript + Express（REST API）+ React
- 数据库：SQLite（better-sqlite3）

## 启动

```bash
npm install
npm run dev   # Express 起在 :4000
```

## API 路由清单

- `GET /api/tasks` — 任务列表
- `POST /api/tasks` — 创建任务
- `PATCH /api/tasks/:id` — 更新任务
- `DELETE /api/tasks/:id` — 删除任务

## 部署

部署到 Vercel（`vercel --prod`）。
