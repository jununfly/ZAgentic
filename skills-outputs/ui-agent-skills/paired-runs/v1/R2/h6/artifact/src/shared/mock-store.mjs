// 本地 mock 持久化层：零依赖、无网络。写入次数由 store 自己记账，状态机侧只读它。
export const TRANSPORT_CODE = Object.freeze({
  OK: 200,
  CONSTRAINT_VIOLATION: 422,
  TIMEOUT: 0,
});

export const TRANSPORT_ERROR = Object.freeze({
  CONSTRAINT: 'server_side_constraint',
  TIMEOUT: 'timeout',
});

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export function createMockStore(name) {
  const records = new Map();
  const journal = [];
  let writes = 0;
  let lastCode = null;

  return {
    name,
    records,
    journal,
    get writeCount() {
      return writes;
    },
    get lastResponseCode() {
      return lastCode;
    },

    read(key) {
      return records.get(key) ?? null;
    },

    // 模拟一次服务端写请求。422 与超时必须如实返回，不得降级为成功。
    async send(key, payload, code = TRANSPORT_CODE.OK, { budgetMs = 5 } = {}) {
      if (code === TRANSPORT_CODE.TIMEOUT) {
        await wait(budgetMs);
        lastCode = TRANSPORT_CODE.TIMEOUT;
        return { ok: false, code: TRANSPORT_CODE.TIMEOUT, error: TRANSPORT_ERROR.TIMEOUT, persisted: false };
      }
      await wait(0);
      if (code === TRANSPORT_CODE.CONSTRAINT_VIOLATION) {
        lastCode = code;
        return { ok: false, code, error: TRANSPORT_ERROR.CONSTRAINT, persisted: false };
      }
      writes += 1;
      lastCode = TRANSPORT_CODE.OK;
      const revision = { key, payload: structuredClone(payload), at: writes };
      records.set(key, revision.payload);
      journal.push(revision);
      return { ok: true, code: TRANSPORT_CODE.OK, error: null, persisted: true, revision };
    },
  };
}
