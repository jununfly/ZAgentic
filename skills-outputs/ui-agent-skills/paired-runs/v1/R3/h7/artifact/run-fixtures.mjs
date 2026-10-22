#!/usr/bin/env node
// 驱动实现跑通全部 frozen fixtures：只对实现做「真实调用」，不写死任何期望值。
import { readdirSync, readFileSync, writeFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

import { FormFlow } from './src/form/machine.mjs';
import { ApprovalFlow } from './src/approval/machine.mjs';
import { outcomeFromResponseCode } from './src/mock/constants.mjs';

const ROOT = process.argv[2];

function readJson(file) {
  return JSON.parse(readFileSync(file, 'utf8'));
}

function deepEqual(a, b) {
  if (a === b) return true;
  if (Array.isArray(a) && Array.isArray(b)) {
    return a.length === b.length && a.every((v, i) => deepEqual(v, b[i]));
  }
  if (a && b && typeof a === 'object' && typeof b === 'object') {
    const ka = Object.keys(a).sort();
    const kb = Object.keys(b).sort();
    return ka.length === kb.length && ka.every((k, i) => k === kb[i] && deepEqual(a[k], b[k]));
  }
  return false;
}

const gates = (list) => list.map((g) => ({ role: g.role, signed: g.signed, at_step: g.at_step }));

async function runForm(input) {
  const flow = new FormFlow({
    userId: input.user ?? 'user',
    profile: input.profile ?? {},
    initialState: input.initial_state ?? 'idle'
  });

  for (const action of input.actions ?? []) {
    switch (action.action) {
      case 'edit': {
        const value = action.value !== undefined ? action.value : (input.profile ?? {})[action.field];
        flow.edit(action.field, value);
        break;
      }
      case 'validate':
        flow.validate();
        break;
      case 'submit':
        await flow.submit({ role: action.role, confirm: true, step: action.seq });
        break;
      case 'persist':
        await flow.resolveSubmission({ scenario: outcomeFromResponseCode(action.response_code, action.error) });
        break;
      default:
        break;
    }
  }

  return {
    final_state: flow.state,
    persisted: flow.persisted,
    error_fields: [...flow.error_fields],
    submit_blocked: flow.submit_blocked,
    human_gates: gates(flow.gates),
    duplicate_suppressed: flow.duplicateSuppressed,
    writes: flow.writes,
    recoverable: flow.recoverable,
    fallback: flow.fallback,
    explicit_marker: flow.explicit_marker,
    last_error: flow.lastError
  };
}

async function runApproval(input) {
  const flow = new ApprovalFlow({
    requestId: `${input.fixture_id}-request`,
    request: input.request ?? {},
    applicantId: input.applicant,
    approverId: input.approver,
    initialState: input.initial_state ?? 'draft'
  });

  for (const action of input.actions ?? []) {
    const actorId = action.actor ?? (action.role === 'approver' ? input.approver : input.applicant);
    switch (action.action) {
      case 'edit':
        flow.edit(action.field, action.value);
        break;
      case 'submit':
        await flow.submitRequest({ role: action.role, actorId, confirm: true, step: action.seq });
        break;
      case 'route':
        flow.route({ role: action.role, step: action.seq });
        break;
      case 'approve':
      case 'reject':
        await flow.decide({
          action: action.action,
          role: action.role,
          actorId,
          confirm: true,
          reason: action.reason ?? null,
          step: action.seq
        });
        break;
      case 'timeout':
        flow.escalateOnTimeout({ role: action.role, step: action.seq });
        break;
      default:
        break;
    }
  }

  return {
    final_state: flow.state,
    persisted: flow.persisted,
    human_gates: gates(flow.gates),
    error_fields: [...flow.error_fields],
    version: flow.version,
    escalated: flow.escalated,
    fallback: flow.fallback,
    explicit_marker: flow.explicit_marker,
    writes: flow.writes,
    history_length: flow.history.length
  };
}

function pick(computed, expected) {
  const actual = {};
  for (const key of Object.keys(expected)) {
    if (key === 'fixture_id' || key === 'assertions') continue;
    actual[key] = key in computed ? computed[key] : null;
  }
  return actual;
}

function fixtureDirs(kind) {
  const base = join(ROOT, kind);
  return readdirSync(base)
    .filter((name) => statSync(join(base, name)).isDirectory())
    .sort();
}

async function main() {
  const results = [];
  for (const kind of ['form', 'approval']) {
    for (const dir of fixtureDirs(kind)) {
      const input = readJson(join(ROOT, kind, dir, 'input.json'));
      const expected = readJson(join(ROOT, kind, dir, 'expected.json'));
      const computed = kind === 'form' ? await runForm(input) : await runApproval(input);
      const actual = pick(computed, expected);
      const mismatch_keys = Object.keys(expected)
        .filter((key) => key !== 'fixture_id' && key !== 'assertions')
        .filter((key) => !deepEqual(actual[key], expected[key]));
      results.push({
        fixture_id: expected.fixture_id ?? dir,
        class: kind,
        match: mismatch_keys.length === 0,
        actual,
        expected,
        mismatch_keys
      });
    }
  }

  const all_match = results.every((r) => r.match);
  const payload = { fixtures: results, all_match };
  const line = JSON.stringify(payload);
  writeFileSync(new URL('./.run-fixtures-result.json', import.meta.url), `${line}\n`);
  process.stdout.write(`${line}\n`);
  process.exit(all_match ? 0 : 1);
}

main().catch((error) => {
  process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
  process.exit(2);
});
