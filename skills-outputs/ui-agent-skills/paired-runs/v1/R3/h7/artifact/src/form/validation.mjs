// 资料编辑表单的实时校验规则。
export const PROFILE_FIELDS = ['nickname', 'email', 'bio'];
export const BIO_MAX_LENGTH = 200;

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateProfile(profile = {}) {
  const errors = [];
  const nickname = String(profile.nickname ?? '').trim();
  const email = String(profile.email ?? '').trim();
  const bio = String(profile.bio ?? '');

  if (nickname.length === 0) {
    errors.push({ field: 'nickname', code: 'required', message: '昵称为必填项' });
  }
  if (email.length === 0) {
    errors.push({ field: 'email', code: 'required', message: '邮箱为必填项' });
  } else if (!EMAIL_PATTERN.test(email)) {
    errors.push({ field: 'email', code: 'format', message: '邮箱格式不正确' });
  }
  if (bio.length > BIO_MAX_LENGTH) {
    errors.push({ field: 'bio', code: 'max_length', message: `简介不能超过 ${BIO_MAX_LENGTH} 个字符` });
  }

  const error_fields = errors.map((e) => e.field);
  return { valid: error_fields.length === 0, errors, error_fields };
}
