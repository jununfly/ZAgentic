// Profile edit form state machine.
//
// States:  idle -> validating -> submitting -> success | error
//          error -> validating          (recoverable: fix and resubmit)
//          success -> validating        (edit again after a save)
//
// Invariants enforced here, independent of any UI:
//  * every keystroke re-runs validation (live validation)
//  * submit is refused unless the form is valid AND a human confirmed it
//  * inputs are locked while a submit is in flight
//  * a failed persist returns the form to an editable state, keeping values

import { validateProfile, validateField, FIELDS } from './validation.mjs';

export const STATES = Object.freeze({
  IDLE: 'idle',
  VALIDATING: 'validating',
  SUBMITTING: 'submitting',
  SUCCESS: 'success',
  ERROR: 'error',
});

/** Allowed transitions, used both as documentation and as a runtime guard. */
export const TRANSITIONS = Object.freeze({
  idle: ['validating'],
  validating: ['validating', 'submitting'],
  submitting: ['success', 'error'],
  success: ['validating'],
  error: ['validating'],
});

export class TransitionError extends Error {}

/**
 * @param {object} opts
 * @param {string} opts.user            logical owner of the profile
 * @param {{load:Function, save:Function, setNextResponse?:Function}} opts.repo
 */
export function createProfileForm({ user, repo }) {
  const values = { ...(repo.load() ?? {}) };
  for (const field of FIELDS) {
    if (typeof values[field] !== 'string') values[field] = '';
  }

  const errors = {};
  const touched = Object.fromEntries(FIELDS.map((f) => [f, false]));

  const state = {
    status: STATES.IDLE,
    locked: false,
    persisted: false,
    persistedPayload: null,
    submitBlocked: false,
    humanGates: [],
    feedback: null, // { kind: 'success' | 'error' | 'info', message: string }
    lastResponseCode: null,
  };

  function transition(next) {
    const allowed = TRANSITIONS[state.status] ?? [];
    if (!allowed.includes(next)) {
      throw new TransitionError(`illegal transition ${state.status} -> ${next}`);
    }
    state.status = next;
  }

  function recompute() {
    const result = validateProfile(values);
    for (const field of FIELDS) delete errors[field];
    Object.assign(errors, result.errors);
    state.locked = state.status === STATES.SUBMITTING;
    return result;
  }

  function snapshot() {
    const { errorFields } = validateProfile(values);
    return {
      user,
      status: state.status,
      values: { ...values },
      errors: { ...errors },
      errorFields,
      valid: errorFields.length === 0,
      touched: { ...touched },
      locked: state.status === STATES.SUBMITTING,
      persisted: state.persisted,
      persistedPayload: state.persistedPayload ? { ...state.persistedPayload } : null,
      submitBlocked: state.submitBlocked,
      humanGates: state.humanGates.map((g) => ({ ...g })),
      feedback: state.feedback ? { ...state.feedback } : null,
      lastResponseCode: state.lastResponseCode,
    };
  }

  /** Live validation entry point: called on every user keystroke. */
  function edit(field, value) {
    if (!FIELDS.includes(field)) throw new Error(`unknown field ${field}`);
    if (state.status === STATES.SUBMITTING) {
      return { ok: false, blocked: true, reason: 'locked', snapshot: snapshot() };
    }
    if (state.status === STATES.SUCCESS) {
      transition(STATES.VALIDATING);
    } else if (state.status === STATES.IDLE || state.status === STATES.ERROR) {
      transition(STATES.VALIDATING);
    } else if (state.status !== STATES.VALIDATING) {
      throw new TransitionError(`cannot edit from ${state.status}`);
    }
    values[field] = value == null ? '' : String(value);
    touched[field] = true;
    const result = recompute();
    state.persisted = false;
    state.feedback = result.valid
      ? null
      : { kind: 'error', message: '请先修正表单中的错误' };
    return {
      ok: true,
      state: state.status,
      valid: result.valid,
      errors: { ...result.errors },
      snapshot: snapshot(),
    };
  }

  /** Explicit validation pass (system driven, also used by the runner). */
  function validate() {
    if (state.status !== STATES.VALIDATING) {
      if (state.status === STATES.IDLE) transition(STATES.VALIDATING);
      else throw new TransitionError(`cannot validate from ${state.status}`);
    }
    const result = recompute();
    return {
      result: result.valid ? 'valid' : 'invalid',
      state: state.status,
      errors: { ...result.errors },
      errorFields: result.errorFields,
      snapshot: snapshot(),
    };
  }

  /**
   * Submit request. A human gate is required: only an explicit user
   * confirmation can move validating -> submitting.
   */
  function submit({ confirmed = false, role = 'user', atStep = null } = {}) {
    const gateSigned = confirmed === true && role === 'user';
    const current = recompute();

    if (state.status !== STATES.VALIDATING) {
      state.submitBlocked = true;
      return {
        ok: false,
        blocked: true,
        reason: `cannot submit from ${state.status}`,
        snapshot: snapshot(),
      };
    }
    if (!gateSigned) {
      state.submitBlocked = true;
      state.feedback = { kind: 'error', message: '提交需要用户显式确认' };
      return { ok: false, blocked: true, reason: 'confirmation-required', snapshot: snapshot() };
    }
    if (!current.valid) {
      state.submitBlocked = true;
      state.feedback = { kind: 'error', message: '存在校验错误，无法提交' };
      return {
        ok: false,
        blocked: true,
        reason: 'invalid',
        errorFields: current.errorFields,
        snapshot: snapshot(),
      };
    }

    state.humanGates.push({ role: 'user', signed: true, at_step: atStep });
    state.submitBlocked = false;
    transition(STATES.SUBMITTING);
    state.locked = true;
    state.feedback = { kind: 'info', message: '正在保存…' };
    return { ok: true, state: state.status, snapshot: snapshot() };
  }

  /**
   * Apply the outcome of the mocked persistence call.
   * @param {number} [responseCode] overrides the repo's queued response
   */
  function persist(responseCode) {
    if (state.status !== STATES.SUBMITTING) {
      throw new TransitionError(`cannot persist from ${state.status}`);
    }
    if (typeof repo.setNextResponse === 'function' && responseCode != null) {
      repo.setNextResponse(responseCode);
    }
    const response = repo.save({ ...values });
    state.lastResponseCode = response.code;
    if (response.code === 200) {
      transition(STATES.SUCCESS);
      state.persisted = true;
      state.persistedPayload = { ...response.record };
      state.locked = false;
      state.feedback = { kind: 'success', message: '资料已保存' };
      return { ok: true, code: 200, state: state.status, snapshot: snapshot() };
    }
    transition(STATES.ERROR);
    state.persisted = false;
    state.locked = false;
    state.feedback = {
      kind: 'error',
      message: response.message || `保存失败（HTTP ${response.code}），请修改后重试`,
    };
    return { ok: false, code: response.code, state: state.status, snapshot: snapshot() };
  }

  /** Abandon an in-flight submit (network cancel / user reset). */
  function cancel() {
    if (state.status !== STATES.SUBMITTING) return snapshot();
    transition(STATES.ERROR);
    state.locked = false;
    state.feedback = { kind: 'error', message: '提交已取消，可修改后重试' };
    return snapshot();
  }

  return {
    snapshot,
    getState: () => state.status,
    edit,
    validate,
    submit,
    persist,
    cancel,
    fieldError: (field) => validateField(field, values[field]),
  };
}
