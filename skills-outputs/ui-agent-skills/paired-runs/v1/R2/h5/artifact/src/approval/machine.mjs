// 费用报销审批 - 状态机
// draft -> submitted -> under_review -> approved | rejected -> draft(新版本)
import { canDecide, canSubmit, ROLE_APPLICANT, ROLE_APPROVER } from './roles.mjs';
import { createRequestStore } from './store.mjs';

export const APPROVAL_STATES = ['draft', 'submitted', 'under_review', 'approved', 'rejected'];

export const TRANSITIONS = {
  draft: ['submitted'],
  submitted: ['under_review', 'draft'],
  under_review: ['approved', 'rejected', 'under_review', 'draft'],
  approved: [],
  rejected: ['draft'],
};

function validateRequest(request = {}) {
  const errors = {};
  const amount = Number(request.amount);
  const reason = typeof request.reason === 'string' ? request.reason.trim() : '';

  if (!Number.isFinite(amount) || amount <= 0) {
    errors.amount = '金额必须大于 0';
  }
  if (!reason) {
    errors.reason = '事由为必填项';
  }

  const errorFields = Object.keys(errors);
  return { valid: errorFields.length === 0, errorFields, errors };
}

export function createApprovalMachine(config = {}) {
  const applicant = config.applicant ?? 'unknown-applicant';
  const approver = config.approver ?? null;
  const key = config.key ?? `expense:${applicant}`;
  const store = config.store ?? createRequestStore();
  let state = config.initialState ?? 'draft';
  let version = config.version ?? 1;
  const request = { amount: 0, currency: 'CNY', reason: '', attachment_ref: null, ...(config.request ?? {}) };
  let errorFields = [];
  let errors = {};
  let persisted = false;
  let submitBlocked = false;
  let escalated = false;
  let fallback = null;
  let explicitMarker = false;
  let lastDecision = null;
  let denial = null;
  const gates = [];
  const decisions = [];

  function can(next) {
    return (TRANSITIONS[state] ?? []).includes(next);
  }
  function go(next) {
    if (!can(next)) return false;
    state = next;
    return true;
  }
  // 调用方可以传角色名，也可以传具体用户 id
  function resolveActor(actor) {
    if (actor === ROLE_APPROVER) return approver;
    if (actor === ROLE_APPLICANT) return applicant;
    return actor;
  }

  function validate() {
    const r = validateRequest(request);
    errorFields = r.errorFields;
    errors = r.errors;
    return r;
  }

  return {
    getState: () => state,
    getRequest: () => ({ ...request }),
    getErrors: () => ({ ...errors }),
    getErrorFields: () => [...errorFields],
    getVersion: () => version,
    getDecisions: () => decisions.map((d) => ({ ...d })),
    getDenial: () => (denial ? { ...denial } : null),

    edit(field, value) {
      if (state !== 'draft') return { ok: false, reason: 'input_locked', state };
      request[field] = value;
      const r = validate();
      return { ok: true, state, valid: r.valid, errorFields: [...errorFields] };
    },

    validate() {
      const r = validate();
      return { valid: r.valid, errorFields: [...errorFields], errors: { ...errors }, state };
    },

    // 申请人提交：需校验通过 + 显式确认
    submit({ confirm = false, atStep = null, role = ROLE_APPLICANT, actor = null } = {}) {
      const who = resolveActor(actor);
      if (!canSubmit({ role, actor: who, applicant })) {
        denial = { denied: true, reason: 'role_not_allowed', role, actor: who };
        return { ok: false, denied: true, reason: 'role_not_allowed', state };
      }
      const gate = { role: ROLE_APPLICANT, signed: false, at_step: atStep };
      gates.push(gate);

      const r = validate();
      if (!r.valid) {
        submitBlocked = true;
        return { ok: false, reason: 'client_validation', errorFields: [...errorFields], state };
      }
      if (state !== 'draft') {
        // submitted / under_review 期间重复提交：拒绝，不创建新申请
        return { ok: false, reason: 'duplicate_or_locked', duplicate: true, state };
      }
      if (!confirm) return { ok: false, reason: 'confirm_required', state };

      gate.signed = true;
      go('submitted');
      store.write(`${key}:v${version}`, { version, state: 'submitted', request: { ...request }, applicant });
      persisted = true;
      return { ok: true, state, version };
    },

    // 系统路由：submitted -> under_review
    route({ atStep = null } = {}) {
      if (state !== 'submitted') return { ok: false, reason: 'not_submitted', state };
      go('under_review');
      store.write(`${key}:v${version}:route`, { version, state: 'under_review', at_step: atStep });
      return { ok: true, state };
    },

    // 审批超时：保持在 under_review，显式标记 + 升级，不伪造成功/失败
    timeout({ atStep = null } = {}) {
      if (state !== 'under_review') return { ok: false, reason: 'not_under_review', state };
      escalated = true;
      fallback = 'stable_path';
      explicitMarker = true;
      store.write(`${key}:v${version}:timeout`, { version, state, at_step: atStep, escalated: true });
      return { ok: true, state, escalated: true };
    },

    approve({ confirm = false, atStep = null, role = null, actor = null, reason = null } = {}) {
      const who = resolveActor(actor);
      if (!canDecide({ role, actor: who, approver, applicant })) {
        denial = { denied: true, reason: 'role_not_allowed', role, actor: who, field: 'role' };
        return { ok: false, denied: true, reason: 'role_not_allowed', state };
      }
      const gate = { role: ROLE_APPROVER, signed: false, at_step: atStep };
      gates.push(gate);
      if (state !== 'under_review') return { ok: false, reason: 'not_under_review', state };
      if (!confirm) return { ok: false, reason: 'confirm_required', state };

      gate.signed = true;
      go('approved');
      lastDecision = { version, action: 'approve', reason: reason ?? '', by: actor ?? approver };
      decisions.push(lastDecision);
      store.write(`${key}:v${version}:decision`, { version, state: 'approved', ...lastDecision });
      persisted = true;
      return { ok: true, state, version };
    },

    // 驳回必须写理由
    reject({ confirm = false, atStep = null, role = null, actor = null, reason = null } = {}) {
      const who = resolveActor(actor);
      if (!canDecide({ role, actor: who, approver, applicant })) {
        denial = { denied: true, reason: 'role_not_allowed', role, actor: who, field: 'role' };
        return { ok: false, denied: true, reason: 'role_not_allowed', state };
      }
      const gate = { role: ROLE_APPROVER, signed: false, at_step: atStep };
      gates.push(gate);
      if (state !== 'under_review') return { ok: false, reason: 'not_under_review', state };
      if (!reason || !String(reason).trim()) {
        return { ok: false, reason: 'reason_required', field: 'reason', state };
      }
      if (!confirm) return { ok: false, reason: 'confirm_required', state };

      gate.signed = true;
      go('rejected');
      lastDecision = { version, action: 'reject', reason: String(reason), by: actor ?? approver };
      decisions.push(lastDecision);
      store.write(`${key}:v${version}:decision`, { version, state: 'rejected', ...lastDecision });
      persisted = true;
      return { ok: true, state, version };
    },

    // 被驳回后：回到 draft 形成新版本，历史记录保留
    revise() {
      if (state !== 'rejected') return { ok: false, reason: 'not_rejected', state };
      version += 1;
      go('draft');
      submitBlocked = false;
      return { ok: true, state, version };
    },

    snapshot() {
      return {
        final_state: state,
        persisted,
        error_fields: [...errorFields],
        submit_blocked: submitBlocked || errorFields.length > 0,
        version,
        writes: store.writes,
        escalated,
        fallback,
        explicit_marker: explicitMarker,
        last_decision: lastDecision ? { ...lastDecision } : null,
        denied: Boolean(denial),
        human_gates: gates.map((g) => ({ ...g })),
      };
    },
  };
}
