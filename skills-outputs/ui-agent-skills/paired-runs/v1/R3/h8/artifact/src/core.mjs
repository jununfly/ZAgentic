// Shared primitives: failure policy, unknown quartet, deny-first field check, idempotent commit store.
// No methodology vocabulary lives here - this is product runtime code.

export const FAILURE_POLICY = Object.freeze({
  fallback_route: 'stable_path',
  marker_label: 'state_unconfirmed',
});

export function unknownQuartet({ path, raw, reason, source }) {
  return { path, raw: raw === undefined ? null : raw, reason, source };
}

export class DeniedError extends Error {
  constructor(message, detail = {}) {
    super(message);
    this.name = 'DeniedError';
    this.detail = detail;
  }
}

// deny-first: an unregistered key is a hard rejection, never a silent drop.
export function assertKnown(key, registry, label = 'field') {
  if (!registry.includes(key)) {
    throw new DeniedError(`${label} is not registered: ${String(key)}`, {
      rejected: [String(key)],
      known: [...registry],
    });
  }
  return key;
}

export function stableStringify(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value) ?? 'null';
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`;
  const keys = Object.keys(value).sort();
  return `{${keys.map((k) => `${JSON.stringify(k)}:${stableStringify(value[k])}`).join(',')}}`;
}

export function createCommitStore() {
  const records = new Map();
  let writes = 0;
  return {
    get writes() {
      return writes;
    },
    size() {
      return records.size;
    },
    has(key) {
      return records.has(key);
    },
    get(key) {
      return records.get(key) ?? null;
    },
    keys() {
      return [...records.keys()];
    },
    // atomic commit with idempotency: replaying identical content does not add a write.
    commit({ key, value }) {
      if (records.has(key)) {
        if (stableStringify(records.get(key)) === stableStringify(value)) {
          return { written: false, reason: 'idempotent_replay', writes };
        }
        return { written: false, reason: 'revision_conflict', writes };
      }
      records.set(key, value);
      writes += 1;
      return { written: true, reason: 'ok', writes };
    },
  };
}

export function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
