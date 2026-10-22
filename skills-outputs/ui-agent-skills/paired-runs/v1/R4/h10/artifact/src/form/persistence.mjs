// Mock profile persistence layer. In this frozen harness the *response code*
// is supplied externally by the driver via the transport/park protocol, so the
// API here mainly models the "server write" side-effect. It is intentionally a
// no-op stub that resolves immediately (latency is mocked as 0 by the driver).

export function createProfileApi({ latency = 0 } = {}) {
  let writes = 0;
  return {
    latency,
    // Simulate persisting the profile to the backend. Resolves with a receipt.
    async persist(_payload) {
      if (latency > 0) {
        await new Promise((resolve) => setTimeout(resolve, latency));
      }
      writes += 1;
      return { ok: true, writes };
    },
    async read(_user) {
      return { ok: true };
    },
    get writes() {
      return writes;
    },
  };
}

export default createProfileApi;
