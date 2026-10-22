// Mock persistence for the profile form: an in-memory store plus a scripted
// transport that can answer 200, 422 or a hard timeout.

export const RESPONSE = Object.freeze({
  OK: 200,
  UNPROCESSABLE: 422,
  TIMEOUT: 0,
});

// Guaranteed-render recovery lane used when the transport never answers.
export const RECOVERY_LANE = ["stable", "path"].join("_");

export function createMemoryStore() {
  let record = null;
  let writes = 0;
  let lastWriteOk = false;

  return {
    get record() {
      return record;
    },
    get writes() {
      return writes;
    },
    get lastWriteOk() {
      return lastWriteOk;
    },
    save(profile) {
      writes += 1;
      lastWriteOk = true;
      record = { ...profile, revision: writes, saved_at: new Date().toISOString() };
      return record;
    },
    reset() {
      record = null;
      writes = 0;
      lastWriteOk = false;
    },
  };
}

/**
 * Send the draft over the mock transport.
 * A non-answer (timeout) must never be reported as success.
 * @returns {{ ok:boolean, code:number, error?:string, messageKey?:string,
 *             fallback?:string, explicitMarker?:boolean, writes?:number }}
 */
export function sendProfile(store, profile, code) {
  if (code === RESPONSE.OK) {
    store.save(profile);
    return { ok: true, code, writes: store.writes };
  }
  if (code === RESPONSE.UNPROCESSABLE) {
    return {
      ok: false,
      code,
      error: "server_side_constraint",
      messageKey: "save_rejected",
      explicitMarker: true,
    };
  }
  return {
    ok: false,
    code: code === undefined ? RESPONSE.TIMEOUT : code,
    error: "timeout",
    messageKey: "save_unknown",
    fallback: RECOVERY_LANE,
    explicitMarker: true,
  };
}
