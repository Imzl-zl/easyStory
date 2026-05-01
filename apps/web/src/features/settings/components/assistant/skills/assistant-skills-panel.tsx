"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { showAppNotice } from "@/components/ui/app-notice";
import { getErrorMessage } from "@/lib/api/client";

import { AssistantSkillEditor } from "@/features/settings/components/assistant/skills/assistant-skill-editor";
import {
  buildAssistantSkillDetailQueryKey,
  buildAssistantSkillListQueryKey,
  buildAssistantSkillsPanelCopy,
  createAssistantSkill,
  deleteAssistantSkill,
  loadAssistantSkillDetail,
  loadAssistantSkills,
  type AssistantSkillsPanelCopy,
  updateAssistantSkill,
} from "@/features/settings/components/assistant/skills/assistant-skills-panel-support";
import {
  buildAssistantSkillPayload,
  buildAssistantSkillListDescription,
  type AssistantSkillDraft,
} from "@/features/settings/components/assistant/skills/assistant-skills-support";

type AssistantSkillsPanelProps = {
  onDirtyChange?: (isDirty: boolean) => void;
  projectId?: string;
  scope?: "project" | "user";
};

export function AssistantSkillsPanel({
  onDirtyChange,
  projectId,
  scope = "user",
}: Readonly<AssistantSkillsPanelProps>) {
  const copy = buildAssistantSkillsPanelCopy(scope);
  const queryClient = useQueryClient();
  const [editorOpen, setEditorOpen] = useState(false);
  const [editorMode, setEditorMode] = useState<"create" | "edit">("create");
  const [editorSkillId, setEditorSkillId] = useState<string | null>(null);
  const [editorDirty, setEditorDirty] = useState(false);

  const listQuery = useQuery({
    queryKey: buildAssistantSkillListQueryKey(scope, projectId),
    queryFn: () => loadAssistantSkills(scope, projectId),
  });

  const detailQuery = useQuery({
    queryKey: buildAssistantSkillDetailQueryKey(scope, projectId, editorSkillId),
    queryFn: () => loadAssistantSkillDetail(scope, projectId, editorSkillId ?? ""),
    enabled: editorMode === "edit" && Boolean(editorSkillId),
  });

  const orderedSkills = useMemo(() => listQuery.data ?? [], [listQuery.data]);
  const enabledCount = orderedSkills.filter((s) => s.enabled).length;

  const createMutation = useMutation({
    mutationFn: (draft: AssistantSkillDraft) =>
      createAssistantSkill(scope, projectId, buildAssistantSkillPayload(draft)),
    onSuccess: async (detail) => {
      showAppNotice({ title: copy.title, content: copy.createSuccess, tone: "success" });
      setEditorOpen(false);
      await queryClient.invalidateQueries({ queryKey: buildAssistantSkillListQueryKey(scope, projectId) });
    },
    onError: (error) => {
      showAppNotice({ title: copy.title, content: getErrorMessage(error), tone: "danger" });
    },
  });

  const updateMutation = useMutation({
    mutationFn: (draft: AssistantSkillDraft) =>
      updateAssistantSkill(scope, projectId, editorSkillId ?? "", buildAssistantSkillPayload(draft)),
    onSuccess: async () => {
      showAppNotice({ title: copy.title, content: copy.saveSuccess, tone: "success" });
      setEditorOpen(false);
      await queryClient.invalidateQueries({ queryKey: buildAssistantSkillListQueryKey(scope, projectId) });
    },
    onError: (error) => {
      showAppNotice({ title: copy.title, content: getErrorMessage(error), tone: "danger" });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (skillId: string) => deleteAssistantSkill(scope, projectId, skillId),
    onSuccess: async () => {
      showAppNotice({ title: copy.title, content: copy.deleteSuccess, tone: "success" });
      await queryClient.invalidateQueries({ queryKey: buildAssistantSkillListQueryKey(scope, projectId) });
    },
    onError: (error) => {
      showAppNotice({ title: copy.title, content: getErrorMessage(error), tone: "danger" });
    },
  });

  const isPending = createMutation.isPending || updateMutation.isPending || deleteMutation.isPending;

  useEffect(() => {
    onDirtyChange?.(editorDirty && editorOpen);
    return () => onDirtyChange?.(false);
  }, [editorDirty, editorOpen, onDirtyChange]);

  const handleCreate = () => {
    setEditorMode("create");
    setEditorSkillId(null);
    setEditorOpen(true);
  };

  const handleEdit = (skillId: string) => {
    setEditorMode("edit");
    setEditorSkillId(skillId);
    setEditorOpen(true);
  };

  const handleCloseEditor = () => {
    if (editorDirty) {
      showAppNotice({
        title: copy.title,
        content: copy.dirtyMessage,
        tone: "warning",
      });
      return;
    }
    setEditorOpen(false);
  };

  const selectedDetail = editorMode === "edit" && detailQuery.data ? detailQuery.data : null;

  return (
    <div className="h-full flex flex-col" style={{ background: "var(--bg-canvas)" }}>
      {/* Header */}
      <header className="px-6 pt-6 pb-4 flex-shrink-0" style={{ borderBottom: "1px solid var(--line-soft)" }}>
        <div className="flex items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: "var(--accent-primary)" }} />
              <span className="text-[10px] font-semibold tracking-[0.15em] uppercase" style={{ color: "var(--accent-primary)" }}>
                辅助能力
              </span>
            </div>
            <h1 className="text-[22px] font-semibold tracking-tight" style={{ color: "var(--text-primary)" }}>
              {copy.title}
            </h1>
            <div className="flex items-center gap-3 mt-2">
              <StatBadge label="已启用" value={enabledCount} color="var(--accent-success)" />
              <StatBadge label="总计" value={orderedSkills.length} />
            </div>
          </div>
          <button
            className="h-8 px-4 rounded-md text-[12px] font-medium flex items-center gap-1.5"
            style={{ background: "var(--accent-primary)", color: "var(--text-on-accent)" }}
            disabled={isPending}
            type="button"
            onClick={handleCreate}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <path d="M12 5v14M5 12h14" />
            </svg>
            新建 Skill
          </button>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 min-h-0 overflow-y-auto" style={{ scrollbarWidth: "thin", scrollbarColor: "var(--line-medium) transparent" }}>
        <div className="px-6 py-5">
          {listQuery.isLoading ? (
            <p className="text-[13px]" style={{ color: "var(--text-tertiary)" }}>{copy.listLoading}</p>
          ) : listQuery.error ? (
            <div className="rounded-md px-3.5 py-2.5 text-[13px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
              {getErrorMessage(listQuery.error)}
            </div>
          ) : orderedSkills.length === 0 ? (
            <EmptyState onCreate={handleCreate} />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {orderedSkills.map((skill) => (
                <SkillCard
                  key={skill.id}
                  description={buildAssistantSkillListDescription(skill)}
                  enabled={skill.enabled}
                  name={skill.name}
                  onDelete={() => deleteMutation.mutate(skill.id)}
                  onEdit={() => handleEdit(skill.id)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Editor Modal */}
      {editorOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "var(--overlay-bg)" }}>
          <div className="w-full max-w-[720px] max-h-[90vh] overflow-hidden rounded-lg flex flex-col" style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}>
            {/* Modal Header */}
            <div className="px-5 py-4 flex items-center justify-between flex-shrink-0" style={{ borderBottom: "1px solid var(--line-soft)" }}>
              <div>
                <h2 className="text-[14px] font-semibold" style={{ color: "var(--text-primary)" }}>
                  {editorMode === "create" ? "新建 Skill" : "编辑 Skill"}
                </h2>
                <p className="text-[11px] mt-0.5" style={{ color: "var(--text-tertiary)" }}>
                  {editorMode === "create" ? "创建一份新的 AI 辅助能力" : "修改这份 Skill 的内容和设置"}
                </p>
              </div>
              <button
                className="w-7 h-7 rounded-md flex items-center justify-center"
                style={{ background: "var(--bg-surface)", color: "var(--text-secondary)" }}
                onClick={handleCloseEditor}
                type="button"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M18 6 6 18M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto" style={{ scrollbarWidth: "thin", scrollbarColor: "var(--line-medium) transparent" }}>
              {editorMode === "edit" && detailQuery.isLoading ? (
                <div className="px-5 py-8 text-center">
                  <p className="text-[13px]" style={{ color: "var(--text-tertiary)" }}>{copy.detailLoading}</p>
                </div>
              ) : editorMode === "edit" && detailQuery.error ? (
                <div className="px-5 py-4">
                  <div className="rounded-md px-3.5 py-2.5 text-[13px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
                    {getErrorMessage(detailQuery.error)}
                  </div>
                </div>
              ) : (
                <AssistantSkillEditor
                  detail={selectedDetail}
                  isPending={isPending}
                  mode={editorMode}
                  onDelete={editorMode === "edit" ? () => {
                    if (editorSkillId) deleteMutation.mutate(editorSkillId);
                    setEditorOpen(false);
                  } : undefined}
                  onDirtyChange={setEditorDirty}
                  onSubmit={(draft) => {
                    if (editorMode === "create") {
                      createMutation.mutate(draft);
                    } else {
                      updateMutation.mutate(draft);
                    }
                  }}
                />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatBadge({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>{label}</span>
      <span className="text-[13px] font-semibold" style={{ color: color || "var(--text-primary)" }}>{value}</span>
    </div>
  );
}

function SkillCard({
  description,
  enabled,
  name,
  onDelete,
  onEdit,
}: {
  description: string;
  enabled: boolean;
  name: string;
  onDelete: () => void;
  onEdit: () => void;
}) {
  return (
    <div
      className="rounded-lg p-4 transition-colors hover:brightness-110"
      style={{
        background: "var(--bg-canvas)",
        border: "1px solid var(--line-soft)",
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span
            className="w-2 h-2 rounded-full flex-shrink-0"
            style={{
              background: enabled ? "var(--accent-success)" : "var(--text-tertiary)",
              boxShadow: enabled ? "0 0 6px #22c55e40" : "none",
            }}
          />
          <span className="text-[13px] font-medium truncate" style={{ color: "var(--text-primary)" }}>
            {name}
          </span>
        </div>
        <span
          className="text-[9px] px-1.5 py-0.5 rounded font-medium flex-shrink-0"
          style={{
            background: enabled ? "var(--accent-success-soft)" : "rgba(75,85,99,0.2)",
            color: enabled ? "var(--accent-success)" : "var(--text-tertiary)",
          }}
        >
          {enabled ? "启用" : "停用"}
        </span>
      </div>
      <p className="mt-2 text-[11px] leading-4 line-clamp-2" style={{ color: "var(--text-tertiary)" }}>
        {description}
      </p>
      <div className="flex gap-2 mt-3">
        <button
          className="h-7 px-3 rounded text-[11px] font-medium"
          style={{ background: "var(--bg-surface)", color: "var(--text-secondary)", border: "1px solid var(--line-medium)" }}
          onClick={onEdit}
          type="button"
        >
          编辑
        </button>
        <button
          className="h-7 px-3 rounded text-[11px] font-medium"
          style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}
          onClick={onDelete}
          type="button"
        >
          删除
        </button>
      </div>
    </div>
  );
}

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="w-12 h-12 rounded-full flex items-center justify-center mb-4" style={{ background: "var(--bg-muted)" }}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="1.5" strokeLinecap="round">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
        </svg>
      </div>
      <p className="text-[14px] font-medium" style={{ color: "var(--text-secondary)" }}>还没有 Skill</p>
      <p className="mt-1 text-[12px]" style={{ color: "var(--text-tertiary)" }}>创建你的第一个 AI 辅助能力</p>
      <button
        className="mt-4 h-8 px-4 rounded-md text-[12px] font-medium"
        style={{ background: "var(--accent-primary)", color: "var(--text-on-accent)" }}
        onClick={onCreate}
        type="button"
      >
        新建 Skill
      </button>
    </div>
  );
}
