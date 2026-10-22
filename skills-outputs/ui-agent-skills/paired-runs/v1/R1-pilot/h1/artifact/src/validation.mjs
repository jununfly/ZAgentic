export const LIMITS = Object.freeze({ nickname: 24, bio: 160 });

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export function validateProfile(profile = {}) {
  const errors = {};
  const nickname = typeof profile.nickname === 'string' ? profile.nickname.trim() : '';
  const email = typeof profile.email === 'string' ? profile.email.trim() : '';
  const bio = typeof profile.bio === 'string' ? profile.bio : '';

  if (!nickname) errors.nickname = '昵称不能为空';
  else if (nickname.length > LIMITS.nickname) errors.nickname = `昵称最多 ${LIMITS.nickname} 个字符`;

  if (!email) errors.email = '邮箱不能为空';
  else if (!EMAIL_RE.test(email)) errors.email = '邮箱格式不正确';

  if (bio.length > LIMITS.bio) errors.bio = `简介最多 ${LIMITS.bio} 个字符`;

  const error_fields = Object.keys(errors);
  return { valid: error_fields.length === 0, errors, error_fields };
}
