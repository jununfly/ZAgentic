import { MockServer } from '../mock/server.mjs';

// 报销单 mock 持久化：按申请号保存当前版本，并把历史版本（含被驳回的旧版）留在 versions 里。
export class MockRequestStore {
  constructor({ server } = {}) {
    this.server = server ?? new MockServer();
    this.records = new Map();
    this.history = new Map();
    this.writeCount = 0;
  }

  async save(requestId, record, { scenario } = {}) {
    this.writeCount += 1;
    const response = await this.server.write({ requestId, record }, { scenario });
    if (response.ok) {
      this.records.set(requestId, { ...record });
      const list = this.history.get(requestId) ?? [];
      list.push({ ...record });
      this.history.set(requestId, list);
      return { ...response, record: this.records.get(requestId) };
    }
    return response;
  }

  read(requestId) {
    return this.records.get(requestId) ?? null;
  }

  versions(requestId) {
    return this.history.get(requestId) ?? [];
  }
}
