// Profile edit form state machine (page one of the product).
//
// States: idle -> validating -> submitting -> success | error
//
// Submission protocol (mandatory park/resume):
//   submit() calls transport(payload, park), stores the park resolver, and
//   awaits the returned promise. That promise stays pending until persist({code})
//   is called, which resolves it with { code }. The driver supplies the code.
//
// Human gates: every explicit user confirmation (submit) is recorded in
// human_gates with { role, signed, at_step }.

const BIO_MAX = 200;

function isValidEmail(value) {
  if (typeof value !== 'string') return false;
  // Pragmatic email check sufficient for client-side validation.
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

function isBlank(value) {
  return value === undefined || value === null || String(value).trim() === '';
}

export function createProfileFormMachine({
  user = 'anonymous',
  profile = {},
  initialState = 'idle',
  api = null,
  transport = null,
} = {}) {
  const data = {
    nickname: profile.nickname ?? '',
    email: profile.email ?? '',
    bio: profile.bio ?? '',
  };

  let state = initialState;
  let errorFields = [];
  let persisted = false;
  let writes = 0;
  let duplicateSuppressed = false;
  let pendingField = null; // which field was last edited
  let pendingPark = null; // the park resolver for the in-flight submit
  let fallback = ''; // e.g. "stable_path" on timeout
  let explicitMarker = ''; // explicit marker flag, set true on timeout
  const humanGates = [];

  function recomputeErrors() {
    const errors = [];
    if (isBlank(data.nickname)) errors.push('nickname');
    if (!isValidEmail(data.email)) errors.push('email');
    if (String(data.bio).length > BIO_MAX) errors.push('bio');
    errorFields = errors;
    return errors;
  }

  function buildPayload() {
    return { user, profile: { ...data } };
  }

  const machine = {
    get state() {
      return state;
    },

    load() {
      // Load current profile into the editable form.
      recomputeErrors();
      if (state === 'idle') state = 'validating';
      return machine;
    },

    edit(field) {
      pendingField = field;
      // Editing implies the user is now interacting; move into validating.
      if (state === 'idle' || state === 'success' || state === 'error') {
        state = 'validating';
      }
      recomputeErrors();
      return machine;
    },

    validate() {
      recomputeErrors();
      if (state === 'idle') state = 'validating';
      return machine;
    },

    async submit({ role = 'user', atStep = 0, confirmed = false } = {}) {
      // Duplicate suppression: a second submit while one is in flight is ignored.
      if (state === 'submitting') {
        duplicateSuppressed = true;
        return machine;
      }

      // Real-time client-side validation gate.
      recomputeErrors();
      if (errorFields.length > 0) {
        // Blocked by client validation — no state change, no human gate.
        return machine;
      }

      if (state === 'idle') state = 'validating';
      state = 'submitting';
      humanGates.push({ role, signed: !!confirmed, at_step: atStep });

      // Park/resume: wait for the driver to answer with persist({code}).
      // The transport returns a promise that resolves with { code } once the
      // parked resolver (stored in pendingPark) is invoked by persist().
      const response = await (transport
        ? transport(buildPayload(), (parkResolve) => { pendingPark = parkResolve; })
        : Promise.resolve({ code: 200 }));

      const code = response && typeof response.code === 'number' ? response.code : 0;

      if (code === 200) {
        persisted = true;
        writes += 1;
        if (api && typeof api.persist === 'function') {
          try { await api.persist(buildPayload()); } catch { /* mock */ }
        }
        state = 'success';
      } else if (code === 0) {
        // Timeout: never pretend success. Fall back to a stable path and mark it.
        persisted = false;
        state = 'error';
        fallback = 'stable_path';
        explicitMarker = true;
      } else {
        // Server-side constraint (e.g. 422) or other non-OK: error + recoverable.
        persisted = false;
        state = 'error';
      }
      return machine;
    },

    persist({ code } = {}) {
      const resolve = pendingPark;
      pendingPark = null;
      if (resolve) resolve({ code });
      return Promise.resolve();
    },

    recover() {
      // From an error state, return to an editable state so the user can fix
      // and re-submit (explicit recovery path).
      if (state === 'error') {
        state = 'validating';
        fallback = '';
        explicitMarker = '';
        recomputeErrors();
      }
      return machine;
    },

    snapshot() {
      return {
        final_state: state,
        persisted,
        error_fields: errorFields.slice(),
        submit_blocked: errorFields.length > 0,
        human_gates: humanGates.slice(),
        duplicate_suppressed: duplicateSuppressed,
        recoverable: state === 'error',
        explicit_marker: explicitMarker,
        fallback,
        writes,
      };
    },
  };

  return machine;
}

export default createProfileFormMachine;
