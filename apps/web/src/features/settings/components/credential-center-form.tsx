"use client";

import { useState } from "react";
import type { Dispatch, SetStateAction } from "react";

import type { CredentialCenterFeedback } from "@/features/settings/components/credential-center-feedback";
import {
  API_DIALECT_OPTIONS,
  AUTH_STRATEGY_OPTIONS,
  createInitialCredentialForm,
  getDefaultAuthStrategy,
  getDefaultBaseUrl,
  type CredentialFormState,
} from "@/features/settings/components/credential-center-support";
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
      <FormIntro mode={mode} />
      <BasicFields formState={formState} mode={mode} setFormState={setFormState} />
      <CompatibilitySettings formState={formState} setFormState={setFormState} />
      <FeedbackNotice feedback={feedback} />
      <FormActions isPending={isPending} mode={mode} onReset={onReset} />
    </form>
  );
}

function FormIntro({ mode }: { mode: CredentialCenterFormMode }) {
  return (
    <div className="space-y-1">
      <h3 className="font-serif text-lg font-semibold">
        {mode === "edit" ? "修改模型连接" : "添加模型连接"}
      </h3>
      <p className="text-sm leading-6 text-[var(--text-secondary)]">
        填好下面几项就能保存一条连接。以后想再接别的模型，继续添加新的连接即可。
      </p>
    </div>
  );
}

function BasicFields({
  formState,
  mode,
  setFormState,
}: {
  formState: CredentialFormState;
  mode: CredentialCenterFormMode;
  setFormState: Dispatch<SetStateAction<CredentialFormState>>;
}) {
  return (
    <>
      {mode === "create" ? (
        <FieldInput
          description="用于区分不同连接，建议填英文、拼音或短横线，例如 openai-main。"
          label="连接代号"
          placeholder="例如：openai-main"
          required
          value={formState.provider}
          onChange={(value) => setFormState((current) => ({ ...current, provider: value }))}
        />
      ) : (
        <StaticField
          description="连接代号创建后不能修改。"
          label="连接代号"
          value={formState.provider}
        />
      )}
      <label className="block">
        <span className="label-text">服务类型</span>
        <select
          className="ink-input"
          value={formState.apiDialect}
          onChange={(event) =>
            setFormState((current) => updateApiDialectState(current, event.target.value as CredentialApiDialect))
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
        description="这个名字会显示在列表和聊天页里。"
        label="显示名称"
        placeholder="例如：薄荷 Gemini"
        required
        value={formState.displayName}
        onChange={(value) => setFormState((current) => ({ ...current, displayName: value }))}
      />
      <FieldInput
        label="访问密钥"
        autoComplete="new-password"
        placeholder={mode === "edit" ? "留空表示继续使用当前访问密钥" : undefined}
        required={mode === "create"}
        type="password"
        value={formState.apiKey}
        onChange={(value) => setFormState((current) => ({ ...current, apiKey: value }))}
      />
      <FieldInput
        description="如果你接的是官方服务，通常保持默认地址即可。"
        label="服务地址"
        placeholder="https://api.openai.com"
        type="url"
        value={formState.baseUrl}
        onChange={(value) => setFormState((current) => ({ ...current, baseUrl: value }))}
      />
      <FieldInput
        description="保存后，验证和聊天会默认使用这个模型。"
        label="默认模型"
        placeholder="例如：gpt-4.1 / gemini-2.5-pro"
        required
        value={formState.defaultModel}
        onChange={(value) => setFormState((current) => ({ ...current, defaultModel: value }))}
      />
    </>
  );
}

function CompatibilitySettings({
  formState,
  setFormState,
}: {
  formState: CredentialFormState;
  setFormState: Dispatch<SetStateAction<CredentialFormState>>;
}) {
  return (
    <details className="rounded-3xl border border-[var(--line-soft)] bg-[rgba(255,255,255,0.52)] p-4">
      <summary className="cursor-pointer text-sm font-medium text-[var(--text-primary)]">
        兼容设置
        <span className="ml-2 text-xs text-[var(--text-secondary)]">大多数情况不用改</span>
      </summary>
      <div className="mt-4 space-y-4">
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          只有当上游服务要求特殊请求头或特殊密钥位置时，才需要修改这里。
        </p>
        <label className="block">
          <span className="label-text">密钥放置方式</span>
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
            当前服务类型默认会使用：{describeDefaultAuthStrategy(formState.apiDialect)}。
          </p>
        </label>
        <FieldInput
          description="只有在上游明确要求自定义请求头名称时才需要填写。"
          disabled={formState.authStrategy !== "custom_header"}
          label="自定义密钥请求头"
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
            这里适合填写站点来源、租户标识这类补充信息。不要在这里填写 Token、Secret 或鉴权头。
          </p>
        </label>
      </div>
    </details>
  );
}

function FeedbackNotice({ feedback }: { feedback: CredentialCenterFeedback }) {
  if (!feedback?.message) {
    return null;
  }
  return (
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
  );
}

function FormActions({
  isPending,
  mode,
  onReset,
}: {
  isPending: boolean;
  mode: CredentialCenterFormMode;
  onReset?: () => void;
}) {
  return (
    <div className="flex flex-wrap gap-3">
      <button className="ink-button flex-1" disabled={isPending} type="submit">
        {isPending ? "提交中..." : mode === "edit" ? "保存修改" : "添加连接"}
      </button>
      {mode === "edit" && onReset ? (
        <button className="ink-button-secondary" disabled={isPending} onClick={onReset} type="button">
          添加另一条连接
        </button>
      ) : null}
    </div>
  );
}

function FieldInput({
  description,
  label,
  value,
  onChange,
  ...props
}: Omit<React.ComponentProps<"input">, "onChange" | "value"> & {
  description?: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="label-text">{label}</span>
      <input className="ink-input" value={value} onChange={(event) => onChange(event.target.value)} {...props} />
      {description ? <p className="mt-2 text-xs text-[var(--text-secondary)]">{description}</p> : null}
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

function describeDefaultAuthStrategy(apiDialect: CredentialApiDialect) {
  const strategy = getDefaultAuthStrategy(apiDialect);
  if (strategy === "bearer") {
    return "Authorization";
  }
  if (strategy === "x_api_key") {
    return "x-api-key";
  }
  return "x-goog-api-key";
}
