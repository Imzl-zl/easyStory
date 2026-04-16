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
        description="留空则按上游默认值处理。"
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
