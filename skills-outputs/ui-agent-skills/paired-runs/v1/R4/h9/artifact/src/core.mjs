// core.mjs — shared deterministic helpers for the ui-agent-skills machines.

// Deterministic JSON stringify: object keys are sorted so two semantically
// equal objects always serialize to the same string. Array order is preserved.
export function stableStringify(value) {
  return JSON.stringify(value, (_key, val) => {
    if (val && typeof val === 'object' && !Array.isArray(val)) {
      const sorted = {};
      for (const k of Object.keys(val).sort()) sorted[k] = val[k];
      return sorted;
    }
    return val;
  });
}

// Deep clone of plain JSON-ish values (used to snapshot request/profile payloads).
export function clone(value) {
  return JSON.parse(JSON.stringify(value ?? null));
}

// Email format check (pragmatic, not RFC-complete — sufficient for client validation).
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Field-level validation for the profile form.
// Returns an array of field names that currently fail validation.
export function validateProfile(profile) {
  const errors = [];
  const nickname = (profile?.nickname ?? '').toString();
  const email = (profile?.email ?? '').toString();
  const bio = (profile?.bio ?? '').toString();

  if (nickname.trim().length === 0) errors.push('nickname');
  if (!EMAIL_RE.test(email)) errors.push('email');
  if (bio.length > 140) errors.push('bio');

  return errors;
}

// Field-level validation for the expense-approval request.
export function validateRequest(request) {
  const errors = [];
  const amount = Number(request?.amount);
  const reason = (request?.reason ?? '').toString();

  if (!Number.isFinite(amount) || amount <= 0) errors.push('amount');
  if (reason.trim().length === 0) errors.push('reason');

  return errors;
}
