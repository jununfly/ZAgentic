import { OUTCOME } from './constants.mjs';

// 离线 mock 服务端：不联网、不依赖任何三方包。
// 每个 scenario 的结果都是固定的，失败的写永远不会返回 ok:true。
const SCENARIOS = {
  [OUTCOME.OK]: { ok: true, code: 200, error: null },
  [OUTCOME.CONFLICT]: { ok: false, code: 422, error: 'server_side_constraint' },
  [OUTCOME.TIMEOUT]: { ok: false, code: 0, error: 'timeout' }
};

export class MockServer {
  constructor({ latencyMs = 0 } = {}) {
    this.latencyMs = latencyMs;
    this.calls = 0;
  }

  async write(payload, { scenario = OUTCOME.OK } = {}) {
    this.calls += 1;
    if (this.latencyMs > 0) {
      await new Promise((resolve) => setTimeout(resolve, this.latencyMs));
    }
    const outcome = SCENARIOS[scenario] ?? SCENARIOS[OUTCOME.CONFLICT];
    return { ...outcome, payload };
  }
}
