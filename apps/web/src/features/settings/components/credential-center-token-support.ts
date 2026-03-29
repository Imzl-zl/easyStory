"use client";

export function sanitizeCredentialTokenInput(value: string) {
  return value.replaceAll(/\D+/g, "");
}

export function toCredentialTokenDraft(value: number | null | undefined) {
  return Number.isInteger(value) && (value ?? 0) > 0 ? String(value) : "";
}

export function parseContextWindowTokensDraft(value: string) {
  return parseOptionalTokenDraft(value);
}

export function parseDefaultMaxOutputTokensDraft(value: string) {
  return parseOptionalTokenDraft(value);
}

export function formatCredentialTokenLimit(value: number | null | undefined) {
  if (typeof value !== "number" || !Number.isInteger(value) || value <= 0) {
    return null;
  }
  if (value >= 1_000_000) {
    return `${formatCompactTokenUnit(value / 1_000_000)}M`;
  }
  if (value >= 1_000) {
    return `${formatCompactTokenUnit(value / 1_000)}K`;
  }
  return String(value);
}

function parseOptionalTokenDraft(value: string) {
  const normalized = sanitizeCredentialTokenInput(value);
  if (!normalized) {
    return null;
  }
  const parsed = Number.parseInt(normalized, 10);
  if (!Number.isFinite(parsed)) {
    return null;
  }
  return parsed;
}

function formatCompactTokenUnit(value: number) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1).replace(/\.0$/, "");
}
