// 用户资料编辑表单 - UI 绑定层（DOM <-> 状态机）
import { createFormMachine } from './machine.mjs';
import { createProfileStore, createBrowserBackend } from './store.mjs';

const FIELD_IDS = ['nickname', 'email', 'bio'];

export function mountForm(doc, options = {}) {
  const root = doc.getElementById('panel-form');
  if (!root) return null;
  const store = createProfileStore({ backend: createBrowserBackend() });
  const saved = store.read(options.user ?? 'user-001');
  const machine = createFormMachine({
    user: options.user ?? 'user-001',
    profile: saved ?? options.profile ?? { nickname: 'zj', email: 'zj@example.com', bio: '' },
    store,
  });

  const $ = (id) => doc.getElementById(id);
  const stateEl = $('f-state');
  const logEl = $('f-log');
  const confirmEl = $('f-confirm');
  const submitEl = $('f-submit');
  const responseEl = $('f-response');
  const fields = FIELD_IDS.map((id) => ({ id, input: $(`f-${id}`), err: $(`f-err-${id}`) }));

  function log(msg) {
    if (!logEl) return;
    const line = doc.createElement('div');
    line.textContent = msg;
    logEl.prepend(line);
  }

  function renderErrors() {
    const errs = machine.getErrors();
    for (const f of fields) {
      if (f.err) f.err.textContent = errs[f.id] ?? '';
    }
  }

  function render() {
    const state = machine.getState();
    const locked = machine.isLocked();
    if (stateEl) stateEl.textContent = state;
    for (const f of fields) {
      if (f.input) {
        if (f.input.value !== machine.getFields()[f.id]) f.input.value = machine.getFields()[f.id] ?? '';
        f.input.disabled = locked;
      }
    }
    if (submitEl) submitEl.disabled = locked;
    renderErrors();
  }

  for (const f of fields) {
    f.input?.addEventListener('input', (e) => {
      machine.edit(f.id, e.target.value);
      render();
    });
  }

  // 用户显式确认后才允许提交
  confirmEl?.addEventListener('change', render);

  submitEl?.addEventListener('click', () => {
    const res = machine.submit({ confirm: Boolean(confirmEl?.checked), atStep: Date.now() });
    if (!res.ok) {
      log(`提交被拦截: ${res.reason}`);
      render();
      return;
    }
    log('已确认提交，等待服务端…');
    render();
    const code = Number(responseEl?.value ?? '200');
    // 服务端交互（mock）：200 / 422 / 超时
    setTimeout(() => {
      const p = machine.persist({ responseCode: code, error: code === 0 ? 'timeout' : null });
      log(p.ok ? '保存成功 (200)' : `保存失败 code=${p.code} error=${p.error}`);
      render();
    }, 700);
  });

  doc.getElementById('f-recover')?.addEventListener('click', () => {
    machine.recover();
    log('回到可编辑状态，可修改后重新提交');
    render();
  });

  doc.getElementById('f-reset')?.addEventListener('click', () => {
    const persisted = machine.readPersisted();
    log(persisted ? `已持久化资料: ${JSON.stringify(persisted)}` : '尚无持久化资料');
  });

  render();
  return machine;
}
