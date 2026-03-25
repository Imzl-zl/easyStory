"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { EmptyState } from "@/components/ui/empty-state";
import { SectionCard } from "@/components/ui/section-card";
import { CredentialAuditPanel } from "@/features/settings/components/credential-audit-panel";
import { CredentialCenterForm } from "@/features/settings/components/credential-center-form";
import { CredentialCenterList } from "@/features/settings/components/credential-center-list";
import {
  createInitialCredentialForm,
  normalizeCredentialBaseUrl,
  resolveActiveCredentialId,
  type CredentialCenterMode,
} from "@/features/settings/components/credential-center-support";
import {
  createCredential,
  deleteCredential,
  disableCredential,
  enableCredential,
  listCredentials,
  verifyCredential,
} from "@/lib/api/credential";
import { getErrorMessage } from "@/lib/api/client";

type CredentialCenterProps = {
  projectId?: string;
  mode?: CredentialCenterMode;
  selectedCredentialId?: string | null;
  onModeChange?: (mode: CredentialCenterMode) => void;
  onSelectCredential?: (credentialId: string | null) => void;
  headerAction?: React.ReactNode;
};

export function CredentialCenter({
  projectId,
  mode = "list",
  selectedCredentialId = null,
  onModeChange,
  onSelectCredential,
  headerAction,
}: CredentialCenterProps) {
  const queryClient = useQueryClient();
  const ownerType = projectId ? "project" : "user";
  const [formState, setFormState] = useState(createInitialCredentialForm);
  const [feedback, setFeedback] = useState<string | null>(null);
  const query = useQuery({
    queryKey: ["credentials", projectId ?? "user"],
    queryFn: () => listCredentials(ownerType, projectId),
  });
  const activeCredentialId = resolveActiveCredentialId(query.data, selectedCredentialId);
  const activeAuditCredentialId = mode === "audit" ? activeCredentialId : null;

  useEffect(() => {
    if (mode !== "audit" || query.data === undefined || selectedCredentialId === activeCredentialId) {
      return;
    }
    onSelectCredential?.(activeCredentialId);
  }, [activeCredentialId, mode, onSelectCredential, query.data, selectedCredentialId]);

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["credentials"] }),
      queryClient.invalidateQueries({ queryKey: ["credential-audit"] }),
    ]);
  };

  const createMutation = useMutation({
    mutationFn: () =>
      createCredential({
        owner_type: ownerType,
        project_id: projectId ?? null,
        provider: formState.provider.trim(),
        api_dialect: formState.apiDialect,
        display_name: formState.displayName.trim(),
        api_key: formState.apiKey,
        base_url: normalizeCredentialBaseUrl(formState.apiDialect, formState.baseUrl),
        default_model: formState.defaultModel.trim(),
      }),
    onSuccess: async () => {
      setFeedback("凭证已创建。");
      setFormState(createInitialCredentialForm());
      await refresh();
    },
    onError: (error) => setFeedback(getErrorMessage(error)),
  });

  const actionMutation = useMutation({
    mutationFn: async ({
      type,
      credentialId,
    }: {
      type: "verify" | "enable" | "disable" | "delete";
      credentialId: string;
    }) => {
      if (type === "verify") {
        return verifyCredential(credentialId);
      }
      if (type === "enable") {
        return enableCredential(credentialId);
      }
      if (type === "disable") {
        return disableCredential(credentialId);
      }
      return deleteCredential(credentialId);
    },
    onSuccess: async () => {
      setFeedback("凭证操作已完成。");
      await refresh();
    },
    onError: (error) => setFeedback(getErrorMessage(error)),
  });

  return (
    <SectionCard
      title="Credential Center"
      description="当前已支持用户级和项目级模型连接管理、验证、启停与凭证审计。"
      action={headerAction}
    >
      <div className="space-y-5">
        <CredentialModeTabs mode={mode} onModeChange={onModeChange} />
        {query.isLoading ? <p className="text-sm text-[var(--text-secondary)]">正在加载凭证...</p> : null}
        {query.error ? (
          <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
            {getErrorMessage(query.error)}
          </div>
        ) : null}
        {query.data && query.data.length > 0 ? (
          <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
            <CredentialCenterList
              activeCredentialId={activeAuditCredentialId}
              credentials={query.data}
              isPending={actionMutation.isPending}
              mode={mode}
              onAction={(type, credentialId) => actionMutation.mutate({ type, credentialId })}
              onSelectCredential={onSelectCredential}
            />
            {mode === "audit" ? (
              <CredentialAuditPanel credentialId={activeAuditCredentialId} />
            ) : (
              <CredentialCenterForm
                feedback={feedback}
                formState={formState}
                isPending={createMutation.isPending}
                setFormState={setFormState}
                onSubmit={() => {
                  setFeedback(null);
                  createMutation.mutate();
                }}
              />
            )}
          </div>
        ) : mode === "audit" ? (
          <EmptyState title="暂无凭证" description="先创建一条凭证，审计子视图才会出现可选目标。" />
        ) : (
          <CredentialCenterForm
            feedback={feedback}
            formState={formState}
            isPending={createMutation.isPending}
            setFormState={setFormState}
            onSubmit={() => {
              setFeedback(null);
              createMutation.mutate();
            }}
          />
        )}
      </div>
    </SectionCard>
  );
}

function CredentialModeTabs({
  mode,
  onModeChange,
}: {
  mode: CredentialCenterMode;
  onModeChange?: (mode: CredentialCenterMode) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {[
        ["list", "凭证列表"],
        ["audit", "审计日志"],
      ].map(([value, label]) => (
        <button
          key={value}
          className="ink-tab"
          data-active={mode === value}
          onClick={() => onModeChange?.(value as CredentialCenterMode)}
          type="button"
        >
          {label}
        </button>
      ))}
    </div>
  );
}
