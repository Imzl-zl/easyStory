import type {
  ProjectIncubatorConversationDraft,
  SettingCompletenessIssue,
} from "@/lib/api/types";

import { formatSettingFieldLabel } from "./incubator-page-support";

type DraftGuidance = {
  actionLabel: string | null;
  detail: string;
  statusLabel: string;
  summary: string;
};

export function buildDraftGuidance(
  draft: ProjectIncubatorConversationDraft,
): DraftGuidance {
  if (draft.setting_completeness.issues.length > 0) {
    return {
      actionLabel: "让 AI 补一版摘要",
      detail: `当前缺少 ${formatIssueLabels(draft.setting_completeness.issues)}。这不影响创建项目，也不影响后面继续用 AI 生成大纲。`,
      statusLabel: "可继续",
      summary: "现在就能继续，剩下的是建议补齐的摘要项。",
    };
  }
  return {
    actionLabel: null,
    detail: "信息已经基本完整，可以直接创建项目，后面继续让 AI 生成大纲和正文。",
    statusLabel: "可开始",
    summary: "这份草稿已经可以直接往下走。",
  };
}

export function buildDraftAiCompletionPrompt(
  draft: ProjectIncubatorConversationDraft,
): string {
  const issueLabels = formatIssueLabels(draft.setting_completeness.issues);
  const questions = draft.follow_up_questions
    .map((question, index) => `${index + 1}. ${question}`)
    .join("\n");
  const sections = [
    "请根据我们前面的聊天内容，直接补齐当前项目草稿里还缺的设定。",
    "不要再让我自己填表，也不要只反问我。",
    "如果信息还不够，请按最适合当前故事方向的一版先补齐，优先保证后面可以继续生成大纲。",
  ];
  if (issueLabels) {
    sections.push(`当前还缺这些内容：${issueLabels}。`);
  }
  if (questions) {
    sections.push(`优先处理这些点：\n${questions}`);
  }
  sections.push("补齐后请直接给出一版可继续创建项目的设定建议。");
  return sections.join("\n");
}

export function shouldOfferDraftAiCompletion(
  draft: ProjectIncubatorConversationDraft | null,
): boolean {
  return Boolean(draft && draft.setting_completeness.issues.length > 0);
}

function formatIssueLabels(issues: SettingCompletenessIssue[]): string {
  const labels = issues.map((issue) => formatSettingFieldLabel(issue.field));
  return Array.from(new Set(labels)).join("、");
}
