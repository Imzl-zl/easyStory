"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { EmptyState } from "@/components/ui/empty-state";
import { SectionCard } from "@/components/ui/section-card";
import { StatusBadge } from "@/components/ui/status-badge";
import { StoryAssetImpactPanel } from "@/features/studio/components/story-asset-impact-panel";
import {
  buildStoryAssetMutationFeedback,
  invalidateStoryAssetQueries,
} from "@/features/studio/components/story-asset-editor-support";
import { ApiError, getErrorMessage } from "@/lib/api/client";
import {
  approveOpeningPlan,
  approveOutline,
  getOpeningPlan,
  getOutline,
  saveOpeningPlan,
  saveOutline,
} from "@/lib/api/content";
import type { StoryAssetImpactSummary } from "@/lib/api/types";

type StoryAssetEditorProps = {
  projectId: string;
  assetType: "outline" | "opening_plan";
};

export function StoryAssetEditor({ projectId, assetType }: StoryAssetEditorProps) {
  const [lastImpactState, setLastImpactState] = useState<{
    assetType: "outline" | "opening_plan";
    impact: StoryAssetImpactSummary | null;
    projectId: string;
  }>({
    projectId,
    assetType,
    impact: null,
  });
  const query = useQuery({
    queryKey: ["story-asset", projectId, assetType],
    queryFn: () => (assetType === "outline" ? getOutline(projectId) : getOpeningPlan(projectId)),
  });
  const isMissingAsset = query.error instanceof ApiError && query.error.status === 404;
  const formKey = query.data ? `${query.data.content_id}:${query.data.version_number}` : assetType;
  const lastImpact =
    lastImpactState.projectId === projectId && lastImpactState.assetType === assetType
      ? lastImpactState.impact
      : null;

  return (
    <StoryAssetEditorForm
      key={formKey}
      asset={query.data}
      assetType={assetType}
      isMissingAsset={isMissingAsset}
      lastImpact={lastImpact}
      onImpactChange={(impact) => setLastImpactState({ projectId, assetType, impact })}
      projectId={projectId}
      queryError={query.error}
      queryLoading={query.isLoading}
    />
  );
}

function StoryAssetEditorForm({
  projectId,
  assetType,
  asset,
  isMissingAsset,
  lastImpact,
  onImpactChange,
  queryLoading,
  queryError,
}: {
  projectId: string;
  assetType: "outline" | "opening_plan";
  asset?: Awaited<ReturnType<typeof getOutline>>;
  isMissingAsset: boolean;
  lastImpact: StoryAssetImpactSummary | null;
  onImpactChange: (impact: StoryAssetImpactSummary | null) => void;
  queryLoading: boolean;
  queryError: unknown;
}) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(asset?.title ?? (assetType === "outline" ? "主线大纲" : "开篇设计"));
  const [contentText, setContentText] = useState(asset?.content_text ?? "");
  const [changeSummary, setChangeSummary] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);

  const saveMutation = useMutation({
    mutationFn: () =>
      (assetType === "outline" ? saveOutline : saveOpeningPlan)(projectId, {
        title,
        content_text: contentText,
        change_summary: changeSummary || undefined,
      }),
    onSuccess: (result) => {
      onImpactChange(result.impact);
      setFeedback(buildStoryAssetMutationFeedback(assetType, "save", result.impact));
      invalidateStoryAssetQueries(queryClient, projectId, assetType, result.impact);
    },
    onError: (error) => {
      onImpactChange(null);
      setFeedback(getErrorMessage(error));
    },
  });

  const approveMutation = useMutation({
    mutationFn: () => (assetType === "outline" ? approveOutline : approveOpeningPlan)(projectId),
    onSuccess: (result) => {
      onImpactChange(result.impact);
      setFeedback(buildStoryAssetMutationFeedback(assetType, "approve", result.impact));
      invalidateStoryAssetQueries(queryClient, projectId, assetType, result.impact);
    },
    onError: (error) => {
      onImpactChange(null);
      setFeedback(getErrorMessage(error));
    },
  });

  return (
    <SectionCard
      title={assetType === "outline" ? "大纲" : "开篇设计"}
      description="编辑大纲或开篇设计，保存后可确认。"
      action={
        <div className="flex flex-wrap gap-2">
          {asset ? <StatusBadge status={asset.status} /> : null}
          <button className="ink-button-secondary" disabled={saveMutation.isPending} onClick={() => saveMutation.mutate()}>
            {saveMutation.isPending ? "保存中..." : "保存草稿"}
          </button>
          <button className="ink-button" disabled={approveMutation.isPending} onClick={() => approveMutation.mutate()}>
            {approveMutation.isPending ? "确认中..." : "确认"}
          </button>
        </div>
      }
    >
      {queryLoading ? <p className="text-sm text-[var(--text-secondary)]">正在加载资产...</p> : null}
      {queryError && !isMissingAsset ? (
        <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
          {getErrorMessage(queryError)}
        </div>
      ) : null}
      {isMissingAsset ? (
        <EmptyState
          title="当前还没有草稿"
          description="填写标题和正文后保存，系统会创建首个版本。"
        />
      ) : null}

      <div className="mt-4 space-y-4">
        <label className="block space-y-2">
          <span className="label-text">标题</span>
          <input className="ink-input" value={title} onChange={(event) => setTitle(event.target.value)} />
        </label>
        <label className="block space-y-2">
          <span className="label-text">变更说明</span>
          <input
            className="ink-input"
            value={changeSummary}
            onChange={(event) => setChangeSummary(event.target.value)}
          />
        </label>
        <label className="block space-y-2">
          <span className="label-text">正文</span>
          <textarea
            className="ink-textarea min-h-[360px]"
            value={contentText}
            onChange={(event) => setContentText(event.target.value)}
          />
        </label>
        {feedback ? (
          <div className="rounded-2xl bg-[rgba(58,124,165,0.1)] px-4 py-3 text-sm text-[var(--accent-info)]">
            {feedback}
          </div>
        ) : null}
        {lastImpact ? <StoryAssetImpactPanel assetType={assetType} impact={lastImpact} /> : null}
      </div>
    </SectionCard>
  );
}
