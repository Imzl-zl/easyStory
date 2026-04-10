import type {
  ProjectSetting,
  SettingCompletenessResult,
} from "@/lib/api/types";

export type SettingPreviewSection = {
  title: string;
  items: Array<{
    label: string;
    value: string;
  }>;
};

type SettingValue = string | number | string[] | null | undefined;

export function buildProjectSettingIssueSummary(
  completeness?: SettingCompletenessResult,
  emptyMessage = "当前信息已基本完整。",
): string {
  if (!completeness || completeness.issues.length === 0) {
    return emptyMessage;
  }
  return completeness.issues
    .map((issue) => `${formatProjectSettingFieldLabel(issue.field)}：${issue.message}`)
    .join(" / ");
}

export function buildProjectSettingSections(setting: ProjectSetting): SettingPreviewSection[] {
  return [
    buildSection("基础设定", [
      ["题材", setting.genre],
      ["子题材", setting.sub_genre],
      ["目标读者", setting.target_readers],
      ["基调", setting.tone],
      ["核心冲突", setting.core_conflict],
      ["剧情方向", setting.plot_direction],
      ["特殊要求", setting.special_requirements],
    ]),
    buildSection("主角", [
      ["姓名", setting.protagonist?.name],
      ["身份", setting.protagonist?.identity],
      ["初始处境", setting.protagonist?.initial_situation],
      ["背景", setting.protagonist?.background],
      ["性格", setting.protagonist?.personality],
      ["目标", setting.protagonist?.goal],
    ]),
    buildSection("世界", [
      ["世界名称", setting.world_setting?.name],
      ["时代基线", setting.world_setting?.era_baseline],
      ["世界规则", setting.world_setting?.world_rules],
      ["力量体系", setting.world_setting?.power_system],
      ["关键地点", setting.world_setting?.key_locations],
    ]),
    buildSection("规模", [
      ["目标字数", setting.scale?.target_words],
      ["目标章节", setting.scale?.target_chapters],
      ["节奏", setting.scale?.pacing],
    ]),
  ].flatMap((section) => (section ? [section] : []));
}

export function formatProjectSettingFieldLabel(field: string): string {
  if (field === "genre") return "题材";
  if (field === "sub_genre") return "子题材";
  if (field === "target_readers") return "目标读者";
  if (field === "tone") return "整体气质";
  if (field === "core_conflict") return "核心冲突";
  if (field === "plot_direction") return "剧情方向";
  if (field === "special_requirements") return "特殊要求";
  if (field === "world_setting") return "世界设定";
  if (field === "scale") return "篇幅规划";
  if (field.startsWith("protagonist.")) return "主角设定";
  if (field.startsWith("world_setting.")) return "世界设定";
  if (field.startsWith("scale.")) return "篇幅规划";
  return field;
}

function buildSection(
  title: string,
  fields: Array<[string, SettingValue]>,
): SettingPreviewSection | null {
  const items = fields.flatMap(([label, rawValue]) => {
    const value = normalizeSettingValue(rawValue);
    return value ? [{ label, value }] : [];
  });
  if (items.length === 0) {
    return null;
  }
  return { title, items };
}

function normalizeSettingValue(value: SettingValue): string | null {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === "number") {
    return String(value);
  }
  if (typeof value === "string") {
    return value.trim() || null;
  }
  if (value.length === 0) {
    return null;
  }
  return value.join(" / ");
}
