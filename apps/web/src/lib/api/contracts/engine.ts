import type { JsonValue } from "@/lib/api/contracts/base";

export type WorkflowReviewStatus = "passed" | "failed" | "warning";

export type WorkflowReviewStatusSummary = {
  passed: number;
  failed: number;
  warning: number;
};

export type WorkflowReviewIssueSeverity = "critical" | "major" | "minor" | "suggestion";

export type WorkflowReviewIssueSummary = {
  total: number;
  critical: number;
  major: number;
  minor: number;
  suggestion: number;
};

export type WorkflowReviewIssueCategory =
  | "plot_inconsistency"
  | "character_inconsistency"
  | "style_deviation"
  | "banned_words"
  | "ai_flavor"
  | "logic_error"
  | "quality_low"
  | "other";

export type WorkflowReviewLocation = {
  paragraph_index: number | null;
  start_offset: number | null;
  end_offset: number | null;
  quoted_text: string | null;
};

export type WorkflowReviewIssue = {
  category: WorkflowReviewIssueCategory;
  severity: WorkflowReviewIssueSeverity;
  location: WorkflowReviewLocation | null;
  description: string;
  suggested_fix: string | null;
  evidence: string | null;
};

export type WorkflowReviewTypeSummary = {
  review_type: string;
  action_count: number;
  statuses: WorkflowReviewStatusSummary;
  issues: WorkflowReviewIssueSummary;
};

export type WorkflowReviewSummary = {
  workflow_execution_id: string;
  project_id: string;
  workflow_status: string;
  reviewed_node_count: number;
  total_actions: number;
  last_reviewed_at: string | null;
  statuses: WorkflowReviewStatusSummary;
  issues: WorkflowReviewIssueSummary;
  review_types: WorkflowReviewTypeSummary[];
};

export type WorkflowReviewAction = {
  id: string;
  node_execution_id: string;
  node_id: string;
  node_type: string;
  node_order: number;
  sequence: number;
  agent_id: string;
  reviewer_name: string | null;
  review_type: string;
  status: WorkflowReviewStatus;
  score: number | null;
  summary: string | null;
  issue_count: number;
  issues: WorkflowReviewIssue[];
  execution_time_ms: number | null;
  tokens_used: number | null;
  created_at: string;
};

export type TokenUsageView = {
  id: string;
  node_execution_id: string | null;
  usage_type: "generate" | "review" | "fix" | "analysis" | "dry_run";
  model_name: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  estimated_cost: string;
  created_at: string;
};

export type WorkflowBillingUsageBreakdown = {
  usage_type: TokenUsageView["usage_type"];
  call_count: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  estimated_cost: string;
};

export type WorkflowBillingBudgetStatus = {
  scope: "workflow" | "project_day" | "user_day";
  used_tokens: number;
  limit_tokens: number;
  warning_threshold: number;
  warning_reached: boolean;
  exceeded: boolean;
};

export type WorkflowBillingSummary = {
  workflow_execution_id: string;
  project_id: string;
  workflow_status: string;
  on_exceed: "pause" | "skip" | "fail";
  budget_recorded_at: string;
  budget_window_start_at: string;
  budget_window_end_at: string;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  total_estimated_cost: string;
  usage_by_type: WorkflowBillingUsageBreakdown[];
  budget_statuses: WorkflowBillingBudgetStatus[];
};

export type NodeExecutionStatus =
  | "pending"
  | "running"
  | "completed"
  | "skipped"
  | "failed"
  | "running_stream"
  | "reviewing"
  | "fixing"
  | "interrupted";

export type ExecutionLogLevel = "INFO" | "WARNING" | "ERROR";

export type WorkflowArtifactView = {
  id: string;
  artifact_type: string;
  content_version_id: string | null;
  payload: Record<string, JsonValue> | null;
  word_count: number | null;
  created_at: string;
};

export type ExecutionReviewActionView = {
  id: string;
  agent_id: string;
  reviewer_name: string | null;
  review_type: string;
  status: WorkflowReviewStatus;
  score: number | null;
  summary: string | null;
  issues: WorkflowReviewIssue[] | Record<string, JsonValue> | null;
  execution_time_ms: number | null;
  tokens_used: number | null;
  created_at: string;
};

export type ContextPreviewRequest = {
  node_id: string;
  chapter_number?: number | null;
  extra_inject?: ContextPreviewInjectItem[];
};

export type ContextPreviewInjectItem = {
  type:
    | "project_setting"
    | "outline"
    | "opening_plan"
    | "chapter_task"
    | "previous_chapters"
    | "story_bible"
    | "style_reference";
  required?: boolean;
  count?: number | null;
  analysis_id?: string | null;
  inject_fields?: string[];
};

export type ContextPreviewSection = {
  type: string;
  status: string;
  token_count: number;
  original_tokens?: number | null;
  selected_fields?: string[];
  items_count?: number | null;
  items_truncated?: number | null;
  phase?: string | null;
};

export type ContextPreviewReport = {
  total_tokens: number;
  budget_limit: number;
  model_context_window: number;
  sections: ContextPreviewSection[];
};

export type ContextPreview = {
  workflow_execution_id: string;
  project_id: string;
  node_id: string;
  node_name: string;
  skill_id: string;
  model_name: string;
  chapter_number: number | null;
  referenced_variables: string[];
  variables: Record<string, string>;
  rendered_prompt: string;
  context_report: ContextPreviewReport;
};

export type NodeExecutionView = {
  id: string;
  workflow_execution_id: string;
  node_id: string;
  sequence: number;
  node_order: number;
  node_type: string;
  status: NodeExecutionStatus;
  input_summary: Record<string, JsonValue>;
  context_report: Record<string, JsonValue> | null;
  output_data: Record<string, JsonValue> | null;
  retry_count: number;
  error_message: string | null;
  execution_time_ms: number | null;
  started_at: string | null;
  completed_at: string | null;
  artifacts: WorkflowArtifactView[];
  review_actions: ExecutionReviewActionView[];
};

export type ExecutionLogView = {
  id: string;
  workflow_execution_id: string;
  node_execution_id: string | null;
  level: ExecutionLogLevel;
  message: string;
  details: Record<string, JsonValue> | null;
  created_at: string;
};

export type AuditLogView = {
  id: string;
  actor_user_id: string | null;
  event_type: string;
  entity_type: string;
  entity_id: string;
  details: Record<string, JsonValue> | null;
  created_at: string;
};

export type PromptReplayView = {
  id: string;
  node_execution_id: string;
  replay_type: string;
  model_name: string;
  prompt_text: string;
  response_text: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  created_at: string;
};

export type ExportCreatePayload = {
  formats: string[];
};

export type ExportView = {
  id: string;
  project_id: string;
  format: string;
  filename: string;
  file_size: number | null;
  created_at: string;
};
