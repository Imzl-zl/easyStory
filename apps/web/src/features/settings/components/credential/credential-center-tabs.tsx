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
    <div className="flex flex-wrap gap-2">
      <button
        className="ink-tab"
        data-active={scope === "user"}
        disabled={isPending}
        onClick={() => onScopeChange?.("user")}
        type="button"
      >
        全局连接
      </button>
      <button
        className="ink-tab"
        data-active={scope === "project"}
        disabled={!canUseProjectScope || isPending}
        onClick={() => onScopeChange?.("project")}
        type="button"
      >
        当前项目连接
      </button>
      {!canUseProjectScope ? (
        <p className="text-sm text-text-secondary">当前没有项目上下文，只能管理全局连接。</p>
      ) : projectId ? (
        <p className="text-sm text-text-secondary">项目上下文：{projectId}</p>
      ) : null}
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
    <div className="flex flex-wrap gap-2">
      {[
        ["list", "连接列表"],
        ["audit", "审计日志"],
      ].map(([value, label]) => (
        <button
          key={value}
          className="ink-tab"
          data-active={mode === value}
          disabled={isPending}
          onClick={() => onModeChange?.(value as CredentialCenterMode)}
          type="button"
        >
          {label}
        </button>
      ))}
    </div>
  );
}
