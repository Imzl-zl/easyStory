"use client";

import { cn } from "@/lib/utils/cn";

type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";
type ButtonSize = "sm" | "md" | "lg";

type ButtonProps = {
  children: React.ReactNode;
  className?: string;
  disabled?: boolean;
  icon?: React.ReactNode;
  iconRight?: React.ReactNode;
  size?: ButtonSize;
  variant?: ButtonVariant;
} & Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "disabled">;

const VARIANT_MAP: Record<ButtonVariant, string> = {
  primary:
    "bg-accent-primary text-text-on-accent border-none hover:bg-accent-hover hover:shadow-[0_2px_12px_rgba(93,122,107,0.20)] active:scale-[0.97] active:shadow-[0_1px_4px_rgba(93,122,107,0.14)]",
  secondary:
    "bg-glass text-text-primary border border-line-soft backdrop-blur-sm hover:bg-surface hover:border-line-strong hover:shadow-sm active:bg-surface-active",
  danger:
    "bg-transparent text-accent-danger border border-accent-danger hover:bg-accent-danger hover:text-text-on-accent active:bg-[rgba(184,90,90,0.9)]",
  ghost:
    "bg-transparent text-text-secondary border-none hover:bg-surface-hover hover:text-text-primary active:bg-surface-active",
};

const SIZE_MAP: Record<ButtonSize, string> = {
  sm: "h-7 px-3 text-xs gap-1",
  md: "h-[34px] px-4 text-[13px] gap-1.5",
  lg: "h-10 px-6 text-sm gap-2",
};

export function Button({
  children,
  className,
  disabled,
  icon,
  iconRight,
  size = "md",
  variant = "primary",
  ...rest
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-pill font-medium leading-none cursor-pointer select-none",
        "transition-all duration-fast",
        "relative overflow-hidden",
        "tracking-[-0.01em]",
        VARIANT_MAP[variant],
        SIZE_MAP[size],
        variant === "primary" &&
          "before:content-[''] before:absolute before:inset-0 before:bg-[linear-gradient(180deg,rgba(255,255,255,0.12)_0%,transparent_60%)] before:opacity-0 before:transition-opacity before:duration-fast hover:before:opacity-100 before:pointer-events-none",
        disabled && "opacity-45 cursor-not-allowed active:scale-100",
        className,
      )}
      disabled={disabled}
      {...rest}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      {children}
      {iconRight && <span className="shrink-0">{iconRight}</span>}
    </button>
  );
}
