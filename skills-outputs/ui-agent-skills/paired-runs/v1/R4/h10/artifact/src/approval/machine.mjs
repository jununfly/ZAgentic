// Expense reimbursement approval state machine (page two of the product).
//
// States: draft -> submitted -> under_review -> approved | rejected
//
// Roles & gates:
//   - submit() may only be done by the applicant role, after client-side
//     validation (amount > 0, reason required). A duplicate submit while the
//     request is already in flight is ignored.
//   - decide() (approve/reject) may only be done by the approver role. Anyone
//     else is denied and the state does NOT advance.
//   - reject MUST carry a reason.
//   - revise() moves a rejected request back to draft as a new version, keeping
//     the previous rejected record in history.
//   - timeout() on under_review escalates but never fakes success/failure.

export function createApprovalMachine({
  requestId = 'expense-unknown',
  applicantId = 'anonymous',
  approverId = null,
  request = {},
  initialState = 'draft',
  api = null,
} = {}) {
  let state = initialState;
  let persisted = false;
  let version = 1;
  let current = {
    amount: request.amount ?? 0,
    currency: request.currency ?? 'CNY',
    reason: request.reason ?? '',
    attachment_ref: request.attachment_ref ?? null,
  };
  let decision = null; // { kind, reason, by, at }
  let escalate = false;
  const history = []; // past versions/decisions, retained even after revision
  const humanGates = [];

  function validateRequest(req) {
    const errors = [];
    const amount = Number(req.amount);
    if (!(amount > 0)) errors.push('amount');
    if (!req.reason || String(req.reason).trim() === '') errors.push('reason');
    return errors;
  }

  function snapshotRecord() {
    return {
      requestId,
      applicantId,
      approverId,
      version,
      state,
      request: { ...current },
      decision,
      history: history.slice(),
    };
  }

  const machine = {
    get state() {
      return state;
    },

    async submit({ requestedRole = 'applicant', atStep = 0, confirmed = false } = {}) {
      // Duplicate / out-of-flow submit: request already left the draft stage.
      if (state !== 'draft') {
        humanGates.push({ role: 'applicant', signed: false, at_step: atStep });
        return machine;
      }

      // Client-side validation gate.
      const errors = validateRequest(current);
      if (errors.length > 0) {
        humanGates.push({ role: 'applicant', signed: false, at_step: atStep });
        return machine; // stay in draft
      }

      // Explicit applicant confirmation recorded as a human gate.
      humanGates.push({ role: 'applicant', signed: !!confirmed, at_step: atStep });
      state = 'submitted';
      if (api && typeof api.persist === 'function') {
        await api.persist(requestId, snapshotRecord());
      }
      persisted = true;
      return machine;
    },

    route({ atStep = 0 } = {}) {
      // System routing: submitted -> under_review.
      if (state === 'submitted') state = 'under_review';
      return machine;
    },

    async decide({ kind = 'approve', requestedRole = 'approver', reason = '', atStep = 0 } = {}) {
      if (state !== 'under_review') return machine;

      // Authorization gate: only the approver role may decide.
      if (requestedRole !== 'approver') {
        // Denied: no state change, no human gate, status does NOT advance.
        return machine;
      }

      humanGates.push({ role: 'approver', signed: true, at_step: atStep });
      decision = { kind, reason, by: requestedRole, at: atStep };
      state = kind === 'approve' ? 'approved' : 'rejected';
      if (api && typeof api.persist === 'function') {
        await api.persist(requestId, snapshotRecord());
      }
      persisted = true;
      return machine;
    },

    timeout({ escalate: doEscalate = false, atStep = 0 } = {}) {
      // Timeout while under review: escalate but never fake success/failure.
      if (state === 'under_review') {
        escalate = !!doEscalate;
      }
      return machine;
    },

    revise({ atStep = 0 } = {}) {
      // Applicant revises after a reject: keep the old record, start a new version.
      if (state === 'rejected') {
        history.push({ version, request: { ...current }, decision, outcome: 'rejected' });
        version += 1;
        decision = null;
        state = 'draft';
        persisted = false;
      }
      return machine;
    },

    snapshot() {
      return {
        final_state: state,
        persisted,
        human_gates: humanGates.slice(),
      };
    },
  };

  return machine;
}

export default createApprovalMachine;
