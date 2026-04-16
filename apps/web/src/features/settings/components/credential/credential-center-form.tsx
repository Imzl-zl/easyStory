"use client";

import { useEffect, useState, type Dispatch, type SetStateAction } from "react";

import { CredentialClientIdentityFields } from "@/features/settings/components/credential/credential-center-client-identity-fields";
import { CredentialCompatibilityPanel } from "@/features/settings/components/credential/credential-center-compatibility-panel";
import type { CredentialCenterFeedback } from "@/features/settings/components/credential/credential-center-feedback";
import {
  API_DIALECT_SELECT_OPTIONS,
  CredentialSelectField,
  FieldInput,
  updateApiDialectState,
  StaticField,
} from "@/features/settings/components/credential/credential-center-form-fields";
import { CredentialTokenFields } from "@/features/settings/components/credential/credential-center-token-fields";
import { createInitialCredentialForm, isCredentialFormDirty, type CredentialFormState } from "@/features/settings/components/credential/credential-center-support";
import type { CredentialApiDialect, CredentialView } from "@/lib/api/types";

type CredentialCenterFormMode = "create" | "edit";

type CredentialCenterFormProps = {
  mode: CredentialCenterFormMode;
  initialState?: CredentialFormState;
  layout?: "full" | "split";
  feedback: CredentialCenterFeedback;
  credential?: CredentialView | null;
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
  credential = null,
  isPending,
  onDirtyChange,
  onReset,
  onSubmit,
}: CredentialCenterFormProps) {
  const [formState, setFormState] = useState(initialState);
  const isDirty = isCredentialFormDirty(formState, initialState, mode === "edit" ? credential : null);

  useEffect(() => {
    onDirtyChange?.(isDirty);
    return () => onDirtyChange?.(false);
  }, [isDirty, onDirtyChange]);

  return (
    <form
      className="panel-muted space-y-4 p-4 sm:p-5"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(formState);
      }}
    >
      <FormIntro mode={mode} />
      <BasicFields formState={formState} layout={layout} mode={mode} setFormState={setFormState} />
      <ClientIdentityPanel formState={formState} layout={layout} setFormState={setFormState} />
      <CredentialCompatibilityPanel formState={formState} layout={layout} setFormState={setFormState} />
      <FeedbackNotice feedback={feedback} />
      <FormActions isDirty={isDirty} isPending={isPending} mode={mode} onReset={onReset} />
    </form>
  );
}

function FormIntro({ mode }: { mode: CredentialCenterFormMode }) {
  return (
    <div className="space-y-1">
      <h3 className="text-[1.02rem] font-semibold text-text-primary">
        {mode === "edit" ? "修改模型连接" : "添加模型连接"}
      </h3>
      <p className="text-[13px] leading-6 text-text-secondary">
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
    <div className={layout === "full" ? "grid gap-4 xl:grid-cols-2" : "grid gap-4"}>
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
        label="默认模型"
        name="defaultModel"
        placeholder="例如：gpt-4.1 / gemini-2.5-pro"
        required
        value={formState.defaultModel}
        onChange={(value) => setFormState((current) => ({ ...current, defaultModel: value }))}
      />
      <CredentialTokenFields
        className={fieldClassName}
        formState={formState}
        setFormState={setFormState}
      />
    </div>
  );
}

function ClientIdentityPanel({
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
    <section className="rounded-2xl bg-muted shadow-sm p-4">
      <div className="space-y-1">
        <h4 className="text-[13px] font-medium leading-5 text-text-primary">客户端标识</h4>
        <p className="text-[12px] leading-5 text-text-secondary">
          某些中转站会按客户端标识分流。需要伪装成 Codex CLI、Claude Code、Gemini CLI 或浏览器时，优先在这里设置。
        </p>
      </div>
      <div className={layout === "full" ? "mt-4 grid gap-4 xl:grid-cols-2" : "mt-4 grid gap-4"}>
        <CredentialClientIdentityFields
          className={fieldClassName}
          descriptionClassName={descriptionClassName}
          formState={formState}
          setFormState={setFormState}
        />
      </div>
    </section>
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
          ? "rounded-2xl bg-accent-danger/10 px-3.5 py-2.5 text-[13px] leading-5 text-accent-danger"
          : "callout-info px-3.5 py-2.5 text-[13px] leading-5 text-accent-info"
      }
      data-tone={feedback.tone}
    >
      {feedback.message}
    </div>
  );
}

function FormActions({
  isDirty,
  isPending,
  mode,
  onReset,
}: {
  isDirty: boolean;
  isPending: boolean;
  mode: CredentialCenterFormMode;
  onReset?: () => void;
}) {
  return (
    <div className="flex flex-wrap gap-3 pt-1">
      <button className="ink-button min-w-[140px] flex-1" disabled={isPending || !isDirty} type="submit">
        {isPending ? "提交中…" : mode === "edit" ? "保存修改" : "添加连接"}
      </button>
      {mode === "edit" && onReset ? (
        <button className="ink-button-secondary min-w-[140px]" disabled={isPending} onClick={onReset} type="button">
          添加另一条连接
        </button>
      ) : null}
    </div>
  );
}
