// Role resolution and deny-first authority checks for the expense approval flow.

export const Role = Object.freeze({
  APPLICANT: 'applicant',
  APPROVER: 'approver',
  SYSTEM: 'system',
  OUTSIDER: 'outsider',
});

export const REGISTERED_ROLES = Object.freeze([Role.APPLICANT, Role.APPROVER, Role.SYSTEM]);

export const DENY_CODES = Object.freeze({
  NOT_APPROVER: 'actor_role_not_approver',
  SELF_APPROVAL: 'actor_is_applicant_self_approval',
  NO_APPROVER: 'no_approver_assigned',
  UNKNOWN_ACTOR: 'actor_not_resolvable',
});

// A request may name a role ("approver") or a raw actor id ("user-006").
export function resolveActorId(requestedRole, parties = {}) {
  if (requestedRole === Role.APPROVER) return parties.approverId ?? null;
  if (requestedRole === Role.APPLICANT) return parties.applicantId ?? null;
  if (requestedRole === Role.SYSTEM) return Role.SYSTEM;
  return requestedRole ?? null;
}

export function actorRole(actorId, parties = {}) {
  if (actorId === Role.SYSTEM) return Role.SYSTEM;
  if (actorId === null || actorId === undefined) return Role.OUTSIDER;
  const isApplicant = parties.applicantId != null && actorId === parties.applicantId;
  const isApprover = parties.approverId != null && actorId === parties.approverId && !isApplicant;
  if (isApprover) return Role.APPROVER;
  if (isApplicant) return Role.APPLICANT;
  return Role.OUTSIDER;
}

// deny-first: collect every violation before answering, never let a decision slip through.
export function authorizeDecision({ requestedRole, parties = {} }) {
  const actorId = resolveActorId(requestedRole, parties);
  const role = actorRole(actorId, parties);
  const denied = [];
  if (actorId === null || actorId === undefined) denied.push(DENY_CODES.UNKNOWN_ACTOR);
  if (parties.approverId === null || parties.approverId === undefined) denied.push(DENY_CODES.NO_APPROVER);
  if (role !== Role.APPROVER) denied.push(DENY_CODES.NOT_APPROVER);
  if (role === Role.APPLICANT) denied.push(DENY_CODES.SELF_APPROVAL);
  return { allowed: denied.length === 0, role, actorId, denied };
}

export function describeParty(actorId, parties = {}) {
  const role = actorRole(actorId, parties);
  const label = role === Role.APPROVER ? 'Approver' : role === Role.APPLICANT ? 'Applicant' : role === Role.SYSTEM ? 'System' : 'Actor';
  return `${label} ${actorId ?? '(none)'}`;
}
