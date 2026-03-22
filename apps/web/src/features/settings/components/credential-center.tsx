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
import type { CredentialApiDialect } from "@/lib/api/types";

type CredentialCenterProps = {
  projectId?: string;
};

const API_DIALECT_OPTIONS: Array<{
  value: CredentialApiDialect;
  label: string;
  description: string;
}> = [
  {
    value: "openai_chat_completions",
    label: "OpenAI Chat Completions",
    description: "POST /v1/chat/completions",
  },
  {
    value: "openai_responses",
    label: "OpenAI Responses",
    description: "POST /v1/responses",
  },
  {
    value: "anthropic_messages",
    label: "Anthropic Messages",
    description: "POST /v1/messages",
  },
  {
    value: "gemini_generate_content",
    label: "Gemini Generate Content",
    description: "POST /v1beta/models/{model}:generateContent",
  },
];

function getApiDialectLabel(value: CredentialApiDialect) {
  return API_DIALECT_OPTIONS.find((option) => option.value === value)?.label ?? value;
}

export function CredentialCenter({ projectId }: CredentialCenterProps) {
  const queryClient = useQueryClient();
  const ownerType = projectId ? "project" : "user";
  const [formState, setFormState] = useState({
    provider: "",
    apiDialect: "openai_chat_completions" as CredentialApiDialect,
    displayName: "",
    apiKey: "",
    baseUrl: "",
    defaultModel: "",
  });
  const [feedback, setFeedback] = useState<string | null>(null);

  const query = useQuery({
    queryKey: ["credentials", projectId ?? "user"],
    queryFn: () => listCredentials(ownerType, projectId),
  });

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["credentials"] });

  const createMutation = useMutation({
    mutationFn: () =>
      createCredential({
        owner_type: ownerType,
        project_id: projectId ?? null,
        provider: formState.provider,
        api_dialect: formState.apiDialect,
        display_name: formState.displayName,
        api_key: formState.apiKey,
        base_url: formState.baseUrl || null,
        default_model: formState.defaultModel,
      }),
    onSuccess: () => {
      setFeedback("凭证已创建。");
      setFormState({
        provider: "",
        apiDialect: "openai_chat_completions",
        displayName: "",
        apiKey: "",
        baseUrl: "",
        defaultModel: "",
      });
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
      description="当前已支持用户级和项目级模型连接管理，可显式选择接口类型、Base URL 与默认模型。"
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
                    渠道键：{credential.provider} · 接口：{getApiDialectLabel(credential.api_dialect)}
                  </p>
                  <p className="text-sm text-[var(--text-secondary)]">
                    默认模型：{credential.default_model ?? "未配置"} · Key：{credential.masked_key}
                  </p>
                  <p className="text-xs text-[var(--text-secondary)]">
                    Base URL：{credential.base_url ?? "官方默认"} · 最近验证：{credential.last_verified_at ?? "未验证"}
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
              所有失败会直接透出后端原因，不做静默降级。`provider` 仅作为渠道键，真正请求协议由接口类型决定。
            </p>
          </div>

          <label className="block">
            <span className="label-text">渠道键 / Provider Key</span>
            <input
              className="ink-input"
              required
              placeholder="openai / openrouter / volcengine / my-proxy"
              value={formState.provider}
              onChange={(event) =>
                setFormState((current) => ({ ...current, provider: event.target.value }))
              }
            />
          </label>

          <label className="block">
            <span className="label-text">接口类型</span>
            <select
              className="ink-input"
              value={formState.apiDialect}
              onChange={(event) =>
                setFormState((current) => ({
                  ...current,
                  apiDialect: event.target.value as CredentialApiDialect,
                }))
              }
            >
              {API_DIALECT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label} · {option.description}
                </option>
              ))}
            </select>
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
              type="password"
              autoComplete="new-password"
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
              placeholder="https://api.openai.com"
              type="url"
              value={formState.baseUrl}
              onChange={(event) =>
                setFormState((current) => ({ ...current, baseUrl: event.target.value }))
              }
            />
          </label>

          <label className="block">
            <span className="label-text">默认模型</span>
            <input
              className="ink-input"
              required
              placeholder="gpt-4o-mini / claude-sonnet-4-20250514 / gemini-2.5-pro"
              value={formState.defaultModel}
              onChange={(event) =>
                setFormState((current) => ({ ...current, defaultModel: event.target.value }))
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
