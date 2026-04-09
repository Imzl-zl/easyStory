"use client";

import type { Dispatch, SetStateAction } from "react";

import { FieldInput } from "@/features/settings/components/credential/credential-center-form-fields";
import {
  sanitizeCredentialTokenInput,
} from "@/features/settings/components/credential/credential-center-token-support";
import type { CredentialFormState } from "@/features/settings/components/credential/credential-center-support";

type CredentialTokenFieldsProps = {
  className?: string;
  setFormState: Dispatch<SetStateAction<CredentialFormState>>;
  formState: CredentialFormState;
};

export function CredentialTokenFields({
  className,
  formState,
  setFormState,
}: Readonly<CredentialTokenFieldsProps>) {
  return (
    <>
      <FieldInput
        autoComplete="off"
        className={className}
        description="多数平台也叫最大输入 token，用来表示这条连接可容纳的上下文规模。"
        inputMode="numeric"
        label="上下文窗口"
        name="contextWindowTokens"
        placeholder="例如：128000"
        value={formState.contextWindowTokens}
        onChange={(value) =>
          setFormState((current) => ({
            ...current,
            contextWindowTokens: sanitizeCredentialTokenInput(value),
          }))
        }
      />
      <FieldInput
        autoComplete="off"
        className={className}
        description="留空则按聊天页或上游默认值处理；填写后会作为这条连接的默认回复上限。"
        inputMode="numeric"
        label="默认单次回复上限"
        name="defaultMaxOutputTokens"
        placeholder="例如：8192"
        value={formState.defaultMaxOutputTokens}
        onChange={(value) =>
          setFormState((current) => ({
            ...current,
            defaultMaxOutputTokens: sanitizeCredentialTokenInput(value),
          }))
        }
      />
    </>
  );
}
