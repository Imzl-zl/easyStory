"use client";

import { useId } from "react";

import { AppSelect } from "@/components/ui/app-select";

type Option = {
  description?: string;
  label: string;
  value: string;
};

export function FormSection({
  children,
  description,
  title,
}: Readonly<{
  children: React.ReactNode;
  description?: string;
  title: string;
}>) {
  return (
    <section className="space-y-3 rounded-[28px] border border-[rgba(101,92,82,0.12)] bg-[rgba(255,255,255,0.5)] p-4">
      <div className="space-y-1">
        <h4 className="font-serif text-lg font-semibold text-[var(--text-primary)]">{title}</h4>
        {description ? (
          <p className="text-sm leading-6 text-[var(--text-secondary)]">{description}</p>
        ) : null}
      </div>
      {children}
    </section>
  );
}

export function StaticField({
  description,
  label,
  value,
}: Readonly<{
  description?: string;
  label: string;
  value: string;
}>) {
  return (
    <div className="space-y-2">
      <span className="label-text">{label}</span>
      <div className="panel-muted px-4 py-3 text-sm text-[var(--text-primary)]">{value}</div>
      {description ? <p className="text-xs text-[var(--text-secondary)]">{description}</p> : null}
    </div>
  );
}

export function TextField({
  label,
  onChange,
  value,
  ...props
}: Readonly<
  Omit<React.ComponentProps<"input">, "onChange" | "value"> & {
    label: string;
    onChange: (value: string) => void;
    value: string;
  }
>) {
  return (
    <label className="block space-y-2">
      <span className="label-text">{label}</span>
      <input
        autoComplete={props.autoComplete ?? "off"}
        className="ink-input"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        {...props}
      />
    </label>
  );
}

export function TextAreaField({
  label,
  minHeightClassName = "min-h-32",
  onChange,
  value,
  ...props
}: Readonly<
  Omit<React.ComponentProps<"textarea">, "onChange" | "value"> & {
    label: string;
    minHeightClassName?: string;
    onChange: (value: string) => void;
    value: string;
  }
>) {
  return (
    <label className="block space-y-2">
      <span className="label-text">{label}</span>
      <textarea
        autoComplete={props.autoComplete ?? "off"}
        className={`ink-textarea ${minHeightClassName}`}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        {...props}
      />
    </label>
  );
}

export function SelectField({
  label,
  onChange,
  options,
  value,
}: Readonly<{
  label: string;
  onChange: (value: string) => void;
  options: Option[];
  value: string;
}>) {
  const fieldId = useId();

  return (
    <div className="space-y-2">
      <label className="label-text inline-flex" htmlFor={fieldId}>
        {label}
      </label>
      <AppSelect id={fieldId} options={options} value={value} onChange={onChange} />
    </div>
  );
}

export function RadioGroupField({
  label,
  onChange,
  options,
  value,
}: Readonly<{
  label: string;
  onChange: (value: string) => void;
  options: Option[];
  value: string;
}>) {
  const name = useId();
  return (
    <fieldset className="space-y-2">
      <legend className="label-text">{label}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => (
          <label
            key={option.value}
            className="rounded-full border border-[rgba(101,92,82,0.16)] bg-white/70 px-3 py-2 text-sm text-[var(--text-primary)]"
          >
            <input
              checked={value === option.value}
              className="mr-2"
              name={name}
              type="radio"
              value={option.value}
              onChange={(event) => onChange(event.target.value)}
            />
            {option.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export function CheckboxListField({
  description,
  emptyMessage,
  label,
  onChange,
  options,
  values,
}: Readonly<{
  description?: string;
  emptyMessage: string;
  label: string;
  onChange: (values: string[]) => void;
  options: Option[];
  values: string[];
}>) {
  return (
    <fieldset className="space-y-2">
      <legend className="label-text">{label}</legend>
      {description ? <p className="text-sm leading-6 text-[var(--text-secondary)]">{description}</p> : null}
      {options.length === 0 ? (
        <div className="panel-muted px-4 py-3 text-sm text-[var(--text-secondary)]">{emptyMessage}</div>
      ) : (
        <div className="grid gap-2 sm:grid-cols-2">
          {options.map((option) => (
            <label
              key={option.value}
              className="rounded-2xl border border-[rgba(101,92,82,0.12)] bg-white/70 px-4 py-3 text-sm text-[var(--text-primary)]"
            >
              <input
                checked={values.includes(option.value)}
                className="mr-2"
                type="checkbox"
                value={option.value}
                onChange={(event) => onChange(updateCheckboxValues(values, option.value, event.target.checked))}
              />
              {option.label}
              {option.description ? (
                <span className="mt-1 block text-xs text-[var(--text-secondary)]">{option.description}</span>
              ) : null}
            </label>
          ))}
        </div>
      )}
    </fieldset>
  );
}

export function FormNotice({
  message,
  tone,
}: Readonly<{
  message: string;
  tone: "danger" | "muted";
}>) {
  const className =
    tone === "danger"
      ? "rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]"
      : "panel-muted px-4 py-3 text-sm text-[var(--text-secondary)]";
  return <div className={className}>{message}</div>;
}

function updateCheckboxValues(values: string[], value: string, checked: boolean): string[] {
  if (checked) {
    return values.includes(value) ? values : [...values, value];
  }
  return values.filter((item) => item !== value);
}
