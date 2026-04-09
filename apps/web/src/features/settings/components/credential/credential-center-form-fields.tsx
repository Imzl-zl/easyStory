"use client";

import { useId } from "react";

import { AppSelect } from "@/components/ui/app-select";
import type { AppSelectOption } from "@/components/ui/app-select";
import {
  API_DIALECT_OPTIONS,
  AUTH_STRATEGY_OPTIONS,
  getDefaultAuthStrategy,
  getDefaultBaseUrl,
  sanitizeCredentialInteropProfileSelection,
  type CredentialFormState,
} from "@/features/settings/components/credential/credential-center-support";
import type { CredentialApiDialect } from "@/lib/api/types";

type FieldInputProps = Omit<React.ComponentProps<"input">, "onChange" | "value"> & {
  className?: string;
  description?: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
};

type StaticFieldProps = {
  className?: string;
  description: string;
  label: string;
  value: string;
};

type CredentialSelectFieldProps = {
  className?: string;
  description?: string;
  disabled?: boolean;
  label: string;
  options: AppSelectOption[];
  value: string;
  onChange: (value: string) => void;
};

export const API_DIALECT_SELECT_OPTIONS = API_DIALECT_OPTIONS.map((option) => ({
  description: option.description,
  label: option.label,
  value: option.value,
}));

export const AUTH_STRATEGY_SELECT_OPTIONS = AUTH_STRATEGY_OPTIONS.map((option) => ({
  description: option.description,
  label: option.label,
  value: option.value,
}));

export function FieldInput({
  className,
  description,
  label,
  value,
  onChange,
  ...props
}: Readonly<FieldInputProps>) {
  return (
    <label className={`block ${className ?? ""}`}>
      <span className="label-text">{label}</span>
      <input className="ink-input" value={value} onChange={(event) => onChange(event.target.value)} {...props} />
      {description ? <p className="mt-1.5 text-[12px] leading-5 text-[var(--text-secondary)]">{description}</p> : null}
    </label>
  );
}

export function StaticField({
  className,
  description,
  label,
  value,
}: Readonly<StaticFieldProps>) {
  return (
    <div className={`space-y-2 ${className ?? ""}`}>
      <span className="label-text">{label}</span>
      <div className="panel-muted px-3.5 py-2.5 text-[13px] leading-5 text-[var(--text-primary)]">{value}</div>
      <p className="text-[12px] leading-5 text-[var(--text-secondary)]">{description}</p>
    </div>
  );
}

export function CredentialSelectField({
  className,
  description,
  disabled = false,
  label,
  options,
  value,
  onChange,
}: Readonly<CredentialSelectFieldProps>) {
  const fieldId = useId();

  return (
    <div className={`space-y-2 ${className ?? ""}`}>
      <label className="label-text inline-flex" htmlFor={fieldId}>
        {label}
      </label>
      <AppSelect density="roomy" disabled={disabled} id={fieldId} options={options} value={value} onChange={onChange} />
      {description ? <p className="mt-1.5 text-[12px] leading-5 text-[var(--text-secondary)]">{description}</p> : null}
    </div>
  );
}

export function updateApiDialectState(
  current: CredentialFormState,
  apiDialect: CredentialApiDialect,
): CredentialFormState {
  const previousDefault = getDefaultBaseUrl(current.apiDialect);
  const nextDefault = getDefaultBaseUrl(apiDialect);
  const shouldReplaceBaseUrl = !current.baseUrl.trim() || current.baseUrl === previousDefault;
  return {
    ...current,
    apiDialect,
    baseUrl: shouldReplaceBaseUrl ? nextDefault : current.baseUrl,
    interopProfile: sanitizeCredentialInteropProfileSelection(apiDialect, current.interopProfile),
  };
}

export function describeDefaultAuthStrategy(apiDialect: CredentialApiDialect) {
  const strategy = getDefaultAuthStrategy(apiDialect);
  if (strategy === "bearer") {
    return "Authorization";
  }
  if (strategy === "x_api_key") {
    return "x-api-key";
  }
  return "x-goog-api-key";
}
