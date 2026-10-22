// 费用报销审批 - 角色校验（纯逻辑，无 DOM）
// 审批动作只能由审批人角色发起；申请人自审批同样被拒绝。

export const ROLE_APPLICANT = 'applicant';
export const ROLE_APPROVER = 'approver';

export function canSubmit({ role, actor, applicant }) {
  if (role === ROLE_APPROVER) return false;
  if (role === ROLE_APPLICANT) return true;
  // 以具体用户 id 调用时，必须是申请人本人
  return Boolean(actor) && actor === applicant;
}

export function canDecide({ role, actor, approver, applicant }) {
  if (role !== ROLE_APPROVER) return false; // 非审批人角色：deny-first
  if (applicant && actor && actor === applicant) return false; // 禁止自审批
  if (approver && actor && actor !== approver) return false; // 非指定审批人
  return true;
}
