// 页面装配层：把报销审批状态机接到 DOM 上。规则与准入全部由 request-machine / roles 决定。
import { createApprovalFlow, APPROVAL_STATES } from './request-machine.mjs';

const APPLICANT = 'user-006';
const APPROVER = 'approver-001';

const SEED_REQUEST = Object.freeze({
  amount: 1200,
  currency: 'CNY',
  reason: '客户拜访差旅费',
  attachment_ref: 'mock://receipt-001',
});

const el = (id) => document.getElementById(id);

const flow = createApprovalFlow({
  applicant: APPLICANT,
  approver: APPROVER,
  request: SEED_REQUEST,
  initialState: APPROVAL_STATES.DRAFT,
});

const fieldNodes = {
  amount: el('amount'),
  reason: el('reason'),
  attachment_ref: el('attachment'),
  currency: el('currency'),
};

for (const [field, node] of Object.entries(fieldNodes)) {
  node.value = flow.draft[field] === null ? '' : String(flow.draft[field] ?? '');
}

let pendingIntent = null;
let busy = false;

fieldNodes.amount.addEventListener('input', () => applyDraftEdit());
fieldNodes.reason.addEventListener('input', () => applyDraftEdit());
fieldNodes.attachment_ref.addEventListener('input', () => applyDraftEdit());
fieldNodes.currency.addEventListener('change', () => applyDraftEdit());

async function applyDraftEdit() {
  await flow.dispatch({
    action: 'edit',
    role: 'applicant',
    actor: APPLICANT,
    from: flow.state,
    values: {
      amount: fieldNodes.amount.value === '' ? null : Number(fieldNodes.amount.value),
      reason: fieldNodes.reason.value,
      attachment_ref: fieldNodes.attachment_ref.value || null,
      currency: fieldNodes.currency.value,
    },
  });
  render();
}

const TONES = {
  [APPROVAL_STATES.APPROVED]: 'approved',
  [APPROVAL_STATES.REJECTED]: 'rejected',
  [APPROVAL_STATES.UNDER_REVIEW]: 'under_review',
};

function ulRender(list, items, emptyText) {
  list.textContent = '';
  if (items.length === 0) {
    const li = document.createElement('li');
    li.className = 'muted';
    li.textContent = emptyText;
    list.appendChild(li);
    return;
  }
  for (const item of items) {
    const li = document.createElement('li');
    li.textContent = item;
    list.appendChild(li);
  }
}

function render(lastDenial) {
  const snapshot = flow.snapshot();
  const flowErrors = snapshot.error_messages ?? {};

  for (const field of ['amount', 'reason']) {
    const messages = flowErrors[field] ?? [];
    fieldNodes[field].setAttribute('aria-invalid', messages.length > 0 ? 'true' : 'false');
    el(`err-${field}`).textContent = messages.join('；');
  }

  const locked = [APPROVAL_STATES.SUBMITTED, APPROVAL_STATES.UNDER_REVIEW, APPROVAL_STATES.APPROVED, APPROVAL_STATES.REJECTED].includes(
    snapshot.final_state,
  );
  for (const node of Object.values(fieldNodes)) node.disabled = locked;

  const badge = el('state-badge');
  badge.textContent = `${snapshot.final_state} · v${snapshot.version}`;
  badge.dataset.tone = TONES[snapshot.final_state] ?? snapshot.final_state;

  el('meta').textContent = `写入次数 ${snapshot.writes} · 已持久化 ${snapshot.persisted ? '是' : '否'}${
    snapshot.escalated ? ' · 已升级待人工接管' : ''
  }`;

  el('submit-btn').disabled = busy || snapshot.final_state !== APPROVAL_STATES.DRAFT;
  el('revise-btn').hidden = snapshot.final_state !== APPROVAL_STATES.REJECTED;
  el('route-btn').disabled = busy || snapshot.final_state !== APPROVAL_STATES.SUBMITTED;
  el('escalate-btn').disabled = busy || snapshot.final_state !== APPROVAL_STATES.UNDER_REVIEW;
  el('approve-btn').disabled = busy || snapshot.final_state !== APPROVAL_STATES.UNDER_REVIEW;
  el('reject-btn').disabled = busy || snapshot.final_state !== APPROVAL_STATES.UNDER_REVIEW;

  const banner = el('banner');
  if (snapshot.final_state === APPROVAL_STATES.APPROVED) {
    banner.hidden = false;
    banner.dataset.tone = 'success';
    banner.textContent = '报销单已通过并写入本地 mock 存储。';
  } else if (snapshot.final_state === APPROVAL_STATES.REJECTED) {
    banner.hidden = false;
    banner.dataset.tone = 'error';
    banner.textContent = '报销单被驳回（原因已记录），可以修改后重新提交新版本。';
  } else {
    banner.hidden = true;
  }

  el('deny-note').textContent = lastDenial ?? '';
  el('workflow-note').textContent = snapshot.escalated
    ? '审批超时：停留在审批中并已落显式升级标记，等待人工接管，不给出通过或驳回结论。'
    : '提交后需要由工作流路由到审批人；审批只能在受理后进行。';

  ulRender(
    el('history'),
    flow.history.map((entry) => `v${entry.version} · ${entry.status}`),
    '暂无历史版本',
  );
  ulRender(
    el('gates'),
    snapshot.human_gates.map((gate) => `step ${gate.at_step} · ${gate.role} · signed=${gate.signed}`),
    '暂无签名记录',
  );
}

function openConfirm(title, body, intent) {
  el('confirm-title').textContent = title;
  el('confirm-body').textContent = body;
  pendingIntent = intent;
  el('confirm-dialog').showModal();
  el('confirm-cancel').focus();
}

el('confirm-cancel').addEventListener('click', () => {
  pendingIntent = null;
  el('confirm-dialog').close();
});

el('confirm-ok').addEventListener('click', async () => {
  const intent = pendingIntent;
  pendingIntent = null;
  el('confirm-dialog').close();
  if (!intent || busy) return;
  busy = true;
  let denial = null;
  if (intent.kind === 'submit') {
    const result = await flow.dispatch({
      action: 'submit',
      role: 'applicant',
      actor: APPLICANT,
      confirmed: true,
      from: flow.state,
    });
    if (!result.ok && result.blocked_by === 'client_validation') {
      denial = '金额或事由不合法，提交被拦截。';
    } else if (!result.ok && result.duplicate) {
      denial = '该单已在流转中，重复提交被忽略。';
    }
  } else if (intent.kind === 'approve' || intent.kind === 'reject') {
    const reason = el('decision-reason').value;
    const result = await flow.dispatch({
      action: intent.kind,
      role: 'approver',
      actor: intent.actor,
      reason,
      confirmed: true,
      from: flow.state,
    });
    if (!result.ok && result.outcome === 'denied') {
      denial = `${intent.actor} 无权审批（${result.reason}），状态没有前进。`;
    } else if (!result.ok && result.blocked_by === 'reason_required') {
      denial = '驳回必须填写理由。';
    }
  }
  busy = false;
  render(denial);
});

el('submit-btn').addEventListener('click', () => {
  openConfirm('确认提交报销单', '提交后单据进入流转，需要审批人处理。这一步由你本人确认。', { kind: 'submit' });
});

el('revise-btn').addEventListener('click', async () => {
  await flow.dispatch({ action: 'edit', role: 'applicant', actor: APPLICANT, from: flow.state });
  render();
});

el('route-btn').addEventListener('click', async () => {
  busy = true;
  await flow.dispatch({ action: 'route', role: 'approver', actor: APPROVER, from: flow.state });
  busy = false;
  render();
});

el('escalate-btn').addEventListener('click', async () => {
  await flow.dispatch({ action: 'escalate', role: 'system', from: flow.state });
  render();
});

el('approve-btn').addEventListener('click', () => {
  const actor = el('approver-id').value;
  openConfirm('确认通过', `由 ${actor} 签发的通过决定。`, { kind: 'approve', actor });
});

el('reject-btn').addEventListener('click', () => {
  const actor = el('approver-id').value;
  openConfirm('确认驳回', `由 ${actor} 签发的驳回决定，附理由。`, { kind: 'reject', actor });
});

render();
