// 用户资料 - mock 持久化层（浏览器落到 localStorage，Node 落到内存）
// 只做 mock：422 / 超时都如实返回失败，绝不伪造成功。

export function createMemoryBackend() {
  const map = new Map();
  return {
    read(key) {
      return map.has(key) ? map.get(key) : null;
    },
    write(key, value) {
      map.set(key, value);
      return value;
    },
  };
}

export function createBrowserBackend() {
  try {
    if (typeof localStorage !== 'undefined' && localStorage) {
      return {
        read(key) {
          const raw = localStorage.getItem(key);
          return raw ? JSON.parse(raw) : null;
        },
        write(key, value) {
          localStorage.setItem(key, JSON.stringify(value));
          return value;
        },
      };
    }
  } catch {
    // 隐私模式等场景下退回内存
  }
  return createMemoryBackend();
}

export function createProfileStore(options = {}) {
  const backend = options.backend ?? createMemoryBackend();
  let writes = 0;
  let nextResponse = options.nextResponse ?? null; // {code, error} 用于模拟服务端异常

  return {
    get writes() {
      return writes;
    },
    setNextResponse(res) {
      nextResponse = res;
    },
    read(user) {
      return backend.read(`profile:${user}`);
    },
    save(user, profile, opts = {}) {
      const forced = opts.force ?? nextResponse;
      if (forced) {
        const code = forced.code ?? 0;
        if (code !== 200) {
          // 真实失败：不写入、不计 writes
          return { ok: false, code, error: forced.error ?? (code === 0 ? 'timeout' : 'server_side_constraint') };
        }
      }
      writes += 1;
      backend.write(`profile:${user}`, { ...profile });
      return { ok: true, code: 200, error: null };
    },
  };
}
