"use client";

import type { Dispatch, SetStateAction } from "react";

import {
  buildCredentialUserAgentPreview,
  RUNTIME_KIND_OPTIONS,
} from "@/features/settings/components/credential/credential-center-client-identity-support";
import {
  applyCredentialUserAgentPreset,
  buildResolvedCredentialUserAgentPreview,
  detectCredentialUserAgentPreset,
  USER_AGENT_PRESET_OPTIONS,
  type CredentialUserAgentPresetValue,
} from "@/features/settings/components/credential/credential-center-user-agent-support";
import {
  CredentialSelectField,
  FieldInput,
} from "@/features/settings/components/credential/credential-center-form-fields";
import type { CredentialFormState } from "@/features/settings/components/credential/credential-center-support";

type CredentialClientIdentityFieldsProps = {
  className?: string;
  descriptionClassName?: string;
  formState: CredentialFormState;
  setFormState: Dispatch<SetStateAction<CredentialFormState>>;
};

export function CredentialClientIdentityFields({
  className,
  descriptionClassName,
  formState,
  setFormState,
}: Readonly<CredentialClientIdentityFieldsProps>) {
  const generatedUserAgentPreview = buildCredentialUserAgentPreview({
    clientName: formState.clientName,
    clientVersion: formState.clientVersion,
    runtimeKind: formState.runtimeKind,
  });
  const userAgentPreview = buildResolvedCredentialUserAgentPreview({
    clientName: formState.clientName,
    clientVersion: formState.clientVersion,
    runtimeKind: formState.runtimeKind,
    userAgentOverride: formState.userAgentOverride,
  });
  const selectedPreset = detectCredentialUserAgentPreset(formState.userAgentOverride);
  const isOverrideActive = userAgentPreview !== null && userAgentPreview !== generatedUserAgentPreview;

  return (
    <>
      <p className={`text-[13px] leading-6 text-[var(--text-secondary)] ${descriptionClassName ?? ""}`}>
        可选。你可以先选一个常见客户端预设，再按上游要求手改 <code>User-Agent</code>；这只影响请求头，不会把连接真正变成官方客户端。
      </p>
      <CredentialSelectField
        className={className}
        description="适合某些中转站按客户端标识分流的场景。预设会填充下面的 User-Agent 覆盖，仍然可以继续修改。"
        label="客户端预设"
        options={USER_AGENT_PRESET_OPTIONS}
        value={selectedPreset}
        onChange={(value) =>
          setFormState((current) => ({
            ...current,
            userAgentOverride: applyCredentialUserAgentPreset(
              value as CredentialUserAgentPresetValue,
              current.userAgentOverride,
            ),
          }))
        }
      />
      <FieldInput
        autoComplete="off"
        className={className}
        description="填写后会优先作为最终 User-Agent 发送，覆盖下面的应用名/版本/运行环境组合。"
        label="User-Agent 覆盖"
        name="userAgentOverride"
        placeholder="例如：codex-cli/0.118.0 (server; node)"
        value={formState.userAgentOverride}
        onChange={(value) => setFormState((current) => ({ ...current, userAgentOverride: value }))}
      />
      <FieldInput
        autoComplete="off"
        className={className}
        description="当上面没有填写 User-Agent 覆盖时，系统会用它来自动生成 User-Agent。"
        label="应用名"
        name="clientName"
        placeholder="例如：easyStory"
        value={formState.clientName}
        onChange={(value) => setFormState((current) => ({ ...current, clientName: value }))}
      />
      <FieldInput
        autoComplete="off"
        className={className}
        description="可选，用于补到自动生成的 User-Agent 版本段。"
        label="客户端版本"
        name="clientVersion"
        placeholder="例如：0.1"
        value={formState.clientVersion}
        onChange={(value) => setFormState((current) => ({ ...current, clientVersion: value }))}
      />
      <CredentialSelectField
        className={className}
        description="只用于补充自动生成的运行时环境标记，不会改变协议格式。"
        label="运行环境"
        options={RUNTIME_KIND_OPTIONS}
        value={formState.runtimeKind}
        onChange={(value) =>
          setFormState((current) => ({ ...current, runtimeKind: value as CredentialFormState["runtimeKind"] }))
        }
      />
      <div className={`space-y-2 ${descriptionClassName ?? ""}`}>
        <span className="label-text">User-Agent 预览</span>
        <div className="panel-muted px-3.5 py-2.5 text-[13px] leading-6 text-[var(--text-primary)]">
          {userAgentPreview ?? "留空时不会发送 User-Agent。"}
        </div>
        <p className="text-[12px] leading-5 text-[var(--text-secondary)]">
          {isOverrideActive ? "当前使用的是覆盖值或客户端预设；下面的应用名不会参与发送。" : "当前使用的是应用名/版本/运行环境自动生成的结果。"}
        </p>
      </div>
    </>
  );
}
