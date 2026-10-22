import { MockServer } from '../mock/server.mjs';

// 本地 mock 持久化：只写入内存 Map，失败时绝不留下「看起来成功」的记录。
export class MockProfileStore {
  constructor({ server } = {}) {
    this.server = server ?? new MockServer();
    this.records = new Map();
    this.writeCount = 0;
  }

  async save(userId, profile, { scenario } = {}) {
    this.writeCount += 1;
    const response = await this.server.write({ userId, profile }, { scenario });
    if (response.ok) {
      this.records.set(userId, { ...profile });
      return { ...response, record: this.records.get(userId) };
    }
    return response;
  }

  read(userId) {
    return this.records.get(userId) ?? null;
  }
}
