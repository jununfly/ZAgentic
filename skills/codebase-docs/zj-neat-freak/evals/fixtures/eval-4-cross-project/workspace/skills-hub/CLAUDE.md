# skills-hub

团队 skill 分发中心：同步、安装、管理团队共享的 agent skills。

## 技术栈

- Bash（setup.sh 安装器）+ React 管理前端

## 启动

```bash
./setup.sh          # 安装 / 更新本机 skills
cd web && pnpm dev  # 管理前端 :5173
```

## 认证

通过 auth-center 的 Authorization Code Flow 登录（浏览器跳转回调）。
