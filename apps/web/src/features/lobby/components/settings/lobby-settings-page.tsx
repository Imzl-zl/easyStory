"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { UnsavedChangesDialog } from "@/components/ui/unsaved-changes-dialog";
import {
  useLobbySettingsRouteState,
  useNormalizeLobbySettingsRoute,
  type LobbySettingsRouteState,
} from "@/features/lobby/components/settings/lobby-settings-route";
import { LobbyAssistantSettingsPanel } from "@/features/lobby/components/settings/lobby-assistant-settings-panel";
import { type LobbySettingsTab } from "@/features/lobby/components/settings/lobby-settings-support";
import { LobbySettingsSidebar } from "@/features/lobby/components/settings/lobby-settings-sidebar";
import { AssistantAgentsPanel } from "@/features/settings/components/assistant/agents/assistant-agents-panel";
import { AssistantHooksPanel } from "@/features/settings/components/assistant/hooks/assistant-hooks-panel";
import { AssistantMcpPanel } from "@/features/settings/components/assistant/mcp/assistant-mcp-panel";
import { AssistantSkillsPanel } from "@/features/settings/components/assistant/skills/assistant-skills-panel";
import { CredentialCenter } from "@/features/settings/components/credential/credential-center";
import { useUnsavedChangesGuard } from "@/lib/hooks/use-unsaved-changes-guard";

export function LobbySettingsPage() {
  const router = useRouter();
  const route = useLobbySettingsRouteState();
  const [assistantPreferencesDirty, setAssistantPreferencesDirty] = useState(false);
  const [assistantRulesDirty, setAssistantRulesDirty] = useState(false);
  const [assistantAgentsDirty, setAssistantAgentsDirty] = useState(false);
  const [assistantSkillsDirty, setAssistantSkillsDirty] = useState(false);
  const [assistantHooksDirty, setAssistantHooksDirty] = useState(false);
  const [assistantMcpDirty, setAssistantMcpDirty] = useState(false);
  const [credentialDirty, setCredentialDirty] = useState(false);
  useNormalizeLobbySettingsRoute(route);
  const currentUrl = route.currentSearch ? `${route.pathname}?${route.currentSearch}` : route.pathname;
  const isDirty = resolveLobbySettingsDirtyState(route.tab, {
    assistant: assistantPreferencesDirty || assistantRulesDirty,
    agents: assistantAgentsDirty,
    credentials: credentialDirty,
    hooks: assistantHooksDirty,
    mcp: assistantMcpDirty,
    skills: assistantSkillsDirty,
  });
  const navigationGuard = useUnsavedChangesGuard({ currentUrl, isDirty, router });

  return (
    <>
      <div className="grid gap-6 xl:grid-cols-[300px_minmax(0,1fr)]">
        <LobbySettingsSidebar
          isDirty={isDirty}
          isPending={route.isPending}
          onNavigateAway={navigationGuard.attemptNavigation}
          onSelectTab={(tab) =>
            navigationGuard.attemptNavigation(() => handleLobbySettingsTabChange(tab, route.setParams))
          }
          tab={route.tab}
        />
        <LobbySettingsContent
          navigationGuard={navigationGuard.attemptNavigation}
          route={route}
          onAssistantPreferencesDirtyChange={setAssistantPreferencesDirty}
          onAssistantRulesDirtyChange={setAssistantRulesDirty}
          onAssistantAgentsDirtyChange={setAssistantAgentsDirty}
          onAssistantHooksDirtyChange={setAssistantHooksDirty}
          onAssistantMcpDirtyChange={setAssistantMcpDirty}
          onAssistantSkillsDirtyChange={setAssistantSkillsDirty}
          onCredentialDirtyChange={setCredentialDirty}
        />
      </div>
      <UnsavedChangesDialog
        isOpen={navigationGuard.isConfirmOpen}
        isPending={false}
        onClose={navigationGuard.handleDialogClose}
        onConfirm={navigationGuard.handleDialogConfirm}
      />
    </>
  );
}

function LobbySettingsContent({
  navigationGuard,
  route,
  onAssistantPreferencesDirtyChange,
  onAssistantRulesDirtyChange,
  onAssistantAgentsDirtyChange,
  onAssistantHooksDirtyChange,
  onAssistantMcpDirtyChange,
  onAssistantSkillsDirtyChange,
  onCredentialDirtyChange,
}: Readonly<{
  navigationGuard: (onConfirm: () => void) => void;
  route: LobbySettingsRouteState;
  onAssistantPreferencesDirtyChange: (isDirty: boolean) => void;
  onAssistantRulesDirtyChange: (isDirty: boolean) => void;
  onAssistantAgentsDirtyChange: (isDirty: boolean) => void;
  onAssistantHooksDirtyChange: (isDirty: boolean) => void;
  onAssistantMcpDirtyChange: (isDirty: boolean) => void;
  onAssistantSkillsDirtyChange: (isDirty: boolean) => void;
  onCredentialDirtyChange: (isDirty: boolean) => void;
}>) {
  if (route.tab === "assistant") {
    return (
      <LobbyAssistantSettingsPanel
        onAssistantPreferencesDirtyChange={onAssistantPreferencesDirtyChange}
        onAssistantRulesDirtyChange={onAssistantRulesDirtyChange}
        onOpenCredentials={() =>
          navigationGuard(() => handleLobbySettingsTabChange("credentials", route.setParams))
        }
        onOpenSkills={() => navigationGuard(() => handleLobbySettingsTabChange("skills", route.setParams))}
      />
    );
  }

  if (route.tab === "agents") {
    return <AssistantAgentsPanel onDirtyChange={onAssistantAgentsDirtyChange} />;
  }

  if (route.tab === "skills") {
    return <AssistantSkillsPanel onDirtyChange={onAssistantSkillsDirtyChange} />;
  }

  if (route.tab === "hooks") {
    return <AssistantHooksPanel onDirtyChange={onAssistantHooksDirtyChange} />;
  }

  if (route.tab === "mcp") {
    return <AssistantMcpPanel onDirtyChange={onAssistantMcpDirtyChange} />;
  }

  return (
    <CredentialCenter
      isNavigationPending={route.isPending}
      mode={route.mode}
      onDirtyChange={onCredentialDirtyChange}
      projectId={route.projectId}
      scope={route.scope}
      selectedCredentialId={route.credentialId}
      onSyncCredential={(nextCredentialId) =>
        route.setParams({
          credential: nextCredentialId,
          scope: route.scope,
          sub: "audit",
          tab: "credentials",
        })
      }
      onSyncCredentialForEdit={(nextCredentialId) =>
        route.setParams({
          credential: nextCredentialId,
          scope: route.scope,
          sub: "list",
          tab: "credentials",
        })
      }
      onModeChange={(nextMode) =>
        navigationGuard(() =>
          route.setParams({
            credential: nextMode === "audit" ? route.credentialId : null,
            scope: route.scope,
            sub: nextMode,
            tab: "credentials",
          }),
        )
      }
      onScopeChange={(nextScope) =>
        navigationGuard(() =>
          route.setParams({
            credential: null,
            scope: nextScope,
            sub: route.mode,
            tab: "credentials",
          }),
        )
      }
      onSelectCredential={(nextCredentialId) =>
        navigationGuard(() =>
          route.setParams({
            credential: nextCredentialId,
            scope: route.scope,
            sub: "audit",
            tab: "credentials",
          }),
        )
      }
      onSelectCredentialForEdit={(nextCredentialId) =>
        navigationGuard(() =>
          route.setParams({
            credential: nextCredentialId,
            scope: route.scope,
            sub: "list",
            tab: "credentials",
          }),
        )
      }
      onResetEditor={() =>
        navigationGuard(() =>
          route.setParams({
            credential: null,
            scope: route.scope,
            sub: "list",
            tab: "credentials",
          }),
        )
      }
    />
  );
}

function handleLobbySettingsTabChange(
  tab: LobbySettingsTab,
  setParams: (patches: Record<string, string | null>) => void,
) {
  if (tab === "credentials") {
    setParams({ tab: "credentials" });
    return;
  }
  if (tab === "skills") {
    setParams({
      credential: null,
      project: null,
      scope: null,
      sub: null,
      tab: "skills",
    });
    return;
  }
  if (tab === "hooks") {
    setParams({
      credential: null,
      project: null,
      scope: null,
      sub: null,
      tab: "hooks",
    });
    return;
  }
  if (tab === "mcp") {
    setParams({
      credential: null,
      project: null,
      scope: null,
      sub: null,
      tab: "mcp",
    });
    return;
  }
  if (tab === "agents") {
    setParams({
      credential: null,
      project: null,
      scope: null,
      sub: null,
      tab: "agents",
    });
    return;
  }
  setParams({
    credential: null,
    project: null,
    scope: null,
    sub: null,
    tab: "assistant",
  });
}

function resolveLobbySettingsDirtyState(
  tab: LobbySettingsTab,
  values: Readonly<Record<LobbySettingsTab, boolean>>,
) {
  return values[tab];
}
