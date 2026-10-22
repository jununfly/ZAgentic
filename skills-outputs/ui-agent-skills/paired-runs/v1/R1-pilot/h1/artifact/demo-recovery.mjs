#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { createMockApi } from './src/mockApi.mjs';
import { createFormMachine } from './src/formMachine.mjs';

const cwd = process.cwd();
const dataFile = path.join(cwd, '.data', 'recovery.json');
fs.mkdirSync(path.dirname(dataFile), { recursive: true });

const profile = { nickname: 'zj', email: 'zj@example.com', bio: 'AI-Native 实践者' };
const api = createMockApi({
  initial: { 'user-001': profile },
  onPersist: (record) => fs.writeFileSync(dataFile, `${JSON.stringify(record, null, 2)}\n`, 'utf8')
});
const machine = createFormMachine({ userId: 'user-001', profile, api });
const steps = [];

async function run(action) {
  const result = await machine.dispatch(action);
  steps.push(`${action.seq} ${action.action}: ${result.from} -> ${result.to}`);
  return result;
}

await run({ seq: 1, role: 'user', action: 'edit', field: 'email', value: 'broken@@example' });
await run({ seq: 2, role: 'system', action: 'validate' });
const blocked = await run({ seq: 3, role: 'user', action: 'submit' });

await run({ seq: 4, role: 'user', action: 'edit', field: 'email', value: 'zj@example.com' });
await run({ seq: 5, role: 'system', action: 'validate' });
await run({ seq: 6, role: 'user', action: 'submit' });
const failed = await run({ seq: 7, role: 'system', action: 'persist', response_code: 500 });

await run({ seq: 8, role: 'user', action: 'edit', field: 'bio', value: 'AI-Native 实践者 · 已更新' });
await run({ seq: 9, role: 'user', action: 'submit' });
const recovered = await run({ seq: 10, role: 'system', action: 'persist' });

const final = machine.snapshot();
const ok =
  blocked.submit_blocked === true &&
  blocked.error_fields.includes('email') &&
  failed.final_state === 'error' &&
  failed.persisted === false &&
  recovered.final_state === 'success' &&
  final.persisted === true &&
  final.human_gates.length === 2;

console.error(steps.join('\n'));
console.log(JSON.stringify({
  final_state: final.final_state,
  persisted: final.persisted,
  error_fields: final.error_fields,
  submit_blocked: final.submit_blocked,
  human_gates: final.human_gates,
  persisted_payload: final.persisted_payload
}));
process.exit(ok ? 0 : 1);
