"use client";

import { useCallback, useDeferredValue, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { showAppNotice } from "@/components/ui/app-notice";
import { GuardedLink } from "@/components/ui/guarded-link";
import { SectionCard } from "@/components/ui/section-card";
import { UnsavedChangesDialog } from "@/components/ui/unsaved-changes-dialog";
import { ConfigRegistryDetailPanel } from "@/features/config-registry/components/config-registry-detail-panel";
import { ConfigRegistryEditorPanel } from "@/features/config-registry/components/config-registry-editor-panel";
import {
  buildConfigRegistrySaveErrorFeedback,
  buildConfigRegistrySaveErrorNotice,
  buildConfigRegistrySaveSuccessNotice,
} from "@/features/config-registry/components/config-registry-notice-support";
import { ConfigRegistryBanner } from "@/features/config-registry/components/config-registry-page-primitives";
import { ConfigRegistrySidebar } from "@/features/config-registry/components/config-registry-sidebar";
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
import { useUnsavedChangesGuard } from "@/lib/hooks/use-unsaved-changes-guard";
import type { ConfigRegistryDetail } from "@/lib/api/types";

const ADMIN_ONLY_MESSAGE = "Control-plane admin access required";

type ScopedConfigRegistryFeedback = ReturnType<typeof buildConfigRegistrySaveErrorFeedback> & {
  scopeKey: string;
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
  const [feedback, setFeedback] = useState<ScopedConfigRegistryFeedback | null>(null);
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
  const feedbackScopeKey = `${type}:${activeItemId ?? "none"}`;
  const visibleFeedback = feedback?.scopeKey === feedbackScopeKey ? feedback : null;
  const effectiveIsDirty = detailQuery.data ? isDirty : false;
  const navigationGuard = useUnsavedChangesGuard({ currentUrl, isDirty: effectiveIsDirty, router });

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
      setFeedback(null);
      showAppNotice(buildConfigRegistrySaveSuccessNotice());
      queryClient.setQueryData(["config-registry", type, result.id, "detail"], result);
      await queryClient.invalidateQueries({ queryKey: ["config-registry", type, "list"] });
    },
    onError: (error) => {
      const message = getErrorMessage(error);
      setFeedback({
        ...buildConfigRegistrySaveErrorFeedback(message),
        scopeKey: feedbackScopeKey,
      });
      showAppNotice(buildConfigRegistrySaveErrorNotice(message));
    },
  });

  return (
    <div className="space-y-6">
      <SectionCard
        title="系统配置"
        action={
          <div className="flex flex-wrap items-center justify-end gap-2.5">
            <button
              className="ink-button-secondary h-9 px-4 text-[13px]"
              type="button"
              onClick={() => navigationGuard.attemptNavigation(() => router.back())}
            >
              返回
            </button>
            <GuardedLink
              className="ink-button-secondary h-9 px-4 text-[13px]"
              href="/workspace/lobby/settings?tab=credentials&sub=list"
              isDirty={effectiveIsDirty}
              onNavigate={navigationGuard.attemptNavigation}
            >
              模型连接
            </GuardedLink>
          </div>
        }
      >
        <div className="space-y-4">
          <ConfigRegistryBanner
            message="管理内置能力配置。日常写作请使用聊天和项目设置。"
            tone="info"
          />
          {visibleFeedback ? (
            <ConfigRegistryBanner
              ariaLive
              message={visibleFeedback.message}
              tone={visibleFeedback.tone}
            />
          ) : null}
          <div className="grid items-start gap-6 xl:grid-cols-[320px_minmax(0,1fr)] min-[1900px]:grid-cols-[320px_minmax(0,1fr)_480px]">
            <div className="xl:sticky xl:top-6">
              <ConfigRegistrySidebar
                activeItemId={activeItemId}
                availableTags={availableTags}
                errorMessage={resolveConfigRegistryErrorMessage(listQuery.error)}
                isLoading={listQuery.isLoading}
                items={filteredItems}
                query={query}
                sort={sort}
                status={status}
                tags={tags}
                type={type}
                onQueryChange={(value) => setParams({ q: value.trim() ? value : null })}
                onSelectItem={(itemId) => navigationGuard.attemptNavigation(() => setParams({ item: itemId }))}
                onSelectType={(nextType) => {
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
            </div>
            <div className="grid min-w-0 gap-6 min-[1900px]:contents">
              <ConfigRegistryDetailPanel
                detail={detailQuery.data ?? null}
                errorMessage={resolveConfigRegistryErrorMessage(detailQuery.error)}
                isLoading={detailQuery.isLoading}
                type={type}
              />
              <div className="min-[1900px]:max-h-[calc(100vh-13rem)] min-[1900px]:overflow-y-auto min-[1900px]:overscroll-y-contain">
                <ConfigRegistryEditorPanel
                  detail={detailQuery.data ?? null}
                  isPending={updateMutation.isPending}
                  mode={mode}
                  type={type}
                  onDirtyChange={setIsDirty}
                  onModeChange={(nextMode) =>
                    setParams({ mode: serializeConfigRegistryEditorMode(type, nextMode) })
                  }
                  onSave={(payload) => updateMutation.mutate(payload)}
                />
              </div>
            </div>
          </div>
        </div>
      </SectionCard>

      <UnsavedChangesDialog
        isOpen={navigationGuard.isConfirmOpen}
        isPending={false}
        onClose={navigationGuard.handleDialogClose}
        onConfirm={navigationGuard.handleDialogConfirm}
      />
    </div>
  );
}

function resolveConfigRegistryErrorMessage(error: unknown) {
  if (!error) {
    return null;
  }
  const message = getErrorMessage(error);
  return message === ADMIN_ONLY_MESSAGE
    ? "当前账号无权限访问该页面。"
    : message;
}
