import express from 'express';
import { nanoid } from 'nanoid';

const app = express();
const store = new Map();

app.use(express.json());
app.post('/shorten', (req, res) => {
  const id = nanoid(7);
  store.set(id, req.body.url);
  res.json({ short: `/s/${id}` });
});
app.get('/s/:id', (req, res) => {
  const url = store.get(req.params.id);
  url ? res.redirect(url) : res.sendStatus(404);
});
app.listen(3000);
