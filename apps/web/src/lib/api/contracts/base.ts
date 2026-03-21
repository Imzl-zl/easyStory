export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export type AuthLoginPayload = {
  username: string;
  password: string;
};

export type AuthRegisterPayload = AuthLoginPayload & {
  email?: string;
};

export type AuthToken = {
  access_token: string;
  token_type: "bearer";
  user_id: string;
  username: string;
};

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

export type ProjectCreatePayload = {
  name: string;
  template_id?: string | null;
  project_setting?: ProjectSetting | null;
  allow_system_credential_pool?: boolean;
};

export type TemplateNodeView = {
  id: string;
  node_order: number;
  node_id: string | null;
  node_name: string | null;
  node_type: string;
  skill_id: string | null;
  config: Record<string, JsonValue> | null;
  position_x: number | null;
  position_y: number | null;
  ui_config: Record<string, JsonValue> | null;
};

export type TemplateGuidedQuestion = {
  question: string;
  variable: string;
};

export type TemplateSummary = {
  id: string;
  name: string;
  description: string | null;
  genre: string | null;
  workflow_id: string | null;
  is_builtin: boolean;
  node_count: number;
  created_at: string;
  updated_at: string;
};

export type TemplateDetail = TemplateSummary & {
  config: Record<string, JsonValue> | null;
  guided_questions: TemplateGuidedQuestion[];
  nodes: TemplateNodeView[];
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

export type ProjectSettingSnapshot = {
  project_id: string;
  genre: string | null;
  target_words: number | null;
  status: ProjectStatus;
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

export type ChapterDetail = ChapterSummary & {
  content_text: string;
  change_summary: string | null;
  created_by: "system" | "user" | "ai_assist" | "auto_fix" | "ai_partial";
  change_source: "user_edit" | "ai_generate" | "ai_fix" | "import";
  context_snapshot_hash: string | null;
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

export type CredentialOwnerType = "system" | "user" | "project";

export type CredentialView = {
  id: string;
  owner_type: CredentialOwnerType;
  owner_id: string | null;
  provider: string;
  display_name: string;
  masked_key: string;
  base_url: string | null;
  is_active: boolean;
  last_verified_at: string | null;
};

export type CredentialCreatePayload = {
  owner_type: CredentialOwnerType;
  project_id?: string | null;
  provider: string;
  display_name: string;
  api_key: string;
  base_url?: string | null;
};

export type CredentialVerifyResult = {
  credential_id: string;
  status: "verified";
  last_verified_at: string;
  message: string;
};
