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
      <CredentialSelectField
        className={className}
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
        label="User-Agent 覆盖"
        name="userAgentOverride"
        placeholder="例如：codex-cli/0.118.0 (server; node)"
        value={formState.userAgentOverride}
        onChange={(value) => setFormState((current) => ({ ...current, userAgentOverride: value }))}
      />
      <FieldInput
        autoComplete="off"
        className={className}
        label="应用名"
        name="clientName"
        placeholder="例如：easyStory"
        value={formState.clientName}
        onChange={(value) => setFormState((current) => ({ ...current, clientName: value }))}
      />
      <FieldInput
        autoComplete="off"
        className={className}
        label="客户端版本"
        name="clientVersion"
        placeholder="例如：0.1"
        value={formState.clientVersion}
        onChange={(value) => setFormState((current) => ({ ...current, clientVersion: value }))}
      />
      <CredentialSelectField
        className={className}
        label="运行环境"
        options={RUNTIME_KIND_OPTIONS}
        value={formState.runtimeKind}
        onChange={(value) =>
          setFormState((current) => ({ ...current, runtimeKind: value as CredentialFormState["runtimeKind"] }))
        }
      />
      <div className={`space-y-2 ${descriptionClassName ?? ""}`}>
        <span className="label-text">User-Agent 预览</span>
        <div className="panel-muted px-3.5 py-2.5 text-[13px] leading-6 text-text-primary">
          {userAgentPreview ?? "留空时不会发送 User-Agent。"}
        </div>
      </div>
    </>
  );
}
