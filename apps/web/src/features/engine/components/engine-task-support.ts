import type {
  ChapterTaskDraft,
  ChapterTaskStatus,
  ChapterTaskUpdatePayload,
  ChapterTaskView,
  WorkflowExecution,
  WorkflowStatus,
} from "@/lib/api/types";

export type ChapterTaskEditorState = {
  title: string;
  brief: string;
  keyCharacters: string;
  keyEvents: string;
};

export type ChapterTaskDraftRow = {
  chapterNumber: string;
  title: string;
  brief: string;
  keyCharacters: string;
  keyEvents: string;
};

type TaskStatusPresentation = {
  badgeStatus: string;
  badgeLabel: string;
  description: string;
};

const ACTIVE_WORKFLOW_STATUSES = new Set<WorkflowStatus>(["created", "running", "paused"]);
const LIST_SEPARATOR = /[\n,，]/;

export function buildTaskEditorState(task: ChapterTaskView): ChapterTaskEditorState {
  return {
    title: task.title,
    brief: task.brief,
    keyCharacters: task.key_characters.join(", "),
    keyEvents: task.key_events.join(", "),
  };
}

export function buildDraftRows(tasks: ChapterTaskView[]): ChapterTaskDraftRow[] {
  if (tasks.length === 0) {
    return [buildEmptyDraftRow()];
  }
  return tasks.map((task) => ({
    chapterNumber: String(task.chapter_number),
    title: task.title,
    brief: task.brief,
    keyCharacters: task.key_characters.join(", "),
    keyEvents: task.key_events.join(", "),
  }));
}

export function buildEmptyDraftRow(chapterNumber = 1): ChapterTaskDraftRow {
  return {
    chapterNumber: String(chapterNumber),
    title: "",
    brief: "",
    keyCharacters: "",
    keyEvents: "",
  };
}

export function resolveTaskStatusPresentation(task: ChapterTaskView): TaskStatusPresentation {
  if (task.status === "generating" && task.content_id) {
    return {
      badgeStatus: "warning",
      badgeLabel: "待确认",
      description: "草稿已生成，等待用户确认当前章节正文。",
    };
  }
  if (task.status === "generating") {
    return {
      badgeStatus: "generating",
      badgeLabel: "生成中",
      description: "当前章节任务正在执行中。",
    };
  }
  if (task.status === "completed") {
    return {
      badgeStatus: "approved",
      badgeLabel: "已确认",
      description: "当前章节任务已经形成可继续推进的正文。",
    };
  }
  if (task.status === "stale") {
    return {
      badgeStatus: "stale",
      badgeLabel: "已失效",
      description: "上游真值已变化，当前任务计划必须重建后再继续使用。",
    };
  }
  if (task.status === "interrupted") {
    return {
      badgeStatus: "interrupted",
      badgeLabel: "已中断",
      description: "当前任务在执行过程中被打断，需要人工决定后续动作。",
    };
  }
  if (task.status === "failed") {
    return {
      badgeStatus: "failed",
      badgeLabel: "失败",
      description: "当前任务执行失败，需要修正任务或恢复工作流。",
    };
  }
  if (task.status === "skipped") {
    return {
      badgeStatus: "archived",
      badgeLabel: "已跳过",
      description: "当前任务已被显式跳过，不再继续执行。",
    };
  }
  return {
    badgeStatus: "draft",
    badgeLabel: "未开始",
    description: "当前任务尚未开始执行。",
  };
}

export function getRegenerateDisabledReason(workflow: WorkflowExecution | undefined): string | null {
  if (!workflow) {
    return "请先载入一个 workflow，再查看或重建章节任务。";
  }
  if (ACTIVE_WORKFLOW_STATUSES.has(workflow.status)) {
    return null;
  }
  return `当前载入的 workflow 状态为 ${workflow.status}，章节任务重建只对 created / running / paused 生效。`;
}

export function toTaskUpdatePayload(editor: ChapterTaskEditorState): ChapterTaskUpdatePayload {
  return {
    title: editor.title.trim(),
    brief: editor.brief.trim(),
    key_characters: splitList(editor.keyCharacters),
    key_events: splitList(editor.keyEvents),
  };
}

export function toRegeneratePayload(rows: ChapterTaskDraftRow[]): ChapterTaskDraft[] {
  const chapters: ChapterTaskDraft[] = rows.map((row) => {
    const chapterNumber = Number(row.chapterNumber.trim());
    if (!Number.isInteger(chapterNumber) || chapterNumber < 1) {
      throw new Error("章节号必须是大于等于 1 的整数。");
    }
    if (!row.title.trim()) {
      throw new Error(`第 ${chapterNumber} 章标题不能为空。`);
    }
    if (!row.brief.trim()) {
      throw new Error(`第 ${chapterNumber} 章任务摘要不能为空。`);
    }
    return {
      chapter_number: chapterNumber,
      title: row.title.trim(),
      brief: row.brief.trim(),
      key_characters: splitList(row.keyCharacters),
      key_events: splitList(row.keyEvents),
    };
  });
  const numbers = chapters.map((chapter) => chapter.chapter_number);
  if (numbers.length !== new Set(numbers).size) {
    throw new Error("章节号必须唯一，不能重复。");
  }
  return [...chapters].sort((left, right) => left.chapter_number - right.chapter_number);
}

export function hasStaleTasks(tasks: ChapterTaskView[]): boolean {
  return tasks.some((task) => task.status === "stale");
}

export function getTaskEditDisabledReason(status: ChapterTaskStatus): string | null {
  if (status === "stale") {
    return "当前任务已 stale，必须先重建章节计划后再编辑。";
  }
  if (isEditableTaskStatus(status)) {
    return null;
  }
  return `当前任务状态为 ${status}，不允许直接编辑。`;
}

export function nextChapterNumber(rows: ChapterTaskDraftRow[]): number {
  const numbers = rows.map((row) => Number(row.chapterNumber)).filter(Number.isFinite);
  return numbers.length === 0 ? 1 : Math.max(...numbers) + 1;
}

function splitList(value: string): string[] {
  return value
    .split(LIST_SEPARATOR)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function isEditableTaskStatus(status: ChapterTaskStatus): boolean {
  return ["pending", "generating", "failed", "interrupted"].includes(status);
}
