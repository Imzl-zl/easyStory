const STATUS_CLASSNAMES: Record<string, string> = {
  draft: "bg-[rgba(101,92,82,0.12)] text-[var(--text-secondary)]",
  active: "bg-[rgba(46,111,106,0.12)] text-[var(--accent-ink)]",
  completed: "bg-[rgba(47,107,69,0.12)] text-[var(--accent-success)]",
  passed: "bg-[rgba(47,107,69,0.12)] text-[var(--accent-success)]",
  archived: "bg-[rgba(101,92,82,0.12)] text-[var(--text-secondary)]",
  approved: "bg-[rgba(47,107,69,0.12)] text-[var(--accent-success)]",
  stale: "bg-[rgba(183,121,31,0.14)] text-[var(--accent-warning)]",
  warning: "bg-[rgba(183,121,31,0.14)] text-[var(--accent-warning)]",
  running: "bg-[rgba(46,111,106,0.12)] text-[var(--accent-ink)]",
  paused: "bg-[rgba(183,121,31,0.14)] text-[var(--accent-warning)]",
  failed: "bg-[rgba(178,65,46,0.14)] text-[var(--accent-danger)]",
  cancelled: "bg-[rgba(101,92,82,0.12)] text-[var(--text-secondary)]",
};

type StatusBadgeProps = {
  status: string;
  label?: string;
};

export function StatusBadge({ status, label }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-xs font-medium uppercase tracking-[0.16em] ${
        STATUS_CLASSNAMES[status] ?? "bg-[rgba(58,124,165,0.12)] text-[var(--accent-info)]"
      }`}
    >
      {label ?? status}
    </span>
  );
}
