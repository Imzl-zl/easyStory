import type { WorkflowExecution } from "@/lib/api/types";

export type EngineTabKey =
  | "overview"
  | "tasks"
  | "reviews"
  | "billing"
  | "logs"
  | "context"
  | "replays";

export type WorkflowStatusCallout = {
  actionLabel: string;
  description: string;
  targetTab: EngineTabKey;
  title: string;
  tone: "warning" | "danger";
};

const PAUSE_REASON_CONFIG: Record<
  string,
  Omit<WorkflowStatusCallout, "description">
> = {
  budget_exceeded: {
    actionLabel: "查看预算",
    targetTab: "billing",
    title: "预算触发暂停",
    tone: "warning",
  },
  error: {
    actionLabel: "查看概览",
    targetTab: "overview",
    title: "运行时错误暂停",
    tone: "danger",
  },
  loop_pause: {
    actionLabel: "查看概览",
    targetTab: "overview",
    title: "流程到达暂停点",
    tone: "warning",
  },
  max_chapters_reached: {
    actionLabel: "查看概览",
    targetTab: "overview",
    title: "达到章节上限",
    tone: "warning",
  },
  review_failed: {
    actionLabel: "查看审核",
    targetTab: "reviews",
    title: "审核未通过",
    tone: "warning",
  },
  user_interrupted: {
    actionLabel: "查看概览",
    targetTab: "overview",
    title: "当前生成已中断",
    tone: "warning",
  },
  user_request: {
    actionLabel: "查看概览",
    targetTab: "overview",
    title: "工作流已暂停",
    tone: "warning",
  },
};

export function resolveWorkflowStatusCallout(
  workflow: WorkflowExecution | null | undefined,
): WorkflowStatusCallout | null {
  if (!workflow || workflow.status !== "paused" || !workflow.pause_reason) {
    return null;
  }

  const config = PAUSE_REASON_CONFIG[workflow.pause_reason] ?? {
    actionLabel: "查看概览",
    targetTab: "overview" as const,
    title: "工作流已暂停",
    tone: "warning" as const,
  };

  return {
    ...config,
    description: buildPauseReasonDescription(workflow),
  };
}

function buildPauseReasonDescription(workflow: WorkflowExecution): string {
  const location = workflow.current_node_name ?? workflow.current_node_id;
  const resumeNode = workflow.resume_from_node;
  const parts = [describePauseReason(workflow.pause_reason)];

  if (location) {
    parts.push(`当前停在 ${location}。`);
  }
  if (resumeNode) {
    parts.push(`恢复后将从 ${resumeNode} 继续。`);
  }
  return parts.join(" ");
}

function describePauseReason(reason: string | null): string {
  switch (reason) {
    case "review_failed":
      return "当前工作流因审核未通过而暂停，需先处理 reviewer 问题。";
    case "budget_exceeded":
      return "当前工作流因预算超限而暂停，需先检查 token 与成本口径。";
    case "user_interrupted":
      return "当前工作流因用户中断本次生成而暂停。";
    case "user_request":
      return "当前工作流由用户主动暂停。";
    case "error":
      return "当前工作流因运行时错误而暂停。";
    case "loop_pause":
      return "当前工作流已到达阶段暂停点，等待继续决策。";
    case "max_chapters_reached":
      return "当前工作流已达到章节上限，需确认后续推进策略。";
    default:
      return `当前工作流因 ${reason ?? "未知原因"} 暂停。`;
  }
}
