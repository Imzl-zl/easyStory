"use client";

import type {
  CredentialCenterMode,
  CredentialCenterScope,
} from "@/features/settings/components/credential/credential-center-support";

export function CredentialScopeTabs({
  canUseProjectScope,
  isPending,
  projectId,
  scope,
  onScopeChange,
}: {
  canUseProjectScope: boolean;
  isPending: boolean;
  projectId: string | null;
  scope: CredentialCenterScope;
  onScopeChange?: (scope: CredentialCenterScope) => void;
}) {
  return (
    <div className="flex gap-0.5">
      {[
        { value: "user" as const, label: "全局" },
        { value: "project" as const, label: "项目" },
      ].map((item) => (
        <button
          key={item.value}
          className="px-3 py-1.5 rounded-md text-[11px] font-medium transition-all"
          data-active={scope === item.value}
          disabled={item.value === "project" && !canUseProjectScope || isPending}
          onClick={() => onScopeChange?.(item.value)}
          style={{
            background: scope === item.value ? "var(--bg-elevated)" : "transparent",
            color: scope === item.value ? "var(--text-primary)" : "var(--text-tertiary)",
          }}
          type="button"
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

export function CredentialModeTabs({
  isPending = false,
  mode,
  onModeChange,
}: {
  isPending?: boolean;
  mode: CredentialCenterMode;
  onModeChange?: (mode: CredentialCenterMode) => void;
}) {
  return (
    <div className="flex gap-0.5">
      {[
        { value: "list" as const, label: "列表" },
        { value: "audit" as const, label: "审计" },
      ].map((item) => (
        <button
          key={item.value}
          className="px-3 py-1.5 rounded-md text-[11px] font-medium transition-all"
          data-active={mode === item.value}
          disabled={isPending}
          onClick={() => onModeChange?.(item.value)}
          style={{
            background: mode === item.value ? "var(--bg-elevated)" : "transparent",
            color: mode === item.value ? "var(--text-primary)" : "var(--text-tertiary)",
          }}
          type="button"
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
