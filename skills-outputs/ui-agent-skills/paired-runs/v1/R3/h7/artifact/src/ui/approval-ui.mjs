import { ApprovalFlow, APPROVAL_STATES } from '../approval/machine.mjs';

const ACTORS = {
  applicant: { id: 'user-001', role: 'applicant', label: '申请人' },
  approver: { id: 'approver-001', role: 'approver', label: '审批人' },
  other: { id: 'user-006', role: 'user-006', label: '其他人（无审批权限）' }
};

// 报销审批的界面装配：每个状态迁移都有对应控件。
// draft -> submitted（确认提交）；submitted -> under_review（路由给审批人）；
// under_review -> approved/rejected（审批人确认决定）；rejected -> draft（改完重提新版本）；
// under_review 超时升级（只标记、不前进）。
export function mountApprovalUI(root = document) {
  const el = (id) => root.getElementById(id);
  const flow = new ApprovalFlow({
    requestId: 'expense-001',
    applicantId: 'user-001',
    approverId: 'approver-001',
    request: { amount: 1200, currency: 'CNY', reason: '客户拜访差旅费', attachment_ref: 'mock://receipt-001' }
  });

  const currentActor = () => ACTORS[el('a-role').value] ?? ACTORS.other;
  const confirmed = () => el('a-confirm').checked;

  function render() {
    el('a-state').textContent = flow.state;
    el('a-version').textContent = String(flow.version);
    el('a-escalated').textContent = flow.escalated ? `${flow.fallback} / 已升级待人工接管` : '无';
    el('a-writes').textContent = String(flow.writes);
    el('a-persisted').textContent = String(flow.persisted);
    el('a-gates').textContent = JSON.stringify(flow.gates);

    if (el('a-amount').value !== String(flow.request.amount)) el('a-amount').value = flow.request.amount;
    if (el('a-reason').value !== flow.request.reason) el('a-reason').value = flow.request.reason;
    if (el('a-attachment').value !== String(flow.request.attachment_ref ?? '')) {
      el('a-attachment').value = flow.request.attachment_ref ?? '';
    }

    const editable = flow.state === APPROVAL_STATES.DRAFT;
    el('a-amount').disabled = !editable;
    el('a-reason').disabled = !editable;
    el('a-attachment').disabled = !editable;

    el('a-err-amount').textContent = flow.errors.find((e) => e.field === 'amount')?.message ?? '';
    el('a-err-reason').textContent = flow.errors.find((e) => e.field === 'reason')?.message ?? '';

    el('a-submit').disabled = flow.state !== APPROVAL_STATES.DRAFT;
    el('a-route').disabled = flow.state !== APPROVAL_STATES.SUBMITTED;
    el('a-approve').disabled = flow.state !== APPROVAL_STATES.UNDER_REVIEW;
    el('a-reject').disabled = flow.state !== APPROVAL_STATES.UNDER_REVIEW;
    el('a-timeout').disabled = flow.state !== APPROVAL_STATES.UNDER_REVIEW;
    el('a-revise').disabled = flow.state !== APPROVAL_STATES.REJECTED;

    el('a-history').textContent = flow.history.length
      ? flow.history.map((h) => `v${h.version}:${h.state}${h.decision ? `(${h.decision.action})` : ''}`).join(' | ')
      : '暂无历史版本';
  }

  function say(message) {
    el('a-feedback').textContent = message;
  }

  el('a-amount').addEventListener('input', (event) => {
    flow.edit('amount', event.target.value);
    render();
  });
  el('a-reason').addEventListener('input', (event) => {
    flow.edit('reason', event.target.value);
    render();
  });
  el('a-attachment').addEventListener('input', (event) => {
    flow.edit('attachment_ref', event.target.value);
    render();
  });

  el('a-submit').addEventListener('click', async () => {
    const actor = currentActor();
    const result = await flow.submitRequest({ role: actor.role, actorId: actor.id, confirm: confirmed() });
    if (result.denied) say(`${actor.label} 无权提交：${result.message}`);
    else if (result.blocked && result.reason === 'client_validation') say(`校验未通过：${result.error_fields.join(', ')}`);
    else if (result.blocked && result.reason === 'confirm_required') say('请先勾选确认再提交。');
    else if (result.duplicate) say('当前状态不是草稿，重复提交被拒绝，未创建新申请。');
    else say('已提交，等待路由给审批人。');
    render();
  });

  el('a-route').addEventListener('click', () => {
    const result = flow.route({ role: 'system' });
    say(result.ok ? '已路由给审批人，进入审批中。' : `路由失败：${result.reason}`);
    render();
  });

  el('a-approve').addEventListener('click', async () => {
    const actor = currentActor();
    const result = await flow.decide({
      action: 'approve',
      role: actor.role,
      actorId: actor.id,
      confirm: confirmed(),
      reason: el('a-comment').value
    });
    if (result.denied) say(`越权被拒绝：${result.message}（状态未前进）`);
    else if (result.blocked) say('需要审批人勾选确认后再决定。');
    else say('审批通过，已持久化。');
    render();
  });

  el('a-reject').addEventListener('click', async () => {
    const actor = currentActor();
    const result = await flow.decide({
      action: 'reject',
      role: actor.role,
      actorId: actor.id,
      confirm: confirmed(),
      reason: el('a-comment').value
    });
    if (result.denied) say(`越权被拒绝：${result.message}（状态未前进）`);
    else if (result.blocked && result.reason === 'reason_required') say('驳回必须填写理由。');
    else if (result.blocked) say('需要审批人勾选确认后再决定。');
    else say('已驳回，申请人可修改后重新提交新版本。');
    render();
  });

  el('a-timeout').addEventListener('click', () => {
    const result = flow.escalateOnTimeout({ role: 'system' });
    say(result.ok ? '审批超时：已升级并显式标记，状态保持审批中，等待人工接管。' : `超时升级失败：${result.reason}`);
    render();
  });

  el('a-revise').addEventListener('click', () => {
    const actor = currentActor();
    const result = flow.revise({ role: actor.role, actorId: actor.id });
    if (result.denied) say(`${actor.label} 无权修改：${result.message}`);
    else say(`已回到草稿，可修改后重新提交（第 ${result.version} 版）。`);
    render();
  });

  render();
  return { flow, render };
}
