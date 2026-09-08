# auth-center

统一认证中台，为所有内部应用提供 OAuth 登录。

## 技术栈

- Node.js + Fastify + PostgreSQL

## 启动

```bash
pnpm install && pnpm dev   # :7000
```

## 路由清单

- `GET /authorize` — OAuth 授权页
- `POST /token` — 换取 access token
- `GET /userinfo` — 用户信息
- `POST /revoke` — 吊销 token

## 环境变量

| 变量 | 说明 |
|---|---|
| DATABASE_URL | PostgreSQL 连接串 |
| JWT_SECRET | token 签名密钥 |
| TOKEN_TTL | access token 有效期（秒） |
