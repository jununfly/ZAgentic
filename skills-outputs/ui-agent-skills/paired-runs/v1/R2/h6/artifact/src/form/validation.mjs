// 资料表单的字段级规则。每条规则只回答「这个字段当前有没有错」，不涉及状态迁移。
export const BIO_MAX_LENGTH = 200;

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export const FIELD_RULES = Object.freeze({
  nickname: [
    {
      id: 'required',
      test: (value) => String(value ?? '').trim().length > 0,
      message: '昵称为必填项',
    },
  ],
  email: [
    {
      id: 'format',
      test: (value) => EMAIL_PATTERN.test(String(value ?? '').trim()),
      message: '邮箱格式不正确',
    },
  ],
  bio: [
    {
      id: 'max_length',
      test: (value) => String(value ?? '').length <= BIO_MAX_LENGTH,
      message: `简介不能超过 ${BIO_MAX_LENGTH} 字`,
    },
  ],
});

export const PROFILE_FIELDS = Object.freeze(['nickname', 'email', 'bio']);

// 返回 { field: [message, ...] }，只包含真正出错的字段，保持字段声明顺序。
export function validateProfile(values) {
  const errors = {};
  for (const field of PROFILE_FIELDS) {
    const messages = (FIELD_RULES[field] ?? [])
      .filter((rule) => !rule.test(values?.[field]))
      .map((rule) => rule.message);
    if (messages.length > 0) errors[field] = messages;
  }
  return errors;
}

export function errorFieldList(values) {
  return Object.keys(validateProfile(values));
}
