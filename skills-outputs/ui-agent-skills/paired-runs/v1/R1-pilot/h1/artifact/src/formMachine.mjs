import { validateProfile } from './validation.mjs';

export const STATE = Object.freeze({
  IDLE: 'idle',
  VALIDATING: 'validating',
  SUBMITTING: 'submitting',
  SUCCESS: 'success',
  ERROR: 'error'
});

export function createFormMachine({ userId, profile, api, requireConfirmation = true }) {
  let current = { ...profile };
  let state = STATE.IDLE;
  let errors = {};
  let errorFields = [];
  let submitBlocked = false;
  let persisted = false;
  let persistedPayload = null;
  let feedback = null;
  const gates = [];
  const events = [];

  const check = () => validateProfile(current);

  function snapshot() {
    const verdict = check();
    return {
      final_state: state,
      persisted,
      error_fields: [...errorFields],
      submit_blocked: submitBlocked,
      human_gates: gates.map((gate) => ({ ...gate })),
      persisted_payload: persistedPayload,
      profile: { ...current },
      valid: verdict.valid,
      errors: { ...errors },
      feedback,
      events: events.map((event) => ({ ...event }))
    };
  }

  async function dispatch(action) {
    const from = state;
    let to = state;

    switch (action.action) {
      case 'edit': {
        if (state === STATE.SUBMITTING) {
          submitBlocked = true;
          feedback = { kind: 'info', message: '提交中，输入已锁定' };
          break;
        }
        if (
          action.field &&
          Object.prototype.hasOwnProperty.call(current, action.field) &&
          action.value !== undefined
        ) {
          current[action.field] = action.value;
        }
        state = STATE.VALIDATING;
        const verdict = check();
        errors = verdict.errors;
        errorFields = verdict.error_fields;
        submitBlocked = false;
        persisted = false;
        feedback = null;
        to = state;
        break;
      }

      case 'validate': {
        const verdict = check();
        errors = verdict.errors;
        errorFields = verdict.error_fields;
        if (state !== STATE.SUBMITTING) state = STATE.VALIDATING;
        to = state;
        break;
      }

      case 'submit': {
        if (requireConfirmation && action.role !== 'user') {
          submitBlocked = true;
          state = STATE.ERROR;
          feedback = { kind: 'gate', message: '需要用户显式确认后才能提交' };
          to = state;
          break;
        }
        const verdict = check();
        errors = verdict.errors;
        errorFields = verdict.error_fields;
        if (!verdict.valid) {
          submitBlocked = true;
          state = STATE.ERROR;
          feedback = { kind: 'error', message: '请先修正校验错误' };
          to = state;
          break;
        }
        gates.push({ role: 'user', signed: true, at_step: action.seq });
        submitBlocked = false;
        state = STATE.SUBMITTING;
        feedback = { kind: 'info', message: '提交中' };
        to = state;
        break;
      }

      case 'persist': {
        if (state !== STATE.SUBMITTING) {
          submitBlocked = true;
          feedback = { kind: 'error', message: '尚未进入提交态' };
          to = state;
          break;
        }
        if (action.response_code && action.response_code !== 200) {
          api.injectFailure(action.response_code);
        }
        const response = await api.persist(userId, current);
        if (response.status === 200) {
          state = STATE.SUCCESS;
          persisted = true;
          persistedPayload = response.record;
          errors = {};
          errorFields = [];
          submitBlocked = false;
          feedback = { kind: 'success', message: '资料已保存' };
        } else {
          state = STATE.ERROR;
          persisted = false;
          persistedPayload = null;
          errorFields = Array.isArray(response.error_fields) ? [...response.error_fields] : [];
          submitBlocked = false;
          feedback = {
            kind: 'error',
            message: `${response.message || '保存失败'}（${response.status}）`
          };
        }
        to = state;
        break;
      }

      case 'recover': {
        if (action.profile && typeof action.profile === 'object') current = { ...action.profile };
        state = STATE.VALIDATING;
        const verdict = check();
        errors = verdict.errors;
        errorFields = verdict.error_fields;
        submitBlocked = false;
        persisted = false;
        feedback = null;
        to = state;
        break;
      }

      default: {
        feedback = { kind: 'error', message: `未知动作 ${action.action}` };
        to = state;
      }
    }

    events.push({ seq: action.seq, action: action.action, from, to });
    return { from, to, ...snapshot() };
  }

  return { dispatch, snapshot };
}
