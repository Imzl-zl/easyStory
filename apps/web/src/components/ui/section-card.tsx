type SectionCardProps = {
  title: string;
  description?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
};

export function SectionCard({ title, description, action, children }: SectionCardProps) {
  return (
    <section className="section-card panel-shell">
      <header className="section-card__header">
        <div className="section-card__copy">
          <h2 className="font-serif text-xl font-semibold text-[var(--text-primary)]">{title}</h2>
          {description ? (
            <p className="max-w-3xl text-sm leading-6 text-[var(--text-secondary)]">
              {description}
            </p>
          ) : null}
        </div>
        {action}
      </header>
      <div className="section-card__body">{children}</div>
    </section>
  );
}
