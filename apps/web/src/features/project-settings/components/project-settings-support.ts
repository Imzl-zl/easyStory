export type ProjectSettingsTab = "setting" | "audit";

const PROJECT_SETTINGS_TABS: ProjectSettingsTab[] = ["setting", "audit"];

export function resolveProjectSettingsTab(value: string | null): ProjectSettingsTab {
  return PROJECT_SETTINGS_TABS.includes(value as ProjectSettingsTab)
    ? (value as ProjectSettingsTab)
    : "setting";
}

export function isValidProjectSettingsTab(value: string | null): value is ProjectSettingsTab {
  return PROJECT_SETTINGS_TABS.includes(value as ProjectSettingsTab);
}

export function normalizeProjectAuditEventType(value: string | null): string | null {
  const normalized = value?.trim() ?? "";
  return normalized ? normalized : null;
}

export function buildProjectSettingsPathWithParams(
  pathname: string,
  currentSearch: string,
  patches: Record<string, string | null>,
): string {
  const next = new URLSearchParams(currentSearch);
  Object.entries(patches).forEach(([key, value]) => {
    if (value === null) {
      next.delete(key);
      return;
    }
    next.set(key, value);
  });
  const search = next.toString();
  return search ? `${pathname}?${search}` : pathname;
}
