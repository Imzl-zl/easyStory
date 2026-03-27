"use client";

import { useEffect, useMemo, useRef } from "react";
import type { Dispatch, SetStateAction } from "react";
import { useQuery } from "@tanstack/react-query";

import { listCredentials } from "@/lib/api/credential";

import type { IncubatorChatSettings } from "./incubator-chat-support";
import {
  buildIncubatorCredentialNotice,
  buildIncubatorCredentialOptions,
  pickIncubatorCredentialOption,
  INCUBATOR_CREDENTIAL_SETTINGS_HREF,
} from "./incubator-chat-credential-support";

export function useIncubatorChatCredentialModel(
  settings: IncubatorChatSettings,
  setSettings: Dispatch<SetStateAction<IncubatorChatSettings>>,
) {
  const hasHydratedDefaultsRef = useRef(false);
  const credentialQuery = useQuery({
    queryKey: ["credentials", "user", "incubator"],
    queryFn: () => listCredentials("user"),
  });
  const credentialOptions = useMemo(
    () => buildIncubatorCredentialOptions(credentialQuery.data),
    [credentialQuery.data],
  );
  const selectedCredential = useMemo(
    () => pickIncubatorCredentialOption(credentialOptions, settings.provider),
    [credentialOptions, settings.provider],
  );

  useEffect(() => {
    if (hasHydratedDefaultsRef.current || credentialQuery.isLoading) {
      return;
    }
    if (selectedCredential) {
      setSettings((current) => ({
        ...current,
        provider: current.provider.trim() || selectedCredential.provider,
        modelName: current.modelName.trim() || selectedCredential.defaultModel,
      }));
    }
    hasHydratedDefaultsRef.current = true;
  }, [credentialQuery.isLoading, selectedCredential, setSettings]);

  return {
    canChat: credentialOptions.length > 0 && settings.provider.trim().length > 0,
    credentialNotice: buildIncubatorCredentialNotice(
      credentialQuery.isLoading,
      credentialOptions,
    ),
    credentialOptions,
    credentialSettingsHref: INCUBATOR_CREDENTIAL_SETTINGS_HREF,
    isCredentialLoading: credentialQuery.isLoading,
  };
}
