type SectionCardProps = {
  action?: React.ReactNode;
  bodyClassName?: string;
  children: React.ReactNode;
  className?: string;
  description?: string;
  headerClassName?: string;
  title: string;
};

export function SectionCard({
  action,
  bodyClassName,
  children,
  className,
  description,
  headerClassName,
  title,
}: SectionCardProps) {
  return (
    <section className={joinClassNames("section-card panel-shell", className)}>
      <header className={joinClassNames("section-card__header", headerClassName)}>
        <div className="section-card__copy">
          <h2 className="text-[1.02rem] font-semibold text-[var(--text-primary)] md:text-[1.12rem]">{title}</h2>
          {description ? (
            <p className="max-w-4xl text-[13px] leading-6 text-[var(--text-secondary)]">
              {description}
            </p>
          ) : null}
        </div>
        {action}
      </header>
      <div className={joinClassNames("section-card__body", bodyClassName)}>{children}</div>
    </section>
  );
}

function joinClassNames(...parts: Array<string | undefined>) {
  return parts.filter(Boolean).join(" ");
}
