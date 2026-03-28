"use client";

import { useMemo } from "react";
import { useQueries } from "@tanstack/react-query";

import { listConfigRegistryEntries } from "@/lib/api/config-registry";
import { getErrorMessage } from "@/lib/api/client";
import type {
  AgentConfigDetail,
  ConfigRegistryDetail,
  ConfigRegistrySummary,
  ConfigRegistryType,
  HookConfigDetail,
  McpServerConfigDetail,
  SkillConfigDetail,
} from "@/lib/api/types";

import {
  buildConfigRegistryReferenceFieldState,
  type ConfigRegistryReferenceOption,
} from "./config-registry-reference-support";
import { HookFormEditor, McpFormEditor } from "./config-registry-hook-mcp-form";
import { AgentFormEditor, SkillFormEditor } from "./config-registry-skill-agent-form";

export function ConfigRegistryStructuredEditor({
  detail,
  isPending,
  onDraftChange,
  onDirtyChange,
  onSave,
  type,
}: Readonly<{
  detail: ConfigRegistryDetail;
  isPending: boolean;
  onDraftChange: (draft: ConfigRegistryDetail) => void;
  onDirtyChange: (value: boolean) => void;
  onSave: (payload: ConfigRegistryDetail) => void;
  type: ConfigRegistryType;
}>) {
  const [skillsQuery, agentsQuery, mcpServersQuery] = useQueries({
    queries: [
      {
        enabled: type === "agents",
        queryFn: () => listConfigRegistryEntries("skills"),
        queryKey: ["config-registry", "skills", "list", "reference"],
      },
      {
        enabled: type === "hooks",
        queryFn: () => listConfigRegistryEntries("agents"),
        queryKey: ["config-registry", "agents", "list", "reference"],
      },
      {
        enabled: type === "agents" || type === "hooks",
        queryFn: () => listConfigRegistryEntries("mcp_servers"),
        queryKey: ["config-registry", "mcp_servers", "list", "reference"],
      },
    ],
  });

  const skillReferenceField = useMemo(
    () =>
      buildConfigRegistryReferenceFieldState({
        defaultEmptyMessage: "暂无可选 Skills，可切换到完整配置。",
        errorMessage: skillsQuery.error ? `Skills 列表加载失败：${getErrorMessage(skillsQuery.error)}` : null,
        isLoading: skillsQuery.isLoading,
        loadingMessage: "正在加载 Skills…",
        options: buildReferenceOptions(skillsQuery.data ?? []),
      }),
    [skillsQuery.data, skillsQuery.error, skillsQuery.isLoading],
  );
  const agentReferenceField = useMemo(
    () =>
      buildConfigRegistryReferenceFieldState({
        defaultEmptyMessage: "暂无可选 Agents。",
        errorMessage: agentsQuery.error ? `Agents 列表加载失败：${getErrorMessage(agentsQuery.error)}` : null,
        isLoading: agentsQuery.isLoading,
        loadingMessage: "正在加载 Agents…",
        options: buildReferenceOptions(agentsQuery.data ?? []),
      }),
    [agentsQuery.data, agentsQuery.error, agentsQuery.isLoading],
  );
  const mcpReferenceField = useMemo(
    () =>
      buildConfigRegistryReferenceFieldState({
        defaultEmptyMessage: "暂无可选 MCP。",
        errorMessage: mcpServersQuery.error
          ? `MCP 列表加载失败：${getErrorMessage(mcpServersQuery.error)}`
          : null,
        isLoading: mcpServersQuery.isLoading,
        loadingMessage: "正在加载 MCP…",
        options: buildReferenceOptions(mcpServersQuery.data ?? []),
      }),
    [mcpServersQuery.data, mcpServersQuery.error, mcpServersQuery.isLoading],
  );

  if (type === "skills") {
    return (
      <SkillFormEditor
        detail={detail as SkillConfigDetail}
        isPending={isPending}
        onDraftChange={(payload) => onDraftChange(payload)}
        onDirtyChange={onDirtyChange}
        onSave={(payload) => onSave(payload)}
      />
    );
  }
  if (type === "agents") {
    return (
      <AgentFormEditor
        detail={detail as AgentConfigDetail}
        isPending={isPending}
        onDraftChange={(payload) => onDraftChange(payload)}
        skillReferenceField={skillReferenceField}
        mcpReferenceField={mcpReferenceField}
        onDirtyChange={onDirtyChange}
        onSave={(payload) => onSave(payload)}
      />
    );
  }
  if (type === "hooks") {
    return (
      <HookFormEditor
        detail={detail as HookConfigDetail}
        isPending={isPending}
        onDraftChange={(payload) => onDraftChange(payload)}
        agentReferenceField={agentReferenceField}
        mcpReferenceField={mcpReferenceField}
        onDirtyChange={onDirtyChange}
        onSave={(payload) => onSave(payload)}
      />
    );
  }
  return (
    <McpFormEditor
      detail={detail as McpServerConfigDetail}
      isPending={isPending}
      onDraftChange={(payload) => onDraftChange(payload)}
      onDirtyChange={onDirtyChange}
      onSave={(payload) => onSave(payload)}
    />
  );
}

function buildReferenceOptions(items: ConfigRegistrySummary[]): ConfigRegistryReferenceOption[] {
  return items.map((item) => ({ label: `${item.name} (${item.id})`, value: item.id }));
}
