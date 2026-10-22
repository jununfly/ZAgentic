// Mock persistence adapters. No network, no backend: a record is kept in memory
// (driver / tests) or in localStorage (browser demo). `writes` counts real commits
// so that duplicate submits can never look like two saves.

function core(initial) {
  let record = initial ? { ...initial } : null;
  let writes = 0;
  return {
    get record() {
      return record;
    },
    get writes() {
      return writes;
    },
    get persisted() {
      return record !== null;
    },
    commit(next) {
      if (!next || typeof next !== 'object') throw new Error('commit requires a record');
      record = { ...next, savedAt: new Date().toISOString() };
      writes += 1;
      return record;
    },
  };
}

export function createMemoryStore(initial = null) {
  return core(initial);
}

export function createLocalStore(storage, key) {
  let seed = null;
  try {
    seed = JSON.parse(storage.getItem(key) || 'null');
  } catch {
    seed = null;
  }
  const mem = core(seed);
  return {
    get record() {
      return mem.record;
    },
    get writes() {
      return mem.writes;
    },
    get persisted() {
      return mem.persisted;
    },
    commit(next) {
      const saved = mem.commit(next);
      storage.setItem(key, JSON.stringify(saved));
      return saved;
    },
    clear() {
      storage.removeItem(key);
    },
  };
}
