#!/usr/bin/env node
// 驱动：读取全部 form/approval 固件的 input.json + expected.json，
// 按顺序驱动实现，产出与 expected 同键名的 actual 并比对。
import { readFileSync, readdirSync, writeFileSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { createFormMachine } from './src/form/machine.mjs';
import { createApprovalMachine } from './src/approval/machine.mjs';

const FIXTURES_ROOT = process.argv[2];
if (!FIXTURES_ROOT) {
  console.error('usage: node run-fixtures.mjs <fixtures-root>');
  process.exit(2);
}
const root = resolve(FIXTURES_ROOT);

function stable(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stable).join(',')}]`;
  const keys = Object.keys(value).sort();
  return `{${keys.map((k) => `${JSON.stringify(k)}:${stable(value[k])}`).join(',')}}`;
}

function readJson(p) {
  return JSON.parse(readFileSync(p, 'utf8'));
}

function listFixtures(cls) {
  const dir = join(root, cls);
  let entries = [];
  try {
    entries = readdirSync(dir);
  } catch {
    return [];
  }
  return entries
    .filter((name) => statSync(join(dir, name)).isDirectory())
    .sort()
    .map((name) => ({ id: name, dir: join(dir, name) }));
}

function runForm(input) {
  const machine = createFormMachine({
    user: input.user ?? 'anonymous',
    profile: input.profile ?? {},
    initialState: input.initial_state ?? 'idle',
  });
  for (const act of input.actions ?? []) {
    switch (act.action) {
      case 'edit':
        machine.edit(act.field, (input.profile ?? {})[act.field] ?? '');
        break;
      case 'validate':
        machine.validate();
        break;
      case 'submit':
        machine.submit({ confirm: true, atStep: act.seq ?? null, role: act.role ?? 'user' });
        break;
      case 'persist':
        machine.persist({ responseCode: act.response_code ?? 200, error: act.error ?? null });
        break;
      case 'recover':
        machine.recover();
        break;
      default:
        break;
    }
  }
  return machine.snapshot();
}

function runApproval(input) {
  const machine = createApprovalMachine({
    applicant: input.applicant ?? 'unknown',
    approver: input.approver ?? null,
    request: input.request ?? {},
    initialState: input.initial_state ?? 'draft',
  });
  for (const act of input.actions ?? []) {
    const base = { confirm: true, atStep: act.seq ?? null, role: act.role ?? null, actor: act.role ?? null };
    switch (act.action) {
      case 'edit':
        machine.edit(act.field, act.value ?? (input.request ?? {})[act.field]);
        break;
      case 'validate':
        machine.validate();
        break;
      case 'submit':
        machine.submit(base);
        break;
      case 'route':
        machine.route({ atStep: act.seq ?? null });
        break;
      case 'approve':
        machine.approve({ ...base, reason: act.reason ?? null });
        break;
      case 'reject':
        machine.reject({ ...base, reason: act.reason ?? null });
        break;
      case 'timeout':
        machine.timeout({ atStep: act.seq ?? null });
        break;
      case 'revise':
        machine.revise();
        break;
      default:
        break;
    }
  }
  return machine.snapshot();
}

const results = [];
for (const cls of ['form', 'approval']) {
  for (const fx of listFixtures(cls)) {
    const input = readJson(join(fx.dir, 'input.json'));
    const expected = readJson(join(fx.dir, 'expected.json'));
    const snapshot = cls === 'form' ? runForm(input) : runApproval(input);

    const actual = {};
    const mismatchKeys = [];
    for (const key of Object.keys(expected)) {
      if (key === 'fixture_id' || key === 'assertions') continue;
      const av = key in snapshot ? snapshot[key] : null;
      actual[key] = av;
      if (stable(av) !== stable(expected[key])) mismatchKeys.push(key);
    }
    const match = mismatchKeys.length === 0;
    results.push({
      fixture_id: expected.fixture_id ?? fx.id,
      class: cls,
      match,
      actual,
      expected: Object.fromEntries(Object.keys(expected).filter((k) => k !== 'fixture_id' && k !== 'assertions').map((k) => [k, expected[k]])),
      mismatch_keys: mismatchKeys,
    });
    console.log(`${expected.fixture_id ?? fx.id} ${match ? 'PASS' : 'FAIL'} ${mismatchKeys.join(',')}`);
  }
}

const allMatch = results.every((r) => r.match);
const payload = { fixtures: results, all_match: allMatch };
const line = JSON.stringify(payload);
writeFileSync(new URL('./.run-fixtures-result.json', import.meta.url), `${line}\n`);
console.log(line);
process.exit(allMatch ? 0 : 1);
