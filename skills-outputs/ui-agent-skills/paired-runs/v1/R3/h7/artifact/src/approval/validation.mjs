// 报销单校验：金额必须 > 0，事由必填，附件为可选 mock 引用。
export function validateAmount(amount) {
  const value = Number(amount);
  return Number.isFinite(value) && value > 0;
}

export function validateRequest(request = {}) {
  const errors = [];
  const reason = String(request.reason ?? '').trim();

  if (!validateAmount(request.amount)) {
    errors.push({ field: 'amount', code: 'invalid_amount', message: '报销金额必须大于 0' });
  }
  if (reason.length === 0) {
    errors.push({ field: 'reason', code: 'required', message: '报销事由为必填项' });
  }

  const error_fields = errors.map((e) => e.field);
  return { valid: error_fields.length === 0, errors, error_fields };
}
