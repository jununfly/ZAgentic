// Profile edit form state machine.
// idle -> validating -> submitting -> success | error ; error -> validating (recoverable)
// Input is locked for the whole submitting phase, so a second submit is ignored.

import { validateProfile, validateField } from "./validation.mjs";
import { createMemoryStore, sendProfile, RESPONSE } from "./persist.mjs";

export const FORM_STATES = Object.freeze({
  IDLE: "idle",
  VALIDATING: "validating",
  SUBMITTING: "submitting",
  SUCCESS: "success",
  ERROR: "error",
});

const EDITABLE = new Set([FORM_STATES.IDLE, FORM_STATES.VALIDATING, FORM_STATES.ERROR]);

export function createFormSession(options = {}) {
  const store = options.store ?? createMemoryStore();
  const actor = options.user ?? "user";
  let draft = { nickname: "", email: "", bio: "", ...(options.profile ?? {}) };
  let state = options.initialState ?? FORM_STATES.IDLE;
  let errors = validateProfile(draft).errors;
  let gates = [];
  let attemptBlocked = false;
  let duplicateSuppressed = false;
  let lastFailure = null;

  const locked = () => state === FORM_STATES.SUBMITTING;
  const errorFields = () => [...new Set(errors.map((error) => error.field))].sort();

  function recompute() {
    errors = validateProfile(draft).errors;
    return errors;
  }

  function edit(payload, seq) {
    if (locked()) {
      // Input is locked while the request is in flight: the keystroke is dropped.
      return { accepted: false, reason: "input_locked", from: state, to: state };
    }
    if (!EDITABLE.has(state)) {
      return { accepted: false, reason: "not_editable", from: state, to: state };
    }
    if (payload.field && Object.prototype.hasOwnProperty.call(draft, payload.field)) {
      draft[payload.field] = payload.value === undefined ? draft[payload.field] : payload.value;
    }
    const from = state;
    state = FORM_STATES.VALIDATING;
    recompute();
    return { accepted: true, from, to: state, errors: errors.map((error) => error.field) };
  }

  function validate(payload) {
    if (payload.field) {
      const problem = validateField(payload.field, draft);
      errors = errors.filter((error) => error.field !== payload.field);
      if (problem) errors.push(problem);
    } else {
      recompute();
    }
    return { from: state, to: state, result: errors.length === 0 ? "valid" : "invalid" };
  }

  function submit(payload = {}) {
    const from = state;
    if (locked()) {
      duplicateSuppressed = true;
      return { accepted: false, reason: "input_locked", from, to: state };
    }
    if (state === FORM_STATES.SUCCESS) {
      return { accepted: false, reason: "already_saved", from, to: state };
    }
    recompute();
    if (errors.length > 0) {
      // Client validation gates the confirm dialog: no human gate is opened.
      attemptBlocked = true;
      return { accepted: false, reason: "client_validation", from, to: state, blockedBy: "client_validation" };
    }
    if (payload.confirmed !== true) {
      return { accepted: false, reason: "unconfirmed", from, to: state };
    }
    attemptBlocked = false;
    gates = gates.concat([{ role: payload.role ?? "user", signed: true, at_step: payload.seq ?? null }]);
    state = FORM_STATES.SUBMITTING;
    return { accepted: true, from, to: state };
  }

  function persist(payload = {}) {
    if (state !== FORM_STATES.SUBMITTING) {
      return { ok: false, reason: "not_submitting", from: state, to: state };
    }
    const code = payload.responseCode === undefined ? RESPONSE.OK : payload.responseCode;
    const outcome = sendProfile(store, { ...draft }, code);
    if (outcome.ok) {
      state = FORM_STATES.SUCCESS;
      lastFailure = null;
      return { ok: true, from: FORM_STATES.SUBMITTING, to: state, code: outcome.code };
    }
    state = FORM_STATES.ERROR;
    lastFailure = outcome;
    return { ok: false, from: FORM_STATES.SUBMITTING, to: state, code: outcome.code, error: outcome.error };
  }

  function recover() {
    if (state !== FORM_STATES.ERROR) return { accepted: false, from: state, to: state };
    state = FORM_STATES.VALIDATING;
    recompute();
    return { accepted: true, from: FORM_STATES.ERROR, to: state };
  }

  function reset() {
    state = FORM_STATES.IDLE;
    lastFailure = null;
    attemptBlocked = false;
    duplicateSuppressed = false;
    return { from: state, to: state };
  }

  const handlers = { edit, validate, submit, persist, recover, reset };

  function apply(action = {}) {
    const handler = handlers[action.action];
    if (!handler) return { accepted: false, reason: "unknown_action", from: state, to: state };
    const payload = {
      ...action,
      seq: action.seq,
      role: action.role,
      confirmed: action.confirmed !== undefined ? action.confirmed : action.role === "user",
      responseCode: action.response_code,
    };
    const result = handler(payload, action.seq);
    return { ...result, action: action.action };
  }

  function snapshot() {
    return {
      final_state: state,
      persisted: state === FORM_STATES.SUCCESS && store.lastWriteOk,
      error_fields: errorFields(),
      submit_blocked: attemptBlocked || errors.length > 0,
      human_gates: gates.map((gate) => ({ ...gate })),
      duplicate_suppressed: duplicateSuppressed,
      writes: store.writes,
      recoverable: state === FORM_STATES.ERROR,
      fallback: lastFailure && lastFailure.fallback ? lastFailure.fallback : null,
      explicit_marker: Boolean(lastFailure && lastFailure.explicitMarker),
      locked: locked(),
    };
  }

  return { apply, snapshot, get state() { return state; }, get draft() { return { ...draft }; }, get errors() { return [...errors]; }, store };
}
