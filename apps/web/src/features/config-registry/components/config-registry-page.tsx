"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { SectionCard } from "@/components/ui/section-card";
import { ConfigRegistryDetailPanel } from "@/features/config-registry/components/config-registry-detail-panel";
import { ConfigRegistryEditorPanel } from "@/features/config-registry/components/config-registry-editor-panel";
import { ConfigRegistrySidebar } from "@/features/config-registry/components/config-registry-sidebar";
import {
  buildConfigRegistryPathWithParams,
  formatConfigRegistryDocument,
  parseConfigRegistryDocument,
  resolveActiveConfigId,
  resolveConfigRegistryRoutePatches,
  resolveConfigRegistryType,
} from "@/features/config-registry/components/config-registry-support";
import {
  getConfigRegistryEntry,
  listConfigRegistryEntries,
  updateConfigRegistryEntry,
} from "@/lib/api/config-registry";
import { getErrorMessage } from "@/lib/api/client";

type Feedback = {
  message: string;
  tone: "danger" | "info";
};

export function ConfigRegistryPage() {
  const pathname = usePathname();
  const queryClient = useQueryClient();
  const router = useRouter();
  const searchParams = useSearchParams();
  const currentSearch = searchParams.toString();
  const routeItemId = searchParams.get("item");
  const routeType = searchParams.get("type");
  const type = resolveConfigRegistryType(routeType);
  const [draftByItemId, setDraftByItemId] = useState<Record<string, string>>({});
  const [feedback, setFeedback] = useState<Feedback | null>(null);

  const setParams = useCallback(
    (patches: Record<string, string | null>) => {
      router.replace(buildConfigRegistryPathWithParams(pathname, currentSearch, patches));
    },
    [currentSearch, pathname, router],
  );

  const listQuery = useQuery({
    queryKey: ["config-registry", type, "list"],
    queryFn: () => listConfigRegistryEntries(type),
  });
  const items = listQuery.data ?? [];
  const activeItemId = resolveActiveConfigId({ items, selectedId: routeItemId });
  const detailQuery = useQuery({
    queryKey: ["config-registry", type, activeItemId, "detail"],
    queryFn: () => getConfigRegistryEntry(type, activeItemId as string),
    enabled: Boolean(activeItemId),
  });

  useEffect(() => {
    const patches = resolveConfigRegistryRoutePatches({
      activeItemId,
      hasLoadedList: listQuery.data !== undefined,
      routeItemId,
      routeType,
      type,
    });
    if (!patches) {
      return;
    }
    setParams(patches);
  }, [activeItemId, listQuery.data, routeItemId, routeType, setParams, type]);

  const detailDocument = useMemo(
    () => (detailQuery.data ? formatConfigRegistryDocument(detailQuery.data) : ""),
    [detailQuery.data],
  );
  const editorValue = activeItemId ? draftByItemId[activeItemId] ?? detailDocument : "";

  const parsedEditor = useMemo(
    () => parseConfigRegistryDocument(editorValue),
    [editorValue],
  );
  const isDirty = detailQuery.data ? editorValue !== detailDocument : false;

  const updateMutation = useMutation({
    mutationFn: () =>
      updateConfigRegistryEntry(type, activeItemId as string, parsedEditor.parsed ?? {}),
    onSuccess: async (result) => {
      const nextDocument = formatConfigRegistryDocument(result);
      setDraftByItemId((current) => ({ ...current, [result.id]: nextDocument }));
      setFeedback({ tone: "info", message: "配置已保存。" });
      queryClient.setQueryData(["config-registry", type, activeItemId, "detail"], result);
      await queryClient.invalidateQueries({ queryKey: ["config-registry", type, "list"] });
    },
    onError: (error) => setFeedback({ tone: "danger", message: getErrorMessage(error) }),
  });

  return (
    <div className="space-y-6">
      <SectionCard
        title="Config Registry"
        description="后端配置真值直接来自 config DTO。当前页面提供列表、详情预览和 JSON 级编辑，不再自造第二套字段映射。"
        action={
          <div className="flex flex-wrap gap-2">
            <Link className="ink-button-secondary" href="/workspace/lobby">
              返回 Lobby
            </Link>
            <Link
              className="ink-button-secondary"
              href="/workspace/lobby/settings?tab=credentials&sub=list"
            >
              全局设置
            </Link>
          </div>
        }
      >
        <div className="space-y-4">
          <Banner
            message="仅配置管理员可访问；若当前账号无权限，页面会直接显示后端返回的 403 / 401 错误。"
            tone="muted"
          />
          {feedback ? <Banner message={feedback.message} tone={feedback.tone} /> : null}
          <div className="grid gap-6 xl:grid-cols-[280px_1fr_420px]">
            <ConfigRegistrySidebar
              activeItemId={activeItemId}
              errorMessage={listQuery.error ? getErrorMessage(listQuery.error) : null}
              isLoading={listQuery.isLoading}
              items={items}
              onSelectItem={(itemId) => {
                setFeedback(null);
                setParams({ item: itemId });
              }}
              onSelectType={(nextType) => {
                setFeedback(null);
                setParams({ item: null, type: nextType });
              }}
              type={type}
            />
            <ConfigRegistryDetailPanel
              detail={detailQuery.data ?? null}
              errorMessage={detailQuery.error ? getErrorMessage(detailQuery.error) : null}
              isLoading={detailQuery.isLoading}
              type={type}
            />
            <ConfigRegistryEditorPanel
              detailId={detailQuery.data?.id ?? null}
              editorValue={editorValue}
              errorMessage={parsedEditor.errorMessage}
              isDirty={isDirty}
              isPending={updateMutation.isPending}
              onChange={(value) => {
                if (!detailQuery.data) {
                  return;
                }
                setDraftByItemId((current) => ({ ...current, [detailQuery.data.id]: value }));
              }}
              onReset={() => {
                if (!detailQuery.data) {
                  return;
                }
                setFeedback(null);
                setDraftByItemId((current) => ({
                  ...current,
                  [detailQuery.data.id]: detailDocument,
                }));
              }}
              onSave={() => {
                setFeedback(null);
                updateMutation.mutate();
              }}
              type={type}
            />
          </div>
        </div>
      </SectionCard>
    </div>
  );
}

function Banner({
  message,
  tone,
}: Readonly<{
  message: string;
  tone: "danger" | "info" | "muted";
}>) {
  if (tone === "danger") {
    return (
      <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
        {message}
      </div>
    );
  }
  if (tone === "info") {
    return (
      <div className="rounded-2xl bg-[rgba(58,124,165,0.1)] px-4 py-3 text-sm text-[var(--accent-info)]">
        {message}
      </div>
    );
  }
  return <div className="panel-muted px-4 py-5 text-sm text-[var(--text-secondary)]">{message}</div>;
}
