// 用户资料编辑表单的状态机。
// 状态、a human gate、失败 fallback 与写入计数都在这里计算；driver 与 UI 都只是它的调用方。
import { createMockStore, TRANSPORT_CODE, TRANSPORT_ERROR } from '../shared/mock-store.mjs';
import { validateProfile, PROFILE_FIELDS } from './validation.mjs';

export const FORM_STATES = Object.freeze({
  IDLE: 'idle',
  VALIDATING: 'validating',
  SUBMITTING: 'submitting',
  SUCCESS: 'success',
  ERROR: 'error',
});

// 失败处理策略：由实现自己声明并被机器依此执行，不是从外部期待值抄来的。
export const FAILURE_POLICY = Object.freeze({
  [TRANSPORT_CODE.CONSTRAINT_VIOLATION]: {
    target: FORM_STATES.ERROR,
    error: TRANSPORT_ERROR.CONSTRAINT,
    recoverable: true,
    marker: true,
    fallback: null,
    message: '服务端校验未通过（422），资料未保存',
  },
  [TRANSPORT_CODE.TIMEOUT]: {
    target: FORM_STATES.ERROR,
    error: TRANSPORT_ERROR.TIMEOUT,
    recoverable: true,
    marker: true,
    fallback: 'stable_path',
    message: '请求超时，未确认是否保存，请重试',
  },
});

const WRITE_ROLE = 'user';
const SYSTEM_ROLE = 'system';

export function createProfileFlow(options = {}) {
  const {
    user = 'user-001',
    profile = {},
    initialState = FORM_STATES.IDLE,
    store = createMockStore('profile'),
    key = 'profile:current',
  } = options;

  const values = {};
  for (const field of PROFILE_FIELDS) values[field] = profile[field] ?? '';

  const state = {
    status: initialState,
    values,
    persisted: false,
    duplicateSuppressed: false,
    failure: null,
    fallback: null,
    gates: [],
    conflicts: [],
    log: [],
  };

  const errorsOf = (snapshotValues) => validateProfile(snapshotValues);
  const currentErrorFields = () => Object.keys(errorsOf(state.values));

  // 可以发起提交的状态：尚未锁定且未在成功终态。
  const canSubmit = () =>
    [FORM_STATES.IDLE, FORM_STATES.VALIDATING, FORM_STATES.ERROR].includes(state.status);

  // 「不能提交」= 有字段级错误，或正在提交中（输入已被锁）。成功态不算被拦。
  const isSubmissionBlocked = () =>
    currentErrorFields().length > 0 || state.status === FORM_STATES.SUBMITTING;

  const record = (entry) => state.log.push(entry);

  function ensureFrom(action, allowed) {
    if (!action.from) return true;
    if (state.status !== action.from) {
      state.conflicts.push({ seq: action.seq ?? null, expected_from: action.from, actual: state.status });
      return false;
    }
    if (allowed && !allowed.includes(action.from)) {
      state.conflicts.push({ seq: action.seq ?? null, unexpected_from: action.from });
      return false;
    }
    return true;
  }

  function signGate(action) {
    state.gates.push({
      role: action.role ?? WRITE_ROLE,
      signed: true,
      at_step: action.seq ?? state.log.length + 1,
    });
  }

  const handlers = {
    edit(action) {
      const allowedFrom = [FORM_STATES.IDLE, FORM_STATES.VALIDATING, FORM_STATES.ERROR, FORM_STATES.SUCCESS];
      if (state.status === FORM_STATES.SUBMITTING) {
        record({ action: 'edit', ok: false, reason: 'input_locked' });
        return { ok: false, reason: 'input_locked', status: state.status };
      }
      if (!ensureFrom(action, allowedFrom)) {
        record({ action: 'edit', ok: false, reason: 'state_mismatch' });
        return { ok: false, reason: 'state_mismatch', status: state.status };
      }
      const field = action.field;
      if (field && Object.prototype.hasOwnProperty.call(values, field) && action.value !== undefined) {
        values[field] = action.value;
      }
      state.status = FORM_STATES.VALIDATING;
      state.failure = null;
      state.fallback = null;
      record({ action: 'edit', ok: true, field: field ?? null });
      return { ok: true, status: state.status, error_fields: currentErrorFields() };
    },

    validate(action) {
      if (!ensureFrom(action)) return { ok: false, reason: 'state_mismatch', status: state.status };
      const fields = currentErrorFields();
      state.status = FORM_STATES.VALIDATING;
      record({ action: 'validate', ok: fields.length === 0, error_fields: fields });
      return { ok: fields.length === 0, status: state.status, error_fields: fields };
    },

    submit(action) {
      if (action.role && action.role !== WRITE_ROLE && action.role !== SYSTEM_ROLE) {
        record({ action: 'submit', ok: false, reason: 'role_not_permitted' });
        return { ok: false, reason: 'role_not_permitted', status: state.status };
      }
      const fields = currentErrorFields();
      if (fields.length > 0) {
        record({ action: 'submit', ok: false, blocked_by: 'client_validation', error_fields: fields });
        return { ok: false, blocked_by: 'client_validation', status: state.status, error_fields: fields };
      }
      if (state.status === FORM_STATES.SUBMITTING) {
        state.duplicateSuppressed = true;
        record({ action: 'submit', ok: false, result: 'ignored', reason: 'input_locked' });
        return { ok: false, result: 'ignored', reason: 'input_locked', status: state.status };
      }
      if (!canSubmit()) {
        record({ action: 'submit', ok: false, blocked_by: 'state_not_submittable' });
        return { ok: false, blocked_by: 'state_not_submittable', status: state.status };
      }
      // Human gate：必须由本人显式确认后才进入提交，绝不自动提交。
      if (!action.confirmed) {
        record({ action: 'submit', ok: false, reason: 'awaiting_human_gate' });
        return { ok: false, reason: 'awaiting_human_gate', status: state.status, needs_confirmation: true };
      }
      state.status = FORM_STATES.SUBMITTING;
      state.failure = null;
      state.fallback = null;
      signGate(action);
      record({ action: 'submit', ok: true });
      return { ok: true, status: state.status };
    },

    async persist(action) {
      const allowedFrom = [FORM_STATES.SUBMITTING];
      if (!ensureFrom(action, allowedFrom)) {
        record({ action: 'persist', ok: false, reason: 'state_mismatch' });
        return { ok: false, reason: 'state_mismatch', status: state.status };
      }
      const code = action.response_code ?? action.code ?? TRANSPORT_CODE.OK;
      const response = await store.send(key, { user, ...state.values }, code, {
        budgetMs: action.budget_ms ?? 5,
      });
      if (response.ok) {
        state.status = FORM_STATES.SUCCESS;
        state.persisted = true;
        state.failure = null;
        state.fallback = null;
        record({ action: 'persist', ok: true, code: response.code });
        return { ok: true, status: state.status, code: response.code };
      }
      const policy = FAILURE_POLICY[response.code] ?? FAILURE_POLICY[TRANSPORT_CODE.CONSTRAINT_VIOLATION];
      state.status = policy.target;
      state.failure = {
        code: response.code,
        error: policy.error,
        recoverable: policy.recoverable,
        marker: policy.marker,
        fallback: policy.fallback,
        message: policy.message,
      };
      state.fallback = policy.fallback;
      record({ action: 'persist', ok: false, code: response.code, error: policy.error });
      return { ok: false, status: state.status, code: response.code, error: policy.error };
    },

    recover(action) {
      const allowedFrom = [FORM_STATES.ERROR];
      if (!ensureFrom(action, allowedFrom)) {
        record({ action: 'recover', ok: false, reason: 'state_mismatch' });
        return { ok: false, reason: 'state_mismatch', status: state.status };
      }
      state.status = FORM_STATES.VALIDATING;
      state.failure = null;
      state.fallback = null;
      record({ action: 'recover', ok: true });
      return { ok: true, status: state.status, error_fields: currentErrorFields() };
    },
  };

  return {
    get user() {
      return user;
    },
    get state() {
      return state.status;
    },
    get values() {
      return { ...state.values };
    },
    get errors() {
      return errorsOf(state.values);
    },
    store,
    confirmInUi: true,

    async dispatch(action) {
      const handler = handlers[action.action];
      if (!handler) {
        record({ action: action.action, ok: false, reason: 'unknown_action' });
        return { ok: false, reason: 'unknown_action', status: state.status };
      }
      return handler(action);
    },

    snapshot() {
      const errorFields = currentErrorFields();
      return {
        final_state: state.status,
        persisted: state.persisted,
        error_fields: errorFields,
        submit_blocked: isSubmissionBlocked(),
        duplicate_suppressed: state.duplicateSuppressed,
        writes: store.writeCount,
        recoverable: Boolean(state.failure?.recoverable),
        fallback: state.fallback ?? null,
        explicit_marker: Boolean(state.failure?.marker),
        human_gates: state.gates.map((gate) => ({ ...gate })),
        conflicts: state.conflicts.map((item) => ({ ...item })),
      };
    },
  };
}
