// Mock persistence for the approval flow: versioned, append-only ledger.

export function createApprovalStore() {
  const versions = [];
  const ledger = [];
  let writes = 0;
  let lastWriteOk = false;

  return {
    get versions() {
      return versions.map((entry) => ({ ...entry }));
    },
    get ledger() {
      return ledger.map((entry) => ({ ...entry }));
    },
    get writes() {
      return writes;
    },
    get lastWriteOk() {
      return lastWriteOk;
    },
    get latest() {
      return versions.length ? versions[versions.length - 1] : null;
    },
    save(record, note) {
      writes += 1;
      lastWriteOk = true;
      const entry = { ...record, revision: writes, saved_at: new Date().toISOString() };
      versions.push(entry);
      ledger.push({ at: entry.saved_at, revision: writes, state: entry.state, note: note ?? null });
      return entry;
    },
    recordRefusal(entry) {
      ledger.push({ at: new Date().toISOString(), revision: writes, state: entry.state ?? null, note: entry.note ?? null, refused: true });
    },
  };
}
