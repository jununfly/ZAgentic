// Expense approval: applicant submits, approver decides, role guard is deny-first,
// rejected versions stay on the timeline and a resubmit opens a new version.

export const APPROVAL_STATES = Object.freeze({
  DRAFT: 'draft',
  SUBMITTED: 'submitted',
  UNDER_REVIEW: 'under_review',
  APPROVED: 'approved',
  REJECTED: 'rejected',
});

// Route used when a review times out: the request keeps its state and waits for a
// human to take over instead of auto-approving or auto-rejecting.
export const FALLBACK_ROUTE = 'stable_path';

const FIELDS = new Set(['amount', 'currency', 'reason', 'attachment_ref']);

export function createRequest(seed = {}) {
  return {
    amount: Number(seed.amount ?? 0),
    currency: seed.currency || 'CNY',
    reason: String(seed.reason ?? ''),
    attachment_ref: seed.attachment_ref ?? null,
  };
}

export function validateRequest(request) {
  const errors = {};
  const amount = Number(request.amount);
  if (!Number.isFinite(amount) || amount <= 0) errors.amount = '金额必须大于 0';
  if (!String(request.reason ?? '').trim()) errors.reason = '事由必填';
  const errorFields = Object.keys(errors);
  return { valid: errorFields.length === 0, errors, errorFields };
}

export class ExpenseApproval {
  constructor({
    request,
    applicant,
    approver = null,
    store,
    initialState = APPROVAL_STATES.DRAFT,
    version = 1,
  } = {}) {
    if (!store) throw new Error('ExpenseApproval requires a store');
    this.request = createRequest(request);
    this.applicant = applicant;
    this.approver = approver;
    this.store = store;
    this.state = Object.values(APPROVAL_STATES).includes(initialState) ? initialState : APPROVAL_STATES.DRAFT;
    this.version = version;
    this.gates = [];
    this.history = [];
    this.denied = null;
    this.suppressed = false;
    this.escalation = null;
    this.errors = {};
    this.errorFields = [];
  }

  get editable() {
    return this.state === APPROVAL_STATES.DRAFT;
  }

  updateField(field, value) {
    if (!this.editable) return { ok: false, reason: 'input_locked' };
    if (!FIELDS.has(field)) return { ok: false, reason: 'unknown_field', field };
    this.request[field] = field === 'amount' ? Number(value) : value;
    const v = validateRequest(this.request);
    this.errors = v.errors;
    this.errorFields = v.errorFields;
    return { ok: true, errorFields: [...v.errorFields] };
  }

  submit({ confirmed = false, role = 'applicant', actor, step = null } = {}) {
    const who = actor ?? this.applicant;
    if (this.state === APPROVAL_STATES.SUBMITTED || this.state === APPROVAL_STATES.UNDER_REVIEW) {
      this.suppressed = true;
      this.gates.push({ role: 'applicant', signed: false, at_step: step });
      return { ok: false, reason: 'duplicate_submission' };
    }
    if (!this.editable) return { ok: false, reason: 'invalid_state' };
    if (role !== 'applicant' || who !== this.applicant) return { ok: false, reason: 'role_not_applicant' };

    const v = validateRequest(this.request);
    this.errors = v.errors;
    this.errorFields = v.errorFields;
    if (!v.valid) {
      this.gates.push({ role: 'applicant', signed: false, at_step: step });
      return { ok: false, reason: 'client_validation', errorFields: [...v.errorFields] };
    }
    if (!confirmed) {
      this.gates.push({ role: 'applicant', signed: false, at_step: step });
      return { ok: false, reason: 'human_gate_unsigned' };
    }

    this.gates.push({ role: 'applicant', signed: true, at_step: step });
    this.state = APPROVAL_STATES.SUBMITTED;
    this.history.push({ type: 'submit', version: this.version, at: step });
    this.store.commit({
      applicant: this.applicant,
      request: { ...this.request },
      status: APPROVAL_STATES.SUBMITTED,
      version: this.version,
    });
    return { ok: true, version: this.version };
  }

  route() {
    if (this.state !== APPROVAL_STATES.SUBMITTED) return { ok: false, reason: 'invalid_state' };
    this.state = APPROVAL_STATES.UNDER_REVIEW;
    this.history.push({ type: 'route', version: this.version });
    return { ok: true };
  }

  #guardApprover(role, actor) {
    if (role !== 'approver' || !actor || actor === this.applicant) {
      const reason = role !== 'approver' ? 'role_not_approver' : 'self_approval_forbidden';
      this.denied = { reason, role, actor, at_state: this.state };
      this.history.push({ type: 'denied', reason, role, version: this.version });
      return { ok: false, reason };
    }
    return { ok: true };
  }

  approve({ role = 'approver', actor, reason = '', confirmed = false, step = null } = {}) {
    if (this.state !== APPROVAL_STATES.UNDER_REVIEW) return { ok: false, reason: 'invalid_state' };
    const who = actor ?? this.approver;
    const guard = this.#guardApprover(role, who);
    if (!guard.ok) return guard;
    if (!confirmed) return { ok: false, reason: 'human_gate_unsigned' };

    this.gates.push({ role: 'approver', signed: true, at_step: step });
    this.state = APPROVAL_STATES.APPROVED;
    this.history.push({ type: 'approve', version: this.version, reason, at: step });
    this.store.commit({
      applicant: this.applicant,
      request: { ...this.request },
      status: APPROVAL_STATES.APPROVED,
      version: this.version,
      decision: { outcome: 'approved', reason: reason || null, by: who, at: step },
    });
    return { ok: true };
  }

  reject({ role = 'approver', actor, reason = '', confirmed = false, step = null } = {}) {
    if (this.state !== APPROVAL_STATES.UNDER_REVIEW) return { ok: false, reason: 'invalid_state' };
    const who = actor ?? this.approver;
    const guard = this.#guardApprover(role, who);
    if (!guard.ok) return guard;
    if (!String(reason).trim()) return { ok: false, reason: 'reason_required' };
    if (!confirmed) return { ok: false, reason: 'human_gate_unsigned' };

    this.gates.push({ role: 'approver', signed: true, at_step: step });
    this.state = APPROVAL_STATES.REJECTED;
    this.history.push({ type: 'reject', version: this.version, reason, at: step });
    this.store.commit({
      applicant: this.applicant,
      request: { ...this.request },
      status: APPROVAL_STATES.REJECTED,
      version: this.version,
      decision: { outcome: 'rejected', reason, by: who, at: step },
    });
    return { ok: true };
  }

  timeout({ step = null } = {}) {
    if (this.state !== APPROVAL_STATES.UNDER_REVIEW) return { ok: false, reason: 'invalid_state' };
    this.escalation = {
      reason: 'approval_timeout',
      at: step,
      route: FALLBACK_ROUTE,
      needsHumanTakeover: true,
    };
    this.history.push({ type: 'escalated', version: this.version, at: step });
    return { ok: true, escalated: true };
  }

  // Rejected -> draft with a new version; the previous version stays in history.
  revise({ step = null } = {}) {
    if (this.state !== APPROVAL_STATES.REJECTED) return { ok: false, reason: 'invalid_state' };
    this.version += 1;
    this.state = APPROVAL_STATES.DRAFT;
    this.duplicateSuppressed = false;
    this.history.push({ type: 'revise', version: this.version, at: step });
    return { ok: true, version: this.version };
  }

  report() {
    return {
      final_state: this.state,
      persisted: this.store.persisted,
      human_gates: this.gates.map((g) => ({ role: g.role, signed: g.signed, at_step: g.at_step })),
      denied: this.denied !== null,
      duplicate_suppressed: this.suppressed,
      writes: this.store.writes,
      escalated: this.escalation !== null,
      version: this.version,
    };
  }
}
