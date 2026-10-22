#!/usr/bin/env node
// Fixture driver: replays every form/ and approval/ fixture through the real state
// machines and reports, per fixture, the values those machines actually exposed.
// Nothing here knows what a fixture expects — `actual` is read off the machine.

import fs from 'node:fs';
import path from 'node:path';
import { ProfileForm } from './src/form/machine.mjs';
import { ExpenseApproval } from './src/approval/machine.mjs';
import { createMemoryStore } from './src/shared/store.mjs';

const fixturesRoot = process.argv[2];
if (!fixturesRoot) {
  console.error('usage: node run-fixtures.mjs <fixtures-root>');
  process.exit(2);
}

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') {
    const out = {};
    for (const key of Object.keys(value).sort()) out[key] = canonical(value[key]);
    return out;
  }
  return value;
}

function equal(a, b) {
  return JSON.stringify(canonical(a)) === JSON.stringify(canonical(b));
}

function buildSession(input, klass) {
  const store = createMemoryStore();
  if (klass === 'form') {
    return new ProfileForm({
      profile: input.profile,
      store,
      user: input.user,
      initialState: input.initial_state,
    });
  }
  return new ExpenseApproval({
    request: input.request,
    applicant: input.applicant,
    approver: input.approver ?? null,
    store,
    initialState: input.initial_state,
  });
}

function dispatch(machine, klass, action, input) {
  const step = action.seq;
  if (klass === 'form') {
    switch (action.action) {
      case 'edit':
        return machine.edit(action.field, (input.profile || {})[action.field]);
      case 'validate':
        return machine.validate();
      case 'submit':
        return machine.submit({ confirmed: action.role === 'user', role: action.role, step });
      case 'persist':
        return machine.persist({ responseCode: action.response_code });
      case 'recover':
        return machine.recover();
      default:
        return { ok: false, reason: 'unknown_action' };
    }
  }

  switch (action.action) {
    case 'edit':
      return machine.updateField(action.field, (input.request || {})[action.field]);
    case 'submit':
      return machine.submit({
        confirmed: action.role === 'applicant',
        role: action.role,
        actor: action.role === 'applicant' ? input.applicant : action.role,
        step,
      });
    case 'route':
      return machine.route();
    case 'approve':
      return machine.approve({
        role: action.role,
        actor: action.role === 'approver' ? input.approver : action.role,
        reason: action.reason || '',
        confirmed: true,
        step,
      });
    case 'reject':
      return machine.reject({
        role: action.role,
        actor: action.role === 'approver' ? input.approver : action.role,
        reason: action.reason || '',
        confirmed: true,
        step,
      });
    case 'timeout':
      return machine.timeout({ step });
    case 'revise':
      return machine.revise({ step });
    default:
      return { ok: false, reason: 'unknown_action' };
  }
}

const summary = [];
const classes = ['form', 'approval'];

for (const klass of classes) {
  const dir = path.join(fixturesRoot, klass);
  if (!fs.existsSync(dir)) continue;
  const cases = fs
    .readdirSync(dir)
    .filter((name) => fs.statSync(path.join(dir, name)).isDirectory())
    .sort();

  for (const name of cases) {
    const caseDir = path.join(dir, name);
    const input = JSON.parse(fs.readFileSync(path.join(caseDir, 'input.json'), 'utf8'));
    const expected = JSON.parse(fs.readFileSync(path.join(caseDir, 'expected.json'), 'utf8'));

    const machine = buildSession(input, klass);
    const trace = [];
    for (const action of input.actions || []) {
      const before = machine.state;
      if (action.from && before !== action.from) {
        trace.push(`state_before_step_${action.seq}:${before}!=${action.from}`);
      }
      const result = dispatch(machine, klass, action, input);
      trace.push(`step_${action.seq}:${action.action}:${result && result.ok ? 'ok' : (result && result.reason) || 'noop'}`);
    }

    const report = machine.report();
    const actual = {};
    const mismatch = [];
    for (const key of Object.keys(expected)) {
      if (key === 'fixture_id' || key === 'assertions') continue;
      actual[key] = Object.prototype.hasOwnProperty.call(report, key) ? report[key] : null;
      if (!equal(actual[key], expected[key])) mismatch.push(key);
    }

    const expectedView = {};
    for (const key of Object.keys(expected)) {
      if (key === 'fixture_id' || key === 'assertions') continue;
      expectedView[key] = expected[key];
    }

    summary.push({
      fixture_id: input.fixture_id || name,
      class: input.class || klass,
      match: mismatch.length === 0,
      actual,
      expected: expectedView,
      mismatch_keys: mismatch,
    });

    const status = mismatch.length === 0 ? 'PASS' : `FAIL(${mismatch.join(',')})`;
    console.log(`${input.fixture_id || name} [${klass}] ${status} ${trace.join(' ')}`);
  }
}

const allMatch = summary.length > 0 && summary.every((row) => row.match);
const payload = { fixtures: summary, all_match: allMatch };
fs.writeFileSync(path.join(process.cwd(), '.run-fixtures-result.json'), JSON.stringify(payload, null, 2));

console.log(JSON.stringify(payload));
process.exit(allMatch ? 0 : 1);
