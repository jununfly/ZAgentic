#!/usr/bin/env node
// Fixture driver: replays every frozen fixture against the real implementation modules.
// Nothing here contains expected values - every value comes from the machine snapshot.

import { readdirSync, readFileSync, writeFileSync, statSync } from 'node:fs';
import { join, resolve as resolvePath } from 'node:path';

import { createProfileFormMachine } from './src/form/machine.mjs';
import { createProfileApi } from './src/form/persistence.mjs';
import { createApprovalMachine } from './src/approval/machine.mjs';
import { createApprovalApi } from './src/approval/persistence.mjs';
import { stableStringify } from './src/core.mjs';

const EXCLUDED_KEYS = new Set(['fixture_id', 'assertions']);
const FIXTURE_CLASSES = ['form', 'approval'];

function readJson(path) {
  return JSON.parse(readFileSync(path, 'utf8'));
}

function comparable(expected) {
  const keys = Object.keys(expected).filter((key) => !EXCLUDED_KEYS.has(key));
  const subset = {};
  for (const key of keys) subset[key] = expected[key];
  return { keys, subset };
}

// Form: the request stays in flight until the fixture's own persist step answers it.
function buildFormMachine(input) {
  return createProfileFormMachine({
    user: input.user ?? 'anonymous',
    profile: input.profile ?? {},
    initialState: input.initial_state ?? 'idle',
    api: createProfileApi({ latency: 0 }),
    transport: (_payload, park) => new Promise((resolveResponse) => park(resolveResponse)),
  });
}

function buildApprovalMachine(input) {
  return createApprovalMachine({
    requestId: `expense-${input.fixture_id}`,
    applicantId: input.applicant ?? 'anonymous',
    approverId: input.approver ?? null,
    request: input.request ?? {},
    initialState: input.initial_state ?? 'draft',
    api: createApprovalApi({ latency: 0 }),
  });
}

async function applyFormAction(machine, action) {
  switch (action.action) {
    case 'load':
      machine.load();
      return;
    case 'edit':
      machine.edit(action.field);
      return;
    case 'validate':
      machine.validate();
      return;
    case 'submit':
      machine.submit({ role: action.role ?? 'user', atStep: action.seq, confirmed: true });
      return;
    case 'persist':
      await machine.persist({ code: action.response_code });
      return;
    case 'recover':
      machine.recover();
      return;
    default:
      throw new Error(`unsupported form action: ${action.action}`);
  }
}

async function applyApprovalAction(machine, action) {
  switch (action.action) {
    case 'submit':
      await machine.submit({
        requestedRole: action.role ?? 'applicant',
        atStep: action.seq,
        confirmed: true,
      });
      return;
    case 'route':
      machine.route({ atStep: action.seq });
      return;
    case 'approve':
    case 'reject':
      await machine.decide({
        kind: action.action,
        requestedRole: action.role ?? 'approver',
        reason: action.reason ?? '',
        atStep: action.seq,
      });
      return;
    case 'timeout':
      machine.timeout({ escalate: action.escalate === true, atStep: action.seq });
      return;
    case 'revise':
      machine.revise({ atStep: action.seq });
      return;
    default:
      throw new Error(`unsupported approval action: ${action.action}`);
  }
}

async function runFixture(dir, fixtureClass) {
  const input = readJson(join(dir, 'input.json'));
  const expected = readJson(join(dir, 'expected.json'));
  const machine =
    fixtureClass === 'form' ? buildFormMachine(input) : buildApprovalMachine(input);

  if (machine.state !== input.initial_state) {
    // Fixture hydration mismatch is caught here rather than smuggled into `actual`.
    throw new Error(`initial state mismatch: ${machine.state} != ${input.initial_state}`);
  }

  for (const action of input.actions ?? []) {
    if (fixtureClass === 'form') await applyFormAction(machine, action);
    else await applyApprovalAction(machine, action);
  }

  const snapshot = machine.snapshot();
  const { keys, subset } = comparable(expected);
  const actual = {};
  for (const key of keys) actual[key] = snapshot[key];

  const mismatch_keys = keys.filter((key) => stableStringify(actual[key]) !== stableStringify(subset[key]));
  return {
    fixture_id: expected.fixture_id ?? input.fixture_id,
    class: fixtureClass,
    match: mismatch_keys.length === 0,
    actual,
    expected: subset,
    mismatch_keys,
  };
}

async function main() {
  const root = resolvePath(process.argv[2] ?? '../tests/ui-agent-skills/fixtures');
  const results = [];
  for (const fixtureClass of FIXTURE_CLASSES) {
    const classRoot = join(root, fixtureClass);
    let entries = [];
    try {
      entries = readdirSync(classRoot).filter((name) => statSync(join(classRoot, name)).isDirectory()).sort();
    } catch {
      entries = [];
    }
    for (const name of entries) {
      const dir = join(classRoot, name);
      try {
        results.push(await runFixture(dir, fixtureClass));
      } catch (error) {
        results.push({
          fixture_id: name,
          class: fixtureClass,
          match: false,
          actual: {},
          expected: {},
          mismatch_keys: [`driver_error: ${error.message}`],
        });
      }
    }
  }

  results.sort((a, b) => a.fixture_id.localeCompare(b.fixture_id));
  const all_match = results.length > 0 && results.every((entry) => entry.match);
  const payload = { fixtures: results, all_match };
  const line = JSON.stringify(payload);
  writeFileSync('.run-fixtures-result.json', `${line}\n`, 'utf8');
  process.stdout.write(`${line}\n`);
  process.exit(all_match ? 0 : 1);
}

await main();
