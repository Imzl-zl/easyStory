import type { JsonValue } from "@/lib/api/contracts/base";

export type WorkflowReviewSummary = {
  workflow_execution_id: string;
  project_id: string;
  workflow_status: string;
  reviewed_node_count: number;
  total_actions: number;
  last_reviewed_at: string | null;
  statuses: Record<string, number>;
  issues: Record<string, number>;
  review_types: Array<Record<string, JsonValue>>;
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
  status: "passed" | "failed" | "warning";
  score: number | null;
  summary: string | null;
  issue_count: number;
  issues: Array<Record<string, JsonValue>>;
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

export type WorkflowBillingSummary = {
  workflow_execution_id: string;
  project_id: string;
  workflow_status: string;
  on_exceed: "pause" | "skip" | "fail";
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  total_estimated_cost: string;
  usage_by_type: Array<Record<string, JsonValue>>;
  budget_statuses: Array<Record<string, JsonValue>>;
};

export type ContextPreviewRequest = {
  node_id: string;
  chapter_number?: number | null;
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
  context_report: Record<string, JsonValue>;
};

export type NodeExecutionView = {
  id: string;
  workflow_execution_id: string;
  node_id: string;
  sequence: number;
  node_order: number;
  node_type: string;
  status: string;
  input_summary: Record<string, JsonValue>;
  context_report: Record<string, JsonValue> | null;
  output_data: Record<string, JsonValue> | null;
  retry_count: number;
  error_message: string | null;
  execution_time_ms: number | null;
  started_at: string | null;
  completed_at: string | null;
  artifacts: Array<Record<string, JsonValue>>;
  review_actions: Array<Record<string, JsonValue>>;
};

export type ExecutionLogView = {
  id: string;
  workflow_execution_id: string;
  node_execution_id: string | null;
  level: string;
  message: string;
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
