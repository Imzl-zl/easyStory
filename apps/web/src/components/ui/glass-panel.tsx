import { clsx } from "clsx";

type PanelVariant = "shell" | "muted" | "glass" | "hero";

type GlassPanelProps = {
  variant?: PanelVariant;
  as?: "div" | "section" | "article" | "aside";
} & React.HTMLAttributes<HTMLDivElement>;

const variantClass: Record<PanelVariant, string> = {
  shell: "panel-shell",
  muted: "panel-muted",
  glass: "panel-glass",
  hero: "hero-card",
};

export function GlassPanel({
  variant = "glass",
  className,
  as: Tag = "div",
  ...rest
}: GlassPanelProps) {
  return (
    <Tag className={clsx(variantClass[variant], className)} {...rest} />
  );
}
