"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState, useTransition } from "react";

import { showAppNotice } from "@/components/ui/app-notice";
import { getErrorMessage } from "@/lib/api/client";
import { createAnalysis, deleteAnalysis, getAnalysis, listAnalyses } from "@/lib/api/analysis";

import { LabCreatePanel } from "./lab-create-panel";
import { LabDetailPanel } from "./lab-detail-panel";
import { LabSidebar } from "./lab-sidebar";
import {
  buildLabAnalysisListOptions,
  buildLabAnalysisQueryKey,
  buildLabCreatePayload,
  createInitialLabAnalysisFilterState,
  createInitialLabAnalysisFormState,
  hasActiveLabAnalysisFilters,
  prependLabAnalysisSummary,
  removeLabAnalysisSummary,
  resolveActiveLabAnalysisId,
  resolveNextLabSelectedIdAfterDelete,
  type LabAnalysisFilterState,
} from "./lab-support";

type LabPageProps = {
  projectId: string;
};

export function LabPage({ projectId }: Readonly<LabPageProps>) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const [filters, setFilters] = useState<LabAnalysisFilterState>(createInitialLabAnalysisFilterState());
  const [isCreating, setIsCreating] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const listOptions = useMemo(() => buildLabAnalysisListOptions(filters), [filters]);
  const listQueryKey = buildLabAnalysisQueryKey(projectId, listOptions);

  const analysesQuery = useQuery({
    queryKey: listQueryKey,
    queryFn: () => listAnalyses(projectId, listOptions),
  });

  const activeId = resolveActiveLabAnalysisId(analysesQuery.data, selectedId);

  const detailQuery = useQuery({
    queryKey: ["analysis-detail", projectId, activeId],
    queryFn: () => (activeId ? getAnalysis(projectId, activeId) : null),
    enabled: Boolean(activeId) && !isCreating,
  });

  const createMutation = useMutation({
    mutationFn: (formState: ReturnType<typeof createInitialLabAnalysisFormState>) =>
      createAnalysis(projectId, buildLabCreatePayload(formState)),
    onSuccess: (analysis) => {
      showAppNotice({
        content: "洞察已保存。",
        title: "分析实验室",
        tone: "success",
      });
      setIsCreating(false);
      queryClient.setQueryData(listQueryKey, (current: typeof analysesQuery.data) =>
        prependLabAnalysisSummary(current, analysis),
      );
      startTransition(() => {
        setSelectedId(analysis.id);
      });
    },
    onError: (error) =>
      showAppNotice({
        content: getErrorMessage(error),
        title: "分析实验室",
        tone: "danger",
      }),
  });

  const deleteMutation = useMutation({
    mutationFn: (analysisId: string) => deleteAnalysis(projectId, analysisId),
    onSuccess: (_, analysisId) => {
      showAppNotice({
        content: "洞察已删除。",
        title: "分析实验室",
        tone: "success",
      });
      setDeleteTarget(null);
      queryClient.setQueryData(listQueryKey, (current: typeof analysesQuery.data) =>
        removeLabAnalysisSummary(current, analysisId),
      );
      const nextId = resolveNextLabSelectedIdAfterDelete(
        analysesQuery.data,
        selectedId,
        analysisId,
      );
      startTransition(() => {
        setSelectedId(nextId);
      });
    },
    onError: (error) =>
      showAppNotice({
        content: getErrorMessage(error),
        title: "分析实验室",
        tone: "danger",
      }),
  });

  const handleFilterChange = (patch: Partial<LabAnalysisFilterState>) => {
    startTransition(() => {
      setFilters((current) => ({ ...current, ...patch }));
      setSelectedId(null);
    });
  };

  const handleSelect = (analysisId: string) => {
    if (isPending) return;
    startTransition(() => {
      setSelectedId(analysisId);
      setIsCreating(false);
    });
  };

  const handleStartCreate = () => {
    setIsCreating(true);
    setSelectedId(null);
  };

  const handleCancelCreate = () => {
    setIsCreating(false);
  };

  const handleRequestDelete = (analysisId: string) => {
    setDeleteTarget(analysisId);
  };

  const handleConfirmDelete = () => {
    if (deleteTarget) {
      deleteMutation.mutate(deleteTarget);
    }
  };

  const handleCancelDelete = () => {
    setDeleteTarget(null);
  };

  return (
    <div className="h-full flex flex-col" style={{ background: "#111418" }}>
      {/* Header */}
      <header className="px-6 pt-6 pb-4 flex-shrink-0" style={{ borderBottom: "1px solid #1f2328" }}>
        <div className="flex items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#e8b86d" }} />
              <span className="text-[10px] font-semibold tracking-[0.15em] uppercase" style={{ color: "#e8b86d" }}>
                分析实验室
              </span>
            </div>
            <h1 className="text-[22px] font-semibold tracking-tight" style={{ color: "#e8e6e3" }}>
              项目洞察
            </h1>
          </div>
          <button
            className="px-4 py-2 rounded text-[12px] font-medium transition-all disabled:opacity-40"
            style={{ background: "#e8b86d", color: "#111418" }}
            disabled={isPending || createMutation.isPending}
            onClick={handleStartCreate}
            type="button"
          >
            新建洞察
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 px-6 py-4 overflow-auto">
        <div className="grid gap-4 h-full" style={{ gridTemplateColumns: "minmax(280px, 320px) minmax(0, 1fr)" }}>
          <LabSidebar
            activeId={activeId}
            analyses={analysesQuery.data ?? []}
            errorMessage={analysesQuery.error ? getErrorMessage(analysesQuery.error) : null}
            filters={filters}
            isLoading={analysesQuery.isLoading}
            isPending={isPending}
            onFilterChange={handleFilterChange}
            onSelect={handleSelect}
          />

          {isCreating ? (
            <LabCreatePanel
              isPending={createMutation.isPending}
              onCancel={handleCancelCreate}
              onSubmit={(formState) => createMutation.mutate(formState)}
            />
          ) : (
            <LabDetailPanel
              activeId={activeId}
              analysis={detailQuery.data ?? undefined}
              errorMessage={detailQuery.error ? getErrorMessage(detailQuery.error) : null}
              hasActiveFilters={hasActiveLabAnalysisFilters(filters)}
              isDeletePending={deleteMutation.isPending}
              isLoading={detailQuery.isLoading}
              onRequestDelete={handleRequestDelete}
            />
          )}
        </div>
      </div>

      {/* Delete Dialog */}
      {deleteTarget ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.6)" }}>
          <div className="rounded p-5 w-full max-w-sm" style={{ background: "#1a1d23", border: "1px solid #2a2f35" }}>
            <h3 className="text-[14px] font-semibold mb-2" style={{ color: "#e8e6e3" }}>删除洞察</h3>
            <p className="text-[12px] mb-4" style={{ color: "#9ca3af" }}>确定要删除这条洞察记录吗？此操作不可撤销。</p>
            <div className="flex gap-2 justify-end">
              <button
                className="px-3 py-1.5 rounded text-[12px] font-medium transition-colors"
                style={{ background: "#1f2328", color: "#9ca3af" }}
                onClick={handleCancelDelete}
                type="button"
              >
                取消
              </button>
              <button
                className="px-3 py-1.5 rounded text-[12px] font-medium transition-all disabled:opacity-40"
                style={{ background: "rgba(220, 38, 38, 0.12)", color: "#f87171", border: "1px solid rgba(220, 38, 38, 0.2)" }}
                disabled={deleteMutation.isPending}
                onClick={handleConfirmDelete}
                type="button"
              >
                {deleteMutation.isPending ? "删除中..." : "删除"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
