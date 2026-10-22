// persistence.mjs — expense-approval persistence (mock backend).

export function createApprovalApi({ latency = 0 } = {}) {
  return {
    async save(payload) {
      if (latency > 0) await new Promise((r) => setTimeout(r, latency));
      return { ok: true, id: payload?.requestId, savedAt: Date.now() };
    },
    async load(id) {
      if (latency > 0) await new Promise((r) => setTimeout(r, latency));
      return { ok: true, id: id ?? null };
    },
  };
}
