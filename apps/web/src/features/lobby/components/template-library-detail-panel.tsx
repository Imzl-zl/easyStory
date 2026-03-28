"use client";

import { EmptyState } from "@/components/ui/empty-state";
import { CodeBlock } from "@/components/ui/code-block";
import { StatusBadge } from "@/components/ui/status-badge";
import { RequestStateCard } from "@/features/lobby/components/incubator-request-state";
import type { TemplateLibraryModel } from "@/features/lobby/components/template-library-model";
import {
  formatGuidedQuestionVariableLabel,
  formatTemplateTime,
} from "@/features/lobby/components/template-library-support";
import { getErrorMessage } from "@/lib/api/client";
import type { TemplateDetail } from "@/lib/api/types";

export function TemplateLibraryDetailPanel({ model }: { model: TemplateLibraryModel }) {
  if (model.detailQuery.isLoading) {
    return <section className="panel-shell min-h-0 p-5 text-sm text-[var(--text-secondary)]">正在读取模板详情…</section>;
  }
  if (model.detailQuery.error) {
    return (
      <RequestStateCard
        title="模板详情加载失败"
        message={getErrorMessage(model.detailQuery.error)}
        actions={
          <button className="ink-button-secondary" onClick={() => void model.detailQuery.refetch()} type="button">
            重试详情
          </button>
        }
      />
    );
  }
  if (!model.detailQuery.data) {
    return (
      <EmptyState
        title="选择模板"
        description="从左侧查看模板详情。"
      />
    );
  }
  return (
    <section className="panel-shell fan-panel flex min-h-0 flex-col gap-5 p-5">
      <DetailHeader model={model} template={model.detailQuery.data} />
      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto pr-1">
        <MetaGrid template={model.detailQuery.data} />
        <GuidedQuestionSection template={model.detailQuery.data} />
        <NodeSection template={model.detailQuery.data} />
        <div className="space-y-2">
          <h3 className="font-serif text-lg font-semibold">配置详情</h3>
          <CodeBlock value={model.detailQuery.data.config} />
        </div>
      </div>
    </section>
  );
}

function DetailHeader({
  template,
  model,
}: {
  template: TemplateDetail;
  model: TemplateLibraryModel;
}) {
  return (
    <header className="space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h2 className="font-serif text-2xl font-semibold">{template.name}</h2>
          <p className="text-sm leading-6 text-[var(--text-secondary)]">{template.description ?? "暂无说明。"}</p>
        </div>
        <StatusBadge
          status={template.is_builtin ? "approved" : "draft"}
          label={template.is_builtin ? "内置" : "自定义"}
        />
      </div>
      <div className="flex flex-wrap gap-2">
        <button className="ink-button-secondary" onClick={model.startDuplicate} type="button">创建副本</button>
        {!template.is_builtin ? <button className="ink-button-secondary" onClick={model.startEdit} type="button">编辑</button> : null}
        {!template.is_builtin ? <button className="ink-button-danger" disabled={model.isDeletePending} onClick={model.deleteActive} type="button">{model.isDeletePending ? "删除中…" : "删除模板"}</button> : null}
      </div>
    </header>
  );
}

function MetaGrid({ template }: { template: TemplateDetail }) {
  return (
    <dl className="grid gap-3 md:grid-cols-2">
      {[
        ["题材", template.genre ?? "未设定"],
        ["流程", template.workflow_id ?? "未设置"],
        ["问题数", String(template.guided_questions.length)],
        ["节点数", String(template.nodes.length)],
        ["创建时间", formatTemplateTime(template.created_at)],
        ["更新时间", formatTemplateTime(template.updated_at)],
      ].map(([label, value]) => (
        <div key={label} className="panel-muted space-y-1 p-4">
          <dt className="text-xs uppercase tracking-[0.18em] text-[var(--text-secondary)]">{label}</dt>
          <dd className="text-sm leading-6">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function GuidedQuestionSection({ template }: { template: TemplateDetail }) {
  if (template.guided_questions.length === 0) {
    return <p className="rounded-2xl bg-[rgba(255,255,255,0.52)] px-4 py-3 text-sm leading-6 text-[var(--text-secondary)]">当前模板未设置引导问题。</p>;
  }
  return (
    <div className="space-y-2">
      <h3 className="font-serif text-lg font-semibold">引导问题</h3>
      <div className="space-y-3">
        {template.guided_questions.map((question) => (
          <article key={question.variable} className="panel-muted space-y-1 p-4">
            <p className="text-xs tracking-[0.12em] text-[var(--text-secondary)]">
              {formatGuidedQuestionVariableLabel(question.variable)}
            </p>
            <p className="text-sm leading-6">{question.question}</p>
          </article>
        ))}
      </div>
    </div>
  );
}

function NodeSection({ template }: { template: TemplateDetail }) {
  return (
    <div className="space-y-3">
      <h3 className="font-serif text-lg font-semibold">流程步骤</h3>
      <div className="space-y-3">
        {template.nodes.map((node) => (
          <article key={node.id} className="panel-muted space-y-3 p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <p className="font-medium">{node.node_name ?? node.node_id ?? `节点 ${node.node_order + 1}`}</p>
                <p className="text-sm leading-6 text-[var(--text-secondary)]">
                  {node.node_type}
                  {" · "}
                  {node.skill_id ? `使用 ${node.skill_id}` : "暂未绑定技能"}
                </p>
              </div>
              <span className="text-xs uppercase tracking-[0.16em] text-[var(--text-secondary)]">#{node.node_order + 1}</span>
            </div>
            <CodeBlock value={node.config} />
          </article>
        ))}
      </div>
    </div>
  );
}
