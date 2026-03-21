type EmptyStateProps = {
  title: string;
  description: string;
  action?: React.ReactNode;
};

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="panel-muted flex min-h-48 flex-col items-start justify-center gap-3 p-6">
      <h3 className="font-serif text-lg font-semibold">{title}</h3>
      <p className="max-w-2xl text-sm leading-6 text-[var(--text-secondary)]">{description}</p>
      {action}
    </div>
  );
}
