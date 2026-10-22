#!/usr/bin/env node
// Fixture driver: replays a fixture's action list against the real form state
// machine, then reports the resulting snapshot as the last stdout line.
//
//   node run-f1.mjs <input.json> <expected.json>

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createProfileForm } from './src/machine.mjs';
import { createMockRepo } from './src/persistence.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const PAYLOAD_PATH = resolve(here, '.data/profile.json');

function readJson(path) {
  return JSON.parse(readFileSync(resolve(process.cwd(), path), 'utf8'));
}

function stable(value) {
  return JSON.stringify(value);
}

function run() {
  const [inputPath, expectedPath] = process.argv.slice(2);
  if (!inputPath || !expectedPath) {
    console.error('usage: node run-f1.mjs <input.json> <expected.json>');
    process.exit(2);
  }

  const input = readJson(inputPath);
  const expected = readJson(expectedPath);
  const mismatches = [];

  const base = createMockRepo({ user: input.user, profile: input.profile });
  const repo = {
    ...base,
    save(values) {
      const result = base.save(values);
      if (result.code === 200) {
        mkdirSync(dirname(PAYLOAD_PATH), { recursive: true });
        writeFileSync(PAYLOAD_PATH, `${JSON.stringify(result.record, null, 2)}\n`, 'utf8');
      }
      return result;
    },
  };

  const form = createProfileForm({ user: input.user, repo });

  if (form.getState() !== input.initial_state) {
    mismatches.push(`initial state: expected ${input.initial_state}, got ${form.getState()}`);
  }

  for (const step of input.actions ?? []) {
    const before = form.getState();
    if (before !== step.from) {
      mismatches.push(`step ${step.seq}: from-state expected ${step.from}, got ${before}`);
    }
    try {
      switch (step.action) {
        case 'edit': {
          const current = form.snapshot().values[step.field];
          form.edit(step.field, step.value === undefined ? current : step.value);
          break;
        }
        case 'validate': {
          const result = form.validate();
          if (step.result && result.result !== step.result) {
            mismatches.push(
              `step ${step.seq}: validate expected ${step.result}, got ${result.result} ` +
                JSON.stringify(result.errorFields),
            );
          }
          break;
        }
        case 'submit': {
          const result = form.submit({
            confirmed: step.confirmed ?? step.role === 'user',
            role: step.role,
            atStep: step.seq,
          });
          if (!result.ok && step.to === 'submitting') {
            mismatches.push(`step ${step.seq}: submit blocked (${result.reason})`);
          }
          break;
        }
        case 'persist': {
          form.persist(step.response_code);
          break;
        }
        case 'cancel': {
          form.cancel();
          break;
        }
        case 'wait': {
          break;
        }
        default:
          mismatches.push(`step ${step.seq}: unsupported action ${step.action}`);
      }
    } catch (error) {
      mismatches.push(`step ${step.seq}: ${error.message}`);
    }

    const after = form.getState();
    if (after !== step.to) {
      mismatches.push(`step ${step.seq}: to-state expected ${step.to}, got ${after}`);
    }
  }

  const snap = form.snapshot();
  const output = {
    final_state: snap.status,
    persisted: snap.persisted,
    error_fields: snap.errorFields,
    submit_blocked: snap.submitBlocked,
    human_gates: snap.humanGates,
    persisted_payload: snap.persistedPayload,
  };

  for (const key of ['final_state', 'persisted', 'error_fields', 'submit_blocked', 'human_gates']) {
    if (key in expected && stable(expected[key]) !== stable(output[key])) {
      mismatches.push(
        `${key}: expected ${stable(expected[key])}, got ${stable(output[key])}`,
      );
    }
  }

  if (snap.persisted) {
    let onDisk = null;
    try {
      onDisk = JSON.parse(readFileSync(PAYLOAD_PATH, 'utf8'));
    } catch {
      mismatches.push('persisted=true but no payload file was written');
    }
    if (onDisk && stable(onDisk) !== stable(snap.persistedPayload)) {
      mismatches.push('persisted payload does not match the on-disk record');
    }
  }

  if (mismatches.length) {
    console.error(`FAIL ${expected.fixture_id ?? input.fixture_id}`);
    for (const line of mismatches) console.error(`  - ${line}`);
  } else {
    console.error(`PASS ${expected.fixture_id ?? input.fixture_id}`);
  }

  process.stdout.write(`${stable(output)}\n`);
  process.exit(mismatches.length ? 1 : 0);
}

run();
