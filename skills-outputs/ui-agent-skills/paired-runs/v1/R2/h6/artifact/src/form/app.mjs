// 页面装配层：把 profile 状态机接到 DOM 上。业务规则一律由 profile-machine 决定，这里只做绑定。
import { createProfileFlow, FORM_STATES } from './profile-machine.mjs';
import { PROFILE_FIELDS, BIO_MAX_LENGTH } from './validation.mjs';

const SEED_PROFILE = Object.freeze({
  nickname: 'zj',
  email: 'zj@example.com',
  bio: 'AI-Native 实践者',
});

const KEY = 'profile:current';
const el = (id) => document.getElementById(id);

const flow = createProfileFlow({ user: 'user-001', profile: {}, initialState: FORM_STATES.IDLE });
// 「加载」当前资料：优先读已持久化的版本，没有则用种子数据。
const loaded = flow.store.read(KEY) ?? SEED_PROFILE;
for (const field of PROFILE_FIELDS) {
  const value = loaded[field] ?? '';
  el(field).value = value;
  flow.dispatch({ action: 'edit', role: 'user', field, value, from: flow.state });
}
flow.dispatch({ action: 'validate', role: 'system', from: flow.state });

const inputs = Object.fromEntries(PROFILE_FIELDS.map((field) => [field, el(field)]));
const errors = Object.fromEntries(PROFILE_FIELDS.map((field) => [field, el(`err-${field}`)]));
const submitBtn = el('submit-btn');
const recoverBtn = el('recover-btn');
const banner = el('banner');
const dialog = el('confirm-dialog');

let busy = false;

function render() {
  const snapshot = flow.snapshot();
  const flowErrors = flow.errors;

  for (const field of PROFILE_FIELDS) {
    const messages = flowErrors[field] ?? [];
    const input = inputs[field];
    input.setAttribute('aria-invalid', messages.length > 0 ? 'true' : 'false');
    input.disabled = busy;
    errors[field].textContent = messages.join('；');
  }
  el('bio-counter').textContent = `${inputs.bio.value.length} / ${BIO_MAX_LENGTH} 字`;
  el('bio-max').textContent = String(BIO_MAX_LENGTH);

  const badge = el('state-badge');
  badge.textContent = snapshot.final_state;
  const tone =
    snapshot.final_state === FORM_STATES.SUCCESS
      ? 'success'
      : snapshot.final_state === FORM_STATES.ERROR
        ? 'error'
        : snapshot.final_state === FORM_STATES.SUBMITTING
          ? 'busy'
          : 'idle';
  badge.dataset.tone = tone;

  el('meta').textContent = `写入次数 ${snapshot.writes} · 已持久化 ${snapshot.persisted ? '是' : '否'}${
    snapshot.duplicate_suppressed ? ' · 重复提交已忽略' : ''
  }${snapshot.fallback ? ` · fallback=${snapshot.fallback}` : ''}`;

  const failure = snapshot.final_state === FORM_STATES.ERROR;
  banner.hidden = snapshot.final_state === FORM_STATES.SUCCESS ? false : !failure;
  if (snapshot.final_state === FORM_STATES.SUCCESS) {
    banner.dataset.tone = 'success';
    banner.textContent = '资料已保存到本地 mock 存储。';
  } else if (failure) {
    banner.dataset.tone = 'error';
    banner.textContent = `提交未完成，资料没有被保存。${
      snapshot.recoverable ? '可以修改后重新提交。' : ''
    }（显式标记：已记录，未伪造成功）`;
  }

  submitBtn.disabled = busy || snapshot.submit_blocked;
  submitBtn.textContent = busy ? '提交中…' : '提交修改';
  el('server-behavior').disabled = busy;
  recoverBtn.hidden = !failure;

  ulRender(
    el('gates'),
    snapshot.human_gates.map((gate) => `step ${gate.at_step} · ${gate.role} · signed=${gate.signed}`),
  );
}

function ulRender(list, items) {
  list.textContent = '';
  if (items.length === 0) {
    const li = document.createElement('li');
    li.className = 'muted';
    li.textContent = '暂无签名记录';
    list.appendChild(li);
    return;
  }
  for (const item of items) {
    const li = document.createElement('li');
    li.textContent = item;
    list.appendChild(li);
  }
}

for (const field of PROFILE_FIELDS) {
  inputs[field].addEventListener('input', async () => {
    if (busy) return; // 提交中锁输入
    await flow.dispatch({ action: 'edit', role: 'user', field, value: inputs[field].value, from: flow.state });
    await flow.dispatch({ action: 'validate', role: 'system', from: flow.state });
    render();
  });
}

submitBtn.addEventListener('click', () => {
  dialog.showModal();
  el('confirm-cancel').focus();
});

el('confirm-cancel').addEventListener('click', () => dialog.close());

el('confirm-ok').addEventListener('click', async () => {
  dialog.close();
  if (busy) return;
  const result = await flow.dispatch({ action: 'submit', role: 'user', confirmed: true, from: flow.state });
  render();
  if (!result.ok) return;
  busy = true;
  render();
  const code = Number(el('server-behavior').value);
  await flow.dispatch({ action: 'persist', role: 'system', response_code: code, from: flow.state });
  busy = false;
  render();
});

recoverBtn.addEventListener('click', async () => {
  await flow.dispatch({ action: 'recover', role: 'user', from: flow.state });
  render();
});

render();
