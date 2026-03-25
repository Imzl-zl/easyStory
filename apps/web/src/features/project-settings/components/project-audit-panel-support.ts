import { formatObservabilityDateTime } from "@/features/observability/components/observability-datetime-support";
import type { AuditLogView } from "@/lib/api/types";

export function formatProjectAuditTime(value: string) {
  return formatObservabilityDateTime(value);
}

export function buildProjectAuditQueryKey(projectId: string, eventType: string | null) {
  return ["project-audit", projectId, eventType] as const;
}

export function summarizeProjectAuditDetails(
  details: AuditLogView["details"],
): string {
  const keys = Object.keys(details ?? {});
  if (keys.length === 0) {
    return "无详情字段";
  }
  if (keys.length <= 3) {
    return keys.join(" · ");
  }
  return `${keys.slice(0, 3).join(" · ")} 等 ${keys.length} 项`;
}

export function formatProjectAuditTarget(item: AuditLogView): string {
  return `${item.entity_type} · ${item.entity_id.slice(0, 8)}`;
}
