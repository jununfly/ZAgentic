// 费用报销审批 - mock 持久化层
// 每次提交 / 每次审批决定都会产生一条写入；历史版本只追加不覆盖。

export function createMemoryBackend() {
  const map = new Map();
  const list = [];
  return {
    read(key) {
      return map.has(key) ? map.get(key) : null;
    },
    write(key, value) {
      map.set(key, value);
      return value;
    },
    append(entry) {
      list.push(entry);
      return entry;
    },
    all() {
      return list.slice();
    },
  };
}

export function createBrowserBackend() {
  try {
    if (typeof localStorage !== 'undefined' && localStorage) {
      const listKey = 'expense:history';
      const list = JSON.parse(localStorage.getItem(listKey) ?? '[]');
      return {
        read(key) {
          const raw = localStorage.getItem(`expense:${key}`);
          return raw ? JSON.parse(raw) : null;
        },
        write(key, value) {
          localStorage.setItem(`expense:${key}`, JSON.stringify(value));
          return value;
        },
        append(entry) {
          list.push(entry);
          localStorage.setItem(listKey, JSON.stringify(list));
          return entry;
        },
        all() {
          return list.slice();
        },
      };
    }
  } catch {
    // 退回内存
  }
  return createMemoryBackend();
}

export function createRequestStore(options = {}) {
  const backend = options.backend ?? createMemoryBackend();
  let writes = 0;
  return {
    get writes() {
      return writes;
    },
    read(key) {
      return backend.read(key);
    },
    write(key, value) {
      writes += 1;
      backend.write(key, value);
      backend.append({ key, at: new Date().toISOString(), record: value });
      return { ok: true };
    },
    history() {
      return backend.all();
    },
  };
}
