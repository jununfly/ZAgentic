// Mock persistence for the profile form: 200 / 422 / timeout are all representable.
// Nothing in here may turn a failure into a success-looking result.

import { DeniedError, sleep, createCommitStore } from '../core.mjs';

export const SAVE_SCENARIOS = Object.freeze(['ok', 'constraint', 'timeout']);

export const DEFAULT_TIMEOUT_MS = 1500;

export class UnknownResponseError extends DeniedError {
  constructor(code) {
    super(`Unsupported mock response code: ${String(code)}`, {
      rejected: [String(code)],
      known: [...RESPONSE_CODE_TABLE.keys()].map(String),
    });
    this.name = 'UnknownResponseError';
  }
}

const RESPONSE_CODE_TABLE = new Map([
  [200, { kind: 'ok', error: null }],
  [422, { kind: 'constraint', error: 'server_side_constraint' }],
  [0, { kind: 'timeout', error: 'timeout' }],
]);

export function supportedResponseCodes() {
  return [...RESPONSE_CODE_TABLE.keys()];
}

export function outcomeFromCode(code) {
  const numeric = Number(code);
  const entry = RESPONSE_CODE_TABLE.get(numeric);
  // deny-first: an unmodelled status code must not be squeezed into a neighbouring meaning.
  if (!entry) throw new UnknownResponseError(code);
  return { code: numeric, kind: entry.kind, error: entry.error };
}

export function scenarioFromCode(code) {
  return outcomeFromCode(code).kind;
}

export const SAVE_MESSAGES = Object.freeze({
  ok: 'Profile saved',
  constraint: 'Server rejected the profile (422). Nothing was saved.',
  timeout: 'Save request timed out. Saved state is unconfirmed - please retry.',
});

export function createProfileApi({ latency = 0, timeoutMs = DEFAULT_TIMEOUT_MS } = {}) {
  return {
    latency,
    timeoutMs,
    async save(record, scenario = 'ok') {
      await sleep(latency);
      if (scenario === 'timeout') {
        // Represented as a rejection carrying the timeout outcome - never as a saved record.
        const failure = new Error('save request timed out');
        failure.outcome = { code: 0, kind: 'timeout', error: 'timeout' };
        throw failure;
      }
      if (scenario === 'constraint') {
        return { code: 422, kind: 'constraint', error: 'server_side_constraint', message: SAVE_MESSAGES.constraint };
      }
      return { code: 200, kind: 'ok', error: null, message: SAVE_MESSAGES.ok };
    },
  };
}

export function createProfileStore() {
  return createCommitStore();
}
