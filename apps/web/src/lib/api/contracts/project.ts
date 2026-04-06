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

export type ProjectDocumentSource =
  | "file"
  | "outline"
  | "opening_plan"
  | "chapter";

export type ProjectDocument = {
  project_id: string;
  path: string;
  content: string;
  version: string;
  source: ProjectDocumentSource;
  updated_at: string | null;
  document_revision_id: string | null;
  run_audit_id: string | null;
};

export type ProjectDocumentContentState = "ready" | "empty" | "placeholder";

export type ProjectDocumentCatalogEntry = {
  path: string;
  document_ref: string;
  binding_version: string;
  resource_uri: string;
  title: string;
  source: ProjectDocumentSource;
  document_kind: string;
  mime_type: string;
  schema_id: string | null;
  content_state: ProjectDocumentContentState;
  writable: boolean;
  version: string;
  updated_at: string | null;
  catalog_version: string;
};

export type ProjectDocumentSavePayload = {
  base_version: string;
  content: string;
};

export type ProjectDocumentEntryType = "file" | "folder";

export type ProjectDocumentTreeNode = {
  label: string;
  node_type: ProjectDocumentEntryType;
  path: string;
  children: ProjectDocumentTreeNode[];
};

export type ProjectDocumentEntry = {
  label: string;
  node_type: ProjectDocumentEntryType;
  path: string;
};

export type ProjectDocumentEntryCreatePayload = {
  kind: ProjectDocumentEntryType;
  path: string;
};

export type ProjectDocumentEntryRenamePayload = {
  path: string;
  next_path: string;
};

export type ProjectDocumentEntryDeleteResult = {
  node_type: ProjectDocumentEntryType;
  path: string;
};

export type ProjectTrashCleanupFailure = {
  project_id: string;
  message: string;
};

export type ProjectTrashCleanupResult = {
  deleted_count: number;
  skipped_count: number;
  failed_count: number;
  skipped_project_ids: string[];
  failed_items: ProjectTrashCleanupFailure[];
};

export type SettingCompletenessIssue = {
  field: string;
  level: "warning";
  message: string;
};

export type SettingCompletenessResult = {
  status: "ready" | "warning";
  issues: SettingCompletenessIssue[];
};

export type ProjectIncubatorAnswer = {
  variable: string;
  value: string;
};

export type ProjectIncubatorQuestion = {
  question: string;
  variable: string;
};

export type ProjectIncubatorTemplate = {
  id: string;
  name: string;
  description: string | null;
  genre: string | null;
  workflow_id: string | null;
  guided_questions: ProjectIncubatorQuestion[];
};

export type ProjectIncubatorAppliedAnswer = {
  variable: string;
  field_path: string;
  value: string | number | string[];
};

export type ProjectIncubatorUnmappedAnswer = {
  variable: string;
  value: string;
  reason: string;
};

export type ProjectIncubatorDraftPayload = {
  template_id: string;
  answers: ProjectIncubatorAnswer[];
};

export type ProjectIncubatorDraft = {
  template: ProjectIncubatorTemplate;
  project_setting: ProjectSetting;
  setting_completeness: SettingCompletenessResult;
  applied_answers: ProjectIncubatorAppliedAnswer[];
  unmapped_answers: ProjectIncubatorUnmappedAnswer[];
};

export type ProjectIncubatorConversationDraftPayload = {
  conversation_text: string;
  provider: string;
  model_name?: string;
};

export type ProjectIncubatorConversationDraft = {
  project_setting: ProjectSetting;
  setting_completeness: SettingCompletenessResult;
  follow_up_questions: string[];
};

export type ProjectIncubatorCreatePayload = {
  name: string;
  template_id: string;
  answers: ProjectIncubatorAnswer[];
  allow_system_credential_pool?: boolean;
};

export type ProjectIncubatorCreateResult = {
  project: ProjectDetail;
  setting_completeness: SettingCompletenessResult;
  applied_answers: ProjectIncubatorAppliedAnswer[];
  unmapped_answers: ProjectIncubatorUnmappedAnswer[];
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
  document_version: string;
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
  document_version: string;
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
