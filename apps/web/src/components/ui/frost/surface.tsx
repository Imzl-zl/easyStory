"use client";

import { cn } from "@/lib/utils/cn";

type SurfaceVariant = "solid" | "glass" | "muted" | "elevated";
type SurfacePadding = "none" | "sm" | "md" | "lg";

type SurfaceProps = {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  padding?: SurfacePadding;
  variant?: SurfaceVariant;
} & React.HTMLAttributes<HTMLDivElement>;

const VARIANT_MAP: Record<SurfaceVariant, string> = {
  solid:
    "bg-surface border border-line-soft shadow-sm",
  glass:
    "bg-glass border border-line-glass shadow-glass backdrop-blur-md",
  muted:
    "bg-muted border border-line-soft",
  elevated:
    "bg-elevated border border-line-soft shadow-md",
};

const PADDING_MAP: Record<SurfacePadding, string> = {
  none: "",
  sm: "p-3",
  md: "p-5",
  lg: "p-7",
};

export function Surface({
  children,
  className,
  hover = false,
  padding = "none",
  variant = "solid",
  ...rest
}: SurfaceProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-xl transition-shadow duration-smooth transition-border-color duration-fast",
        VARIANT_MAP[variant],
        PADDING_MAP[padding],
        hover && "hover:shadow-md hover:border-line-strong",
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  );
}
