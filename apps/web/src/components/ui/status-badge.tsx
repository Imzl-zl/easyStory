const STATUS_CLASSNAMES: Record<string, string> = {
  ready: "bg-accent-primary/10 text-accent-primary",
  draft: "bg-text-tertiary/10 text-text-secondary",
  active: "bg-accent-primary/10 text-accent-primary",
  completed: "bg-accent-success/10 text-accent-success",
  passed: "bg-accent-success/10 text-accent-success",
  archived: "bg-text-tertiary/10 text-text-secondary",
  approved: "bg-accent-success/10 text-accent-success",
  stale: "bg-accent-warning/10 text-accent-warning",
  warning: "bg-accent-warning/10 text-accent-warning",
  running: "bg-accent-primary/10 text-accent-primary",
  paused: "bg-accent-warning/10 text-accent-warning",
  failed: "bg-accent-danger/10 text-accent-danger",
  cancelled: "bg-text-tertiary/10 text-text-secondary",
  blocked: "bg-accent-danger/10 text-accent-danger",
  not_started: "bg-text-tertiary/10 text-text-secondary",
  generating: "bg-accent-primary/10 text-accent-primary",
  interrupted: "bg-accent-warning/10 text-accent-warning",
  setting: "bg-accent-primary/10 text-accent-primary",
  outline: "bg-accent-primary/10 text-accent-primary",
  opening_plan: "bg-accent-primary/10 text-accent-primary",
  chapter_tasks: "bg-accent-primary/10 text-accent-primary",
  workflow: "bg-accent-primary/10 text-accent-primary",
  chapter: "bg-accent-primary/10 text-accent-primary",
};

const STATUS_LABELS: Record<string, string> = {
  ready: "就绪",
  draft: "草稿",
  active: "进行中",
  completed: "已完成",
  passed: "已通过",
  archived: "已归档",
  approved: "已确认",
  stale: "待更新",
  warning: "需注意",
  running: "进行中",
  paused: "已暂停",
  failed: "失败",
  cancelled: "已取消",
  blocked: "无法继续",
  not_started: "未开始",
  generating: "生成中",
  interrupted: "已中断",
  setting: "设定",
  outline: "大纲",
  opening_plan: "开篇规划",
  chapter_tasks: "章节任务",
  workflow: "流程",
  chapter: "正文",
};

type StatusBadgeProps = {
  status: string;
  label?: string;
};

export function StatusBadge({ status, label }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex rounded-pill px-3 py-1 text-xs font-medium tracking-[0.04em] shadow-xs ${
        STATUS_CLASSNAMES[status] ?? "bg-accent-primary/10 text-accent-primary"
      }`}
    >
      {label ?? STATUS_LABELS[status] ?? status}
    </span>
  );
}
