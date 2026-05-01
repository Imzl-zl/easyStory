export type StudioChatLayoutMode = "default" | "compact" | "icon";

export const STUDIO_DESKTOP_BREAKPOINT = 1024;
export const STUDIO_XL_BREAKPOINT = 1280;
export const STUDIO_CHAT_RESIZE_STEP = 24;
export const STUDIO_CHAT_COMPACT_LAYOUT_WIDTH = 420;
export const STUDIO_CHAT_ICON_LAYOUT_WIDTH = 360;
export const STUDIO_LEFT_COLLAPSED_WIDTH = 44;
export const STUDIO_LEFT_MIN_WIDTH = 180;
export const STUDIO_LEFT_MAX_WIDTH = 400;
export const STUDIO_LEFT_RESIZE_STEP = 24;

const STUDIO_CHAT_DEFAULT_LG_WIDTH = 360;
const STUDIO_CHAT_DEFAULT_XL_WIDTH = 376;
const STUDIO_CHAT_MIN_WIDTH = 280;
const STUDIO_CHAT_MAX_WIDTH = 720;
const STUDIO_EDITOR_MIN_WIDTH = 420;
const STUDIO_LEFT_PANEL_LG_WIDTH = 236;
const STUDIO_LEFT_PANEL_XL_WIDTH = 244;

export function isStudioDesktopLayout(containerWidth: number) {
  return containerWidth >= STUDIO_DESKTOP_BREAKPOINT;
}

export function resolveLeftPanelWidth(
  containerWidth: number,
  leftCollapsed: boolean,
  customLeftWidth?: number | null,
) {
  if (leftCollapsed) {
    return STUDIO_LEFT_COLLAPSED_WIDTH;
  }
  if (customLeftWidth != null) {
    return clampStudioLeftPanelWidth(customLeftWidth, containerWidth);
  }
  return containerWidth >= STUDIO_XL_BREAKPOINT
    ? STUDIO_LEFT_PANEL_XL_WIDTH
    : STUDIO_LEFT_PANEL_LG_WIDTH;
}

export function resolveStudioLeftPanelBounds(containerWidth: number) {
  const maxWidth = Math.max(
    STUDIO_LEFT_MIN_WIDTH,
    Math.min(STUDIO_LEFT_MAX_WIDTH, containerWidth - STUDIO_EDITOR_MIN_WIDTH),
  );
  return { max: maxWidth, min: STUDIO_LEFT_MIN_WIDTH };
}

export function clampStudioLeftPanelWidth(width: number, containerWidth: number) {
  const bounds = resolveStudioLeftPanelBounds(containerWidth);
  return Math.round(Math.min(bounds.max, Math.max(bounds.min, width)));
}

export function resolveStudioChatSidebarBounds(containerWidth: number, leftPanelWidth?: number) {
  const effectiveLeftWidth = leftPanelWidth ?? (containerWidth >= STUDIO_XL_BREAKPOINT
    ? STUDIO_LEFT_PANEL_XL_WIDTH
    : STUDIO_LEFT_PANEL_LG_WIDTH);
  const maxWidth = Math.max(
    STUDIO_CHAT_MIN_WIDTH,
    Math.min(STUDIO_CHAT_MAX_WIDTH, containerWidth - effectiveLeftWidth - STUDIO_EDITOR_MIN_WIDTH),
  );
  return { max: maxWidth, min: STUDIO_CHAT_MIN_WIDTH };
}

export function clampStudioChatSidebarWidth(width: number, containerWidth: number, leftPanelWidth?: number) {
  const bounds = resolveStudioChatSidebarBounds(containerWidth, leftPanelWidth);
  return Math.round(Math.min(bounds.max, Math.max(bounds.min, width)));
}

export function resolveDefaultStudioChatSidebarWidth(containerWidth: number) {
  const preferredWidth = containerWidth >= STUDIO_XL_BREAKPOINT
    ? STUDIO_CHAT_DEFAULT_XL_WIDTH
    : STUDIO_CHAT_DEFAULT_LG_WIDTH;
  return clampStudioChatSidebarWidth(preferredWidth, containerWidth);
}

export function buildStudioChatGridTemplateColumns(options: {
  chatOpen: boolean;
  chatWidth: number | null;
  containerWidth: number;
  customLeftWidth?: number | null;
  leftCollapsed?: boolean;
}) {
  if (!options.chatOpen || options.chatWidth === null || !isStudioDesktopLayout(options.containerWidth)) {
    return null;
  }
  const leftPanelWidth = resolveLeftPanelWidth(
    options.containerWidth,
    options.leftCollapsed ?? false,
    options.customLeftWidth,
  );
  const chatWidth = clampStudioChatSidebarWidth(options.chatWidth, options.containerWidth, leftPanelWidth);
  return `${leftPanelWidth}px minmax(0, 1fr) ${chatWidth}px`;
}

export function buildStudioLeftPanelGridTemplateColumns(options: {
  chatOpen: boolean;
  chatWidth: number | null;
  containerWidth: number;
  leftCollapsed: boolean;
  customLeftWidth?: number | null;
}) {
  if (!isStudioDesktopLayout(options.containerWidth)) {
    return null;
  }
  const leftPanelWidth = resolveLeftPanelWidth(
    options.containerWidth,
    options.leftCollapsed,
    options.customLeftWidth,
  );
  if (!options.chatOpen || options.chatWidth === null) {
    return `${leftPanelWidth}px minmax(0, 1fr)`;
  }
  const chatWidth = clampStudioChatSidebarWidth(options.chatWidth, options.containerWidth, leftPanelWidth);
  return `${leftPanelWidth}px minmax(0, 1fr) ${chatWidth}px`;
}

export function resolveStudioChatLayoutMode(chatWidth: number): StudioChatLayoutMode {
  if (chatWidth > 0 && chatWidth <= STUDIO_CHAT_ICON_LAYOUT_WIDTH) {
    return "icon";
  }
  if (chatWidth > 0 && chatWidth <= STUDIO_CHAT_COMPACT_LAYOUT_WIDTH) {
    return "compact";
  }
  return "default";
}
