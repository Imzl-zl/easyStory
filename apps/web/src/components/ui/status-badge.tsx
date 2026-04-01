const STATUS_CLASSNAMES: Record<string, string> = {
  ready: "bg-accent-ink/10 text-accent-ink",
  draft: "bg-text-tertiary/10 text-text-secondary",
  active: "bg-accent-ink/10 text-accent-ink",
  completed: "bg-accent-success/10 text-accent-success",
  passed: "bg-accent-success/10 text-accent-success",
  archived: "bg-text-tertiary/10 text-text-secondary",
  approved: "bg-accent-success/10 text-accent-success",
  stale: "bg-accent-warning/10 text-accent-warning",
  warning: "bg-accent-warning/10 text-accent-warning",
  running: "bg-accent-ink/10 text-accent-ink",
  paused: "bg-accent-warning/10 text-accent-warning",
  failed: "bg-accent-danger/10 text-accent-danger",
  cancelled: "bg-text-tertiary/10 text-text-secondary",
  blocked: "bg-accent-danger/10 text-accent-danger",
  not_started: "bg-text-tertiary/10 text-text-secondary",
  generating: "bg-accent-ink/10 text-accent-ink",
  interrupted: "bg-accent-warning/10 text-accent-warning",
  setting: "bg-accent-ink/10 text-accent-ink",
  outline: "bg-accent-ink/10 text-accent-ink",
  opening_plan: "bg-accent-ink/10 text-accent-ink",
  chapter_tasks: "bg-accent-ink/10 text-accent-ink",
  workflow: "bg-accent-ink/10 text-accent-ink",
  chapter: "bg-accent-ink/10 text-accent-ink",
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
      className={`inline-flex rounded-full px-3 py-1 text-xs font-medium tracking-[0.08em] ${
        STATUS_CLASSNAMES[status] ?? "bg-accent-ink/10 text-accent-ink"
      }`}
    >
      {label ?? STATUS_LABELS[status] ?? status}
    </span>
  );
}
