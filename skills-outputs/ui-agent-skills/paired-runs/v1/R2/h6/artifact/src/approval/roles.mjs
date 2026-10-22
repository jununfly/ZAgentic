// 角色准入：deny-first。越权者连 gate 都不是参与者，因此既不能推进状态，也不会被记账成签名。
export const APPROVAL_ROLES = Object.freeze({
  APPLICANT: 'applicant',
  APPROVER: 'approver',
  SYSTEM: 'system',
});

export const DENY_REASON = Object.freeze({
  NOT_APPROVER: 'role_not_permitted',
  SELF_APPROVAL: 'self_approval_denied',
  NOT_APPLICANT: 'role_not_permitted',
});

const idOf = (action) => action.actor ?? action.actor_id ?? null;

export function isApplicantActor(action, parties) {
  if (action.role === APPROVAL_ROLES.APPLICANT) return true;
  const id = idOf(action);
  return Boolean(id) && id === parties.applicant;
}

// 审批决定只能由审批人发起，且不得自审批（职责分离）。
export function checkDecisionAuthority(action, parties) {
  const id = idOf(action);
  if (id && parties.applicant && id === parties.applicant) {
    return { allowed: false, reason: DENY_REASON.SELF_APPROVAL, field: 'approver', path: 'role.authority' };
  }
  const byRole = action.role === APPROVAL_ROLES.APPROVER;
  const byIdentity = Boolean(id) && Boolean(parties.approver) && id === parties.approver;
  if (!byRole && !byIdentity) {
    return { allowed: false, reason: DENY_REASON.NOT_APPROVER, field: 'approver', path: 'role.authority' };
  }
  return { allowed: true, reason: null };
}

export function checkRoutingAuthority(action) {
  const allowedRoles = [APPROVAL_ROLES.SYSTEM, APPROVAL_ROLES.APPROVER];
  return { allowed: allowedRoles.includes(action.role), reason: allowedRoles.includes(action.role) ? null : DENY_REASON.NOT_APPROVER };
}
