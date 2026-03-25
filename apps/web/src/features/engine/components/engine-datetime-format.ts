import { formatObservabilityDateTime } from "@/features/observability/components/observability-datetime-support";

export function formatEngineDateTime(value: string | null): string {
  return formatObservabilityDateTime(value);
}
