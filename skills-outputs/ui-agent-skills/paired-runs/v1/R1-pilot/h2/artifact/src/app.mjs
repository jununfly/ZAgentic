// Browser wiring for the profile edit form. All behaviour lives in the shared
// state machine; this module only renders it and forwards user intent.

import { createProfileForm } from './machine.mjs';
import { createBrowserRepo } from './persistence.mjs';
import { LIMITS, FIELDS } from './validation.mjs';

// Local mock "current profile" — no real backend.
const CURRENT_PROFILE = {
  nickname: 'zj',
  email: 'zj@example.com',
  bio: 'AI-Native 实践者',
};

const USER = 'user-001';

const repo = createBrowserRepo({ user: USER, profile: CURRENT_PROFILE });
const form = createProfileForm({ user: USER, repo });

let step = 0; // user action counter, feeds human_gate.at_step
let pendingTimer = null;

const el = {
  form: document.getElementById('profile-form'),
  fieldset: document.getElementById('fields'),
  nickname: document.getElementById('nickname'),
  email: document.getElementById('email'),
  bio: document.getElementById('bio'),
  nicknameError: document.getElementById('nickname-error'),
  emailError: document.getElementById('email-error'),
  bioError: document.getElementById('bio-error'),
  bioCount: document.getElementById('bio-count'),
  submit: document.getElementById('submit'),
  reset: document.getElementById('reset'),
  status: document.getElementById('status'),
  stateBadge: document.getElementById('state-badge'),
  dialog: document.getElementById('confirm-dialog'),
  dialogSummary: document.getElementById('confirm-summary'),
  dialogConfirm: document.getElementById('confirm-ok'),
  dialogCancel: document.getElementById('confirm-cancel'),
  simulate: document.getElementById('simulate'),
  gates: document.getElementById('gates'),
};

const inputs = { nickname: el.nickname, email: el.email, bio: el.bio };

function render() {
  const snap = form.snapshot();

  for (const field of FIELDS) {
    const input = inputs[field];
    if (document.activeElement !== input) input.value = snap.values[field];
    const showError = Boolean(snap.touched[field] && snap.errors[field]);
    const errorNode = el[`${field}Error`];
    errorNode.textContent = showError ? snap.errors[field] : '';
    input.setAttribute('aria-invalid', String(showError));
    input.classList.toggle('invalid', showError);
    input.disabled = snap.locked;
  }

  el.bioCount.textContent = `${Array.from(snap.values.bio).length}/${LIMITS.bioMax}`;
  el.bioCount.classList.toggle('over', Boolean(snap.errors.bio));

  el.submit.disabled = snap.locked || !snap.valid;
  el.submit.textContent = snap.locked ? '保存中…' : '保存资料';
  el.reset.disabled = snap.locked;

  el.stateBadge.textContent = snap.status;
  el.stateBadge.dataset.state = snap.status;

  el.status.className = 'status';
  el.status.setAttribute('aria-live', 'polite');
  if (snap.feedback) {
    el.status.classList.add(snap.feedback.kind);
    el.status.textContent = snap.feedback.message;
  } else if (!snap.valid && snap.status !== 'idle') {
    el.status.classList.add('error');
    el.status.textContent = '请先修正表单中的错误';
  } else {
    el.status.textContent = snap.status === 'idle' ? '资料已加载，可开始编辑' : '';
  }

  el.gates.textContent = snap.humanGates.length
    ? snap.humanGates.map((g) => `#${g.at_step} ${g.role} 已确认`).join(' · ')
    : '尚未提交确认';
}

function onInput(event) {
  const { name, value } = event.target;
  step += 1;
  form.edit(name, value);
  render();
}

function openConfirm() {
  const snap = form.snapshot();
  if (!snap.valid || snap.locked) {
    render();
    return;
  }
  el.dialogSummary.replaceChildren();
  for (const field of FIELDS) {
    const row = document.createElement('div');
    row.className = 'summary-row';
    const key = document.createElement('span');
    key.textContent = field;
    const val = document.createElement('strong');
    val.textContent = snap.values[field] || '（空）';
    row.append(key, val);
    el.dialogSummary.append(row);
  }
  el.dialog.showModal();
}

function confirmSubmit() {
  step += 1;
  const atStep = step;
  const result = form.submit({ confirmed: true, role: 'user', atStep });
  el.dialog.close();
  render();
  if (!result.ok) return;

  // Simulated latency, then the mocked persistence outcome.
  const simulated = Number(el.simulate.value);
  repo.setNextResponse(simulated);
  pendingTimer = setTimeout(() => {
    pendingTimer = null;
    form.persist(simulated);
    render();
    if (simulated !== 200) {
      inputs.nickname.focus();
    }
  }, 600);
}

function resetForm() {
  clearTimeout(pendingTimer);
  pendingTimer = null;
  window.location.reload();
}

el.form.addEventListener('input', onInput);
el.form.addEventListener('submit', (event) => {
  event.preventDefault();
  step += 1;
  if (!form.snapshot().valid) {
    form.submit({ confirmed: false, role: 'user', atStep: step });
    render();
    return;
  }
  openConfirm();
});
el.dialogConfirm.addEventListener('click', confirmSubmit);
el.dialogCancel.addEventListener('click', () => el.dialog.close());
el.dialog.addEventListener('cancel', (event) => {
  event.preventDefault();
  el.dialog.close();
});
el.reset.addEventListener('click', resetForm);

render();
