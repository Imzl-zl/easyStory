"use client";

import { useEffect, useMemo } from "react";
import type { Dispatch, SetStateAction } from "react";
import { useQuery } from "@tanstack/react-query";

import { getMyAssistantPreferences } from "@/lib/api/assistant";
import { getErrorMessage } from "@/lib/api/client";
import { listCredentials } from "@/lib/api/credential";

import type { IncubatorChatSettings } from "./incubator-chat-support";
import {
  buildIncubatorCredentialNotice,
  buildIncubatorCredentialOptions,
  INCUBATOR_CREDENTIAL_SETTINGS_HREF,
  resolveSelectedIncubatorCredentialOption,
  resolveHydratedIncubatorChatSettings,
  resolveIncubatorCredentialState,
} from "./incubator-chat-credential-support";

export function useIncubatorChatCredentialModel(
  hasUserMessage: boolean,
  settings: IncubatorChatSettings,
  setSettings: Dispatch<SetStateAction<IncubatorChatSettings>>,
) {
  const credentialQuery = useQuery({
    queryKey: ["credentials", "user", "incubator"],
    queryFn: () => listCredentials("user"),
  });
  const preferencesQuery = useQuery({
    queryKey: ["assistant-preferences", "me"],
    queryFn: getMyAssistantPreferences,
  });
  const credentialOptions = useMemo(
    () => buildIncubatorCredentialOptions(credentialQuery.data),
    [credentialQuery.data],
  );
  const preferredProvider = preferencesQuery.data?.default_provider?.trim() ?? "";
  const selectedCredential = useMemo(
    () => resolveSelectedIncubatorCredentialOption({
      currentProvider: settings.provider,
      hasUserMessage,
      options: credentialOptions,
      preferredProvider,
    }),
    [credentialOptions, hasUserMessage, preferredProvider, settings.provider],
  );
  const credentialErrorMessage = credentialQuery.error ? getErrorMessage(credentialQuery.error) : null;
  const credentialState = resolveIncubatorCredentialState({
    credentialOptions,
    errorMessage: credentialErrorMessage,
    isLoading: credentialQuery.isLoading,
  });

  useEffect(() => {
    if (credentialState !== "ready" || preferencesQuery.isLoading) {
      return;
    }
    setSettings((current) => {
      const nextSettings = resolveHydratedIncubatorChatSettings(
        current,
        selectedCredential,
        preferencesQuery.data,
      );
      return nextSettings ? { ...current, ...nextSettings } : current;
    });
  }, [credentialState, preferencesQuery.data, preferencesQuery.isLoading, selectedCredential, setSettings]);

  return {
    canChat: credentialState === "ready" && settings.provider.trim().length > 0,
    credentialNotice: buildIncubatorCredentialNotice({
      credentialOptions,
      errorMessage: credentialErrorMessage,
      isLoading: credentialQuery.isLoading,
    }),
    credentialOptions,
    credentialSettingsHref: INCUBATOR_CREDENTIAL_SETTINGS_HREF,
    credentialState,
    isCredentialLoading: credentialQuery.isLoading || preferencesQuery.isLoading,
  };
}
