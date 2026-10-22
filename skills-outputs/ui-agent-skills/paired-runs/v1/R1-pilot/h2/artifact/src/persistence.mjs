// Local mock persistence layer. No network, no backend.
//
// The repo keeps the canonical profile record in memory and can be told which
// HTTP status the next save() should simulate, so both the happy path (200)
// and the failure path (422) are reproducible from the UI and from fixtures.

const MESSAGES = {
  200: 'ok',
  422: '保存失败：服务端校验未通过（HTTP 422）',
  500: '保存失败：服务端异常（HTTP 500）',
  0: '网络异常，请稍后重试',
};

/**
 * @param {{user:string, profile:object}} opts
 */
export function createMockRepo({ user, profile }) {
  let record = normalize(profile);
  const queue = [];

  function normalize(input) {
    return {
      user,
      nickname: String(input?.nickname ?? ''),
      email: String(input?.email ?? ''),
      bio: String(input?.bio ?? ''),
    };
  }

  return {
    load() {
      return { ...record };
    },
    /** Queue the status code for the next save() call. */
    setNextResponse(code) {
      queue.push(Number(code));
    },
    get pendingResponses() {
      return queue.length;
    },
    save(values) {
      const code = queue.length ? queue.shift() : 200;
      if (code === 200) {
        record = normalize(values);
        return { code, record: { ...record }, message: MESSAGES[200] };
      }
      return {
        code,
        record: null,
        message: MESSAGES[code] ?? `保存失败（HTTP ${code}）`,
      };
    },
    /** Current server-side record, regardless of form state. */
    peek() {
      return { ...record };
    },
  };
}

/**
 * Browser-side repository: same contract, but the record survives reloads via
 * localStorage when available.
 */
export function createBrowserRepo({ user, profile, storageKey = 'profile-edit:v1' }) {
  let record = null;
  try {
    const raw = globalThis.localStorage?.getItem(storageKey);
    record = raw ? JSON.parse(raw) : null;
  } catch {
    record = null;
  }
  if (!record) record = { user, ...profile };
  const mem = createMockRepo({ user, profile: record });

  return {
    ...mem,
    load: () => ({ ...mem.load() }),
    save(values) {
      const result = mem.save(values);
      if (result.code === 200) {
        try {
          globalThis.localStorage?.setItem(storageKey, JSON.stringify(result.record));
        } catch {
          /* storage disabled: in-memory only */
        }
      }
      return result;
    },
  };
}
