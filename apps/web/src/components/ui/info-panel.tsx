import { clsx } from "clsx";

type InfoPanelTone = "default" | "accent" | "warning" | "danger";

type InfoPanelProps = {
  title?: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
  tone?: InfoPanelTone;
};

const TONE_BORDER: Record<InfoPanelTone, string> = {
  default: "border-transparent",
  accent: "border-accent-primary-muted",
  warning: "border-accent-warning/30",
  danger: "border-accent-danger/30",
};

const TONE_BG: Record<InfoPanelTone, string> = {
  default: "bg-muted",
  accent: "bg-accent-primary-soft",
  warning: "bg-accent-warning/8",
  danger: "bg-accent-danger/8",
};

export function InfoPanel({
  title,
  description,
  children,
  className,
  tone = "default",
}: InfoPanelProps) {
  return (
    <section
      className={clsx(
        "space-y-3 rounded-2xl border p-4 shadow-sm",
        TONE_BORDER[tone],
        TONE_BG[tone],
        className,
      )}
    >
      {title || description ? (
        <header className="space-y-1">
          {title ? (
            <h3 className="font-serif text-lg font-semibold text-text-primary">{title}</h3>
          ) : null}
          {description ? (
            <p className="text-sm leading-6 text-text-secondary">{description}</p>
          ) : null}
        </header>
      ) : null}
      {children}
    </section>
  );
}
