// Mock persistence for expense requests: submit saves the request, a decision saves the outcome.
// Approval timeouts escalate to a manual route; they never record a pass or a fail.

import { createCommitStore, FAILURE_POLICY, sleep } from '../core.mjs';

export const REVIEW_TIMEOUT_MS = 30000;

export const ESCALATION_POLICY = Object.freeze({
  fallback_route: FAILURE_POLICY.fallback_route,
  marker_label: FAILURE_POLICY.marker_label,
  message: 'Review window elapsed - escalated for manual takeover. No decision recorded.',
});

export const REQUEST_FIELDS = Object.freeze(['amount', 'currency', 'reason', 'attachment_ref']);

export function validateRequest(request = {}) {
  const error_fields = [];
  const field_errors = {};
  const amount = request.amount;
  if (typeof amount !== 'number' || !Number.isFinite(amount)) {
    error_fields.push('amount');
    field_errors.amount = 'Amount must be a number';
  } else if (!(amount > 0)) {
    error_fields.push('amount');
    field_errors.amount = 'Amount must be greater than 0';
  }
  const reason = request.reason;
  if (typeof reason !== 'string' || reason.trim() === '') {
    error_fields.push('reason');
    field_errors.reason = 'Reason is required';
  }
  // attachment is optional: the raw requirement does not declare it mandatory.
  return { valid: error_fields.length === 0, error_fields, field_errors };
}

export function createRequestStore() {
  return createCommitStore();
}

export function requestRecordKey(requestId, version) {
  return `expense:${requestId}:v${version}`;
}

export function decisionRecordKey(requestId, version) {
  return `expense:${requestId}:v${version}:decision`;
}

export function createApprovalApi({ latency = 0 } = {}) {
  return {
    latency,
    async saveRequest(request) {
      await sleep(latency);
      return { ok: true, savedAt: request.submittedAt ?? null, record: request };
    },
    async saveDecision(record) {
      await sleep(latency);
      return { ok: true, record };
    },
  };
}
