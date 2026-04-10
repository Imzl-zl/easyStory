"use client";

import { cn } from "@/lib/utils/cn";

type InputVariant = "default" | "glass";

type InputProps = {
  className?: string;
  variant?: InputVariant;
} & Omit<React.InputHTMLAttributes<HTMLInputElement>, "size">;

const VARIANT_MAP: Record<InputVariant, string> = {
  default:
    "bg-surface border border-line-soft hover:border-line-strong focus:border-accent-primary focus:shadow-[0_0_0_3px_var(--line-focus)]",
  glass:
    "bg-glass border border-line-soft backdrop-blur-sm hover:border-line-strong focus:bg-surface focus:border-accent-primary focus:shadow-[0_0_0_3px_var(--line-focus)]",
};

export function Input({ className, variant = "default", ...rest }: InputProps) {
  return (
    <input
      className={cn(
        "w-full min-h-[36px] px-3 py-2 rounded-md",
        "text-text-primary text-sm leading-normal",
        "placeholder:text-text-placeholder",
        "outline-none",
        "transition-all duration-fast",
        VARIANT_MAP[variant],
        rest.disabled && "opacity-50 cursor-not-allowed",
        className,
      )}
      {...rest}
    />
  );
}
