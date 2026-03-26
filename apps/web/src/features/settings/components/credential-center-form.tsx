"use client";

import { useState } from "react";

import {
  API_DIALECT_OPTIONS,
  AUTH_STRATEGY_OPTIONS,
  createInitialCredentialForm,
  getDefaultAuthStrategy,
  getDefaultBaseUrl,
  type CredentialFormState,
} from "@/features/settings/components/credential-center-support";
import type { CredentialCenterFeedback } from "@/features/settings/components/credential-center-feedback";
import type { CredentialApiDialect } from "@/lib/api/types";

type CredentialCenterFormMode = "create" | "edit";

type CredentialCenterFormProps = {
  mode: CredentialCenterFormMode;
  initialState?: CredentialFormState;
  feedback: CredentialCenterFeedback;
  isPending: boolean;
  onReset?: () => void;
  onSubmit: (formState: CredentialFormState) => void;
};

export function CredentialCenterForm({
  mode,
  initialState = createInitialCredentialForm(),
  feedback,
  isPending,
  onReset,
  onSubmit,
}: CredentialCenterFormProps) {
  const [formState, setFormState] = useState(initialState);

  return (
    <form
      className="panel-muted space-y-4 p-5"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(formState);
      }}
    >
      <div className="space-y-1">
        <h3 className="font-serif text-lg font-semibold">{mode === "edit" ? "编辑凭证" : "新增凭证"}</h3>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          所有失败会直接透出后端原因，不做静默降级。`provider` 仅作为渠道键，真正请求协议由接口类型决定。
        </p>
      </div>
      {mode === "create" ? (
        <FieldInput
          label="渠道键 / Provider Key"
          placeholder="openai / openrouter / volcengine / my-proxy"
          required
          value={formState.provider}
          onChange={(value) => setFormState((current) => ({ ...current, provider: value }))}
        />
      ) : (
        <StaticField
          label="渠道键 / Provider Key"
          value={formState.provider}
          description="渠道键创建后不可修改。"
        />
      )}
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
        placeholder={mode === "edit" ? "留空表示不轮换当前 API Key" : undefined}
        required={mode === "create"}
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
      <div className="panel-muted space-y-4 p-4">
        <div className="space-y-1">
          <h4 className="font-serif text-base font-semibold">高级兼容设置</h4>
          <p className="text-sm leading-6 text-[var(--text-secondary)]">
            只在上游不是标准官方接口时再改这里。默认情况下，保持“跟随接口类型默认”即可。
          </p>
        </div>
        <label className="block">
          <span className="label-text">鉴权方式</span>
          <select
            className="ink-input"
            value={formState.authStrategy}
            onChange={(event) =>
              setFormState((current) => {
                const nextAuthStrategy = event.target.value;
                return {
                  ...current,
                  authStrategy: nextAuthStrategy as typeof current.authStrategy,
                  apiKeyHeaderName: nextAuthStrategy === "custom_header" ? current.apiKeyHeaderName : "",
                };
              })
            }
          >
            {AUTH_STRATEGY_OPTIONS.map((option) => (
              <option key={option.value || "default"} value={option.value}>
                {option.label} · {option.description}
              </option>
            ))}
          </select>
          <p className="mt-2 text-xs text-[var(--text-secondary)]">
            当前接口类型默认使用 {getDefaultAuthStrategy(formState.apiDialect)}。
          </p>
        </label>
        <FieldInput
          disabled={formState.authStrategy !== "custom_header"}
          label="API Key Header 名称"
          placeholder="例如：api-key"
          value={formState.apiKeyHeaderName}
          onChange={(value) => setFormState((current) => ({ ...current, apiKeyHeaderName: value }))}
        />
        <label className="block">
          <span className="label-text">额外请求头</span>
          <textarea
            className="ink-input min-h-32"
            placeholder={'例如：{\n  "HTTP-Referer": "https://app.example.com",\n  "X-Title": "easyStory"\n}'}
            value={formState.extraHeadersText}
            onChange={(event) =>
              setFormState((current) => ({ ...current, extraHeadersText: event.target.value }))
            }
          />
          <p className="mt-2 text-xs text-[var(--text-secondary)]">
            请输入 JSON 对象。这里适合放 Referer、租户标识、上游要求的自定义 Header。
          </p>
          <p className="mt-2 text-xs text-[var(--text-secondary)]">
            这里只支持非敏感元数据请求头；鉴权、Token、Secret 一类请求头请改用上面的鉴权方式配置。
          </p>
        </label>
      </div>
      {feedback?.message ? (
        <div
          className={
            feedback.tone === "danger"
              ? "rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]"
              : "rounded-2xl bg-[rgba(58,124,165,0.1)] px-4 py-3 text-sm text-[var(--accent-info)]"
          }
          data-tone={feedback.tone}
        >
          {feedback.message}
        </div>
      ) : null}
      <div className="flex flex-wrap gap-3">
        <button className="ink-button flex-1" disabled={isPending} type="submit">
          {isPending ? "提交中..." : mode === "edit" ? "保存修改" : "创建凭证"}
        </button>
        {mode === "edit" && onReset ? (
          <button className="ink-button-secondary" disabled={isPending} onClick={onReset} type="button">
            回到新增
          </button>
        ) : null}
      </div>
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

function StaticField({
  description,
  label,
  value,
}: {
  description: string;
  label: string;
  value: string;
}) {
  return (
    <div className="space-y-2">
      <span className="label-text">{label}</span>
      <div className="panel-muted px-4 py-3 text-sm text-[var(--text-primary)]">{value}</div>
      <p className="text-xs text-[var(--text-secondary)]">{description}</p>
    </div>
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
