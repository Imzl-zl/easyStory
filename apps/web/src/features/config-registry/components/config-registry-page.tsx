"use client";

import { useCallback, useDeferredValue, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { SectionCard } from "@/components/ui/section-card";
import { ConfigRegistryDetailPanel } from "@/features/config-registry/components/config-registry-detail-panel";
import { ConfigRegistryEditorPanel } from "@/features/config-registry/components/config-registry-editor-panel";
import {
  ConfigRegistryBanner,
  ConfigRegistryProtectedLink,
} from "@/features/config-registry/components/config-registry-page-primitives";
import { ConfigRegistrySidebar } from "@/features/config-registry/components/config-registry-sidebar";
import { ConfigRegistryUnsavedDialog } from "@/features/config-registry/components/config-registry-unsaved-dialog";
import { useConfigRegistryNavigationGuard } from "@/features/config-registry/components/use-config-registry-navigation-guard";
import {
  filterConfigRegistryItems,
  listConfigRegistryFilterTags,
  parseConfigRegistryCsvParam,
  resolveConfigRegistryEditorMode,
  resolveConfigRegistryRoutePatches,
  resolveConfigRegistrySortValue,
  resolveConfigRegistryStatusValue,
  serializeConfigRegistryCsvParam,
  serializeConfigRegistryEditorMode,
  serializeConfigRegistrySortValue,
  serializeConfigRegistryStatusValue,
} from "@/features/config-registry/components/config-registry-state-support";
import {
  buildConfigRegistryPathWithParams,
  resolveActiveConfigId,
  resolveConfigRegistryType,
} from "@/features/config-registry/components/config-registry-support";
import {
  getConfigRegistryEntry,
  listConfigRegistryEntries,
  updateConfigRegistryEntry,
} from "@/lib/api/config-registry";
import { getErrorMessage } from "@/lib/api/client";
import type { ConfigRegistryDetail } from "@/lib/api/types";

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
  const currentUrl = currentSearch ? `${pathname}?${currentSearch}` : pathname;
  const routeItemId = searchParams.get("item");
  const routeMode = searchParams.get("mode");
  const routeQuery = searchParams.get("q");
  const routeSort = searchParams.get("sort");
  const routeStatus = searchParams.get("status");
  const routeTags = searchParams.get("tags");
  const routeType = searchParams.get("type");
  const type = resolveConfigRegistryType(routeType);
  const mode = resolveConfigRegistryEditorMode(type, routeMode);
  const query = routeQuery ?? "";
  const sort = resolveConfigRegistrySortValue(routeSort);
  const status = resolveConfigRegistryStatusValue(type, routeStatus);
  const tags = parseConfigRegistryCsvParam(routeTags);
  const deferredQuery = useDeferredValue(query);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [isDirty, setIsDirty] = useState(false);

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
  const items = useMemo(() => listQuery.data ?? [], [listQuery.data]);
  const filteredItems = useMemo(
    () =>
      filterConfigRegistryItems({
        items,
        query: deferredQuery,
        sort,
        status,
        tags,
        type,
      }),
    [deferredQuery, items, sort, status, tags, type],
  );
  const availableTags = useMemo(() => listConfigRegistryFilterTags(items, type), [items, type]);
  const activeItemId = resolveActiveConfigId({ items, selectedId: routeItemId });
  const detailQuery = useQuery({
    queryKey: ["config-registry", type, activeItemId, "detail"],
    queryFn: () => getConfigRegistryEntry(type, activeItemId as string),
    enabled: Boolean(activeItemId),
  });
  const effectiveIsDirty = detailQuery.data ? isDirty : false;
  const navigationGuard = useConfigRegistryNavigationGuard({ currentUrl, isDirty: effectiveIsDirty, router });

  useEffect(() => {
    const patches = resolveConfigRegistryRoutePatches({
      activeItemId,
      hasLoadedList: listQuery.data !== undefined,
      mode,
      query,
      routeItemId,
      routeMode,
      routeQuery,
      routeSort,
      routeStatus,
      routeTags,
      routeType,
      sort,
      status,
      tags,
      type,
    });
    if (patches) {
      setParams(patches);
    }
  }, [
    activeItemId,
    listQuery.data,
    mode,
    query,
    routeItemId,
    routeMode,
    routeQuery,
    routeSort,
    routeStatus,
    routeTags,
    routeType,
    setParams,
    sort,
    status,
    tags,
    type,
  ]);

  const updateMutation = useMutation({
    mutationFn: (payload: ConfigRegistryDetail) =>
      updateConfigRegistryEntry(type, activeItemId as string, payload),
    onSuccess: async (result) => {
      setFeedback({ tone: "info", message: "配置已保存。" });
      queryClient.setQueryData(["config-registry", type, result.id, "detail"], result);
      await queryClient.invalidateQueries({ queryKey: ["config-registry", type, "list"] });
    },
    onError: (error) => setFeedback({ tone: "danger", message: getErrorMessage(error) }),
  });

  return (
    <div className="space-y-6">
      <SectionCard
        title="配置中心"
        description="管理系统配置，支持结构化表单与 JSON 双模式编辑。"
        action={
          <div className="flex flex-wrap gap-2">
            <ConfigRegistryProtectedLink
              href="/workspace/lobby"
              isDirty={effectiveIsDirty}
              label="返回项目大厅"
              onNavigate={navigationGuard.attemptNavigation}
            />
            <ConfigRegistryProtectedLink
              href="/workspace/lobby/settings?tab=credentials&sub=list"
              isDirty={effectiveIsDirty}
              label="全局设置"
              onNavigate={navigationGuard.attemptNavigation}
            />
          </div>
        }
      >
        <div className="space-y-4">
          <ConfigRegistryBanner message="仅配置管理员可访问；若当前账号无权限，页面会直接显示后端返回的 403 / 401 错误。" tone="muted" />
          {feedback ? <ConfigRegistryBanner ariaLive message={feedback.message} tone={feedback.tone} /> : null}
          <div className="grid gap-6 xl:grid-cols-[320px_1fr_480px]">
            <ConfigRegistrySidebar
              activeItemId={activeItemId}
              availableTags={availableTags}
              errorMessage={listQuery.error ? getErrorMessage(listQuery.error) : null}
              isLoading={listQuery.isLoading}
              items={filteredItems}
              query={query}
              sort={sort}
              status={status}
              tags={tags}
              type={type}
              onQueryChange={(value) => setParams({ q: value.trim() ? value : null })}
              onSelectItem={(itemId) => {
                setFeedback(null);
                navigationGuard.attemptNavigation(() => setParams({ item: itemId }));
              }}
              onSelectType={(nextType) => {
                setFeedback(null);
                navigationGuard.attemptNavigation(() =>
                  setParams({
                    item: null,
                    mode: serializeConfigRegistryEditorMode(
                      nextType,
                      resolveConfigRegistryEditorMode(nextType, null),
                    ),
                    status: null,
                    tags: null,
                    type: nextType,
                  }),
                );
              }}
              onSortChange={(value) => setParams({ sort: serializeConfigRegistrySortValue(value) })}
              onStatusChange={(value) =>
                setParams({ status: serializeConfigRegistryStatusValue(type, value) })
              }
              onTagToggle={(tag) =>
                setParams({
                  tags: serializeConfigRegistryCsvParam(
                    tags.includes(tag) ? tags.filter((item) => item !== tag) : [...tags, tag],
                  ),
                })
              }
            />
            <ConfigRegistryDetailPanel
              detail={detailQuery.data ?? null}
              errorMessage={detailQuery.error ? getErrorMessage(detailQuery.error) : null}
              isLoading={detailQuery.isLoading}
              type={type}
            />
            <ConfigRegistryEditorPanel
              detail={detailQuery.data ?? null}
              isPending={updateMutation.isPending}
              mode={mode}
              type={type}
              onDirtyChange={setIsDirty}
              onModeChange={(nextMode) =>
                setParams({ mode: serializeConfigRegistryEditorMode(type, nextMode) })
              }
              onSave={(payload) => {
                setFeedback(null);
                updateMutation.mutate(payload);
              }}
            />
          </div>
        </div>
      </SectionCard>

      <ConfigRegistryUnsavedDialog
        isOpen={navigationGuard.isConfirmOpen}
        isPending={false}
        onClose={navigationGuard.handleDialogClose}
        onConfirm={navigationGuard.handleDialogConfirm}
      />
    </div>
  );
}
