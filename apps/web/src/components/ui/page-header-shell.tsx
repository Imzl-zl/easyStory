import type { ReactNode } from "react";

type PageHeaderShellProps = {
  actions?: ReactNode;
  description: ReactNode;
  eyebrow: string;
  footer?: ReactNode;
  title: ReactNode;
  titleBadges?: ReactNode;
};

export function PageHeaderShell({
  actions,
  description,
  eyebrow,
  footer,
  title,
  titleBadges,
}: Readonly<PageHeaderShellProps>) {
  return (
    <section className="panel-shell p-6">
      <div className="flex flex-wrap items-start justify-between gap-5">
        <div className="min-w-0 flex-1 space-y-2">
          <p className="text-xs uppercase tracking-[0.28em] text-[var(--accent-ink)]">{eyebrow}</p>
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="font-serif text-3xl font-semibold text-[var(--text-primary)]">{title}</h1>
            {titleBadges}
          </div>
          <p className="max-w-3xl text-sm leading-6 text-[var(--text-secondary)]">{description}</p>
        </div>
        {actions ? <div className="flex max-w-full flex-wrap gap-2">{actions}</div> : null}
      </div>
      {footer ? <div className="mt-6 border-t border-[var(--line-soft)] pt-5">{footer}</div> : null}
    </section>
  );
}
