"use client";

import { useEffect, useState } from "react";

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
      className="rounded-lg"
      style={{
        background: "var(--bg-canvas)",
        border: "1px solid var(--line-soft)",
      }}
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(formState);
      }}
    >
      {/* Form Header */}
      <div className="px-4 pt-4 pb-3" style={{ borderBottom: "1px solid var(--line-soft)" }}>
        <h3 className="text-[13px] font-semibold" style={{ color: "var(--text-primary)" }}>
          {mode === "edit" ? "修改连接" : "添加连接"}
        </h3>
        <p className="mt-0.5 text-[11px]" style={{ color: "var(--text-tertiary)" }}>
          {mode === "edit" ? "更新这条模型连接的设置" : "配置新的模型 API 连接"}
        </p>
      </div>

      <div className="px-4 py-4 space-y-5">
        {/* Basic Fields */}
        <div className="space-y-3">
          <SectionLabel>基本信息</SectionLabel>
          {mode === "create" ? (
            <FieldInput
              autoComplete="off"
              description="建议用英文或拼音，例如 openai-main"
              label="连接代号"
              name="provider"
              placeholder="例如：openai-main"
              required
              value={formState.provider}
              onChange={(value) => setFormState((c) => ({ ...c, provider: value }))}
            />
          ) : (
            <StaticField description="连接代号创建后不可修改" label="连接代号" value={formState.provider} />
          )}
          <CredentialSelectField
            label="服务类型"
            options={API_DIALECT_SELECT_OPTIONS}
            value={formState.apiDialect}
            onChange={(value) => setFormState((c) => updateApiDialectState(c, value as CredentialApiDialect))}
          />
          <FieldInput
            autoComplete="off"
            label="显示名称"
            name="displayName"
            placeholder="例如：薄荷 Gemini"
            required
            value={formState.displayName}
            onChange={(value) => setFormState((c) => ({ ...c, displayName: value }))}
          />
          <FieldInput
            autoComplete="new-password"
            label="访问密钥"
            name="apiKey"
            placeholder={mode === "edit" ? "留空表示不修改" : undefined}
            required={mode === "create"}
            type="password"
            value={formState.apiKey}
            onChange={(value) => setFormState((c) => ({ ...c, apiKey: value }))}
          />
          <FieldInput
            autoComplete="url"
            label="服务地址"
            name="baseUrl"
            placeholder="https://api.openai.com"
            type="url"
            value={formState.baseUrl}
            onChange={(value) => setFormState((c) => ({ ...c, baseUrl: value }))}
          />
          <FieldInput
            autoComplete="off"
            label="默认模型"
            name="defaultModel"
            placeholder="例如：gpt-4.1 / gemini-2.5-pro"
            required
            value={formState.defaultModel}
            onChange={(value) => setFormState((c) => ({ ...c, defaultModel: value }))}
          />
          <CredentialTokenFields formState={formState} setFormState={setFormState} />
        </div>

        {/* Client Identity */}
        <div className="space-y-2">
          <SectionLabel>客户端标识</SectionLabel>
          <p className="text-[10px]" style={{ color: "var(--text-tertiary)" }}>
            某些中转站会按客户端标识分流，需要伪装时在此设置
          </p>
          <CredentialClientIdentityFields formState={formState} setFormState={setFormState} />
        </div>

        {/* Compatibility */}
        <CredentialCompatibilityPanel formState={formState} layout="full" setFormState={setFormState} />

        {/* Feedback */}
        {feedback?.message ? (
          <div
            className="rounded-md px-3 py-2 text-[11px]"
            style={{
              background: feedback.tone === "danger" ? "var(--accent-danger-soft)" : "var(--accent-info-soft)",
              color: feedback.tone === "danger" ? "var(--accent-danger)" : "var(--accent-info)",
            }}
          >
            {feedback.message}
          </div>
        ) : null}

        {/* Actions */}
        <div className="flex gap-2 pt-1">
          <button
            className="flex-1 h-8 rounded-md text-[12px] font-medium transition-colors"
            disabled={isPending || !isDirty}
            style={{
              background: isDirty ? "var(--accent-primary)" : "var(--bg-surface)",
              color: isDirty ? "var(--text-on-accent)" : "var(--text-tertiary)",
            }}
            type="submit"
          >
            {isPending ? "提交中…" : mode === "edit" ? "保存修改" : "添加连接"}
          </button>
          {mode === "edit" && onReset ? (
            <button
              className="h-8 px-3 rounded-md text-[12px] font-medium"
              disabled={isPending}
              onClick={onReset}
              style={{ background: "var(--bg-surface)", color: "var(--text-secondary)", border: "1px solid var(--line-medium)" }}
              type="button"
            >
              新建
            </button>
          ) : null}
        </div>
      </div>
    </form>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-[10px] font-semibold tracking-[0.1em] uppercase" style={{ color: "var(--accent-primary)" }}>
      {children}
    </span>
  );
}
