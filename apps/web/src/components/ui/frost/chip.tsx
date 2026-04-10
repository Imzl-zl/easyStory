"use client";

import { cn } from "@/lib/utils/cn";

type ChipVariant = "default" | "active" | "success" | "warning" | "danger";

type ChipProps = {
  children: React.ReactNode;
  className?: string;
  icon?: React.ReactNode;
  onRemove?: () => void;
  variant?: ChipVariant;
} & React.HTMLAttributes<HTMLSpanElement>;

const VARIANT_MAP: Record<ChipVariant, string> = {
  default:
    "bg-glass border border-line-soft text-text-secondary backdrop-blur-sm",
  active:
    "bg-accent-primary border border-accent-primary text-text-on-accent",
  success:
    "bg-[rgba(90,138,107,0.10)] border border-[rgba(90,138,107,0.20)] text-accent-success",
  warning:
    "bg-[rgba(196,136,61,0.10)] border border-[rgba(196,136,61,0.20)] text-accent-warning",
  danger:
    "bg-[rgba(196,90,90,0.10)] border border-[rgba(196,90,90,0.20)] text-accent-danger",
};

export function Chip({
  children,
  className,
  icon,
  onRemove,
  variant = "default",
  ...rest
}: ChipProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 h-6 px-2.5",
        "rounded-pill",
        "text-[11px] font-medium leading-none",
        "tracking-[-0.01em]",
        "whitespace-nowrap select-none",
        "transition-all duration-fast",
        VARIANT_MAP[variant],
        className,
      )}
      {...rest}
    >
      {icon && <span className="shrink-0 [&>svg]:w-3 [&>svg]:h-3">{icon}</span>}
      {children}
      {onRemove && (
        <button
          aria-label="移除"
          className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full hover:bg-[rgba(0,0,0,0.08)] transition-colors duration-fast cursor-pointer"
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          type="button"
        >
          <svg fill="none" height="8" viewBox="0 0 8 8" width="8" xmlns="http://www.w3.org/2000/svg">
            <path d="M1 1L7 7M7 1L1 7" stroke="currentColor" strokeLinecap="round" strokeWidth="1.2" />
          </svg>
        </button>
      )}
    </span>
  );
}
