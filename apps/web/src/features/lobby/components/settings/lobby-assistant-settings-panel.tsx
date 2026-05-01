"use client";

import { useQuery } from "@tanstack/react-query";

import { getMyAssistantPreferences, getMyAssistantRules } from "@/lib/api/assistant";
import { listCredentials } from "@/lib/api/credential";

import { AssistantPreferencesPanel } from "@/features/settings/components/assistant/preferences/assistant-preferences-panel";
import { AssistantRulesEditor } from "@/features/settings/components/assistant/rules/assistant-rules-editor";

type LobbyAssistantSettingsPanelProps = {
  onAssistantPreferencesDirtyChange: (isDirty: boolean) => void;
  onAssistantRulesDirtyChange: (isDirty: boolean) => void;
};

export function LobbyAssistantSettingsPanel({
  onAssistantPreferencesDirtyChange,
  onAssistantRulesDirtyChange,
}: Readonly<LobbyAssistantSettingsPanelProps>) {
  const credentialsQuery = useQuery({
    queryKey: ["credentials", "user"],
    queryFn: () => listCredentials("user"),
  });
  const rulesQuery = useQuery({
    queryKey: ["assistant-rules", "user", null],
    queryFn: () => getMyAssistantRules(),
  });

  const activeCredentials = credentialsQuery.data?.filter((c) => c.is_active).length ?? 0;
  const totalCredentials = credentialsQuery.data?.length ?? 0;
  const rulesEnabled = rulesQuery.data?.enabled ?? false;
  const rulesContentLength = rulesQuery.data?.content?.length ?? 0;

  return (
    <div
      className="h-full overflow-y-auto"
      style={{
        scrollbarWidth: "thin",
        scrollbarColor: "var(--line-medium) transparent",
      }}
    >
      {/* Header */}
      <header
        className="px-6 pt-6 pb-4 flex-shrink-0"
        style={{ borderBottom: "1px solid var(--line-soft)" }}
      >
        <div className="flex items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: "var(--accent-primary)" }} />
              <span
                className="text-[10px] font-semibold tracking-[0.15em] uppercase"
                style={{ color: "var(--accent-primary)" }}
              >
                默认协作方式
              </span>
            </div>
            <h1
              className="text-[22px] font-semibold tracking-tight"
              style={{ color: "var(--text-primary)" }}
            >
              AI 助手设置
            </h1>
            <div className="flex items-center gap-3 mt-2">
              <StatBadge
                label="可用连接"
                value={`${activeCredentials}/${totalCredentials}`}
                color={activeCredentials > 0 ? "var(--accent-success)" : "var(--text-tertiary)"}
              />
              <StatBadge
                label="长期规则"
                value={rulesEnabled ? `${rulesContentLength} 字` : "未启用"}
                color={rulesEnabled ? "var(--accent-primary)" : "var(--text-tertiary)"}
              />
            </div>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="px-6 py-5 max-w-[800px]">
        <div className="space-y-5">
          <AssistantPreferencesPanel
            onDirtyChange={onAssistantPreferencesDirtyChange}
          />
          <AssistantRulesEditor
            onDirtyChange={onAssistantRulesDirtyChange}
            scope="user"
            title="长期规则"
          />
        </div>
      </div>
    </div>
  );
}

function StatBadge({
  label,
  value,
  color,
}: {
  label: string;
  value: string | number;
  color?: string;
}) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>{label}</span>
      <span className="text-[13px] font-semibold" style={{ color: color || "var(--text-primary)" }}>
        {value}
      </span>
    </div>
  );
}
