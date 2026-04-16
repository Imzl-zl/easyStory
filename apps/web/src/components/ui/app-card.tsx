import { clsx } from "clsx";

type CardVariant = "solid" | "muted" | "glass";

type AppCardProps = {
  /** Optional header content rendered above the body */
  header?: React.ReactNode;
  /** Optional footer content rendered below the body */
  footer?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  /** Visual style variant. solid = panel-shell, muted = panel-muted, glass = panel-glass */
  variant?: CardVariant;
  /** HTML element to render as */
  as?: "article" | "aside" | "div" | "section";
};

const VARIANT_CLASS: Record<CardVariant, string> = {
  solid: "panel-shell",
  muted: "panel-muted",
  glass: "panel-glass",
};

export function AppCard({
  header,
  footer,
  children,
  className,
  variant = "solid",
  as: Element = "div",
}: AppCardProps) {
  return (
    <Element className={clsx(VARIANT_CLASS[variant], className)}>
      {header ? (
        <div className="border-b border-line-soft px-5 py-4">{header}</div>
      ) : null}
      <div className="px-5 py-4">{children}</div>
      {footer ? (
        <div className="border-t border-line-soft px-5 py-4">{footer}</div>
      ) : null}
    </Element>
  );
}
