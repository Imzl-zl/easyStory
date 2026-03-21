"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { SectionCard } from "@/components/ui/section-card";
import { StatusBadge } from "@/components/ui/status-badge";
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
};

export function CredentialCenter({ projectId }: CredentialCenterProps) {
  const queryClient = useQueryClient();
  const [formState, setFormState] = useState({
    ownerType: projectId ? "project" : "user",
    provider: "",
    displayName: "",
    apiKey: "",
    baseUrl: "",
  });
  const [feedback, setFeedback] = useState<string | null>(null);

  const query = useQuery({
    queryKey: ["credentials", projectId ?? "user"],
    queryFn: () => listCredentials(projectId ? "project" : "user", projectId),
  });

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["credentials"] });

  const createMutation = useMutation({
    mutationFn: () =>
      createCredential({
        owner_type: formState.ownerType as "user" | "project",
        project_id: projectId ?? null,
        provider: formState.provider,
        display_name: formState.displayName,
        api_key: formState.apiKey,
        base_url: formState.baseUrl || null,
      }),
    onSuccess: () => {
      setFeedback("凭证已创建。");
      setFormState((current) => ({
        ...current,
        provider: "",
        displayName: "",
        apiKey: "",
        baseUrl: "",
      }));
      refresh();
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
    onSuccess: () => {
      setFeedback("凭证操作已完成。");
      refresh();
    },
    onError: (error) => setFeedback(getErrorMessage(error)),
  });

  return (
    <SectionCard
      title="Credential Center"
      description="当前 MVP 已支持用户级和项目级模型凭证管理、验证与启停。"
    >
      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-4">
          {query.isLoading ? <p className="text-sm text-[var(--text-secondary)]">正在加载凭证...</p> : null}
          {query.error ? (
            <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
              {getErrorMessage(query.error)}
            </div>
          ) : null}
          <div className="space-y-3">
            {query.data?.map((credential) => (
              <article
                key={credential.id}
                className="panel-muted flex flex-col gap-3 p-4 md:flex-row md:items-center md:justify-between"
              >
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-medium">{credential.display_name}</h3>
                    <StatusBadge
                      status={credential.is_active ? "active" : "archived"}
                      label={credential.is_active ? "启用中" : "已停用"}
                    />
                  </div>
                  <p className="text-sm text-[var(--text-secondary)]">
                    {credential.provider} · {credential.masked_key}
                  </p>
                  <p className="text-xs text-[var(--text-secondary)]">
                    最近验证：{credential.last_verified_at ?? "未验证"}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    className="ink-button-secondary"
                    disabled={actionMutation.isPending}
                    onClick={() => actionMutation.mutate({ type: "verify", credentialId: credential.id })}
                  >
                    验证
                  </button>
                  <button
                    className="ink-button-secondary"
                    disabled={actionMutation.isPending}
                    onClick={() =>
                      actionMutation.mutate({
                        type: credential.is_active ? "disable" : "enable",
                        credentialId: credential.id,
                      })
                    }
                  >
                    {credential.is_active ? "停用" : "启用"}
                  </button>
                  <button
                    className="ink-button-danger"
                    disabled={actionMutation.isPending}
                    onClick={() => actionMutation.mutate({ type: "delete", credentialId: credential.id })}
                  >
                    删除
                  </button>
                </div>
              </article>
            ))}
          </div>
        </div>

        <form
          className="panel-muted space-y-4 p-5"
          onSubmit={(event) => {
            event.preventDefault();
            setFeedback(null);
            createMutation.mutate();
          }}
        >
          <div className="space-y-1">
            <h3 className="font-serif text-lg font-semibold">新增凭证</h3>
            <p className="text-sm leading-6 text-[var(--text-secondary)]">
              所有失败会直接透出后端原因，不做静默降级。
            </p>
          </div>

          <label className="block">
            <span className="label-text">Provider</span>
            <input
              className="ink-input"
              required
              value={formState.provider}
              onChange={(event) =>
                setFormState((current) => ({ ...current, provider: event.target.value }))
              }
            />
          </label>

          <label className="block">
            <span className="label-text">显示名称</span>
            <input
              className="ink-input"
              required
              value={formState.displayName}
              onChange={(event) =>
                setFormState((current) => ({ ...current, displayName: event.target.value }))
              }
            />
          </label>

          <label className="block">
            <span className="label-text">API Key</span>
            <input
              className="ink-input"
              required
              value={formState.apiKey}
              onChange={(event) =>
                setFormState((current) => ({ ...current, apiKey: event.target.value }))
              }
            />
          </label>

          <label className="block">
            <span className="label-text">Base URL</span>
            <input
              className="ink-input"
              value={formState.baseUrl}
              onChange={(event) =>
                setFormState((current) => ({ ...current, baseUrl: event.target.value }))
              }
            />
          </label>

          {feedback ? (
            <div className="rounded-2xl bg-[rgba(58,124,165,0.1)] px-4 py-3 text-sm text-[var(--accent-info)]">
              {feedback}
            </div>
          ) : null}

          <button className="ink-button w-full" disabled={createMutation.isPending} type="submit">
            {createMutation.isPending ? "提交中..." : "创建凭证"}
          </button>
        </form>
      </div>
    </SectionCard>
  );
}
