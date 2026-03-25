"use client";

import { DialogShell } from "@/components/ui/dialog-shell";
import { StatusBadge } from "@/components/ui/status-badge";
import type { AnalysisType } from "@/lib/api/types";

type LabDeleteConfirmDialogProps = {
  analysisTitle: string;
  analysisType: AnalysisType;
  generatedSkillKey: string | null;
  isPending: boolean;
  onClose: () => void;
  onConfirm: () => void;
};

export function LabDeleteConfirmDialog({
  analysisTitle,
  analysisType,
  generatedSkillKey,
  isPending,
  onClose,
  onConfirm,
}: Readonly<LabDeleteConfirmDialogProps>) {
  return (
    <DialogShell
      title="确认删除分析记录"
      description="删除后该记录将从列表中移除。"
      onClose={onClose}
    >
      <div className="space-y-4">
        <div className="space-y-3 rounded-[20px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.56)] p-4">
          <div className="flex flex-wrap gap-2">
            <StatusBadge status="failed" label="删除确认" />
            <StatusBadge status="active" label={analysisType} />
            {generatedSkillKey ? <StatusBadge status="approved" label={generatedSkillKey} /> : null}
          </div>
          <p className="text-base font-medium text-[var(--text-primary)]">{analysisTitle}</p>
          <p className="text-sm leading-6 text-[var(--text-secondary)]">
            删除后列表会回退到下一条可用记录；若当前过滤条件下不再有结果，详情区会显式回到空态。
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button className="ink-button-danger" disabled={isPending} onClick={onConfirm} type="button">
            {isPending ? "删除中..." : "确认删除"}
          </button>
          <button className="ink-button-secondary" disabled={isPending} onClick={onClose} type="button">
            先保留
          </button>
        </div>
      </div>
    </DialogShell>
  );
}
