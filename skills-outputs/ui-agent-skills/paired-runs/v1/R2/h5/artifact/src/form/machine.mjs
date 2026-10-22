// 用户资料编辑表单 - 状态机
// idle -> validating -> submitting -> success | error -> validating(可恢复)
import { validateProfile } from './validation.mjs';
import { createProfileStore } from './store.mjs';

export const FORM_STATES = ['idle', 'validating', 'submitting', 'success', 'error'];

export const TRANSITIONS = {
  idle: ['validating'],
  validating: ['validating', 'submitting', 'error'],
  submitting: ['success', 'error'],
  success: ['validating'],
  error: ['validating', 'submitting'],
};

export function createFormMachine(config = {}) {
  const user = config.user ?? 'anonymous';
  const store = config.store ?? createProfileStore(config.storeOptions);
  let state = config.initialState ?? 'idle';
  const fields = { nickname: '', email: '', bio: '', ...(config.profile ?? {}) };
  let errorFields = [];
  let errors = {};
  let locked = state === 'submitting';
  let persisted = false;
  let lastResponse = null;
  let duplicateSuppressed = false;
  let submitBlocked = false;
  let recoverable = false;
  let fallback = null;
  let explicitMarker = false;
  const gates = [];

  function can(next) {
    return (TRANSITIONS[state] ?? []).includes(next);
  }
  function go(next) {
    if (!can(next)) return false;
    state = next;
    return true;
  }
  function revalidate() {
    const r = validateProfile(fields);
    errorFields = r.errorFields;
    errors = r.errors;
    return r;
  }
  function pushGate(role, atStep) {
    const gate = { role, signed: true, at_step: atStep };
    gates.push(gate);
    return gate;
  }

  return {
    getState: () => state,
    getFields: () => ({ ...fields }),
    getErrors: () => ({ ...errors }),
    getErrorFields: () => [...errorFields],
    isLocked: () => locked,
    getLastResponse: () => lastResponse,
    readPersisted: () => store.read(user),

    // 用户输入：实时校验
    edit(field, value) {
      if (locked) return { ok: false, reason: 'input_locked', state };
      fields[field] = value;
      go('validating');
      const r = revalidate();
      return { ok: true, state, valid: r.valid, errorFields: [...errorFields] };
    },

    validate() {
      const r = revalidate();
      if (state === 'idle') go('validating');
      return { valid: r.valid, errorFields: [...errorFields], errors: { ...errors }, state };
    },

    // 提交：必须先通过校验 + 用户显式确认（Human gate）
    submit({ confirm = false, atStep = null, role = 'user' } = {}) {
      if (locked || state === 'submitting') {
        duplicateSuppressed = true;
        return { ok: false, reason: 'input_locked', duplicateSuppressed: true, state };
      }
      const r = revalidate();
      if (!r.valid) {
        submitBlocked = true;
        return { ok: false, reason: 'client_validation', errorFields: [...errorFields], state };
      }
      if (!confirm) {
        submitBlocked = true;
        return { ok: false, reason: 'confirm_required', state };
      }
      go('submitting');
      locked = true;
      submitBlocked = false;
      duplicateSuppressed = false;
      pushGate(role, atStep);
      return { ok: true, state };
    },

    // mock 服务端落库
    persist({ responseCode = 200, error = null } = {}) {
      if (state !== 'submitting') return { ok: false, reason: 'not_submitting', state };
      const force = responseCode === 200 ? null : { code: responseCode, error };
      const res = store.save(user, fields, { force });
      lastResponse = res;
      locked = false;
      if (res.ok) {
        persisted = true;
        recoverable = false;
        fallback = null;
        explicitMarker = false;
        go('success');
      } else {
        go('error');
        recoverable = true; // 失败后可改完再提交
        if (res.code === 0 || res.error === 'timeout') {
          fallback = 'stable_path'; // 超时：显式标记并回退到稳定路径，不伪造成功
          explicitMarker = true;
        }
      }
      return { ok: res.ok, code: res.code, error: res.error, state };
    },

    // 失败后恢复可编辑
    recover() {
      if (state !== 'error' && state !== 'success') return { ok: false, reason: 'not_recoverable', state };
      go('validating');
      submitBlocked = false;
      return { ok: true, state };
    },

    snapshot() {
      return {
        final_state: state,
        persisted,
        error_fields: [...errorFields],
        submit_blocked: submitBlocked || errorFields.length > 0,
        duplicate_suppressed: duplicateSuppressed,
        writes: store.writes,
        recoverable,
        fallback,
        explicit_marker: explicitMarker,
        last_error: lastResponse && !lastResponse.ok ? lastResponse.error : null,
        human_gates: gates.map((g) => ({ ...g })),
      };
    },
  };
}
