// persistence.mjs — profile form persistence (mock backend).
//
// createProfileApi returns a mock "server" used by the form machine. In the
// frozen driver the transport/park protocol carries the actual response code
// (200 / 422 / 0-timeout) and this api object is kept for parity with the
// approval side; latency is accepted but the harness always passes 0.

export function createProfileApi({ latency = 0 } = {}) {
  return {
    async load() {
      if (latency > 0) await new Promise((r) => setTimeout(r, latency));
      return { ok: true, profile: null };
    },
    async save(payload) {
      if (latency > 0) await new Promise((r) => setTimeout(r, latency));
      return { ok: true, savedAt: Date.now(), payload };
    },
  };
}
