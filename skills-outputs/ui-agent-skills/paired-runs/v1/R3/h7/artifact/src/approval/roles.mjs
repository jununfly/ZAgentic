// 角色守卫：审批决定只能由 role=approver 发起，且不能自审。
// deny-first —— 角色不合法的调用在进入任何业务判定之前就被拒绝，不产生 gate，状态也不前进。
export const ROLES = {
  APPLICANT: 'applicant',
  APPROVER: 'approver',
  SYSTEM: 'system'
};

export const DECISION_ACTIONS = ['approve', 'reject'];

export function checkActor({ role, actorId = null, applicantId = null, action }) {
  if (DECISION_ACTIONS.includes(action)) {
    if (role !== ROLES.APPROVER) {
      return { allowed: false, reason: 'role_denied', field: 'role', message: '只有审批人角色可以发起通过或驳回' };
    }
    if (actorId && applicantId && actorId === applicantId) {
      return { allowed: false, reason: 'self_approval_denied', field: 'role', message: '申请人不能审批自己的单据' };
    }
    return { allowed: true };
  }

  if (action === 'submit') {
    if (role !== ROLES.APPLICANT) {
      return { allowed: false, reason: 'role_denied', field: 'role', message: '只有申请人可以提交报销单' };
    }
    return { allowed: true };
  }

  if (action === 'route' || action === 'timeout') {
    if (role !== ROLES.SYSTEM) {
      return { allowed: false, reason: 'role_denied', field: 'role', message: '路由与超时升级只能由系统触发' };
    }
    return { allowed: true };
  }

  return { allowed: false, reason: 'unknown_action', field: 'action', message: '未知动作' };
}
