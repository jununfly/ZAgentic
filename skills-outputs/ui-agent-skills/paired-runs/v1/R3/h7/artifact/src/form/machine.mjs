import { MockProfileStore } from './store.mjs';
import { validateProfile } from './validation.mjs';
import { MockServer } from '../mock/server.mjs';
import { STABLE_PATH, isUnresolvedOutcome } from '../mock/constants.mjs';

export const FORM_STATES = {
  IDLE: 'idle',
  VALIDATING: 'validating',
  SUBMITTING: 'submitting',
  SUCCESS: 'success',
  ERROR: 'error'
};

// 资料编辑表单状态机。
// 迁移： idle -> validating (编辑) ; validating -> submitting (显式确认后提交) ;
//        submitting -> success (200) / error (422 或超时) ; error -> validating (返回修改，可恢复) ;
//        success -> validating (再次编辑)。
// 提交中锁定输入：submitting 期间任何提交都会被吞掉，只可能落一次写。
export class FormFlow {
  constructor({ userId = 'user', profile = {}, store, initialState = FORM_STATES.IDLE } = {}) {
    this.userId = userId;
    this.profile = { nickname: '', email: '', bio: '', ...profile };
    this.store = store ?? new MockProfileStore({ server: new MockServer() });
    this.state = initialState;

    this.error_fields = [];
    this.errors = [];
    this.gates = [];
    this.writes = 0;
    this.persisted = false;
    this.duplicateSuppressed = false;
    this.lastError = null;
    this.lastCode = null;
    this.fallback = null;
    this.explicit_marker = false;
    // 稳定路径上的最后已知良好草稿：任何失败回退都以此为基准，不丢用户输入。
    this.stableDraft = { ...this.profile };
    const initial = validateProfile(this.profile);
    this.errors = initial.errors;
    this.error_fields = initial.error_fields;
  }

  get locked() {
    return this.state === FORM_STATES.SUBMITTING;
  }

  get submit_blocked() {
    return this.error_fields.length > 0;
  }

  get recoverable() {
    return this.state === FORM_STATES.ERROR;
  }

  validate() {
    if (this.locked) return { ok: false, reason: 'input_locked', ...this.snapshotValidation() };
    const result = validateProfile(this.profile);
    this.errors = result.errors;
    this.error_fields = result.error_fields;
    if (this.state === FORM_STATES.IDLE || this.state === FORM_STATES.SUCCESS || this.state === FORM_STATES.ERROR) {
      this.state = FORM_STATES.VALIDATING;
    }
    return { ok: true, ...result };
  }

  snapshotValidation() {
    return { valid: this.error_fields.length === 0, errors: this.errors, error_fields: this.error_fields };
  }

  edit(field, value) {
    if (this.locked) {
      return { ok: false, reason: 'input_locked', ignored: true };
    }
    if (value !== undefined && this.profile[field] !== value) {
      this.profile[field] = value;
    }
    this.state = FORM_STATES.VALIDATING;
    const result = validateProfile(this.profile);
    this.errors = result.errors;
    this.error_fields = result.error_fields;
    return { ok: true, ...result };
  }

  // 提交必须由用户显式确认：confirm=false 时不落 gate、不改状态。
  // 被客户端校验拦下时同样不落 gate —— 用户根本没走到确认这一步。
  submit({ role = 'user', confirm = false, step = null } = {}) {
    if (this.locked) {
      this.duplicateSuppressed = true;
      return { ok: false, ignored: true, reason: 'input_locked' };
    }
    const result = validateProfile(this.profile);
    this.errors = result.errors;
    this.error_fields = result.error_fields;
    if (!result.valid) {
      this.state = FORM_STATES.VALIDATING;
      return { ok: false, blocked: true, reason: 'client_validation', error_fields: result.error_fields };
    }
    if (!confirm) {
      return { ok: false, blocked: true, reason: 'confirm_required' };
    }
    this.state = FORM_STATES.SUBMITTING;
    this.gates.push({ role, signed: true, at_step: step });
    return { ok: true, pending: true };
  }

  // 把 submitting 态推进到服务端结局。成功才写库；422 与超时都进 error 且 persisted 保持 false。
  async resolveSubmission({ scenario } = {}) {
    if (!this.locked) {
      return { ok: false, reason: 'not_submitting' };
    }
    this.writes += 1;
    const response = await this.store.save(this.userId, this.profile, { scenario });
    this.lastCode = response.code;
    if (response.ok) {
      this.state = FORM_STATES.SUCCESS;
      this.persisted = true;
      this.lastError = null;
      this.stableDraft = { ...this.profile };
      return { ok: true, code: response.code, state: this.state };
    }
    this.state = FORM_STATES.ERROR;
    this.persisted = false;
    this.lastError = response.error;
    this.fallback = STABLE_PATH;
    this.explicit_marker = isUnresolvedOutcome(response.error);
    this.profile = { ...this.stableDraft };
    return { ok: false, code: response.code, error: response.error, state: this.state };
  }

  // 失败后回到可编辑态：保留用户输入与显式标记，允许改完再提交。
  recover() {
    if (this.state !== FORM_STATES.ERROR) {
      return { ok: false, reason: 'not_recoverable' };
    }
    const result = validateProfile(this.profile);
    this.errors = result.errors;
    this.error_fields = result.error_fields;
    this.state = FORM_STATES.VALIDATING;
    return { ok: true, state: this.state };
  }
}
