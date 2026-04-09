"use client";

import type { ReactNode } from "react";

import { EmptyState } from "@/components/ui/empty-state";
import { IncubatorPreview } from "@/features/lobby/components/incubator/incubator-preview";
import {
  buildTemplatePreviewEmptyMessage,
} from "@/features/lobby/components/incubator/incubator-page-support";
import { RequestStateCard } from "@/features/lobby/components/common/request-state";
import { getErrorMessage } from "@/lib/api/client";

import {
  TemplateControlCard,
  TemplateQuestionsCard,
} from "@/features/lobby/components/incubator/incubator-panels-support";
import type { IncubatorTemplateModel } from "@/features/lobby/components/incubator/incubator-template-model";

type TemplateModePanelProps = {
  model: IncubatorTemplateModel;
  onSwitchToChat: () => void;
};

export function TemplateModePanel({
  model,
  onSwitchToChat,
}: TemplateModePanelProps) {
  const guard = renderTemplateModeGuard(model, onSwitchToChat);
  if (guard) {
    return guard;
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[0.84fr_1.16fr]">
      <div className="space-y-4">
        <TemplateControlCard model={model} />
        <TemplateQuestionsCard model={model} />
      </div>
      <IncubatorPreview
        title="项目草稿"
        description="根据填写内容生成项目草稿。"
        emptyMessage={buildPreviewEmptyMessage(model)}
        completeness={model.draftMutation.data?.setting_completeness}
        setting={model.draftMutation.data?.project_setting}
        appliedAnswers={model.draftMutation.data?.applied_answers}
        staleMessage={model.isDraftStale ? "你刚修改了回答，请先重新整理草稿。" : null}
        unmappedAnswers={model.draftMutation.data?.unmapped_answers}
      />
    </div>
  );
}

function renderTemplateModeGuard(
  model: IncubatorTemplateModel,
  onSwitchToChat: () => void,
): ReactNode | null {
  if (model.templatesQuery.isLoading) {
    return (
      <div className="panel-muted px-4 py-5 text-sm text-[var(--text-secondary)]">
        正在加载模板列表…
      </div>
    );
  }
  if (model.templatesQuery.error) {
    return (
      <RequestStateCard
        actions={renderTemplateListErrorActions(model, onSwitchToChat)}
        message={getErrorMessage(model.templatesQuery.error)}
        title="模板列表加载失败"
      />
    );
  }
  if ((model.templatesQuery.data?.length ?? 0) === 0) {
    return (
      <EmptyState
        title="当前没有模板"
        description="当前没有可用模板，请使用 AI 聊天。"
        action={
          <button className="ink-button-secondary" onClick={onSwitchToChat} type="button">
            使用 AI 聊天
          </button>
        }
      />
    );
  }
  return null;
}

function renderTemplateListErrorActions(
  model: IncubatorTemplateModel,
  onSwitchToChat: () => void,
) {
  return (
    <>
      <button
        className="ink-button-secondary"
        onClick={() => void model.templatesQuery.refetch()}
        type="button"
      >
        重试模板列表
      </button>
      <button className="ink-button-secondary" onClick={onSwitchToChat} type="button">
        使用 AI 聊天
      </button>
    </>
  );
}

function buildPreviewEmptyMessage(model: IncubatorTemplateModel) {
  return buildTemplatePreviewEmptyMessage({
    hasSelectedTemplate: model.selectedTemplateId.length > 0,
    isTemplateDetailLoading:
      model.selectedTemplateId.length > 0 && model.templateDetailQuery.isLoading,
    templateDetailError: model.templateDetailQuery.error
      ? getErrorMessage(model.templateDetailQuery.error)
      : null,
  });
}
