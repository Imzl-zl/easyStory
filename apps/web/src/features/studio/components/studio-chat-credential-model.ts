"use client";

import { useEffect, useMemo } from "react";
import type { Dispatch, SetStateAction } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  getMyAssistantPreferences,
  getProjectAssistantPreferences,
} from "@/lib/api/assistant";
import { getErrorMessage } from "@/lib/api/client";
import { listCredentials } from "@/lib/api/credential";
import {
  buildIncubatorCredentialNotice,
  buildIncubatorCredentialOptions,
  resolveHydratedIncubatorChatSettings,
  resolveIncubatorCredentialState,
  resolveSelectedIncubatorCredentialOption,
} from "@/features/lobby/components/incubator-chat-credential-support";

import {
  buildStudioCredentialSettingsHref,
  buildStudioProviderOptions,
  mergeStudioAssistantPreferences,
  type StudioChatSettings,
} from "./studio-chat-support";

export function useStudioChatCredentialModel(
  projectId: string,
  hasUserMessage: boolean,
  settings: StudioChatSettings,
  setSettings: Dispatch<SetStateAction<StudioChatSettings>>,
) {
  const credentialsQuery = useQuery({
    queryKey: ["credentials", "studio", projectId],
    queryFn: async () => {
      const [projectCredentials, userCredentials] = await Promise.all([
        listCredentials("project", projectId),
        listCredentials("user"),
      ]);
      return [...projectCredentials, ...userCredentials];
    },
  });
  const projectPreferencesQuery = useQuery({
    queryKey: ["assistant-preferences", "project", projectId, "studio"],
    queryFn: () => getProjectAssistantPreferences(projectId),
  });
  const userPreferencesQuery = useQuery({
    queryKey: ["assistant-preferences", "user", "studio"],
    queryFn: getMyAssistantPreferences,
  });
  const credentialOptions = useMemo(
    () => buildIncubatorCredentialOptions(credentialsQuery.data),
    [credentialsQuery.data],
  );
  const preferences = useMemo(
    () => mergeStudioAssistantPreferences(projectPreferencesQuery.data, userPreferencesQuery.data),
    [projectPreferencesQuery.data, userPreferencesQuery.data],
  );
  const selectedCredential = useMemo(
    () => resolveSelectedIncubatorCredentialOption({
      currentProvider: settings.provider,
      hasUserMessage,
      options: credentialOptions,
      preferredProvider: preferences?.default_provider?.trim() ?? "",
    }),
    [credentialOptions, hasUserMessage, preferences?.default_provider, settings.provider],
  );
  const credentialErrorMessage = credentialsQuery.error ? getErrorMessage(credentialsQuery.error) : null;
  const credentialState = resolveIncubatorCredentialState({
    credentialOptions,
    errorMessage: credentialErrorMessage,
    isLoading: credentialsQuery.isLoading,
  });

  useEffect(() => {
    if (
      credentialState !== "ready"
      || projectPreferencesQuery.isLoading
      || userPreferencesQuery.isLoading
    ) {
      return;
    }
    setSettings((current) => {
      const nextSettings = resolveHydratedIncubatorChatSettings(
        current,
        selectedCredential,
        preferences,
      );
      return nextSettings ? { ...current, ...nextSettings } : current;
    });
  }, [
    credentialState,
    preferences,
    projectPreferencesQuery.isLoading,
    selectedCredential,
    setSettings,
    userPreferencesQuery.isLoading,
  ]);

  return {
    canChat: credentialState === "ready" && settings.provider.trim().length > 0,
    credentialNotice: buildIncubatorCredentialNotice({
      credentialOptions,
      errorMessage: credentialErrorMessage,
      isLoading: credentialsQuery.isLoading,
    }),
    credentialOptions,
    credentialSettingsHref: buildStudioCredentialSettingsHref(projectId),
    credentialState,
    isCredentialLoading:
      credentialsQuery.isLoading
      || projectPreferencesQuery.isLoading
      || userPreferencesQuery.isLoading,
    providerOptions: buildStudioProviderOptions(credentialOptions),
    selectedCredential,
  };
}
