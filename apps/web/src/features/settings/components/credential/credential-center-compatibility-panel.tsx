"use client";

import type { Dispatch, SetStateAction } from "react";

import {
  AUTH_STRATEGY_SELECT_OPTIONS,
  CredentialSelectField,
  describeDefaultAuthStrategy,
  FieldInput,
} from "@/features/settings/components/credential/credential-center-form-fields";
import {
  getInteropProfileOptions,
  type CredentialFormState,
  supportsCredentialInteropProfile,
} from "@/features/settings/components/credential/credential-center-support";

type CredentialCompatibilityPanelProps = {
  formState: CredentialFormState;
  layout: "full" | "split";
  setFormState: Dispatch<SetStateAction<CredentialFormState>>;
};

export function CredentialCompatibilityPanel({
  formState,
  layout,
  setFormState,
}: Readonly<CredentialCompatibilityPanelProps>) {
  const fieldClassName = layout === "full" ? "xl:col-span-1" : undefined;
  const descriptionClassName = layout === "full" ? "xl:col-span-2" : undefined;
  const interopProfileOptions = getInteropProfileOptions(formState.apiDialect).map((option) => ({
    description: option.description,
    label: option.label,
    value: option.value,
  }));
  const showInteropProfileField = supportsCredentialInteropProfile(formState.apiDialect);

  return (
    <details className="rounded-2xl bg-muted shadow-sm p-4">
      <summary className="cursor-pointer text-[13px] font-medium leading-5 text-text-primary">
        兼容设置
        <span className="ml-2 text-xs text-text-secondary">大多数情况不用改</span>
      </summary>
      <div className={layout === "full" ? "mt-4 grid gap-4 xl:grid-cols-2" : "mt-4 grid gap-4"}>
        {showInteropProfileField ? (
          <CredentialSelectField
            className={fieldClassName}
            label="协议兼容 Profile"
            options={interopProfileOptions}
            value={formState.interopProfile}
            onChange={(value) =>
              setFormState((current) => ({
                ...current,
                interopProfile: value as typeof current.interopProfile,
              }))
            }
          />
        ) : null}
        <CredentialSelectField
          className={fieldClassName}
          description={`当前服务类型默认会使用：${describeDefaultAuthStrategy(formState.apiDialect)}。`}
          label="密钥放置方式"
          options={AUTH_STRATEGY_SELECT_OPTIONS}
          value={formState.authStrategy}
          onChange={(value) =>
            setFormState((current) => ({
              ...current,
              authStrategy: value as typeof current.authStrategy,
              apiKeyHeaderName: value === "custom_header" ? current.apiKeyHeaderName : "",
            }))
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
          <p className="mt-2 text-xs text-text-secondary">
            这里适合填写站点来源、租户标识这类补充信息。不要在这里填写 Token、Secret 或鉴权头。
          </p>
        </label>
      </div>
    </details>
  );
}
