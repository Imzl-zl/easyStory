const RETIRED_MODEL_MARKERS = [
  "is no longer available",
  "Please switch to",
] as const;

export function looksLikeRetiredModelMessage(message: string) {
  const trimmed = message.trim();
  return RETIRED_MODEL_MARKERS.some((marker) => trimmed.includes(marker));
}

export function normalizeModelProviderMessage(message: string) {
  const trimmed = message.trim();
  if (!trimmed) {
    return "模型服务暂时不可用，请稍后重试。";
  }
  if (!looksLikeRetiredModelMessage(trimmed)) {
    return trimmed;
  }
  return `当前默认模型已不可用，请换成可用模型后再试。上游提示：${trimmed}`;
}
