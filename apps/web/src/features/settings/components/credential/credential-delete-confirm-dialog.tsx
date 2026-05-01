"use client";

import type { CredentialView } from "@/lib/api/types";

type CredentialDeleteConfirmDialogProps = {
  credential: CredentialView;
  onClose: () => void;
  onConfirm: () => void;
};

export function CredentialDeleteConfirmDialog({
  credential,
  onClose,
  onConfirm,
}: Readonly<CredentialDeleteConfirmDialogProps>) {
  const scopeLabel = credential.owner_type === "project" ? "项目级" : "全局";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "rgba(0,0,0,0.6)" }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-[420px] rounded-lg overflow-hidden"
        style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}
        onClick={(event) => event.stopPropagation()}
      >
        {/* Header */}
        <div className="px-5 py-4" style={{ borderBottom: "1px solid var(--line-soft)" }}>
          <h2 className="text-[14px] font-semibold" style={{ color: "var(--text-primary)" }}>
            确认删除{scopeLabel}连接
          </h2>
          <p className="text-[11px] mt-0.5" style={{ color: "var(--text-tertiary)" }}>
            删除后无法恢复，请谨慎操作
          </p>
        </div>

        {/* Content */}
        <div className="px-5 py-4 space-y-3">
          <div
            className="rounded-md px-3 py-2.5"
            style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}
          >
            <p className="text-[12px] font-medium" style={{ color: "var(--text-primary)" }}>
              {credential.display_name}
            </p>
            <p className="text-[11px] mt-0.5" style={{ color: "var(--text-tertiary)" }}>
              {credential.provider} · {credential.is_active ? "启用中" : "已停用"}
            </p>
          </div>

          <div className="rounded-md px-3 py-2.5 text-[11px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
            删除后，引用这条连接的模型调用可能会直接失败。如果已产生用量历史，后端会拒绝删除。
          </div>
        </div>

        {/* Actions */}
        <div className="px-5 py-4 flex gap-2" style={{ borderTop: "1px solid var(--line-soft)" }}>
          <button
            className="h-8 px-4 rounded-md text-[12px] font-medium"
            style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}
            onClick={onConfirm}
            type="button"
          >
            确认删除
          </button>
          <button
            className="h-8 px-4 rounded-md text-[12px] font-medium"
            style={{ background: "var(--line-soft)", color: "var(--text-secondary)", border: "1px solid var(--line-medium)" }}
            onClick={onClose}
            type="button"
          >
            取消
          </button>
        </div>
      </div>
    </div>
  );
}
