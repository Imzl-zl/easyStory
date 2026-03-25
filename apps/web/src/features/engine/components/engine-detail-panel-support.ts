import type { EngineTabKey } from "./engine-workflow-status-support";

export type EngineDetailTabOption = {
  key: EngineTabKey;
  label: string;
};

const ENGINE_DETAIL_TAB_OPTIONS: EngineDetailTabOption[] = [
  { key: "overview", label: "执行概览" },
  { key: "tasks", label: "章节任务" },
  { key: "reviews", label: "审核" },
  { key: "billing", label: "账单" },
  { key: "logs", label: "日志" },
  { key: "context", label: "上下文" },
  { key: "replays", label: "Prompt 回放" },
];

const ENGINE_DETAIL_TAB_SET = new Set<EngineTabKey>(
  ENGINE_DETAIL_TAB_OPTIONS.map((item) => item.key),
);

export function listEngineDetailTabs(): EngineDetailTabOption[] {
  return ENGINE_DETAIL_TAB_OPTIONS;
}

export function resolveEngineDetailTab(value: string | null): EngineTabKey {
  if (!value) {
    return "overview";
  }
  if (ENGINE_DETAIL_TAB_SET.has(value as EngineTabKey)) {
    return value as EngineTabKey;
  }
  return "overview";
}
