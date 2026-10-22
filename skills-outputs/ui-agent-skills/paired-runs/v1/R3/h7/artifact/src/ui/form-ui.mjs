import { FormFlow, FORM_STATES } from '../form/machine.mjs';
import { OUTCOME } from '../mock/constants.mjs';

const FIELDS = ['nickname', 'email', 'bio'];

// 资料编辑表单的界面装配：所有状态迁移都由这里的控件触发。
// idle -> validating 由输入触发；validating -> submitting 由「确认提交」触发；
// submitting -> success/error 由「触发服务端响应」触发；error -> validating 由「返回修改」触发。
export function mountFormUI(root = document) {
  const el = (id) => root.getElementById(id);
  const flow = new FormFlow({
    userId: 'user-001',
    profile: { nickname: 'zj', email: 'zj@example.com', bio: 'AI-Native 实践者' }
  });

  const scenarioOf = () => {
    const value = el('f-scenario').value;
    if (value === '422') return OUTCOME.CONFLICT;
    if (value === 'timeout') return OUTCOME.TIMEOUT;
    return OUTCOME.OK;
  };

  function render() {
    el('f-state').textContent = flow.state;
    el('f-writes').textContent = String(flow.writes);
    el('f-persisted').textContent = String(flow.persisted);
    el('f-gates').textContent = String(flow.gates.length);
    el('f-marker').textContent = flow.explicit_marker ? `${flow.fallback} / 结果未确认` : '无';

    for (const field of FIELDS) {
      const error = flow.errors.find((e) => e.field === field);
      el(`f-err-${field}`).textContent = error ? error.message : '';
      el(`f-${field}`).disabled = flow.locked;
      if (el(`f-${field}`).value !== String(flow.profile[field] ?? '')) {
        el(`f-${field}`).value = flow.profile[field] ?? '';
      }
    }

    el('f-submit').disabled = flow.locked;
    el('f-respond').disabled = !flow.locked;
    el('f-recover').disabled = !flow.recoverable;

    const messages = [];
    if (flow.locked) messages.push('提交中：输入已锁定，重复点击不会生效。');
    if (flow.state === FORM_STATES.SUCCESS) messages.push('保存成功，已写入本地 mock 存储。');
    if (flow.state === FORM_STATES.ERROR && flow.explicit_marker) {
      messages.push('服务端超时：结果未确认，已回退到稳定路径并显式标记，未伪造成功。');
    } else if (flow.state === FORM_STATES.ERROR) {
      messages.push(`保存失败（${flow.lastError}）：可修改后重新提交。`);
    }
    if (flow.duplicateSuppressed) messages.push('重复的提交已被忽略，只落一次写。');
    el('f-feedback').textContent = messages.join(' ');
  }

  for (const field of FIELDS) {
    el(`f-${field}`).addEventListener('input', (event) => {
      flow.edit(field, event.target.value);
      render();
    });
  }

  el('f-submit').addEventListener('click', () => {
    const confirmed = el('f-confirm').checked;
    const result = flow.submit({ role: 'user', confirm: confirmed });
    if (!confirmed) {
      el('f-feedback').textContent = '请先勾选确认，再提交（不允许自动提交）。';
    } else if (!result.ok && result.reason === 'client_validation') {
      el('f-feedback').textContent = `校验未通过，禁止提交：${result.error_fields.join(', ')}`;
    }
    render();
  });

  el('f-respond').addEventListener('click', async () => {
    await flow.resolveSubmission({ scenario: scenarioOf() });
    render();
  });

  el('f-recover').addEventListener('click', () => {
    flow.recover();
    render();
  });

  render();
  return { flow, render };
}
