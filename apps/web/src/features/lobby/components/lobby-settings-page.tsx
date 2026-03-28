"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { GuardedLink } from "@/components/ui/guarded-link";
import { SectionCard } from "@/components/ui/section-card";
import { UnsavedChangesDialog } from "@/components/ui/unsaved-changes-dialog";
import {
  useLobbySettingsRouteState,
  useNormalizeLobbySettingsRoute,
  type LobbySettingsRouteState,
} from "@/features/lobby/components/lobby-settings-route";
import { type LobbySettingsTab } from "@/features/lobby/components/lobby-settings-support";
import { AssistantPreferencesPanel } from "@/features/settings/components/assistant-preferences-panel";
import { AssistantRulesEditor } from "@/features/settings/components/assistant-rules-editor";
import { CredentialCenter } from "@/features/settings/components/credential-center";
import { useUnsavedChangesGuard } from "@/lib/hooks/use-unsaved-changes-guard";

export function LobbySettingsPage() {
  const router = useRouter();
  const route = useLobbySettingsRouteState();
  const [assistantPreferencesDirty, setAssistantPreferencesDirty] = useState(false);
  const [assistantRulesDirty, setAssistantRulesDirty] = useState(false);
  const [credentialDirty, setCredentialDirty] = useState(false);
  useNormalizeLobbySettingsRoute(route);
  const currentUrl = route.currentSearch ? `${route.pathname}?${route.currentSearch}` : route.pathname;
  const isDirty = route.tab === "assistant"
    ? assistantPreferencesDirty || assistantRulesDirty
    : credentialDirty;
  const navigationGuard = useUnsavedChangesGuard({ currentUrl, isDirty, router });

  return (
    <>
      <div className="grid gap-6 xl:grid-cols-[300px_minmax(0,1fr)]">
        <LobbySettingsSidebar
          isDirty={isDirty}
          isPending={route.isPending}
          onNavigate={navigationGuard.attemptNavigation}
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

function LobbySettingsSidebar({
  isDirty,
  isPending,
  onNavigate,
  onSelectTab,
  tab,
}: Readonly<{
  isDirty: boolean;
  isPending: boolean;
  onNavigate: (onConfirm: () => void) => void;
  onSelectTab: (tab: LobbySettingsTab) => void;
  tab: LobbySettingsTab;
}>) {
  return (
    <aside className="space-y-4 xl:sticky xl:top-6 xl:self-start">
      <SectionCard
        action={
          <GuardedLink
            className="ink-button-secondary"
            href="/workspace/lobby"
            isDirty={isDirty}
            onNavigate={onNavigate}
          >
            返回项目大厅
          </GuardedLink>
        }
        description="管理模型连接、默认模型和长期规则。"
        title="AI 设置"
      >
        <div className="space-y-3">
          <LobbySettingsNavButton
            active={tab === "assistant"}
            description="默认连接、默认模型、长期规则"
            disabled={isPending}
            label="AI 助手"
            onClick={() => onSelectTab("assistant")}
          />
          <LobbySettingsNavButton
            active={tab === "credentials"}
            description="添加、验证、启用或切换模型连接"
            disabled={isPending}
            label="模型连接"
            onClick={() => onSelectTab("credentials")}
          />
        </div>
      </SectionCard>
      <div className="panel-muted space-y-2 px-4 py-3 text-sm leading-6 text-[var(--text-secondary)]">
        <p>管理个人默认设置。</p>
        <p>项目专属规则请前往“项目设置”。</p>
      </div>
    </aside>
  );
}

function LobbySettingsNavButton({
  active,
  description,
  disabled,
  label,
  onClick,
}: Readonly<{
  active: boolean;
  description: string;
  disabled: boolean;
  label: string;
  onClick: () => void;
}>) {
  return (
    <button
      className="ink-tab w-full justify-start rounded-[20px] px-4 py-3 text-left"
      data-active={active}
      disabled={disabled}
      onClick={onClick}
      type="button"
    >
      <span className="flex flex-col items-start gap-1">
        <span className="text-sm font-medium text-[var(--text-primary)]">{label}</span>
        <span className="text-[12px] leading-5 text-[var(--text-secondary)]">{description}</span>
      </span>
    </button>
  );
}

function LobbySettingsContent({
  navigationGuard,
  route,
  onAssistantPreferencesDirtyChange,
  onAssistantRulesDirtyChange,
  onCredentialDirtyChange,
}: Readonly<{
  navigationGuard: (onConfirm: () => void) => void;
  route: LobbySettingsRouteState;
  onAssistantPreferencesDirtyChange: (isDirty: boolean) => void;
  onAssistantRulesDirtyChange: (isDirty: boolean) => void;
  onCredentialDirtyChange: (isDirty: boolean) => void;
}>) {
  if (route.tab === "assistant") {
    return (
      <div className="space-y-4">
        <AssistantPreferencesPanel onDirtyChange={onAssistantPreferencesDirtyChange} />
        <AssistantRulesEditor
          description="保存后，新聊天会自动带上这些规则。"
          onDirtyChange={onAssistantRulesDirtyChange}
          scope="user"
          title="个人长期规则"
        />
      </div>
    );
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
  setParams({
    credential: null,
    project: null,
    scope: null,
    sub: null,
    tab: "assistant",
  });
}
