import { validateProfile } from './validation.mjs';

function clone(value) {
  return value === undefined ? undefined : structuredClone(value);
}

export function createMockApi({ initial = {}, onPersist = null } = {}) {
  const store = new Map();
  let revision = 0;
  let queuedFailure = null;

  for (const [userId, profile] of Object.entries(initial)) {
    store.set(userId, {
      user: userId,
      profile: { ...profile },
      revision: ++revision,
      savedAt: new Date(0).toISOString()
    });
  }

  return {
    load(userId) {
      const record = store.get(userId);
      if (!record) return { status: 404, ok: false, error_fields: ['user'], message: '用户不存在' };
      return { status: 200, ok: true, record: clone(record) };
    },
    injectFailure(status) {
      queuedFailure = status;
    },
    async persist(userId, profile) {
      if (queuedFailure) {
        const status = queuedFailure;
        queuedFailure = null;
        return {
          status,
          ok: false,
          error_fields: [],
          message: status === 422 ? '服务端校验未通过' : '保存失败，请重试'
        };
      }

      const check = validateProfile(profile);
      if (!check.valid) {
        return {
          status: 422,
          ok: false,
          error_fields: check.error_fields,
          errors: check.errors,
          message: '服务端校验未通过'
        };
      }

      const record = {
        user: userId,
        profile: { ...profile },
        revision: ++revision,
        savedAt: new Date().toISOString()
      };
      store.set(userId, record);
      if (onPersist) await onPersist(clone(record));
      return { status: 200, ok: true, record: clone(record) };
    }
  };
}
