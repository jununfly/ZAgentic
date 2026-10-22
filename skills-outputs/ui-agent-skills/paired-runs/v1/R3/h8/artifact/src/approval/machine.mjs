// Expense approval state machine: draft -> submitted -> under_review -> approved | rejected -> draft(v+1).
// Decisions are deny-first authorized; failures escalate instead of resolving silently.

import { DeniedError, assertKnown } from '../core.mjs';
import { Role, authorizeDecision, resolveActorId, actorRole } from './roles.mjs';
import {
  REQUEST_FIELDS,
  REVIEW_TIMEOUT_MS,
  ESCALATION_POLICY,
  validateRequest,
  createRequestStore,
  createApprovalApi,
  requestRecordKey,
  decisionRecordKey,
} from './persistence.mjs';

export const ApprovalState = Object.freeze({
  DRAFT: 'draft',
  SUBMITTED: 'submitted',
  UNDER_REVIEW: 'under_review',
  APPROVED: 'approved',
  REJECTED: 'rejected',
});

export const EDITABLE_STATES = Object.freeze([ApprovalState.DRAFT]);
export const TERMINAL_STATES = Object.freeze([ApprovalState.APPROVED]);

export const TRANSITIONS = Object.freeze({
  [ApprovalState.DRAFT]: Object.freeze({
    edit: ApprovalState.DRAFT,
    validate: ApprovalState.DRAFT,
    submit: ApprovalState.SUBMITTED,
  }),
  [ApprovalState.SUBMITTED]: Object.freeze({
    submit: ApprovalState.SUBMITTED,
    route: ApprovalState.UNDER_REVIEW,
  }),
  [ApprovalState.UNDER_REVIEW]: Object.freeze({
    approve: ApprovalState.APPROVED,
    reject: ApprovalState.REJECTED,
    timeout: ApprovalState.UNDER_REVIEW,
  }),
  [ApprovalState.REJECTED]: Object.freeze({
    revise: ApprovalState.DRAFT,
    edit: ApprovalState.DRAFT,
  }),
  [ApprovalState.APPROVED]: Object.freeze({}),
});

export function transitionsFrom(state) {
  const row = TRANSITIONS[state];
  if (!row) throw new DeniedError(`Unknown approval state: ${String(state)}`, { known: Object.keys(TRANSITIONS) });
  return Object.entries(row).map(([action, to]) => ({ action, to }));
}

export function createApprovalMachine(options = {}) {
  const {
    requestId = 'expense-unknown',
    applicantId = 'anonymous',
    approverId = null,
    request: initialRequest = {},
    initialState = ApprovalState.DRAFT,
    store = createRequestStore(),
    api = createApprovalApi({ latency: 0 }),
    timeoutMs = REVIEW_TIMEOUT_MS,
  } = options;

  const parties = { applicantId, approverId };
  const record = {
    requestId,
    version: 1,
    applicantId,
    approverId,
    request: { amount: null, currency: 'CNY', reason: '', attachment_ref: null, ...initialRequest },
  };

  let state = ApprovalState.DRAFT;
  let validation = validateRequest(record.request);
  const humanGates = [];
  const history = [];
  let lastDecision = null;
  let escalated = false;
  let explicitMarker = false;
  let fallback = null;
  let lastRejectReason = null;
  const listeners = new Set();

  function emit(event, payload = {}) {
    for (const listener of listeners) listener({ event, state, ...payload });
  }

  function setState(next) {
    if (!TRANSITIONS[next]) throw new DeniedError(`Unknown approval state: ${String(next)}`, { known: Object.keys(TRANSITIONS) });
    state = next;
    emit('state', { snapshot: snapshot() });
  }

  function requestKey() {
    return requestRecordKey(record.requestId, record.version);
  }

  function decisionKey() {
    return decisionRecordKey(record.requestId, record.version);
  }

  function isPersisted() {
    return store.has(requestKey()) || store.has(decisionKey());
  }

  function restore(nextState) {
    if (!TRANSITIONS[nextState]) {
      throw new DeniedError(`Unknown approval state: ${String(nextState)}`, { known: Object.keys(TRANSITIONS) });
    }
    state = nextState;
    validation = validateRequest(record.request);
    emit('restore', { snapshot: snapshot() });
    return snapshot();
  }

  function edit(field, value) {
    assertKnown(field, REQUEST_FIELDS, 'request field');
    if (state === ApprovalState.UNDER_REVIEW || TERMINAL_STATES.includes(state) || state === ApprovalState.SUBMITTED) {
      return { suppressed: true, reason: 'locked_for_applicant', state };
    }
    if (value !== undefined) record.request[field] = value;
    validation = validateRequest(record.request);
    setState(ApprovalState.DRAFT);
    return { suppressed: false, state, validation };
  }

  function validate() {
    validation = validateRequest(record.request);
    emit('state', { snapshot: snapshot() });
    return validation;
  }

  async function submit({ requestedRole = Role.APPLICANT, atStep = 0, confirmed = true } = {}) {
    validation = validateRequest(record.request);
    if (state !== ApprovalState.DRAFT) {
      // duplicate / out-of-turn submit: no new request record is created.
      humanGates.push({ role: requestedRole, signed: false, at_step: atStep });
      emit('suppressed', { reason: 'duplicate_submit', atStep });
      return { advanced: false, duplicate: true, reason: 'duplicate_submit', state };
    }
    if (!validation.valid) {
      humanGates.push({ role: requestedRole, signed: false, at_step: atStep });
      emit('blocked', { reason: 'client_validation', error_fields: validation.error_fields, atStep });
      return { advanced: false, blocked: true, reason: 'client_validation', error_fields: validation.error_fields, state };
    }
    if (!confirmed) {
      humanGates.push({ role: requestedRole, signed: false, at_step: atStep });
      emit('blocked', { reason: 'confirmation_required', atStep });
      return { advanced: false, blocked: true, reason: 'confirmation_required', state };
    }
    humanGates.push({ role: requestedRole, signed: true, at_step: atStep });
    const submittedAt = Date.now();
    const written = store.commit({
      key: requestKey(),
      value: {
        requestId: record.requestId,
        version: record.version,
        applicantId,
        approverId,
        request: { ...record.request },
        submittedAt,
        state: ApprovalState.SUBMITTED,
      },
    });
    await api.saveRequest(store.get(requestKey()));
    setState(ApprovalState.SUBMITTED);
    emit('submitted', { written: written.written, version: record.version });
    return { advanced: true, duplicate: false, written: written.written, state };
  }

  // System routing: exposed in the UI as an explicit dispatch control, never automatic.
  function route({ atStep = 0 } = {}) {
    if (state !== ApprovalState.SUBMITTED) {
      return { advanced: false, reason: 'not_submitted', state };
    }
    setState(ApprovalState.UNDER_REVIEW);
    emit('routed', { approverId, atStep });
    return { advanced: true, state };
  }

  async function decide({ kind = 'approve', requestedRole = Role.APPROVER, reason = '', atStep = 0 } = {}) {
    if (!['approve', 'reject'].includes(kind)) {
      throw new DeniedError(`Unknown decision kind: ${String(kind)}`, { known: ['approve', 'reject'] });
    }
    const authorization = authorizeDecision({ requestedRole, parties });
    if (!authorization.allowed) {
      // denied before touching state - the request must not advance.
      emit('denied', { kind, denied: authorization.denied, actorId: authorization.actorId, atStep });
      return { advanced: false, denied: true, denied_codes: authorization.denied, actor: authorization.actorId, state };
    }
    if (state !== ApprovalState.UNDER_REVIEW) {
      return { advanced: false, reason: 'not_under_review', state };
    }
    const trimmed = typeof reason === 'string' ? reason.trim() : '';
    if (kind === 'reject' && trimmed === '') {
      humanGates.push({ role: Role.APPROVER, signed: false, at_step: atStep });
      emit('blocked', { reason: 'reject_reason_required', atStep });
      return { advanced: false, blocked: true, reason: 'reject_reason_required', state };
    }
    humanGates.push({ role: Role.APPROVER, signed: true, at_step: atStep });
    const decidedAt = Date.now();
    const previous = store.get(requestKey());
    if (previous) {
      history.push(previous);
    }
    lastDecision = {
      kind,
      approverId: authorization.actorId,
      reason: trimmed,
      decidedAt,
      version: record.version,
    };
    if (kind === 'reject') lastRejectReason = trimmed;
    const written = store.commit({
      key: decisionKey(),
      value: {
        requestId: record.requestId,
        version: record.version,
        applicantId,
        approverId: authorization.actorId,
        request: { ...record.request },
        submittedAt: previous?.submittedAt ?? null,
        decision: { ...lastDecision },
        state: kind === 'approve' ? ApprovalState.APPROVED : ApprovalState.REJECTED,
      },
    });
    await api.saveDecision(store.get(decisionKey()));
    setState(kind === 'approve' ? ApprovalState.APPROVED : ApprovalState.REJECTED);
    emit('decided', { kind, written: written.written });
    return { advanced: true, state, decision: { ...lastDecision } };
  }

  // Review timeouts keep the request reviewable and hand it to a human; no pass, no fail.
  function timeout({ escalate = true, atStep = 0 } = {}) {
    if (state !== ApprovalState.UNDER_REVIEW) {
      return { advanced: false, reason: 'not_under_review', state };
    }
    escalated = escalate;
    explicitMarker = escalate;
    fallback = escalate ? ESCALATION_POLICY.fallback_route : null;
    emit('escalated', { fallback, atStep, timeoutMs });
    return { advanced: true, escalated, fallback, state };
  }

  // Rejected -> editable draft with a new version; the rejected record stays in history.
  function revise({ atStep = 0 } = {}) {
    if (state !== ApprovalState.REJECTED) {
      return { advanced: false, reason: 'not_rejected', state };
    }
    const previousKey = requestKey();
    const rejected = store.get(previousKey);
    if (rejected) history.push(rejected);
    record.version += 1;
    explicitMarker = false;
    fallback = null;
    escalated = false;
    validation = validateRequest(record.request);
    setState(ApprovalState.DRAFT);
    emit('revised', { version: record.version, atStep, rejectReason: lastRejectReason });
    return { advanced: true, version: record.version, state };
  }

  function snapshot() {
    return {
      final_state: state,
      persisted: isPersisted(),
      error_fields: [...validation.error_fields],
      field_errors: { ...validation.field_errors },
      version: record.version,
      locked: state === ApprovalState.SUBMITTED || state === ApprovalState.UNDER_REVIEW || TERMINAL_STATES.includes(state),
      terminal: TERMINAL_STATES.includes(state),
      escalated,
      explicit_marker: explicitMarker,
      fallback,
      writes: store.writes,
      last_decision: lastDecision ? { ...lastDecision } : null,
      reject_reason: lastRejectReason,
      history_versions: history.map((entry) => entry.version),
      requestId: record.requestId,
      applicantId,
      approverId,
      request: { ...record.request },
      transitions: transitionsFrom(state).map((entry) => entry.action),
      human_gates: humanGates.map((gate) => ({ ...gate })),
    };
  }

  restore(initialState);

  return {
    kind: 'expense-approval',
    get state() {
      return state;
    },
    get version() {
      return record.version;
    },
    snapshot,
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    edit,
    validate,
    submit,
    route,
    decide,
    approve(args = {}) {
      return decide({ ...args, kind: 'approve' });
    },
    reject(args = {}) {
      return decide({ ...args, kind: 'reject' });
    },
    timeout,
    revise,
    restore,
    parties,
    store,
    // introspection helpers used by the UI to render allowed controls
    transitionsFrom: () => transitionsFrom(state),
    resolveRole: (requestedRole) => actorRole(resolveActorId(requestedRole, parties), parties),
  };
}
