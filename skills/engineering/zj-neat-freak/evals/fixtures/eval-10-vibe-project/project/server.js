const express = require("express");
const fs = require("fs");
const path = require("path");

const app = express();
const PORT = 3005;
const DATA_FILE = path.join(__dirname, "data.json");

app.use(express.json());
app.use(express.static(__dirname));

function loadTodos() {
  try {
    return JSON.parse(fs.readFileSync(DATA_FILE, "utf8"));
  } catch {
    return [];
  }
}

function saveTodos(todos) {
  fs.writeFileSync(DATA_FILE, JSON.stringify(todos, null, 2));
}

app.get("/api/todos", (req, res) => {
  res.json(loadTodos());
});

app.post("/api/todos", (req, res) => {
  const todos = loadTodos();
  const todo = { id: Date.now(), text: req.body.text, done: false };
  todos.push(todo);
  saveTodos(todos);
  res.status(201).json(todo);
});

app.patch("/api/todos/:id", (req, res) => {
  const todos = loadTodos();
  const todo = todos.find((t) => t.id === Number(req.params.id));
  if (!todo) return res.status(404).json({ error: "not found" });
  todo.done = Boolean(req.body.done);
  saveTodos(todos);
  res.json(todo);
});

app.listen(PORT, () => {
  console.log(`quicktodo listening on http://localhost:${PORT}`);
});
