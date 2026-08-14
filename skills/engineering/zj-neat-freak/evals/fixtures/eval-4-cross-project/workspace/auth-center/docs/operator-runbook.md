# auth-center 运维手册

## 冒烟

```bash
curl -s localhost:7000/healthz
curl -s localhost:7000/authorize?client_id=demo | head
```

## 环境变量

DATABASE_URL / JWT_SECRET / TOKEN_TTL —— 见 CLAUDE.md 表。
