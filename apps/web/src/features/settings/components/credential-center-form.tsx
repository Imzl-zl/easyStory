"use client";

import type { Dispatch, SetStateAction } from "react";

import {
  API_DIALECT_OPTIONS,
  getDefaultBaseUrl,
  type CredentialFormState,
} from "@/features/settings/components/credential-center-support";
import type { CredentialApiDialect } from "@/lib/api/types";

type CredentialCenterFormProps = {
  formState: CredentialFormState;
  setFormState: Dispatch<SetStateAction<CredentialFormState>>;
  feedback: string | null;
  isPending: boolean;
  onSubmit: () => void;
};

export function CredentialCenterForm({
  formState,
  setFormState,
  feedback,
  isPending,
  onSubmit,
}: CredentialCenterFormProps) {
  return (
    <form
      className="panel-muted space-y-4 p-5"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <div className="space-y-1">
        <h3 className="font-serif text-lg font-semibold">新增凭证</h3>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          所有失败会直接透出后端原因，不做静默降级。`provider` 仅作为渠道键，真正请求协议由接口类型决定。
        </p>
      </div>
      <FieldInput
        label="渠道键 / Provider Key"
        placeholder="openai / openrouter / volcengine / my-proxy"
        required
        value={formState.provider}
        onChange={(value) => setFormState((current) => ({ ...current, provider: value }))}
      />
      <label className="block">
        <span className="label-text">接口类型</span>
        <select
          className="ink-input"
          value={formState.apiDialect}
          onChange={(event) =>
            setFormState((current) =>
              updateApiDialectState(current, event.target.value as CredentialApiDialect),
            )
          }
        >
          {API_DIALECT_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label} · {option.description}
            </option>
          ))}
        </select>
      </label>
      <FieldInput
        label="显示名称"
        required
        value={formState.displayName}
        onChange={(value) => setFormState((current) => ({ ...current, displayName: value }))}
      />
      <FieldInput
        label="API Key"
        autoComplete="new-password"
        required
        type="password"
        value={formState.apiKey}
        onChange={(value) => setFormState((current) => ({ ...current, apiKey: value }))}
      />
      <FieldInput
        label="Base URL"
        placeholder="https://api.openai.com"
        type="url"
        value={formState.baseUrl}
        onChange={(value) => setFormState((current) => ({ ...current, baseUrl: value }))}
      />
      <FieldInput
        label="默认模型"
        placeholder="gpt-4o-mini / claude-sonnet-4-20250514 / gemini-2.5-pro"
        required
        value={formState.defaultModel}
        onChange={(value) => setFormState((current) => ({ ...current, defaultModel: value }))}
      />
      {feedback ? (
        <div className="rounded-2xl bg-[rgba(58,124,165,0.1)] px-4 py-3 text-sm text-[var(--accent-info)]">
          {feedback}
        </div>
      ) : null}
      <button className="ink-button w-full" disabled={isPending} type="submit">
        {isPending ? "提交中..." : "创建凭证"}
      </button>
    </form>
  );
}

function FieldInput({
  label,
  value,
  onChange,
  ...props
}: Omit<React.ComponentProps<"input">, "onChange" | "value"> & {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="label-text">{label}</span>
      <input className="ink-input" value={value} onChange={(event) => onChange(event.target.value)} {...props} />
    </label>
  );
}

function updateApiDialectState(
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
  };
}
