// 用户资料编辑表单 - 字段校验规则（纯逻辑，无 DOM）

export const LIMITS = {
  nicknameMax: 24,
  bioMax: 120,
};

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function asString(v) {
  return typeof v === 'string' ? v : v === undefined || v === null ? '' : String(v);
}

export function validateProfile(profile = {}) {
  const errors = {};
  const nickname = asString(profile.nickname).trim();
  const email = asString(profile.email).trim();
  const bio = asString(profile.bio);

  if (!nickname) {
    errors.nickname = '昵称为必填项';
  } else if (nickname.length > LIMITS.nicknameMax) {
    errors.nickname = `昵称长度不能超过 ${LIMITS.nicknameMax}`;
  }

  if (!email) {
    errors.email = '邮箱为必填项';
  } else if (!EMAIL_RE.test(email)) {
    errors.email = '邮箱格式不正确';
  }

  if (bio.length > LIMITS.bioMax) {
    errors.bio = `简介长度不能超过 ${LIMITS.bioMax}`;
  }

  const errorFields = Object.keys(errors);
  return { valid: errorFields.length === 0, errorFields, errors };
}
