// Field validation rules for the profile edit form.
// Kept free of any DOM / node API so both the browser view and the
// headless fixture runner share the exact same rules.

export const FIELDS = ['nickname', 'email', 'bio'];

export const LIMITS = {
  nicknameMax: 32,
  bioMax: 140,
};

export const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

/** Count user-perceived characters (CJK / emoji safe). */
export function charLength(value) {
  return Array.from(String(value ?? '')).length;
}

/**
 * Validate a single field.
 * @returns {string|null} human readable message, or null when valid.
 */
export function validateField(field, value) {
  const raw = value == null ? '' : String(value);
  switch (field) {
    case 'nickname': {
      const trimmed = raw.trim();
      if (!trimmed) return '昵称不能为空';
      if (charLength(trimmed) > LIMITS.nicknameMax) {
        return `昵称不能超过 ${LIMITS.nicknameMax} 个字符`;
      }
      return null;
    }
    case 'email': {
      const trimmed = raw.trim();
      if (!trimmed) return '邮箱不能为空';
      if (!EMAIL_RE.test(trimmed)) return '邮箱格式不正确';
      return null;
    }
    case 'bio': {
      if (charLength(raw) > LIMITS.bioMax) {
        return `简介不能超过 ${LIMITS.bioMax} 个字符`;
      }
      return null;
    }
    default:
      return `未知字段 ${field}`;
  }
}

/**
 * Validate every field.
 * @returns {{errors: Record<string,string>, errorFields: string[], valid: boolean}}
 */
export function validateProfile(values) {
  const errors = {};
  for (const field of FIELDS) {
    const message = validateField(field, values?.[field]);
    if (message) errors[field] = message;
  }
  const errorFields = FIELDS.filter((f) => errors[f]);
  return { errors, errorFields, valid: errorFields.length === 0 };
}
