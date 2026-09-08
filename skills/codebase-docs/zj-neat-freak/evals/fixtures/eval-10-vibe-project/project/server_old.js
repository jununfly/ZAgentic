// 旧版：内存数组存储，已被 server.js 的 data.json 文件存储替代
const express = require("express");
const app = express();
let todos = [];

app.use(express.json());

app.get("/api/todos", (req, res) => res.json(todos));

app.listen(3000, () => console.log("quicktodo on 3000"));
