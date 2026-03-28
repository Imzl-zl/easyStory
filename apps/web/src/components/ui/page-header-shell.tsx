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
    <section className="panel-shell px-4 py-4 md:px-5 xl:px-6 xl:py-5">
      <div className="flex flex-wrap items-start justify-between gap-3 md:gap-4">
        <div className="min-w-0 flex-1 space-y-1.5">
          <p className="text-[10px] tracking-[0.18em] text-[var(--accent-ink)]">{eyebrow}</p>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-[1.35rem] font-semibold text-[var(--text-primary)] md:text-[1.6rem]">{title}</h1>
            {titleBadges}
          </div>
          <p className="max-w-4xl text-[13px] leading-6 text-[var(--text-secondary)]">{description}</p>
        </div>
        {actions ? <div className="flex max-w-full flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
      {footer ? <div className="mt-4 border-t border-[var(--line-soft)] pt-4 md:mt-5 md:pt-[1.125rem]">{footer}</div> : null}
    </section>
  );
}
