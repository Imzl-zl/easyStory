import {
  createMyAssistantSkill,
  createProjectAssistantSkill,
  deleteMyAssistantSkill,
  deleteProjectAssistantSkill,
  getMyAssistantSkill,
  getProjectAssistantSkill,
  listMyAssistantSkills,
  listProjectAssistantSkills,
  updateMyAssistantSkill,
  updateProjectAssistantSkill,
} from "@/lib/api/assistant-skills";
import type { AssistantSkillPayload } from "@/lib/api/types";

export type AssistantSkillsPanelCopy = {
  createHint: string;
  createSuccess: string;
  deleteSuccess: string;
  description: string;
  detailLoading: string;
  dirtyMessage: string;
  emptyHint: string;
  listLoading: string;
  saveSuccess: string;
  summaryLabel: string;
  title: string;
};

export function buildAssistantSkillListQueryKey(scope: "project" | "user", projectId?: string) {
  return ["assistant-skills", scope, projectId ?? "me"] as const;
}

export function buildAssistantSkillDetailQueryKey(
  scope: "project" | "user",
  projectId: string | undefined,
  skillId: string | null,
) {
  return ["assistant-skill", scope, projectId ?? "me", skillId ?? "none"] as const;
}

export function buildAssistantSkillsPanelCopy(scope: "project" | "user"): AssistantSkillsPanelCopy {
  if (scope === "project") {
    return {
      createHint: "正在准备项目 Skills...",
      createSuccess: "项目 Skill 已创建。",
      deleteSuccess: "项目 Skill 已删除。",
      description: "只在当前项目里生效。适合写题材口径、角色语气和这个项目专用的长期写法。",
      detailLoading: "正在加载项目 Skill...",
      dirtyMessage: "当前项目 Skill 还有未保存的改动，请先保存或还原。",
      emptyHint: "右侧已经放好项目起步模板，也可以切到“按文件编辑”直接写第一份 SKILL.md。",
      listLoading: "正在读取项目 Skills...",
      saveSuccess: "项目 Skill 已保存。",
      summaryLabel: "项目 Skills",
      title: "项目 Skills",
    };
  }
  return {
    createHint: "正在准备 Skills...",
    createSuccess: "新的 Skill 已创建。",
    deleteSuccess: "Skill 已删除。",
    description: "你的聊天方式文件。可以用可视化编辑，也可以直接改 SKILL.md，聊天页能直接切换。",
    detailLoading: "正在加载 Skill...",
    dirtyMessage: "当前 Skill 还有未保存的改动，请先保存或还原。",
    emptyHint: "右侧已经放好一份起步模板，也可以切到“按文件编辑”直接写第一份 SKILL.md。",
    listLoading: "正在读取你的 Skills...",
    saveSuccess: "Skill 已保存。",
    summaryLabel: "我的 Skills",
    title: "Skills",
  };
}

export function loadAssistantSkills(scope: "project" | "user", projectId?: string) {
  if (scope === "project") {
    return listProjectAssistantSkills(requireProjectId(projectId, "Skills"));
  }
  return listMyAssistantSkills();
}

export function loadAssistantSkillDetail(
  scope: "project" | "user",
  projectId: string | undefined,
  skillId: string,
) {
  if (scope === "project") {
    return getProjectAssistantSkill(requireProjectId(projectId, "Skills"), skillId);
  }
  return getMyAssistantSkill(skillId);
}

export function createAssistantSkill(
  scope: "project" | "user",
  projectId: string | undefined,
  payload: AssistantSkillPayload,
) {
  if (scope === "project") {
    return createProjectAssistantSkill(requireProjectId(projectId, "Skills"), payload);
  }
  return createMyAssistantSkill(payload);
}

export function updateAssistantSkill(
  scope: "project" | "user",
  projectId: string | undefined,
  skillId: string,
  payload: AssistantSkillPayload,
) {
  if (scope === "project") {
    return updateProjectAssistantSkill(requireProjectId(projectId, "Skills"), skillId, payload);
  }
  return updateMyAssistantSkill(skillId, payload);
}

export function deleteAssistantSkill(
  scope: "project" | "user",
  projectId: string | undefined,
  skillId: string,
) {
  if (scope === "project") {
    return deleteProjectAssistantSkill(requireProjectId(projectId, "Skills"), skillId);
  }
  return deleteMyAssistantSkill(skillId);
}

function requireProjectId(projectId: string | undefined, label: string) {
  if (projectId) {
    return projectId;
  }
  throw new Error(`缺少项目 ID，无法读取${label}。`);
}
