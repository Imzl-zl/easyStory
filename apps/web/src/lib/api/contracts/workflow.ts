export type WorkflowPauseReason =
  | "user_request"
  | "user_interrupted"
  | "budget_exceeded"
  | "review_failed"
  | "error"
  | "loop_pause"
  | "max_chapters_reached";

export type WorkflowNodeSummary = {
  id: string;
  name: string;
  node_type: string;
  depends_on: string[];
};

export type WorkflowStatus =
  | "created"
  | "running"
  | "paused"
  | "completed"
  | "failed"
  | "cancelled";

export type WorkflowExecution = {
  execution_id: string;
  project_id: string;
  template_id: string | null;
  workflow_id: string | null;
  workflow_name: string | null;
  workflow_version: string | null;
  mode: "manual" | "auto" | null;
  status: WorkflowStatus;
  current_node_id: string | null;
  current_node_name: string | null;
  pause_reason: string | null;
  resume_from_node: string | null;
  has_runtime_snapshot: boolean;
  started_at: string | null;
  completed_at: string | null;
  nodes: WorkflowNodeSummary[];
};

export type WorkflowStartPayload = {
  workflow_id?: string | null;
};

export type WorkflowPausePayload = {
  reason?: WorkflowPauseReason;
};

export type ChapterTaskDraft = {
  chapter_number: number;
  title: string;
  brief: string;
  key_characters?: string[];
  key_events?: string[];
};

export type ChapterTaskStatus =
  | "pending"
  | "generating"
  | "completed"
  | "failed"
  | "skipped"
  | "stale"
  | "interrupted";

export type ChapterTaskUpdatePayload = {
  title?: string;
  brief?: string;
  key_characters?: string[] | null;
  key_events?: string[] | null;
};

export type ChapterTaskView = {
  task_id: string;
  project_id: string;
  workflow_execution_id: string;
  chapter_number: number;
  title: string;
  brief: string;
  key_characters: string[];
  key_events: string[];
  status: ChapterTaskStatus;
  content_id: string | null;
};

export type ChapterTaskBatch = {
  project_id: string;
  workflow_execution_id: string;
  current_node_id: string | null;
  tasks: ChapterTaskView[];
};
