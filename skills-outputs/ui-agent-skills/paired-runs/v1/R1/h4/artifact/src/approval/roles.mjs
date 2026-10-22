// Role resolution and authorisation for the expense approval flow.
// Deny-first: anything that is not an explicit approver decision call is refused.

export const APPROVAL_ROLES = Object.freeze({
  APPLICANT: "applicant",
  APPROVER: "approver",
  SYSTEM: "system",
  UNKNOWN: "unknown",
});

export const DENIAL = Object.freeze({
  ROLE: "role_denied",
  SELF: "self_approval_denied",
  STATE: "state_denied",
  REASON: "reason_required",
});

/**
 * Map a raw actor handle (either a lane role or a concrete user id) to an
 * identity. Only the literal approver lane resolves to the approver role.
 */
export function resolveActor(handle, context = {}) {
  const applicantId = context.applicant ?? null;
  const approverId = context.approver ?? null;

  if (handle === APPROVAL_ROLES.APPROVER) {
    return { role: APPROVAL_ROLES.APPROVER, userId: approverId, handle };
  }
  if (handle === APPROVAL_ROLES.APPLICANT) {
    return { role: APPROVAL_ROLES.APPLICANT, userId: applicantId, handle };
  }
  if (handle === APPROVAL_ROLES.SYSTEM) {
    return { role: APPROVAL_ROLES.SYSTEM, userId: null, handle };
  }
  if (approverId && handle === approverId) {
    return { role: APPROVAL_ROLES.APPROVER, userId: handle, handle };
  }
  if (applicantId && handle === applicantId) {
    return { role: APPROVAL_ROLES.APPLICANT, userId: handle, handle };
  }
  return { role: APPROVAL_ROLES.UNKNOWN, userId: handle ?? null, handle };
}

/**
 * Decide whether this actor may act on the request at all.
 * @returns {{ allowed: boolean, code?: string, field?: string }}
 */
export function canDecide(actor, request) {
  if (actor.role !== APPROVAL_ROLES.APPROVER) {
    return { allowed: false, code: DENIAL.ROLE, field: "role" };
  }
  if (!actor.userId) {
    return { allowed: false, code: DENIAL.ROLE, field: "role" };
  }
  if (actor.userId === request.applicant) {
    return { allowed: false, code: DENIAL.SELF, field: "approver" };
  }
  return { allowed: true };
}

export function canSubmit(actor, request) {
  if (actor.role !== APPROVAL_ROLES.APPLICANT) {
    return { allowed: false, code: DENIAL.ROLE, field: "role" };
  }
  if (!actor.userId || actor.userId !== request.applicant) {
    return { allowed: false, code: DENIAL.ROLE, field: "applicant" };
  }
  return { allowed: true };
}
