// Profile edit form: client validation + explicit submit gate + locked submitting
// + mock persistence with 422 and timeout outcomes. No success is ever faked.

export const FORM_STATES = Object.freeze({
  IDLE: 'idle',
  VALIDATING: 'validating',
  SUBMITTING: 'submitting',
  SUCCESS: 'success',
  ERROR: 'error',
});

export const BIO_MAX = 120;
export const NICKNAME_MAX = 40;

// Route taken when the outcome is unknown (timeout): keep the user on a stable
// screen instead of implying the save went through.
export const FALLBACK_ROUTE = 'stable_path';

const EDITABLE = new Set([FORM_STATES.IDLE, FORM_STATES.VALIDATING, FORM_STATES.ERROR]);
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[A-Za-z]{2,}$/;
const FIELDS = new Set(['nickname', 'email', 'bio']);

export function createProfile(seed = {}) {
  return {
    nickname: String(seed.nickname ?? ''),
    email: String(seed.email ?? ''),
    bio: String(seed.bio ?? ''),
  };
}

export function validateProfile(profile) {
  const errors = {};
  const nickname = String(profile.nickname ?? '');
  const email = String(profile.email ?? '').trim();
  const bio = String(profile.bio ?? '');

  if (!nickname.trim()) errors.nickname = '昵称必填';
  else if (nickname.trim().length > NICKNAME_MAX) errors.nickname = `昵称最多 ${NICKNAME_MAX} 个字符`;

  if (!email) errors.email = '邮箱必填';
  else if (!EMAIL_RE.test(email)) errors.email = '邮箱格式不正确，例如 name@example.com';

  if (bio.length > BIO_MAX) errors.bio = `简介最多 ${BIO_MAX} 个字符（当前 ${bio.length}）`;

  const errorFields = Object.keys(errors);
  return { valid: errorFields.length === 0, errors, errorFields };
}

export class ProfileForm {
  constructor({ profile, store, user = 'user-001', initialState = FORM_STATES.IDLE } = {}) {
    if (!store) throw new Error('ProfileForm requires a store');
    this.user = user;
    this.profile = createProfile(profile);
    this.store = store;
    this.state = EDITABLE.has(initialState) || initialState === FORM_STATES.SUCCESS ? initialState : FORM_STATES.IDLE;
    this.gates = [];
    this.lastError = null;
    this.duplicateSuppressed = false;
    this.revalidate();
  }

  revalidate() {
    const result = validateProfile(this.profile);
    this.errors = result.errors;
    this.errorFields = result.errorFields;
    return result;
  }

  get valid() {
    return this.errorFields.length === 0;
  }

  edit(field, value) {
    if (!EDITABLE.has(this.state)) return { ok: false, reason: 'input_locked' };
    if (!FIELDS.has(field)) return { ok: false, reason: 'unknown_field', field };
    this.profile[field] = String(value ?? '');
    this.state = FORM_STATES.VALIDATING;
    this.revalidate();
    return { ok: true, errorFields: [...this.errorFields] };
  }

  validate() {
    const result = this.revalidate();
    if (this.state === FORM_STATES.IDLE) this.state = FORM_STATES.VALIDATING;
    return { result: result.valid ? 'valid' : 'invalid', errorFields: [...result.errorFields] };
  }

  // `confirmed` is the human gate: the caller must pass the state of an explicit
  // confirmation control. Nothing is submitted on the user's behalf.
  submit({ confirmed = false, role = 'user', step = null } = {}) {
    if (this.state === FORM_STATES.SUBMITTING) {
      this.duplicateSuppressed = true;
      return { ok: false, reason: 'input_locked' };
    }
    if (this.state === FORM_STATES.SUCCESS) return { ok: false, reason: 'already_saved' };
    if (role !== 'user') return { ok: false, reason: 'role_not_allowed' };
    if (this.state === FORM_STATES.ERROR) return { ok: false, reason: 'recover_first' };

    this.revalidate();
    if (!this.valid) {
      this.state = FORM_STATES.VALIDATING;
      return { ok: false, reason: 'client_validation', errorFields: [...this.errorFields] };
    }
    if (!confirmed) return { ok: false, reason: 'human_gate_unsigned' };

    this.gates.push({ role: 'user', signed: true, at_step: step });
    this.state = FORM_STATES.SUBMITTING;
    return { ok: true };
  }

  // responseCode 200 -> persisted; 422 -> recoverable error; 0 -> timeout
  // (outcome unknown, explicit marker + stable route).
  persist({ responseCode = 200 } = {}) {
    if (this.state !== FORM_STATES.SUBMITTING) return { ok: false, reason: 'not_submitting' };
    const code = Number(responseCode);

    if (code === 200) {
      this.lastError = null;
      this.state = FORM_STATES.SUCCESS;
      this.store.commit({ user: this.user, profile: { ...this.profile } });
      return { ok: true, persisted: true };
    }

    if (code === 0) {
      this.lastError = {
        kind: 'timeout',
        recoverable: true,
        fallback: FALLBACK_ROUTE,
        explicitMarker: true,
        message: '请求超时，无法确认是否已保存',
      };
    } else {
      this.lastError = {
        kind: code === 422 ? 'server_validation' : 'server_error',
        code,
        recoverable: code < 500,
        fallback: null,
        explicitMarker: true,
        message: code === 422 ? '服务端拒绝了本次修改（422）' : `服务端错误（${code}）`,
      };
    }
    this.state = FORM_STATES.ERROR;
    return { ok: false, reason: this.lastError.kind };
  }

  recover() {
    if (this.state !== FORM_STATES.ERROR) return { ok: false, reason: 'not_in_error' };
    this.state = FORM_STATES.VALIDATING;
    return { ok: true };
  }

  report() {
    const v = validateProfile(this.profile);
    const settled = this.state === FORM_STATES.SUCCESS || this.state === FORM_STATES.SUBMITTING;
    return {
      final_state: this.state,
      persisted: this.store.persisted,
      error_fields: [...v.errorFields],
      submit_blocked: settled ? false : !v.valid,
      human_gates: this.gates.map((g) => ({ role: g.role, signed: g.signed, at_step: g.at_step })),
      duplicate_suppressed: this.duplicateSuppressed,
      writes: this.store.writes,
      recoverable: this.state === FORM_STATES.ERROR ? Boolean(this.lastError && this.lastError.recoverable) : false,
      fallback: this.lastError ? this.lastError.fallback : null,
      explicit_marker: Boolean(this.state === FORM_STATES.ERROR && this.lastError && this.lastError.explicitMarker),
    };
  }
}

// Browser-side mock transport: same shape as a fetch result, delay included so the
// locked "submitting" state is observable.
export function mockPersist(profile, { mode = 'ok', delay = 900 } = {}) {
  return new Promise((resolve) => {
    setTimeout(() => {
      if (mode === 'timeout') resolve({ responseCode: 0, error: 'timeout' });
      else if (mode === 'constraint') resolve({ responseCode: 422, error: 'server_side_constraint' });
      else resolve({ responseCode: 200, profile });
    }, delay);
  });
}
