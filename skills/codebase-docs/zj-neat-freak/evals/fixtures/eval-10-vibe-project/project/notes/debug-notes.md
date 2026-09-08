# 调试流水

- 端口 3000 被占了，换 3005
- express.json() 忘了挂，POST body 一直是 undefined
- fs.writeFileSync 路径要用 __dirname 拼，不然 cwd 不对
