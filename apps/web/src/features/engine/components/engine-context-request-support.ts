import type { ContextPreviewInjectItem } from "@/lib/api/types";

export const EXTRA_INJECT_PLACEHOLDER = `[
  {
    "type": "style_reference",
    "analysis_id": "00000000-0000-0000-0000-000000000001",
    "inject_fields": ["writing_style"]
  }
]`;

type StyleReferenceConfig = {
  analysisId: string;
  injectFields: string[];
};

export function normalizeNodeId(value: string): string {
  const normalized = value.trim();
  if (!normalized) {
    throw new Error("node_id 不能为空。");
  }
  return normalized;
}

export function parseChapterNumber(value: string): number | undefined {
  const normalized = value.trim();
  if (!normalized) {
    return undefined;
  }
  const parsed = Number(normalized);
  if (!Number.isInteger(parsed) || parsed < 1) {
    throw new Error("chapter_number 必须是大于 0 的整数。");
  }
  return parsed;
}

export function parseExtraInject(value: string): ContextPreviewInjectItem[] | undefined {
  const normalized = value.trim();
  if (!normalized) {
    return undefined;
  }
  const parsed = JSON.parse(normalized) as unknown;
  if (!Array.isArray(parsed)) {
    throw new Error("extra_inject 必须是 JSON 数组。");
  }
  return parsed as ContextPreviewInjectItem[];
}

export function parseInjectFields(value: string): string[] {
  const fields = value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);

  if (fields.length === 0) {
    throw new Error("inject_fields 至少需要一个字段。");
  }
  return Array.from(new Set(fields));
}

export function upsertStyleReferenceExtraInject(
  currentValue: string,
  config: StyleReferenceConfig,
): string {
  const existing = parseExtraInject(currentValue) ?? [];
  const preserved = existing.filter((item) => item.type !== "style_reference");
  const next: ContextPreviewInjectItem[] = [
    ...preserved,
    {
      type: "style_reference",
      analysis_id: config.analysisId,
      inject_fields: config.injectFields,
    },
  ];
  return JSON.stringify(next, null, 2);
}
