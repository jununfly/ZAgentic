// Profile edit form state machine.
// idle -> validating -> submitting -> success | error -> validating (explicit recover).
// Input is locked while submitting; a duplicate submit during that window is suppressed, not queued.

import { FAILURE_POLICY, createCommitStore, sleep } from '../core.mjs';
import { DeniedError, assertKnown } from '../core.mjs';
import { FIELD_ORDER, validateProfile } from './validation.mjs';
import { outcomeFromCode, createProfileApi, createProfileStore, SAVE_MESSAGES } from './persistence.mjs';

export const FormState = Object.freeze({
  IDLE: 'idle',
  VALIDATING: 'validating',
  SUBMITTING: 'submitting',
  SUCCESS: 'success',
  ERROR: 'error',
});

export const EDITABLE_STATES = Object.freeze([FormState.IDLE, FormState.VALIDATING]);

// target '*' means the handler decides; it is declared here so nothing moves off-book.
export const TRANSITIONS = Object.freeze({
  [FormState.IDLE]: Object.freeze({ load: FormState.IDLE, edit: FormState.VALIDATING, submit: FormState.VALIDATING }),
  [FormState.VALIDATING]: Object.freeze({
    load: FormState.IDLE,
    edit: FormState.VALIDATING,
    validate: FormState.VALIDATING,
    submit: FormState.SUBMITTING,
  }),
  [FormState.SUBMITTING]: Object.freeze({ submit: FormState.SUBMITTING, persist: '*' }),
  [FormState.SUCCESS]: Object.freeze({ load: FormState.IDLE, edit: FormState.VALIDATING }),
  [FormState.ERROR]: Object.freeze({
    load: FormState.IDLE,
    edit: FormState.VALIDATING,
    recover: FormState.VALIDATING,
  }),
});

export function transitionsFrom(state) {
  const row = TRANSITIONS[state];
  if (!row) throw new DeniedError(`Unknown form state: ${String(state)}`, { known: Object.keys(TRANSITIONS) });
  return Object.entries(row).map(([action, to]) => ({ action, to }));
}

export function canLeaveBy(state, action) {
  return transitionsFrom(state).some((entry) => entry.action === action);
}

export function createProfileFormMachine(options = {}) {
  const {
    user = 'anonymous',
    profile = {},
    initialState = FormState.IDLE,
    store = createProfileStore(),
    api = createProfileApi({ latency: 0 }),
    transport = null,
  } = options;

  const record = {
    user,
    profile: { nickname: '', email: '', bio: '', ...profile },
  };

  let state = FormState.IDLE;
  let validation = validateProfile(record.profile);
  const touched = new Set();
  const humanGates = [];
  let attemptSeq = 0;
  let inflight = null;
  let releaseServer = null;
  let serverSettled = true;
  let duplicateSuppressed = false;
  let blockedByValidation = false;
  let lastError = null;
  let fallback = null;
  let explicitMarker = false;
  const listeners = new Set();

  function emit(event, payload = {}) {
    for (const listener of listeners) listener({ event, state, ...payload });
  }

  function setState(next) {
    if (!TRANSITIONS[next]) throw new DeniedError(`Unknown form state: ${String(next)}`, { known: Object.keys(TRANSITIONS) });
    state = next;
    emit('state', { validation, snapshot: snapshot() });
  }

  function persistKey() {
    return `profile:${record.user}`;
  }

  function isLocked() {
    return state === FormState.SUBMITTING;
  }

  // Hydration only (page load with a known state / replayed fixture initial state).
  // It never writes, so `persisted` stays honest.
  function restore(nextState) {
    if (!TRANSITIONS[nextState]) {
      throw new DeniedError(`Unknown form state: ${String(nextState)}`, { known: Object.keys(TRANSITIONS) });
    }
    state = nextState;
    validation = validateProfile(record.profile);
    emit('restore', { validation });
    return snapshot();
  }

  function load(saved = store.get(persistKey())) {
    if (saved) record.profile = { ...record.profile, ...saved.profile };
    touched.clear();
    validation = validateProfile(record.profile);
    setState(FormState.IDLE);
    return snapshot();
  }

  function edit(field, value) {
    assertKnown(field, FIELD_ORDER, 'form field');
    if (isLocked()) {
      return { suppressed: true, reason: 'input_locked', state, validation };
    }
    if (value !== undefined) record.profile[field] = value;
    touched.add(field);
    validation = validateProfile(record.profile);
    setState(FormState.VALIDATING);
    return { suppressed: false, state, validation };
  }

  function validate() {
    if (isLocked()) return { suppressed: true, reason: 'input_locked', validation };
    validation = validateProfile(record.profile);
    if (state === FormState.IDLE || state === FormState.SUCCESS || state === FormState.ERROR) {
      setState(FormState.VALIDATING);
    } else {
      emit('state', { validation, snapshot: snapshot() });
    }
    return { suppressed: false, validation };
  }

  // `park` lets a caller keep the request in flight until an explicit server response step arrives.
  function startTransport(park) {
    const payload = { user: record.user, profile: { ...record.profile }, attempt: attemptSeq };
    if (transport) return Promise.resolve(transport(payload, park));
    return Promise.resolve(api.save(payload, record.scenario || 'ok'));
  }

  function applyOutcome(outcome) {
    serverSettled = true;
    releaseServer = null;
    if (outcome.kind === 'ok') {
      const result = store.commit({ key: persistKey(), value: { user: record.user, profile: { ...record.profile } } });
      lastError = null;
      fallback = null;
      explicitMarker = false;
      setState(FormState.SUCCESS);
      emit('saved', { written: result.written, outcome });
      return { written: result.written, outcome };
    }
    const timedOut = outcome.kind === 'timeout';
    lastError = { code: outcome.code, error: outcome.error, message: timedOut ? SAVE_MESSAGES.timeout : SAVE_MESSAGES.constraint };
    fallback = timedOut ? FAILURE_POLICY.fallback_route : null;
    explicitMarker = true;
    setState(FormState.ERROR);
    emit('failed', { outcome, fallback });
    return { written: false, outcome };
  }

  function submit({ role = 'user', atStep = 0, confirmed = false, scenario = null } = {}) {
    if (scenario) record.scenario = scenario;
    if (isLocked()) {
      // second click lands here: no second request, no second write.
      duplicateSuppressed = true;
      emit('suppressed', { reason: 'input_locked', atStep });
      return { advanced: false, suppressed: true, reason: 'input_locked', state };
    }
    validation = validateProfile(record.profile);
    if (!validation.valid) {
      blockedByValidation = true;
      if (state !== FormState.VALIDATING) setState(FormState.VALIDATING);
      emit('blocked', { reason: 'client_validation', error_fields: validation.error_fields, atStep });
      return { advanced: false, blocked: true, reason: 'client_validation', error_fields: validation.error_fields, state };
    }
    if (!confirmed) {
      emit('blocked', { reason: 'confirmation_required', atStep });
      return { advanced: false, blocked: true, reason: 'confirmation_required', state };
    }
    attemptSeq += 1;
    serverSettled = false;
    setState(FormState.SUBMITTING);
    humanGates.push({ role, signed: true, at_step: atStep });
    try {
      const promise = startTransport((resolve) => {
        releaseServer = resolve;
      });
      inflight = Promise.resolve(promise).then(applyOutcome, (failure) => {
        if (failure && failure.outcome) return applyOutcome(failure.outcome);
        return applyOutcome({ code: 0, kind: 'timeout', error: 'timeout' });
      });
      emit('request_started', { attempt: attemptSeq, atStep });
      return { advanced: true, suppressed: false, attempt: attemptSeq, state, inflight };
    } catch (failure) {
      return applyOutcome(failure && failure.outcome ? failure.outcome : { code: 0, kind: 'timeout', error: 'timeout' });
    }
  }

  function respond({ code }) {
    if (!releaseServer) return Promise.resolve(null);
    const outcome = outcomeFromCode(code);
    releaseServer(outcome);
    return inflight;
  }

  async function persist({ code }) {
    if (releaseServer) respond({ code });
    if (inflight) await inflight;
    return snapshot();
  }

  async function awaitSettled() {
    if (inflight) await inflight;
    return snapshot();
  }

  function recover() {
    if (state !== FormState.ERROR) {
      return { advanced: false, reason: 'not_in_error_state', state };
    }
    lastError = null;
    explicitMarker = false;
    setState(FormState.VALIDATING);
    return { advanced: true, state };
  }

  function resetFailureFlags() {
    duplicateSuppressed = false;
    blockedByValidation = false;
  }

  function recoverable() {
    // Derived from the transition table, not from a constant: ERROR can reach an editable state.
    return transitionsFrom(FormState.ERROR).some((entry) => EDITABLE_STATES.includes(entry.to));
  }

  function snapshot() {
    const persisted = store.has(persistKey());
    const currentlyBlocked = !validation.valid || blockedByValidation;
    return {
      final_state: state,
      persisted,
      error_fields: [...validation.error_fields],
      field_errors: { ...validation.field_errors },
      submit_blocked: currentlyBlocked,
      duplicate_suppressed: duplicateSuppressed,
      writes: store.writes,
      recoverable: recoverable(),
      fallback,
      explicit_marker: explicitMarker,
      locked: isLocked(),
      in_flight: !serverSettled,
      attempt_seq: attemptSeq,
      last_error: lastError ? { ...lastError } : null,
      user: record.user,
      profile: { ...record.profile },
      transitions: transitionsFrom(state).map((entry) => entry.action),
      human_gates: humanGates.map((gate) => ({ ...gate })),
    };
  }

  restore(initialState);
  resetFailureFlags();

  return {
    kind: 'profile-form',
    get state() {
      return state;
    },
    get profile() {
      return { ...record.profile };
    },
    get validation() {
      return validation;
    },
    snapshot,
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    setScenario(scenario) {
      record.scenario = scenario;
      return scenario;
    },
    getScenario() {
      return record.scenario || 'ok';
    },
    edit,
    validate,
    submit,
    respond,
    persist,
    awaitSettled,
    recover,
    load,
    restore,
    recoverable,
    isLocked,
    profileApi: api,
    store,
  };
}

export { sleep };
