// 费用报销审批 - UI 绑定层（DOM <-> 状态机）
import { createApprovalMachine } from './machine.mjs';
import { createRequestStore, createBrowserBackend } from './store.mjs';

export function mountApproval(doc, options = {}) {
  const root = doc.getElementById('panel-approval');
  if (!root) return null;
  const applicant = options.applicant ?? 'user-001';
  const approver = options.approver ?? 'approver-001';
  const machine = createApprovalMachine({
    applicant,
    approver,
    request: options.request ?? { amount: 1200, currency: 'CNY', reason: '客户拜访差旅费', attachment_ref: 'mock://receipt-001' },
    store: createRequestStore({ backend: createBrowserBackend() }),
  });

  const $ = (id) => doc.getElementById(id);
  const stateEl = $('a-state');
  const versionEl = $('a-version');
  const logEl = $('a-log');
  const amountEl = $('a-amount');
  const reasonEl = $('a-reason');
  const attachEl = $('a-attachment');
  const confirmEl = $('a-confirm');
  const actorEl = $('a-actor');
  const decisionReasonEl = $('a-decision-reason');

  function log(msg) {
    if (!logEl) return;
    const line = doc.createElement('div');
    line.textContent = msg;
    logEl.prepend(line);
  }

  function renderErrors() {
    const errs = machine.getErrors();
    const amountErr = doc.getElementById('a-err-amount');
    const reasonErr = doc.getElementById('a-err-reason');
    if (amountErr) amountErr.textContent = errs.amount ?? '';
    if (reasonErr) reasonErr.textContent = errs.reason ?? '';
  }

  function render() {
    const state = machine.getState();
    const draftEditable = state === 'draft';
    if (stateEl) stateEl.textContent = state;
    if (versionEl) versionEl.textContent = String(machine.getVersion());
    const req = machine.getRequest();
    if (amountEl && document.activeElement !== amountEl) amountEl.value = String(req.amount ?? '');
    if (reasonEl && document.activeElement !== reasonEl) reasonEl.value = String(req.reason ?? '');
    if (attachEl && document.activeElement !== attachEl) attachEl.value = String(req.attachment_ref ?? '');
    for (const el of [amountEl, reasonEl, attachEl]) if (el) el.disabled = !draftEditable;
    renderErrors();
  }

  const bindEdit = (el, field) => {
    el?.addEventListener('input', (e) => {
      const raw = e.target.value;
      machine.edit(field, field === 'amount' ? Number(raw) : raw);
      renderErrors();
    });
  };
  bindEdit(amountEl, 'amount');
  bindEdit(reasonEl, 'reason');
  bindEdit(attachEl, 'attachment_ref');

  // 申请人提交（显式确认）
  $('a-submit')?.addEventListener('click', () => {
    const res = machine.submit({ confirm: Boolean(confirmEl?.checked), atStep: Date.now(), role: 'applicant', actor: applicant });
    log(res.ok ? '已提交，进入 submitted' : `提交被拦截: ${res.reason}`);
    render();
  });

  // 系统路由：submitted -> under_review
  $('a-route')?.addEventListener('click', () => {
    const res = machine.route({ atStep: Date.now() });
    log(res.ok ? '已路由到审批人，进入 under_review' : `路由失败: ${res.reason}`);
    render();
  });

  const decision = (kind) => {
    const role = actorEl?.value ?? 'applicant';
    const actor = role === 'applicant' ? applicant : role === 'approver' ? approver : role;
    const reason = decisionReasonEl?.value ?? '';
    const res = kind === 'approve'
      ? machine.approve({ confirm: Boolean(confirmEl?.checked), atStep: Date.now(), role, actor, reason })
      : machine.reject({ confirm: Boolean(confirmEl?.checked), atStep: Date.now(), role, actor, reason });
    if (res.denied) log(`审批被拒绝: ${res.reason} (role=${role}, actor=${actor}) 状态未前进`);
    else if (!res.ok) log(`审批未完成: ${res.reason}`);
    else log(`${kind === 'approve' ? '通过' : '驳回'}成功，状态=${res.state}`);
    render();
  };

  $('a-approve')?.addEventListener('click', () => decision('approve'));
  $('a-reject')?.addEventListener('click', () => decision('reject'));

  // 审批超时：保持 under_review，显式标记 + 升级
  $('a-timeout')?.addEventListener('click', () => {
    const res = machine.timeout({ atStep: Date.now() });
    log(res.ok ? '审批超时：已显式标记并升级，等待人工接管' : `超时处理失败: ${res.reason}`);
    render();
  });

  // 驳回后改完重新提交，形成新版本
  $('a-revise')?.addEventListener('click', () => {
    const res = machine.revise();
    log(res.ok ? `已基于驳回创建新版本 v${res.version}，可修改后重新提交` : `无法创建新版本: ${res.reason}`);
    render();
  });

  render();
  return machine;
}
