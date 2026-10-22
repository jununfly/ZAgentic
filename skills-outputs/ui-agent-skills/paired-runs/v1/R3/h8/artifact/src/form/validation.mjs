// Field-level validation for the profile edit form. Pure functions, no side effects.

export const BIO_MAX_LENGTH = 200;
export const FIELD_ORDER = Object.freeze(['nickname', 'email', 'bio']);

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export const FIELD_RULES = Object.freeze({
  nickname: {
    label: 'Nickname',
    hint: 'Nickname is required',
    check(value) {
      if (typeof value !== 'string' || value.trim() === '') return 'Nickname is required';
      return null;
    },
  },
  email: {
    label: 'Email',
    hint: 'Use a valid address, e.g. name@example.com',
    check(value) {
      if (typeof value !== 'string' || value.trim() === '') return 'Email is required';
      if (!EMAIL_PATTERN.test(value.trim())) return 'Email format is invalid';
      return null;
    },
  },
  bio: {
    label: 'Bio',
    hint: `Bio must be ${BIO_MAX_LENGTH} characters or fewer`,
    check(value) {
      if (value === null || value === undefined) return null;
      if (typeof value !== 'string') return 'Bio must be text';
      if (value.length > BIO_MAX_LENGTH) return `Bio exceeds ${BIO_MAX_LENGTH} characters`;
      return null;
    },
  },
});

export function validateField(field, value) {
  const rule = FIELD_RULES[field];
  if (!rule) {
    return { field, message: `Unknown field: ${String(field)}`, known: false };
  }
  const message = rule.check(value);
  return { field, message, known: true };
}

export function validateProfile(profile) {
  const error_fields = [];
  const field_errors = {};
  for (const field of FIELD_ORDER) {
    const result = validateField(field, profile ? profile[field] : undefined);
    if (result.message) {
      error_fields.push(field);
      field_errors[field] = result.message;
    }
  }
  return { valid: error_fields.length === 0, error_fields, field_errors };
}

export function bioRemaining(profile) {
  const length = typeof profile?.bio === 'string' ? profile.bio.length : 0;
  return Math.max(0, BIO_MAX_LENGTH - length);
}
