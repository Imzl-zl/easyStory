"use client";

export const DEFAULT_ASSISTANT_MAX_OUTPUT_TOKENS = 4096;
export const MIN_ASSISTANT_MAX_OUTPUT_TOKENS = 128;
export const MAX_ASSISTANT_MAX_OUTPUT_TOKENS = 131072;

export function sanitizeAssistantOutputTokenInput(value: string) {
  return value.replaceAll(/\D+/g, "");
}

export function resolveAssistantMaxOutputTokens(value: number | string | null | undefined) {
  const parsed = typeof value === "number" ? value : Number.parseInt((value ?? "").trim(), 10);
  if (!Number.isInteger(parsed)) {
    return DEFAULT_ASSISTANT_MAX_OUTPUT_TOKENS;
  }
  if (parsed < MIN_ASSISTANT_MAX_OUTPUT_TOKENS) {
    return DEFAULT_ASSISTANT_MAX_OUTPUT_TOKENS;
  }
  if (parsed > MAX_ASSISTANT_MAX_OUTPUT_TOKENS) {
    return MAX_ASSISTANT_MAX_OUTPUT_TOKENS;
  }
  return parsed;
}

export function toAssistantOutputTokenDraft(value: number | string | null | undefined) {
  return String(resolveAssistantMaxOutputTokens(value));
}
