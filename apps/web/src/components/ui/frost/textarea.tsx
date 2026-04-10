"use client";

import { cn } from "@/lib/utils/cn";

type TextareaVariant = "default" | "glass";

type TextareaProps = {
  className?: string;
  variant?: TextareaVariant;
} & React.TextareaHTMLAttributes<HTMLTextAreaElement>;

const VARIANT_MAP: Record<TextareaVariant, string> = {
  default:
    "bg-surface border border-line-soft hover:border-line-strong focus:border-accent-primary focus:shadow-[0_0_0_3px_var(--line-focus)]",
  glass:
    "bg-glass border border-line-soft backdrop-blur-sm hover:border-line-strong focus:bg-surface focus:border-accent-primary focus:shadow-[0_0_0_3px_var(--line-focus)]",
};

export function Textarea({ className, variant = "default", ...rest }: TextareaProps) {
  return (
    <textarea
      className={cn(
        "w-full px-3 py-2.5 rounded-md",
        "text-text-primary text-sm leading-relaxed",
        "placeholder:text-text-placeholder",
        "outline-none resize-y",
        "transition-all duration-fast",
        VARIANT_MAP[variant],
        rest.disabled && "opacity-50 cursor-not-allowed",
        className,
      )}
      {...rest}
    />
  );
}
