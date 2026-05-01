"use client";

import { useEffect, useState } from "react";

import { CredentialClientIdentityFields } from "@/features/settings/components/credential/credential-center-client-identity-fields";
import { CredentialCompatibilityPanel } from "@/features/settings/components/credential/credential-center-compatibility-panel";
import {
  API_DIALECT_SELECT_OPTIONS,
  CredentialSelectField,
  FieldInput,
  updateApiDialectState,
  StaticField,
} from "@/features/settings/components/credential/credential-center-form-fields";
import { CredentialTokenFields } from "@/features/settings/components/credential/credential-center-token-fields";
import { createCredentialFormFromView, createInitialCredentialForm, isCredentialFormDirty, type CredentialFormState } from "@/features/settings/components/credential/credential-center-support";
import type { CredentialApiDialect, CredentialView } from "@/lib/api/types";

export function CredentialEditorModal({
  mode,
  credential,
  isPending,
  onClose,
  onSubmit,
}: {
  mode: "create" | "edit";
  credential: CredentialView | null;
  isPending: boolean;
  onClose: () => void;
  onSubmit: (formState: CredentialFormState) => void;
}) {
  const initialState = mode === "edit" && credential
    ? createCredentialFormFromView(credential)
    : createInitialCredentialForm();

  const [formState, setFormState] = useState(initialState);
  const isDirty = isCredentialFormDirty(formState, initialState, mode === "edit" ? credential : null);

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "var(--overlay-bg)" }}>
      <div
        className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-xl"
        style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-medium)" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-5 pb-3" style={{ borderBottom: "1px solid var(--line-soft)" }}>
          <div>
            <h2 className="text-[15px] font-semibold" style={{ color: "var(--text-primary)" }}>
              {mode === "edit" ? "修改连接" : "添加连接"}
            </h2>
            <p className="text-[11px] mt-0.5" style={{ color: "var(--text-tertiary)" }}>
              {mode === "edit" ? "更新这条模型连接的设置" : "配置新的模型 API 连接"}
            </p>
          </div>
          <button
            className="w-7 h-7 rounded-md flex items-center justify-center"
            style={{ background: "var(--bg-surface)", color: "var(--text-tertiary)" }}
            onClick={onClose}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form
          className="px-5 py-4 space-y-5"
          onSubmit={(e) => { e.preventDefault(); onSubmit(formState); }}
        >
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

          <div className="space-y-2">
            <SectionLabel>客户端标识</SectionLabel>
            <p className="text-[10px]" style={{ color: "var(--text-tertiary)" }}>
              某些中转站会按客户端标识分流，需要伪装时在此设置
            </p>
            <CredentialClientIdentityFields formState={formState} setFormState={setFormState} />
          </div>

          <CredentialCompatibilityPanel formState={formState} layout="full" setFormState={setFormState} />

          {/* Actions */}
          <div className="flex gap-2 pt-2">
            <button
              className="flex-1 h-9 rounded-md text-[12px] font-medium transition-colors"
              disabled={isPending || !isDirty}
              style={{
                background: isDirty ? "var(--accent-primary)" : "var(--line-soft)",
                color: isDirty ? "var(--text-on-accent)" : "var(--text-tertiary)",
              }}
              type="submit"
            >
              {isPending ? "提交中…" : mode === "edit" ? "保存修改" : "添加连接"}
            </button>
            <button
              className="h-9 px-4 rounded-md text-[12px] font-medium"
              style={{ background: "var(--bg-surface)", color: "var(--text-secondary)", border: "1px solid var(--line-medium)" }}
              onClick={onClose}
              type="button"
            >
              取消
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-[10px] font-semibold tracking-[0.1em] uppercase" style={{ color: "var(--accent-primary)" }}>
      {children}
    </span>
  );
}
