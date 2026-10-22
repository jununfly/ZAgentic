// Expense approval state machine.
// draft -> submitted -> under_review -> approved | rejected ; rejected -> draft (new version)

import { createApprovalStore } from "./persist.mjs";
import { resolveActor, canDecide, canSubmit, DENIAL, APPROVAL_ROLES } from "./roles.mjs";

export const APPROVAL_STATES = Object.freeze({
  DRAFT: "draft",
  SUBMITTED: "submitted",
  UNDER_REVIEW: "under_review",
  APPROVED: "approved",
  REJECTED: "rejected",
});

const IN_FLIGHT = new Set([APPROVAL_STATES.SUBMITTED, APPROVAL_STATES.UNDER_REVIEW]);
const DECIDABLE = new Set([APPROVAL_STATES.UNDER_REVIEW]);

export function validateRequest(request) {
  const errors = [];
  const amount = request.amount;
  if (typeof amount !== "number" || !Number.isFinite(amount) || amount <= 0) {
    errors.push({ field: "amount", code: "invalid_amount", message: "金额必须大于 0" });
  }
  const reason = typeof request.reason === "string" ? request.reason.trim() : "";
  if (reason.length === 0) {
    errors.push({ field: "reason", code: "required", message: "事由不能为空" });
  }
  return { ok: errors.length === 0, errors };
}

export function createApprovalSession(options = {}) {
  const store = options.store ?? createApprovalStore();
  const ctx = {
    applicant: options.applicant ?? null,
    approver: options.approver ?? null,
  };
  let request = {
    amount: null,
    currency: "CNY",
    reason: "",
    attachment_ref: null,
    ...(options.request ?? {}),
  };
  let state = options.initialState ?? APPROVAL_STATES.DRAFT;
  let version = 1;
  let gates = [];
  let escalation = null;
  let errors = [];
  let lastDenial = null;

  const human = (payload) => payload.confirmed === true;

  function submit(payload) {
    const actor = resolveActor(payload.role, ctx);
    if (IN_FLIGHT.has(state)) {
      // Submission already in flight: refuse silently and keep one request only.
      gates = gates.concat([{ role: APPROVAL_ROLES.APPLICANT, signed: false, at_step: payload.seq ?? null }]);
      return { accepted: false, reason: "duplicate_submit", duplicate: true, from: state, to: state };
    }
    if (state === APPROVAL_STATES.APPROVED) {
      return { accepted: false, reason: "already_decided", from: state, to: state };
    }
    const auth = canSubmit(actor, { applicant: ctx.applicant });
    if (!auth.allowed) {
      lastDenial = auth.code;
      return { accepted: false, reason: auth.code, from: state, to: state };
    }
    const check = validateRequest(request);
    errors = check.errors;
    if (!check.ok) {
      // The confirmation dialog was opened and left unsigned.
      gates = gates.concat([{ role: APPROVAL_ROLES.APPLICANT, signed: false, at_step: payload.seq ?? null }]);
      return { accepted: false, reason: "client_validation", blockedBy: "client_validation", from: state, to: state };
    }
    if (!human(payload)) {
      return { accepted: false, reason: "unconfirmed", from: state, to: state };
    }
    gates = gates.concat([{ role: APPROVAL_ROLES.APPLICANT, signed: true, at_step: payload.seq ?? null }]);
    if (state === APPROVAL_STATES.REJECTED) version += 1;
    state = APPROVAL_STATES.SUBMITTED;
    store.save({ ...request, state, version, applicant: ctx.applicant }, "submitted");
    return { accepted: true, from: APPROVAL_STATES.DRAFT, to: state, version };
  }

  function route(payload) {
    const from = state;
    if (!IN_FLIGHT.has(state) || state === APPROVAL_STATES.UNDER_REVIEW) {
      return { accepted: false, reason: "not_routable", from, to: state };
    }
    state = APPROVAL_STATES.UNDER_REVIEW;
    store.save({ ...request, state, version, applicant: ctx.applicant }, "routed");
    return { accepted: true, from, to: state };
  }

  function decide(payload, decision) {
    const actor = resolveActor(payload.role, ctx);
    const auth = canDecide(actor, { applicant: ctx.applicant });
    if (!auth.allowed) {
      lastDenial = auth.code;
      store.recordRefusal({ state, note: auth.code });
      return { accepted: false, reason: auth.code, field: auth.field, from: state, to: state };
    }
    if (!DECIDABLE.has(state)) {
      lastDenial = DENIAL.STATE;
      return { accepted: false, reason: DENIAL.STATE, field: "state", from: state, to: state };
    }
    if (decision === APPROVAL_STATES.REJECTED) {
      const reason = typeof payload.reason === "string" ? payload.reason.trim() : "";
      if (reason.length === 0) {
        lastDenial = DENIAL.REASON;
        return { accepted: false, reason: DENIAL.REASON, field: "reason", from: state, to: state };
      }
    }
    if (!human(payload)) {
      return { accepted: false, reason: "unconfirmed", from: state, to: state };
    }
    gates = gates.concat([{ role: APPROVAL_ROLES.APPROVER, signed: true, at_step: payload.seq ?? null }]);
    const from = state;
    state = decision;
    store.save(
      { ...request, state, version, applicant: ctx.applicant, decision_reason: payload.reason ?? null },
      decision,
    );
    return { accepted: true, from, to: state };
  }

  function approve(payload) {
    return decide(payload, APPROVAL_STATES.APPROVED);
  }

  function reject(payload) {
    return decide(payload, APPROVAL_STATES.REJECTED);
  }

  function timeout(payload) {
    if (state !== APPROVAL_STATES.UNDER_REVIEW) {
      return { accepted: false, reason: DENIAL.STATE, from: state, to: state };
    }
    // No fabricated decision: mark explicitly and hand over to a human queue.
    escalation = {
      escalated: payload.escalate !== false,
      lane: "manual_review",
      tag: "approval_timeout",
      from_state: state,
    };
    store.recordRefusal({ state, note: "timeout_escalated" });
    return { accepted: true, from: state, to: state, escalated: true };
  }

  function revise() {
    if (state !== APPROVAL_STATES.REJECTED) return { accepted: false, from: state, to: state };
    const from = state;
    state = APPROVAL_STATES.DRAFT;
    return { accepted: true, from, to: state };
  }

  function updateDraft(patch = {}) {
    if (IN_FLIGHT.has(state) || state === APPROVAL_STATES.APPROVED) {
      return { accepted: false, reason: "input_locked" };
    }
    for (const key of ["amount", "currency", "reason", "attachment_ref"]) {
      if (Object.prototype.hasOwnProperty.call(patch, key)) request[key] = patch[key];
    }
    return { accepted: true };
  }

  const handlers = { submit, route, approve, reject, timeout, escalate: timeout, revise };

  function apply(action = {}) {
    const handler = handlers[action.action];
    if (!handler) return { accepted: false, reason: "unknown_action", from: state, to: state };
    const payload = {
      ...action,
      role: action.role,
      confirmed: action.confirmed !== undefined ? action.confirmed : action.role !== APPROVAL_ROLES.SYSTEM,
    };
    return { ...handler(payload), action: action.action };
  }

  function snapshot() {
    const latest = store.latest;
    return {
      final_state: state,
      persisted: Boolean(latest && latest.state === state && store.lastWriteOk),
      human_gates: gates.map((gate) => ({ ...gate })),
      version,
      writes: store.writes,
      errors: errors.map((error) => error.field),
      escalation,
      last_denial: lastDenial,
      history: store.versions.map((entry) => entry.state),
    };
  }

  return { apply, updateDraft, snapshot, get state() { return state; }, get request() { return { ...request }; }, store };
}
