# auth-center 接入指南

下游应用接入统一登录的步骤。

## 接入流程（Authorization Code Flow）

1. 注册应用拿 client_id / client_secret
2. 引导用户到 `GET /authorize?client_id=...&redirect_uri=...`
3. 回调拿 code，`POST /token` 换 access token
4. 用 token 调 `GET /userinfo`

## API 速查表

| Method | Path | 说明 |
|---|---|---|
| GET | /authorize | 授权页 |
| POST | /token | code 换 token |
| GET | /userinfo | 用户信息 |
| POST | /revoke | 吊销 |

## 错误码

- `invalid_client` — client_id 不存在
- `invalid_grant` — code 过期或已用
