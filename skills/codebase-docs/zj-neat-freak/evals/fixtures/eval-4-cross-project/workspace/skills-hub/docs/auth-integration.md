# skills-hub × auth-center 集成说明

skills-hub 的登录走 auth-center 的 Authorization Code Flow：

1. `setup.sh` 打开浏览器到 auth-center 的 `/authorize`
2. 回调到本地 `http://127.0.0.1:8976/callback` 拿 code
3. code 换 token 存 `~/.skills-hub/token`

CLI 场景（无浏览器的服务器）暂不支持登录。
