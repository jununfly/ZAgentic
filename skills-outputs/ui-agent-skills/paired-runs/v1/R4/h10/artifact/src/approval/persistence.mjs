// Mock approval persistence layer. The driver uses latency 0, so writes resolve
// immediately. This models the backend store for expense-approval requests.

export function createApprovalApi({ latency = 0 } = {}) {
  const store = new Map(); // requestId -> record
  return {
    latency,
    async persist(requestId, record) {
      if (latency > 0) {
        await new Promise((resolve) => setTimeout(resolve, latency));
      }
      store.set(requestId, record);
      return { ok: true, requestId };
    },
    async read(requestId) {
      return store.get(requestId) ?? null;
    },
  };
}

export default createApprovalApi;
