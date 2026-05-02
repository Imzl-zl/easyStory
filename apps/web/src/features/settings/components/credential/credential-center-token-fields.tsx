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
        description="用于输入预算和上下文压缩；留空时不按连接窗口做预算限制。"
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
        description="作为运行时 max_tokens / max output 默认值；单次请求可由模型设置覆盖。"
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
