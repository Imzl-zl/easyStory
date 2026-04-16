"use client";

import { AppSelect } from "@/components/ui/app-select";

type SelectOption = { label: string; value: string; description?: string };

export function AssistantTextField({
  label,
  maxLength,
  placeholder,
  value,
  onChange,
}: Readonly<{
  label: string;
  maxLength: number;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
}>) {
  return (
    <label className="block space-y-2">
      <span className="text-sm font-medium text-text-primary">{label}</span>
      <input
        className="ink-input"
        maxLength={maxLength}
        placeholder={placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

export function AssistantTextareaField({
  className = "ink-input min-h-[88px]",
  label,
  maxLength,
  placeholder,
  value,
  onChange,
}: Readonly<{
  className?: string;
  label: string;
  maxLength: number;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
}>) {
  return (
    <label className="block space-y-2">
      <span className="text-sm font-medium text-text-primary">{label}</span>
      <textarea
        className={className}
        maxLength={maxLength}
        placeholder={placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

export function AssistantToggleField({
  checked,
  description,
  label,
  onChange,
}: Readonly<{
  checked: boolean;
  description: string;
  label: string;
  onChange: (value: boolean) => void;
}>) {
  return (
    <label className="flex items-start gap-3 rounded-2xl bg-glass shadow-glass px-4 py-3">
      <input
        checked={checked}
        className="mt-1 size-4 shrink-0 accent-accent-primary"
        type="checkbox"
        onChange={(event) => onChange(event.target.checked)}
      />
      <span className="space-y-1">
        <span className="block text-sm font-medium text-text-primary">{label}</span>
        <span className="block text-[12px] leading-5 text-text-secondary">
          {description}
        </span>
      </span>
    </label>
  );
}

export function AssistantSelectField({
  description,
  label,
  options,
  tone = "default",
  value,
  onChange,
}: Readonly<{
  description?: string;
  label: string;
  options: ReadonlyArray<SelectOption>;
  tone?: "default" | "danger";
  value: string;
  onChange: (value: string) => void;
}>) {
  return (
    <div className="space-y-2">
      <span className="text-sm font-medium text-text-primary">{label}</span>
      <AppSelect className="min-w-0" options={options} value={value} onChange={onChange} />
      {description ? (
        <p
          className={
            tone === "danger"
              ? "rounded-2xl bg-accent-danger/10 px-3 py-2 text-[12px] leading-5 text-accent-danger"
              : "text-[12px] leading-5 text-text-secondary"
          }
        >
          {description}
        </p>
      ) : null}
    </div>
  );
}
