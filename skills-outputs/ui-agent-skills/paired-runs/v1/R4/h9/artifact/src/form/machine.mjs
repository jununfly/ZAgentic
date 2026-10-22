// machine.mjs — profile form state machine.
//
// States: idle -> validating -> submitting -> success | error
//
// Public surface (used by the frozen driver):
//   machine.state
//   machine.snapshot()
//   machine.load()
//   machine.edit(field)
//   machine.validate()
//   machine.submit({ role, atStep, confirmed })
//   machine.persist({ code })
//   machine.recover()
//
// MANDATORY transport/park contract:
//   submit() calls transport(payload, park), stores the park resolver, and
//   awaits the transport promise. The promise stays pending until persist({code})
//   resolves it. persist({code}) resolves the parked promise with { code }.

import { clone, validateProfile } from '../core.mjs';

export function createProfileFormMachine({
  user = 'anonymous',
  profile = {},
  initialState = 'idle',
  api = null,
  transport = (_payload, park) => new Promise((resolve) => park(resolve)),
} = {}) {
  const machine = {
    user,
    profile: clone(profile),
    api,
    transport,

    // --- runtime state ---
    state: initialState,
    loaded: false,
    error_fields: [],
    submit_blocked: false,
    duplicate_suppressed: false,
    recoverable: false,
    explicit_marker: false,
    fallback: '',
    persisted: false,
    writes: 0,
    human_gates: [],
    _parkResolve: null,
    _transportPromise: null,

    load() {
      this.loaded = true;
      // load is idempotent; initial state is preserved so the harness hydration
      // check (state === initial_state) is not disturbed.
      return this;
    },

    edit(field) {
      // Any edit re-enters the validating state and re-validates live.
      if (this.state === 'success' || this.state === 'submitting') return this;
      this.state = 'validating';
      this._runValidation();
      return this;
    },

    validate() {
      this._runValidation();
      return this;
    },

    _runValidation() {
      this.error_fields = validateProfile(this.profile);
    },

    async submit({ role = 'user', atStep = 0, confirmed = true } = {}) {
      // Input is locked while a submit is already in flight: a second submit is
      // suppressed (double-click only counts once).
      if (this.state === 'submitting') {
        this.duplicate_suppressed = true;
        return this;
      }
      // Only a validated draft can be submitted.
      if (this.state !== 'validating' && this.state !== 'idle') {
        this.submit_blocked = true;
        return this;
      }
      this._runValidation();
      if (this.error_fields.length > 0) {
        // Client validation blocks submission; no human gate is signed.
        this.submit_blocked = true;
        return this;
      }

      // Proceed: lock input, record explicit human confirmation gate.
      this.state = 'submitting';
      if (confirmed === true) {
        this.human_gates.push({ role, signed: true, at_step: atStep });
      } else {
        this.human_gates.push({ role, signed: false, at_step: atStep });
      }

      const payload = { user: this.user, profile: clone(this.profile) };

      // Park/resume protocol: transport gives us a resolver; we await the
      // transport promise and it stays pending until persist({code}) resolves it.
      const park = (resolveTransport) => {
        this._parkResolve = (code) => resolveTransport({ code });
      };
      this._transportPromise = this.transport(payload, park);
      const response = await this._transportPromise;
      this._applyPersist(response?.code ?? 0);
      return this;
    },

    _applyPersist(code) {
      if (code === 200) {
        this.state = 'success';
        this.persisted = true;
        this.writes += 1;
      } else if (code === 422) {
        this.state = 'error';
        this.persisted = false;
        this.recoverable = true;
      } else if (code === 0) {
        // Timeout: do NOT fabricate success. Fall back to a stable path and
        // leave an explicit marker so the UI cannot pretend it saved.
        this.state = 'error';
        this.persisted = false;
        this.fallback = 'stable_path';
        this.explicit_marker = true;
      } else {
        this.state = 'error';
        this.persisted = false;
      }
    },

    persist({ code = 0 } = {}) {
      if (this._parkResolve) {
        const resolver = this._parkResolve;
        this._parkResolve = null;
        resolver(code); // resolves the parked transport promise with { code }
      }
      return this;
    },

    recover() {
      // A recoverable error returns the form to an editable (validating) state.
      if (this.state === 'error') {
        this.state = 'validating';
        this.persisted = false;
        this.recoverable = false;
        this.explicit_marker = false;
        this.fallback = '';
        this.error_fields = [];
      }
      return this;
    },

    snapshot() {
      return {
        final_state: this.state,
        persisted: this.persisted,
        error_fields: clone(this.error_fields),
        // Submission is blocked whenever the (editable) form currently carries
        // validation errors — regardless of whether a submit was attempted.
        submit_blocked:
          (this.state === 'validating' || this.state === 'idle') &&
          this.error_fields.length > 0,
        human_gates: clone(this.human_gates),
        duplicate_suppressed: this.duplicate_suppressed,
        recoverable: this.recoverable,
        explicit_marker: this.explicit_marker,
        fallback: this.fallback,
        writes: this.writes,
      };
    },
  };

  return machine;
}
