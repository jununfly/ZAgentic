import { initTRPC } from '@trpc/server';
import { z } from 'zod';
import { db } from './db';

const t = initTRPC.create();

export const appRouter = t.router({
  taskList: t.procedure.query(() => db.prepare('SELECT * FROM tasks').all()),
  taskCreate: t.procedure
    .input(z.object({ title: z.string(), assignee: z.string().optional() }))
    .mutation(({ input }) =>
      db.prepare('INSERT INTO tasks (title, assignee) VALUES (?, ?)').run(input.title, input.assignee)
    ),
  taskUpdate: t.procedure
    .input(z.object({ id: z.number(), done: z.boolean() }))
    .mutation(({ input }) => db.prepare('UPDATE tasks SET done = ? WHERE id = ?').run(input.done ? 1 : 0, input.id)),
  taskDelete: t.procedure
    .input(z.object({ id: z.number() }))
    .mutation(({ input }) => db.prepare('DELETE FROM tasks WHERE id = ?').run(input.id)),
});

export type AppRouter = typeof appRouter;
