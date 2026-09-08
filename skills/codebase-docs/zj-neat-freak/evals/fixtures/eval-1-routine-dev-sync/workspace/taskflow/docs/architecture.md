# TaskFlow 架构

## 总览

Express REST API + React 前端。所有端点挂在 `/api/` 下，JSON in/out。

## Routes

| Method | Path | 说明 |
|---|---|---|
| GET | /api/tasks | 列表 |
| POST | /api/tasks | 创建 |
| PATCH | /api/tasks/:id | 更新 |
| DELETE | /api/tasks/:id | 删除 |

## 部署

Vercel serverless functions，`vercel.json` 配置 rewrites。
