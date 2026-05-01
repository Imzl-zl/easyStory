"use client";

import { useState } from "react";

import { CredentialDeleteConfirmDialog } from "@/features/settings/components/credential/credential-delete-confirm-dialog";
import type { PendingCredentialAction } from "@/features/settings/components/credential/credential-center-action-support";
import type { CredentialOverrideInfo } from "@/features/settings/components/credential/credential-center-override-support";

export type CredentialListItemData = {
  id: string;
  name: string;
  provider: string;
  dialect: string;
  model: string | null;
  isActive: boolean;
  isSelected: boolean;
  overrideInfo?: CredentialOverrideInfo;
  streamStatus: "ok" | "warning" | "error" | "unknown";
  bufferedStatus: "ok" | "warning" | "error" | "unknown";
};

type CredentialCenterListProps = {
  items: CredentialListItemData[];
  onSelect: (id: string) => void;
  onEdit: (id: string) => void;
  onAction: (type: PendingCredentialAction["type"], credentialId: string) => void;
  pendingAction: PendingCredentialAction | null;
  isPending: boolean;
};

export function CredentialCenterList({
  items,
  onSelect,
  onEdit,
  onAction,
  pendingAction,
  isPending,
}: CredentialCenterListProps) {
  const [pendingDelete, setPendingDelete] = useState<CredentialListItemData | null>(null);

  return (
    <>
      <div className="space-y-1.5">
        {items.map((item) => (
          <div
            key={item.id}
            className="flex items-center gap-3 px-4 py-3 rounded-lg cursor-pointer transition-all"
            onClick={() => onSelect(item.id)}
            style={{
              background: item.isSelected ? "var(--bg-muted)" : "transparent",
              border: item.isSelected ? "1px solid var(--line-medium)" : "1px solid transparent",
            }}
          >
            {/* Status */}
            <StatusDot status={item.isActive ? "active" : "inactive"} />

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-[13px] font-medium truncate" style={{ color: item.isActive ? "var(--text-primary)" : "var(--text-tertiary)" }}>
                  {item.name}
                </span>
                {item.overrideInfo && (
                  <span className="text-[9px] px-1 py-0.5 rounded flex-shrink-0" style={{ background: "var(--accent-primary-soft)", color: "var(--accent-primary)" }}>
                    覆盖
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="text-[10px]" style={{ color: "var(--text-tertiary)" }}>{item.provider}</span>
                <span style={{ color: "var(--text-tertiary)" }}>·</span>
                <span className="text-[10px] truncate" style={{ color: "var(--text-tertiary)" }}>{item.model ?? "无默认模型"}</span>
              </div>
            </div>

            {/* Status Indicators */}
            <div className="flex items-center gap-1.5">
              <StatusDot status={item.streamStatus} size="sm" title="流式链路" />
              <StatusDot status={item.bufferedStatus} size="sm" title="非流链路" />
            </div>

            {/* Actions */}
            <div className="flex items-center gap-1.5">
              <button
                className="px-2 py-1 rounded text-[10px] font-medium"
                style={{ background: "var(--bg-surface)", color: "var(--text-secondary)", border: "1px solid var(--line-medium)" }}
                onClick={(e) => { e.stopPropagation(); onEdit(item.id); }}
                disabled={isPending}
              >
                编辑
              </button>
              <button
                className="px-2 py-1 rounded text-[10px] font-medium"
                style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}
                onClick={(e) => { e.stopPropagation(); setPendingDelete(item); }}
                disabled={isPending}
              >
                删除
              </button>
            </div>
          </div>
        ))}
      </div>

      {pendingDelete && (
        <CredentialDeleteConfirmDialog
          credential={{ id: pendingDelete.id, display_name: pendingDelete.name, provider: pendingDelete.provider } as any}
          onClose={() => setPendingDelete(null)}
          onConfirm={() => { onAction("delete", pendingDelete.id); setPendingDelete(null); }}
        />
      )}
    </>
  );
}

function StatusDot({ status, size = "md", title }: { status: string; size?: "sm" | "md"; title?: string }) {
  const colors: Record<string, string> = {
    active: "var(--accent-success)",
    inactive: "var(--text-tertiary)",
    ok: "var(--accent-success)",
    warning: "var(--accent-warning)",
    error: "var(--accent-danger)",
    unknown: "var(--text-tertiary)",
  };
  const color = colors[status] || "var(--text-tertiary)";
  const dim = status === "inactive" || status === "unknown";

  return (
    <span
      className={size === "sm" ? "w-1.5 h-1.5" : "w-2 h-2"}
      style={{
        background: color,
        borderRadius: "50%",
        boxShadow: !dim ? `0 0 ${size === "sm" ? "4px" : "6px"} ${color}40` : "none",
        display: "inline-block",
        flexShrink: 0,
      }}
      title={title}
    />
  );
}
