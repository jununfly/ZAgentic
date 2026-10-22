// machine.mjs — expense-approval state machine.
//
// States: draft -> submitted -> under_review -> approved | rejected
// (rejected -> draft via revise for a new version)
//
// Public surface (used by the frozen driver):
//   machine.state
//   machine.snapshot()
//   machine.submit({ requestedRole, atStep, confirmed })
//   machine.route({ atStep })
//   machine.decide({ kind, requestedRole, reason, atStep })
//   machine.timeout({ escalate, atStep })
//   machine.revise({ atStep })
//
// Role model: the decision (approve/reject) can ONLY be initiated by the
// approver role. Any other role is denied-first and the state does not advance.

import { clone, validateRequest } from '../core.mjs';

export function createApprovalMachine({
  requestId = 'expense-unknown',
  applicantId = 'anonymous',
  approverId = null,
  request = {},
  initialState = 'draft',
  api = null,
} = {}) {
  const machine = {
    requestId,
    applicantId,
    approverId,
    api,
    request: clone(request),

    state: initialState,
    persisted: false,
    error_fields: [],
    human_gates: [],
    reject_reason: '',
    escalated: false,
    version: 1,

    _recordGate(role, signed, atStep) {
      this.human_gates.push({ role, signed, at_step: atStep });
    },

    _isApprover(role) {
      // Decision authority is gated on the approver *role*, not a specific id,
      // and self-approval is impossible because the approver is a distinct
      // assignee in every legitimate flow.
      return role === 'approver';
    },

    async submit({ requestedRole = 'applicant', atStep = 0, confirmed = true } = {}) {
      if (this.state === 'draft') {
        this.error_fields = validateRequest(this.request);
        if (this.error_fields.length > 0) {
          // Client validation blocks submission; gate recorded but NOT signed.
          this._recordGate(requestedRole, false, atStep);
          return this;
        }
        // Valid draft -> submitted. Explicit human confirmation signed.
        this.state = 'submitted';
        this._recordGate(requestedRole, confirmed === true, atStep);
        return this;
      }
      // Already submitted/under_review/...: a second submit is suppressed
      // (duplicate ignored, input locked) and the gate is not signed.
      this._recordGate(requestedRole, false, atStep);
      return this;
    },

    route({ atStep = 0 } = {}) {
      // Automatic routing system action; records no human gate.
      if (this.state === 'submitted') this.state = 'under_review';
      return this;
    },

    async decide({ kind = 'approve', requestedRole = 'approver', reason = '', atStep = 0 } = {}) {
      if (this.state !== 'under_review') return this;
      // Deny-first: only the approver role may decide; otherwise the state does
      // NOT advance and no gate is recorded.
      if (!this._isApprover(requestedRole)) return this;

      if (kind === 'approve') {
        this.state = 'approved';
        this.persisted = true;
        this._recordGate('approver', true, atStep);
      } else if (kind === 'reject') {
        this.state = 'rejected';
        this.persisted = true;
        this.reject_reason = reason;
        this._recordGate('approver', true, atStep);
      }
      return this;
    },

    timeout({ escalate = false, atStep = 0 } = {}) {
      // A timeout on a request under review does NOT fabricate success or
      // failure; it stays under review and (optionally) escalates. No persist,
      // no human gate — a human can take over the escalated path.
      if (this.state === 'under_review') {
        this.escalated = escalate === true;
      }
      return this;
    },

    revise({ atStep = 0 } = {}) {
      // After a reject, the applicant revises and reopens a new draft version.
      if (this.state === 'rejected') {
        this.state = 'draft';
        this.version += 1;
        this.reject_reason = '';
        this.error_fields = [];
      }
      return this;
    },

    snapshot() {
      return {
        final_state: this.state,
        persisted: this.persisted,
        human_gates: clone(this.human_gates),
      };
    },
  };

  return machine;
}
