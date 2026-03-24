export type CharacterSetting = {
  name?: string;
  identity?: string;
  initial_situation?: string;
  background?: string;
  personality?: string;
  goal?: string;
};

export type WorldSetting = {
  name?: string;
  era_baseline?: string;
  world_rules?: string;
  power_system?: string;
  key_locations?: string[];
};

export type ScaleSetting = {
  target_words?: number;
  target_chapters?: number;
  pacing?: string;
};

export type ProjectSetting = {
  genre?: string;
  sub_genre?: string;
  target_readers?: string;
  tone?: string;
  core_conflict?: string;
  plot_direction?: string;
  protagonist?: CharacterSetting;
  key_supporting_roles?: CharacterSetting[];
  world_setting?: WorldSetting;
  scale?: ScaleSetting;
  special_requirements?: string;
};

export type ProjectStatus = "draft" | "active" | "completed" | "archived";
export type SettingImpactAction = "mark_stale";
export type SettingImpactTarget = "outline" | "opening_plan" | "chapter" | "chapter_tasks";

export type ProjectCreatePayload = {
  name: string;
  template_id?: string | null;
  project_setting?: ProjectSetting | null;
  allow_system_credential_pool?: boolean;
};

export type ProjectSummary = {
  id: string;
  name: string;
  status: ProjectStatus;
  genre: string | null;
  target_words: number | null;
  template_id: string | null;
  allow_system_credential_pool: boolean;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ProjectDetail = ProjectSummary & {
  owner_id: string;
  project_setting: ProjectSetting | null;
};

export type SettingCompletenessIssue = {
  field: string;
  level: "warning" | "blocked";
  message: string;
};

export type SettingCompletenessResult = {
  status: "ready" | "warning" | "blocked";
  issues: SettingCompletenessIssue[];
};

export type ProjectSettingImpactItem = {
  target: SettingImpactTarget;
  action: SettingImpactAction;
  count: number;
  message: string;
};

export type ProjectSettingImpactSummary = {
  has_impact: boolean;
  total_affected_entries: number;
  items: ProjectSettingImpactItem[];
};

export type ProjectSettingSnapshot = {
  project_id: string;
  genre: string | null;
  target_words: number | null;
  status: ProjectStatus;
  project_setting: ProjectSetting | null;
  impact: ProjectSettingImpactSummary;
};

export type PreparationAssetStepStatus =
  | "not_started"
  | "draft"
  | "approved"
  | "stale"
  | "archived";

export type PreparationChapterTaskStepStatus =
  | "not_started"
  | "pending"
  | "generating"
  | "completed"
  | "failed"
  | "stale"
  | "interrupted";

export type PreparationNextStep =
  | "setting"
  | "outline"
  | "opening_plan"
  | "chapter_tasks"
  | "workflow"
  | "chapter";

export type PreparationAssetStatus = {
  content_id: string | null;
  step_status: PreparationAssetStepStatus;
  content_status: "draft" | "approved" | "stale" | "archived" | null;
  version_number: number | null;
  has_content: boolean;
  updated_at: string | null;
};

export type PreparationChapterTaskCounts = {
  pending: number;
  generating: number;
  completed: number;
  failed: number;
  skipped: number;
  stale: number;
  interrupted: number;
};

export type PreparationChapterTaskStatus = {
  workflow_execution_id: string | null;
  step_status: PreparationChapterTaskStepStatus;
  total: number;
  counts: PreparationChapterTaskCounts;
};

export type WorkflowExecutionSummary = {
  execution_id: string;
  project_id: string;
  template_id: string | null;
  workflow_id: string | null;
  workflow_name: string | null;
  workflow_version: string | null;
  mode: "manual" | "auto" | null;
  status: "created" | "running" | "paused" | "failed" | "completed" | "cancelled";
  current_node_id: string | null;
  current_node_name: string | null;
  pause_reason: string | null;
  resume_from_node: string | null;
  has_runtime_snapshot: boolean;
  started_at: string | null;
  completed_at: string | null;
};

export type ProjectPreparationStatus = {
  project_id: string;
  setting: SettingCompletenessResult;
  outline: PreparationAssetStatus;
  opening_plan: PreparationAssetStatus;
  chapter_tasks: PreparationChapterTaskStatus;
  active_workflow: WorkflowExecutionSummary | null;
  can_start_workflow: boolean;
  next_step: PreparationNextStep;
  next_step_detail: string;
};

export type StoryAssetSavePayload = {
  title: string;
  content_text: string;
  change_summary?: string;
  created_by?: "system" | "user" | "ai_assist" | "auto_fix" | "ai_partial";
  change_source?: "user_edit" | "ai_generate" | "ai_fix" | "import";
};

export type StoryAsset = {
  project_id: string;
  content_id: string;
  content_type: "outline" | "opening_plan";
  title: string;
  status: "draft" | "approved" | "stale" | "archived";
  version_number: number;
  content_text: string;
};

export type StoryAssetImpactAction = "mark_stale";
export type StoryAssetImpactTarget = "opening_plan" | "chapter" | "chapter_tasks";

export type StoryAssetImpactItem = {
  target: StoryAssetImpactTarget;
  action: StoryAssetImpactAction;
  count: number;
  message: string;
};

export type StoryAssetImpactSummary = {
  has_impact: boolean;
  total_affected_entries: number;
  items: StoryAssetImpactItem[];
};

export type StoryAssetMutation = StoryAsset & {
  impact: StoryAssetImpactSummary;
};

export type ChapterSummary = {
  project_id: string;
  content_id: string;
  chapter_number: number;
  title: string;
  status: "draft" | "approved" | "stale" | "archived";
  current_version_number: number;
  best_version_number: number | null;
  word_count: number | null;
  last_edited_at: string | null;
};

export type ChapterImpactAction = "mark_stale";
export type ChapterImpactTarget = "chapter";

export type ChapterImpactItem = {
  target: ChapterImpactTarget;
  action: ChapterImpactAction;
  count: number;
  message: string;
};

export type ChapterImpactSummary = {
  has_impact: boolean;
  total_affected_entries: number;
  items: ChapterImpactItem[];
};

export type ChapterDetail = ChapterSummary & {
  content_text: string;
  change_summary: string | null;
  created_by: "system" | "user" | "ai_assist" | "auto_fix" | "ai_partial";
  change_source: "user_edit" | "ai_generate" | "ai_fix" | "import";
  context_snapshot_hash: string | null;
  impact: ChapterImpactSummary;
};

export type ChapterSavePayload = StoryAssetSavePayload & {
  context_snapshot_hash?: string | null;
};

export type ChapterVersion = {
  version_number: number;
  content_text: string;
  created_by: "system" | "user" | "ai_assist" | "auto_fix" | "ai_partial";
  change_source: "user_edit" | "ai_generate" | "ai_fix" | "import";
  change_summary: string | null;
  word_count: number | null;
  is_current: boolean;
  is_best: boolean;
  context_snapshot_hash: string | null;
  created_at: string;
};
