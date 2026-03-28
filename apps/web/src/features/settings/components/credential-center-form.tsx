"use client";

import { useEffect, useState } from "react";
import type { Dispatch, SetStateAction } from "react";

import type { CredentialCenterFeedback } from "@/features/settings/components/credential-center-feedback";
import {
  API_DIALECT_SELECT_OPTIONS,
  AUTH_STRATEGY_SELECT_OPTIONS,
  CredentialSelectField,
  describeDefaultAuthStrategy,
  FieldInput,
  StaticField,
  updateApiDialectState,
} from "@/features/settings/components/credential-center-form-fields";
import {
  createInitialCredentialForm,
  isCredentialFormDirty,
  type CredentialFormState,
} from "@/features/settings/components/credential-center-support";
import type { CredentialApiDialect } from "@/lib/api/types";

type CredentialCenterFormMode = "create" | "edit";

type CredentialCenterFormProps = {
  mode: CredentialCenterFormMode;
  initialState?: CredentialFormState;
  layout?: "full" | "split";
  feedback: CredentialCenterFeedback;
  isPending: boolean;
  onDirtyChange?: (isDirty: boolean) => void;
  onReset?: () => void;
  onSubmit: (formState: CredentialFormState) => void;
};

export function CredentialCenterForm({
  mode,
  initialState = createInitialCredentialForm(),
  layout = "split",
  feedback,
  isPending,
  onDirtyChange,
  onReset,
  onSubmit,
}: CredentialCenterFormProps) {
  const [formState, setFormState] = useState(initialState);
  const isDirty = isCredentialFormDirty(formState, initialState);

  useEffect(() => {
    onDirtyChange?.(isDirty);
    return () => onDirtyChange?.(false);
  }, [isDirty, onDirtyChange]);

  return (
    <form
      className="panel-muted space-y-3.5 p-4 sm:p-[1.125rem]"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(formState);
      }}
    >
      <FormIntro mode={mode} />
      <BasicFields formState={formState} layout={layout} mode={mode} setFormState={setFormState} />
      <CompatibilitySettings formState={formState} layout={layout} setFormState={setFormState} />
      <FeedbackNotice feedback={feedback} />
      <FormActions isPending={isPending} mode={mode} onReset={onReset} />
    </form>
  );
}

function FormIntro({ mode }: { mode: CredentialCenterFormMode }) {
  return (
    <div className="space-y-1">
      <h3 className="text-base font-semibold text-[var(--text-primary)]">
        {mode === "edit" ? "修改模型连接" : "添加模型连接"}
      </h3>
      <p className="text-[13px] leading-5 text-[var(--text-secondary)]">
        填好下面几项就能保存一条连接。以后想再接别的模型，继续添加新的连接即可。
      </p>
    </div>
  );
}

function BasicFields({
  formState,
  layout,
  mode,
  setFormState,
}: {
  formState: CredentialFormState;
  layout: CredentialCenterFormProps["layout"];
  mode: CredentialCenterFormMode;
  setFormState: Dispatch<SetStateAction<CredentialFormState>>;
}) {
  const fieldClassName = layout === "full" ? "xl:col-span-1" : undefined;

  return (
    <div className={layout === "full" ? "grid gap-3 sm:gap-4 xl:grid-cols-2" : "grid gap-3"}>
      {mode === "create" ? (
        <FieldInput
          autoComplete="off"
          className={fieldClassName}
          description="用于区分不同连接，建议填英文、拼音或短横线，例如 openai-main。"
          label="连接代号"
          name="provider"
          placeholder="例如：openai-main"
          required
          value={formState.provider}
          onChange={(value) => setFormState((current) => ({ ...current, provider: value }))}
        />
      ) : (
        <StaticField
          className={fieldClassName}
          description="连接代号创建后不能修改。"
          label="连接代号"
          value={formState.provider}
        />
      )}
      <CredentialSelectField
        className={fieldClassName}
        label="服务类型"
        options={API_DIALECT_SELECT_OPTIONS}
        value={formState.apiDialect}
        onChange={(value) =>
          setFormState((current) => updateApiDialectState(current, value as CredentialApiDialect))
        }
      />
      <FieldInput
        autoComplete="off"
        className={fieldClassName}
        description="这个名字会显示在列表和聊天页里。"
        label="显示名称"
        name="displayName"
        placeholder="例如：薄荷 Gemini"
        required
        value={formState.displayName}
        onChange={(value) => setFormState((current) => ({ ...current, displayName: value }))}
      />
      <FieldInput
        autoComplete="new-password"
        className={fieldClassName}
        label="访问密钥"
        name="apiKey"
        placeholder={mode === "edit" ? "留空表示继续使用当前访问密钥" : undefined}
        required={mode === "create"}
        type="password"
        value={formState.apiKey}
        onChange={(value) => setFormState((current) => ({ ...current, apiKey: value }))}
      />
      <FieldInput
        autoComplete="url"
        className={fieldClassName}
        description="如果你接的是官方服务，通常保持默认地址即可。"
        label="服务地址"
        name="baseUrl"
        placeholder="https://api.openai.com"
        type="url"
        value={formState.baseUrl}
        onChange={(value) => setFormState((current) => ({ ...current, baseUrl: value }))}
      />
      <FieldInput
        autoComplete="off"
        className={fieldClassName}
        description="保存后，验证和聊天会默认使用这个模型。"
        label="默认模型"
        name="defaultModel"
        placeholder="例如：gpt-4.1 / gemini-2.5-pro"
        required
        value={formState.defaultModel}
        onChange={(value) => setFormState((current) => ({ ...current, defaultModel: value }))}
      />
    </div>
  );
}

function CompatibilitySettings({
  formState,
  layout,
  setFormState,
}: {
  formState: CredentialFormState;
  layout: CredentialCenterFormProps["layout"];
  setFormState: Dispatch<SetStateAction<CredentialFormState>>;
}) {
  const fieldClassName = layout === "full" ? "xl:col-span-1" : undefined;
  const descriptionClassName = layout === "full" ? "xl:col-span-2" : undefined;

  return (
    <details className="rounded-[20px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.56)] p-3.5">
      <summary className="cursor-pointer text-[13px] font-medium text-[var(--text-primary)]">
        兼容设置
        <span className="ml-2 text-xs text-[var(--text-secondary)]">大多数情况不用改</span>
      </summary>
      <div className={layout === "full" ? "mt-3 grid gap-3 sm:gap-4 xl:grid-cols-2" : "mt-3 grid gap-3"}>
        <p className={`text-[13px] leading-5 text-[var(--text-secondary)] ${descriptionClassName ?? ""}`}>
          只有当上游服务要求特殊请求头或特殊密钥位置时，才需要修改这里。
        </p>
        <CredentialSelectField
          className={fieldClassName}
          description={`当前服务类型默认会使用：${describeDefaultAuthStrategy(formState.apiDialect)}。`}
          label="密钥放置方式"
          options={AUTH_STRATEGY_SELECT_OPTIONS}
          value={formState.authStrategy}
          onChange={(value) =>
            setFormState((current) => {
              const nextAuthStrategy = value;
              return {
                ...current,
                authStrategy: nextAuthStrategy as typeof current.authStrategy,
                apiKeyHeaderName: nextAuthStrategy === "custom_header" ? current.apiKeyHeaderName : "",
              };
            })
          }
        />
        <FieldInput
          autoComplete="off"
          className={fieldClassName}
          description="只有在上游明确要求自定义请求头名称时才需要填写。"
          disabled={formState.authStrategy !== "custom_header"}
          label="自定义密钥请求头"
          name="apiKeyHeaderName"
          placeholder="例如：api-key"
          value={formState.apiKeyHeaderName}
          onChange={(value) => setFormState((current) => ({ ...current, apiKeyHeaderName: value }))}
        />
        <label className={`block ${descriptionClassName ?? ""}`}>
          <span className="label-text">额外请求头</span>
          <textarea
            autoComplete="off"
            className="ink-textarea min-h-32"
            name="extraHeadersText"
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
          ? "rounded-xl bg-[rgba(178,65,46,0.12)] px-3.5 py-2.5 text-[13px] leading-5 text-[var(--accent-danger)]"
          : "rounded-xl bg-[rgba(58,124,165,0.1)] px-3.5 py-2.5 text-[13px] leading-5 text-[var(--accent-info)]"
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
    <div className="flex flex-wrap gap-2.5">
      <button className="ink-button flex-1" disabled={isPending} type="submit">
        {isPending ? "提交中…" : mode === "edit" ? "保存修改" : "添加连接"}
      </button>
      {mode === "edit" && onReset ? (
        <button className="ink-button-secondary" disabled={isPending} onClick={onReset} type="button">
          添加另一条连接
        </button>
      ) : null}
    </div>
  );
}
