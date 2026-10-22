#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { createMockApi } from './src/mockApi.mjs';
import { createFormMachine } from './src/formMachine.mjs';
import { writeReceipt } from './src/verify.mjs';

const [inputArg, expectedArg] = process.argv.slice(2);
if (!inputArg || !expectedArg) {
  console.error('usage: node run-f1.mjs <input.json> <expected.json>');
  process.exit(2);
}

const input = JSON.parse(fs.readFileSync(inputArg, 'utf8'));
const expected = JSON.parse(fs.readFileSync(expectedArg, 'utf8'));

const cwd = process.cwd();
const dataFile = path.join(cwd, '.data', 'profile.json');
fs.mkdirSync(path.dirname(dataFile), { recursive: true });

const api = createMockApi({
  initial: { [input.user]: input.profile },
  onPersist: (record) => {
    fs.writeFileSync(dataFile, `${JSON.stringify(record, null, 2)}\n`, 'utf8');
  }
});

const machine = createFormMachine({ userId: input.user, profile: input.profile, api });
const transitions = [];

for (const action of input.actions) {
  const result = await machine.dispatch(action);
  transitions.push({
    seq: action.seq,
    action: action.action,
    from: result.from,
    to: result.to,
    expected_from: action.from,
    expected_to: action.to
  });
  console.error(`[F-1] step ${action.seq} ${action.role} ${action.action}: ${result.from} -> ${result.to}`);
}

const result = machine.snapshot();

function deepEqual(a, b) {
  if (a === b) return true;
  if (typeof a !== typeof b) return false;
  if (a && b && typeof a === 'object') {
    if (Array.isArray(a) !== Array.isArray(b)) return false;
    if (Array.isArray(a)) {
      return a.length === b.length && a.every((value, index) => deepEqual(value, b[index]));
    }
    const keysA = Object.keys(a);
    const keysB = Object.keys(b);
    if (keysA.length !== keysB.length) return false;
    return keysA.every((key) => deepEqual(a[key], b[key]));
  }
  return false;
}

const failures = [];
for (const key of Object.keys(expected)) {
  if (key === 'fixture_id' || key === 'assertions') continue;
  if (!deepEqual(result[key], expected[key])) {
    failures.push({ key, expected: expected[key], actual: result[key] });
  }
}
for (const item of transitions) {
  if (item.from !== item.expected_from) {
    failures.push({ key: `step ${item.seq} from`, expected: item.expected_from, actual: item.from });
  }
  if (item.to !== item.expected_to) {
    failures.push({ key: `step ${item.seq} to`, expected: item.expected_to, actual: item.to });
  }
}

const receipt = writeReceipt({
  cwd,
  fixtureFiles: [inputArg, expectedArg],
  scenarioPass: failures.length === 0,
  persistedPayload: result.persisted_payload
});

const output = {
  final_state: result.final_state,
  persisted: result.persisted,
  error_fields: result.error_fields,
  submit_blocked: result.submit_blocked,
  human_gates: result.human_gates,
  persisted_payload: result.persisted_payload
};

if (failures.length > 0) {
  console.error('DIFF:');
  console.error(JSON.stringify(failures, null, 2));
}
console.error(`[verify] receipt status ${receipt.status} (${receipt.passed}/${receipt.checked})`);

console.log(JSON.stringify(output));
process.exit(failures.length === 0 && receipt.status === 'PASS' ? 0 : 1);
