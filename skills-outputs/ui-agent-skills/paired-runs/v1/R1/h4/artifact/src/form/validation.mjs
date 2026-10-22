// Field-level validation for the profile edit form.
// Pure functions: no DOM, no storage. Errors are { field, code, message }.

export const BIO_MAX_LENGTH = 200;
export const NICKNAME_MAX_LENGTH = 40;

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[A-Za-z]{2,}$/;

export const FIELDS = Object.freeze(["nickname", "email", "bio"]);

export function validateNickname(value) {
  const raw = typeof value === "string" ? value : "";
  const trimmed = raw.trim();
  if (trimmed.length === 0) {
    return { code: "required", message: "昵称不能为空" };
  }
  if (trimmed.length > NICKNAME_MAX_LENGTH) {
    return { code: "too_long", message: `昵称不能超过 ${NICKNAME_MAX_LENGTH} 个字符` };
  }
  return null;
}

export function validateEmail(value) {
  const raw = typeof value === "string" ? value.trim() : "";
  if (raw.length === 0) {
    return { code: "required", message: "邮箱不能为空" };
  }
  if (!EMAIL_PATTERN.test(raw)) {
    return { code: "format", message: "邮箱格式不正确" };
  }
  return null;
}

export function validateBio(value) {
  const raw = typeof value === "string" ? value : "";
  if (raw.length > BIO_MAX_LENGTH) {
    return { code: "too_long", message: `简介不能超过 ${BIO_MAX_LENGTH} 个字符` };
  }
  return null;
}

const RULES = {
  nickname: validateNickname,
  email: validateEmail,
  bio: validateBio,
};

/** Validate a single field. Returns an error object or null. */
export function validateField(field, profile) {
  const rule = RULES[field];
  if (!rule) return null;
  const problem = rule(profile[field]);
  return problem ? { field, ...problem } : null;
}

/**
 * Validate the whole draft.
 * @returns {{ ok: boolean, errors: Array<{field:string,code:string,message:string}> }}
 */
export function validateProfile(profile) {
  const errors = [];
  for (const field of FIELDS) {
    const problem = validateField(field, profile);
    if (problem) errors.push(problem);
  }
  return { ok: errors.length === 0, errors };
}

/** Map of field -> message, convenient for inline error rendering. */
export function errorsByField(errors) {
  const map = {};
  for (const error of errors) {
    if (!map[error.field]) map[error.field] = error.message;
  }
  return map;
}
