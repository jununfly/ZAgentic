import { MockRequestStore } from './store.mjs';
import { validateRequest } from './validation.mjs';
import { checkActor } from './roles.mjs';
import { MockServer } from '../mock/server.mjs';
import { STABLE_PATH } from '../mock/constants.mjs';

export const APPROVAL_STATES = {
  DRAFT: 'draft',
  SUBMITTED: 'submitted',
  UNDER_REVIEW: 'under_review',
  APPROVED: 'approved',
  REJECTED: 'rejected'
};

// 费用报销审批状态机。
// 迁移： draft -> submitted (申请人显式确认提交) ;
//        submitted -> under_review (系统路由给审批人) ;
//        under_review -> approved / rejected (审批人显式确认决定，驳回必须带理由) ;
//        rejected -> draft (申请人修改后重提，生成新版本，旧版本留在历史里) ;
//        under_review -> under_review (审批超时升级，只标记不前进、不伪造成功或失败)。
// gate 约定：角色合法的一次尝试都会被记录，signed 表示这次人工确认是否真正生效；
// 角色不合法时 deny-first，不产生 gate。
export class ApprovalFlow {
  constructor({
    requestId = 'expense-001',
    request = {},
    applicantId = 'user',
    approverId = null,
    store,
    initialState = APPROVAL_STATES.DRAFT
  } = {}) {
    this.requestId = requestId;
    this.request = { amount: 0, currency: 'CNY', reason: '', attachment_ref: null, ...request };
    this.applicantId = applicantId;
    this.approverId = approverId;
    this.store = store ?? new MockRequestStore({ server: new MockServer() });
    this.state = initialState;

    this.version = 1;
    this.history = [];
    this.gates = [];
    this.writes = 0;
    this.persisted = false;
    this.escalated = false;
    this.fallback = null;
    this.explicit_marker = false;
    this.lastDecision = null;
    this.error_fields = [];
    this.errors = [];
    const initial = validateRequest(this.request);
    this.errors = initial.errors;
    this.error_fields = initial.error_fields;
  }

  get locked() {
    return this.state !== APPROVAL_STATES.DRAFT;
  }

  async persist({ kind, scenario, decision = null }) {
    this.writes += 1;
    const record = {
      requestId: this.requestId,
      version: this.version,
      state: this.state,
      request: { ...this.request },
      applicantId: this.applicantId,
      approverId: this.approverId,
      decision,
      kind,
      at: new Date().toISOString()
    };
    const response = await this.store.save(this.requestId, record, { scenario });
    if (response.ok) {
      this.persisted = true;
      if (kind === 'submit' || kind === 'decision') this.history.push(record);
      return { ok: true, code: response.code };
    }
    return { ok: false, code: response.code, error: response.error };
  }

  edit(field, value) {
    if (this.locked) {
      return { ok: false, reason: 'input_locked', ignored: true };
    }
    if (value !== undefined) this.request[field] = value;
    if (field === 'amount' && typeof this.request.amount === 'string' && this.request.amount !== '') {
      this.request.amount = Number(this.request.amount);
    }
    const result = validateRequest(this.request);
    this.errors = result.errors;
    this.error_fields = result.error_fields;
    return { ok: true, ...result };
  }

  async submitRequest({ role = 'applicant', actorId = null, confirm = false, step = null, scenario } = {}) {
    const guard = checkActor({ role, actorId, applicantId: this.applicantId, action: 'submit' });
    if (!guard.allowed) {
      return { ok: false, denied: true, reason: guard.reason, field: guard.field, message: guard.message };
    }

    if (this.state !== APPROVAL_STATES.DRAFT) {
      this.gates.push({ role, signed: false, at_step: step });
      return { ok: false, duplicate: true, reason: 'state_locked' };
    }

    const result = validateRequest(this.request);
    this.errors = result.errors;
    this.error_fields = result.error_fields;
    if (!result.valid) {
      this.gates.push({ role, signed: false, at_step: step });
      return { ok: false, blocked: true, reason: 'client_validation', error_fields: result.error_fields };
    }

    if (!confirm) {
      this.gates.push({ role, signed: false, at_step: step });
      return { ok: false, blocked: true, reason: 'confirm_required' };
    }

    this.state = APPROVAL_STATES.SUBMITTED;
    this.gates.push({ role, signed: true, at_step: step });
    const write = await this.persist({ kind: 'submit', scenario });
    if (!write.ok) {
      this.state = APPROVAL_STATES.DRAFT;
      return { ok: false, reason: 'persist_failed', error: write.error, state: this.state };
    }
    return { ok: true, state: this.state };
  }

  route({ role = 'system', step = null } = {}) {
    const guard = checkActor({ role, action: 'route' });
    if (!guard.allowed) {
      return { ok: false, denied: true, reason: guard.reason, field: guard.field, message: guard.message };
    }
    if (this.state !== APPROVAL_STATES.SUBMITTED) {
      return { ok: false, reason: 'state_locked' };
    }
    this.state = APPROVAL_STATES.UNDER_REVIEW;
    return { ok: true, state: this.state, at_step: step };
  }

  async decide({ action, role = 'approver', actorId = null, confirm = false, reason = null, step = null, scenario } = {}) {
    const guard = checkActor({ role, actorId, applicantId: this.applicantId, action });
    if (!guard.allowed) {
      return { ok: false, denied: true, reason: guard.reason, field: guard.field, message: guard.message };
    }

    if (this.state !== APPROVAL_STATES.UNDER_REVIEW) {
      this.gates.push({ role, signed: false, at_step: step });
      return { ok: false, reason: 'state_locked' };
    }

    if (action === 'reject' && String(reason ?? '').trim().length === 0) {
      this.gates.push({ role, signed: false, at_step: step });
      return { ok: false, blocked: true, reason: 'reason_required', field: 'reason' };
    }

    if (!confirm) {
      this.gates.push({ role, signed: false, at_step: step });
      return { ok: false, blocked: true, reason: 'confirm_required' };
    }

    const target = action === 'approve' ? APPROVAL_STATES.APPROVED : APPROVAL_STATES.REJECTED;
    this.state = target;
    this.lastDecision = { action, reason: reason ?? null, actorId, at_step: step, version: this.version };
    this.gates.push({ role, signed: true, at_step: step });
    const write = await this.persist({ kind: 'decision', scenario, decision: this.lastDecision });
    if (!write.ok) {
      this.state = APPROVAL_STATES.UNDER_REVIEW;
      return { ok: false, reason: 'persist_failed', error: write.error, state: this.state };
    }
    return { ok: true, state: this.state };
  }

  // 审批超时升级：停留在 under_review，只做显式标记并回退到稳定路径，等待人工接管。
  escalateOnTimeout({ role = 'system', step = null } = {}) {
    const guard = checkActor({ role, action: 'timeout' });
    if (!guard.allowed) {
      return { ok: false, denied: true, reason: guard.reason, field: guard.field, message: guard.message };
    }
    if (this.state !== APPROVAL_STATES.UNDER_REVIEW) {
      return { ok: false, reason: 'state_locked' };
    }
    this.escalated = true;
    this.fallback = STABLE_PATH;
    this.explicit_marker = true;
    return { ok: true, state: this.state, escalated: true, at_step: step };
  }

  // 驳回后申请人改完重新提交，形成新的一版；被驳回的旧版本保留在 history 中。
  revise({ role = 'applicant', actorId = null, step = null } = {}) {
    const guard = checkActor({ role, actorId, applicantId: this.applicantId, action: 'submit' });
    if (this.state !== APPROVAL_STATES.REJECTED) {
      return { ok: false, reason: 'state_locked' };
    }
    if (!guard.allowed) {
      return { ok: false, denied: true, reason: guard.reason, field: guard.field, message: guard.message };
    }
    this.history.push({
      version: this.version,
      state: APPROVAL_STATES.REJECTED,
      request: { ...this.request },
      decision: this.lastDecision
    });
    this.version += 1;
    this.state = APPROVAL_STATES.DRAFT;
    this.escalated = false;
    this.explicit_marker = false;
    this.fallback = null;
    this.lastDecision = null;
    return { ok: true, state: this.state, version: this.version, at_step: step };
  }
}
