// 费用报销审批的状态机：申请人 / 审批人 / 工作流引擎三方动作与 gate 记账都在这里。
import { createMockStore, TRANSPORT_CODE } from '../shared/mock-store.mjs';
import {
  APPROVAL_ROLES,
  checkDecisionAuthority,
  checkRoutingAuthority,
  isApplicantActor,
} from './roles.mjs';

export const APPROVAL_STATES = Object.freeze({
  DRAFT: 'draft',
  SUBMITTED: 'submitted',
  UNDER_REVIEW: 'under_review',
  APPROVED: 'approved',
  REJECTED: 'rejected',
});

// 审批侧的失败/升级策略：由实现声明，机器照此执行。
export const ESCALATION_POLICY = Object.freeze({
  target: APPROVAL_STATES.UNDER_REVIEW,
  marker: true,
  fallback: 'stable_path',
  message: '审批超时已升级，等待人工接管，未产生通过或驳回结论',
});

function validateRequest(request) {
  const errors = {};
  const amount = Number(request.amount);
  if (!Number.isFinite(amount) || amount <= 0) {
    errors.amount = ['金额必须大于 0'];
  }
  if (String(request.reason ?? '').trim().length === 0) {
    errors.reason = ['事由为必填项'];
  }
  return errors;
}

export function createApprovalFlow(options = {}) {
  const {
    applicant = 'user-001',
    approver = null,
    request = {},
    initialState = APPROVAL_STATES.DRAFT,
    store = createMockStore('approval'),
  } = options;

  const parties = { applicant, approver };

  const state = {
    status: initialState,
    version: 1,
    draft: {
      amount: request.amount ?? null,
      currency: request.currency ?? 'CNY',
      reason: request.reason ?? '',
      attachment_ref: request.attachment_ref ?? null,
    },
    persisted: false,
    errors: validateRequest(request),
    history: [],
    gates: [],
    escalated: false,
    fallback: null,
    conflicts: [],
    log: [],
    decisions: [],
  };

  const record = (entry) => state.log.push(entry);
  const errorFields = () => Object.keys(validateRequest(state.draft));

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

  // 审批侧 gate 语义：通过准入的每一次人类动作都记账，signed 表示它是否真正生效。
  function noteGate(action, signed) {
    state.gates.push({
      role: action.role ?? APPROVAL_ROLES.APPLICANT,
      signed,
      at_step: action.seq ?? state.log.length + 1,
    });
  }

  async function persistCurrent(reasonNote) {
    const response = await store.send(
      `expense:${applicant}:v${state.version}`,
      {
        version: state.version,
        applicant,
        approver,
        status: state.status,
        ...state.draft,
        note: reasonNote ?? null,
        history: state.history.length,
      },
      TRANSPORT_CODE.OK,
    );
    if (response.ok) state.persisted = true;
    return response;
  }

  const handlers = {
    edit(action) {
      const allowedFrom = [APPROVAL_STATES.DRAFT, APPROVAL_STATES.REJECTED];
      if (!ensureFrom(action, allowedFrom)) {
        record({ action: 'edit', ok: false, reason: 'state_mismatch' });
        return { ok: false, reason: 'state_mismatch', status: state.status };
      }
      if (!isApplicantActor(action, parties)) {
        record({ action: 'edit', ok: false, reason: 'role_not_permitted' });
        return { ok: false, reason: 'role_not_permitted', status: state.status };
      }
      if (action.values) Object.assign(state.draft, action.values);
      if (state.status === APPROVAL_STATES.REJECTED) {
        // 驳回后修订：旧版本留在历史里，重提会形成新的一版。
        state.history.push({
          version: state.version,
          status: APPROVAL_STATES.REJECTED,
          snapshot: structuredClone(state.draft),
          decisions: [...state.decisions],
        });
        state.version += 1;
        state.decisions = [];
        state.escalated = false;
        state.fallback = null;
      }
      state.status = APPROVAL_STATES.DRAFT;
      state.errors = validateRequest(state.draft);
      record({ action: 'edit', ok: true, version: state.version });
      return { ok: true, status: state.status, error_fields: errorFields() };
    },

    async submit(action) {
      if (!isApplicantActor(action, parties)) {
        record({ action: 'submit', ok: false, reason: 'role_not_permitted' });
        return { ok: false, reason: 'role_not_permitted', status: state.status };
      }
      if (state.status !== APPROVAL_STATES.DRAFT) {
        noteGate(action, false);
        record({ action: 'submit', ok: false, duplicate: true, outcome: 'rejected_or_ignored' });
        return { ok: false, duplicate: true, outcome: 'rejected_or_ignored', status: state.status };
      }
      const errors = validateRequest(state.draft);
      state.errors = errors;
      if (Object.keys(errors).length > 0) {
        noteGate(action, false);
        record({ action: 'submit', ok: false, blocked_by: 'client_validation', error_fields: Object.keys(errors) });
        return { ok: false, blocked_by: 'client_validation', status: state.status, error_fields: Object.keys(errors) };
      }
      if (!action.confirmed) {
        record({ action: 'submit', ok: false, reason: 'awaiting_human_gate' });
        return { ok: false, reason: 'awaiting_human_gate', status: state.status, needs_confirmation: true };
      }
      state.status = APPROVAL_STATES.SUBMITTED;
      noteGate(action, true);
      await persistCurrent('applicant submitted');
      record({ action: 'submit', ok: true });
      return { ok: true, status: state.status };
    },

    async route(action) {
      const authority = checkRoutingAuthority(action);
      if (!authority.allowed) {
        record({ action: 'route', ok: false, reason: authority.reason });
        return { ok: false, reason: authority.reason, status: state.status };
      }
      if (!ensureFrom(action, [APPROVAL_STATES.SUBMITTED])) {
        record({ action: 'route', ok: false, reason: 'state_mismatch' });
        return { ok: false, reason: 'state_mismatch', status: state.status };
      }
      state.status = APPROVAL_STATES.UNDER_REVIEW;
      await persistCurrent('routed to approver queue');
      record({ action: 'route', ok: true });
      return { ok: true, status: state.status };
    },

    async approve(action) {
      const authority = checkDecisionAuthority(action, parties);
      if (!authority.allowed) {
        record({ action: 'approve', ok: false, outcome: 'denied', reason: authority.reason, field: authority.field });
        return { ok: false, outcome: 'denied', reason: authority.reason, status: state.status };
      }
      if (!ensureFrom(action, [APPROVAL_STATES.UNDER_REVIEW])) {
        record({ action: 'approve', ok: false, reason: 'state_mismatch' });
        return { ok: false, outcome: 'ignored', reason: 'state_mismatch', status: state.status };
      }
      if (!action.confirmed) {
        record({ action: 'approve', ok: false, reason: 'awaiting_human_gate' });
        return { ok: false, reason: 'awaiting_human_gate', status: state.status, needs_confirmation: true };
      }
      state.status = APPROVAL_STATES.APPROVED;
      state.decisions.push({ outcome: 'approved', reason: action.reason ?? null, by: parties.approver });
      noteGate(action, true);
      await persistCurrent(action.reason ?? 'approved');
      record({ action: 'approve', ok: true });
      return { ok: true, status: state.status };
    },

    async reject(action) {
      const authority = checkDecisionAuthority(action, parties);
      if (!authority.allowed) {
        record({ action: 'reject', ok: false, outcome: 'denied', reason: authority.reason, field: authority.field });
        return { ok: false, outcome: 'denied', reason: authority.reason, status: state.status };
      }
      if (!ensureFrom(action, [APPROVAL_STATES.UNDER_REVIEW])) {
        record({ action: 'reject', ok: false, reason: 'state_mismatch' });
        return { ok: false, outcome: 'ignored', reason: 'state_mismatch', status: state.status };
      }
      const reason = String(action.reason ?? '').trim();
      if (reason.length === 0) {
        noteGate(action, false);
        record({ action: 'reject', ok: false, blocked_by: 'reason_required' });
        return { ok: false, blocked_by: 'reason_required', status: state.status };
      }
      if (!action.confirmed) {
        record({ action: 'reject', ok: false, reason: 'awaiting_human_gate' });
        return { ok: false, reason: 'awaiting_human_gate', status: state.status, needs_confirmation: true };
      }
      state.status = APPROVAL_STATES.REJECTED;
      state.decisions.push({ outcome: 'rejected', reason, by: parties.approver });
      noteGate(action, true);
      await persistCurrent(reason);
      record({ action: 'reject', ok: true });
      return { ok: true, status: state.status };
    },

    escalate(action) {
      if (!ensureFrom(action, [APPROVAL_STATES.UNDER_REVIEW])) {
        record({ action: 'escalate', ok: false, reason: 'state_mismatch' });
        return { ok: false, reason: 'state_mismatch', status: state.status };
      }
      if (action.role !== APPROVAL_ROLES.SYSTEM) {
        record({ action: 'escalate', ok: false, reason: 'role_not_permitted' });
        return { ok: false, reason: 'role_not_permitted', status: state.status };
      }
      // 超时升级：原地保留 under_review，落显式标记，不写持久化，也不给出成功或失败结论。
      state.status = ESCALATION_POLICY.target;
      state.escalated = ESCALATION_POLICY.marker;
      state.fallback = ESCALATION_POLICY.fallback;
      record({ action: 'escalate', ok: true, escalated: true });
      return { ok: true, status: state.status, escalated: true };
    },
  };

  return {
    get applicant() {
      return applicant;
    },
    get approver() {
      return approver;
    },
    get state() {
      return state.status;
    },
    get version() {
      return state.version;
    },
    get draft() {
      return { ...state.draft };
    },
    get history() {
      return state.history.map((item) => structuredClone(item));
    },
    store,

    async dispatch(action) {
      const handler = handlers[action.action] ?? handlers[action.action === 'timeout' ? 'escalate' : action.action];
      if (!handler) {
        record({ action: action.action, ok: false, reason: 'unknown_action' });
        return { ok: false, reason: 'unknown_action', status: state.status };
      }
      return handler(action);
    },

    snapshot() {
      return {
        final_state: state.status,
        persisted: state.persisted,
        human_gates: state.gates.map((gate) => ({ ...gate })),
        error_fields: errorFields(),
        error_messages: validateRequest(state.draft),
        version: state.version,
        writes: store.writeCount,
        escalated: state.escalated,
        explicit_marker: state.escalated,
        fallback: state.fallback,
        history_count: state.history.length,
        conflicts: state.conflicts.map((item) => ({ ...item })),
      };
    },
  };
}
