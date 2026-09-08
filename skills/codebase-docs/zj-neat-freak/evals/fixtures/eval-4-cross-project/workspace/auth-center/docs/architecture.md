# auth-center 架构

## 数据模型

| 表 | 说明 |
|---|---|
| clients | 注册的下游应用 |
| auth_codes | 一次性授权码 |
| tokens | access/refresh token |

## Flow

标准 Authorization Code Flow，状态机：pending → exchanged → revoked。
