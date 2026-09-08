# bug：勾选完成不生效

现象：点勾选，刷新后状态丢。
原因：PATCH 路由把 id 当字符串比较，找不到条目。
修法：`Number(req.params.id)` 转数字再比。

已修，server.js 里现在就是这么写的。
