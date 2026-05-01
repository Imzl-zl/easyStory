import { useCallback, useRef, useState } from "react";

import {
  clampStudioChatSidebarWidth,
  clampStudioLeftPanelWidth,
  isStudioDesktopLayout,
  resolveDefaultStudioChatSidebarWidth,
  resolveLeftPanelWidth,
  resolveStudioChatSidebarBounds,
  resolveStudioLeftPanelBounds,
  STUDIO_CHAT_RESIZE_STEP,
  STUDIO_LEFT_RESIZE_STEP,
} from "./studio-layout";

type PanelResizeConfig = {
  canResize: () => boolean;
  clampWidth: (width: number, containerWidth: number) => number;
  currentWidth: () => number;
  growKey: "ArrowRight" | "ArrowLeft";
  resizeStep: number;
  resolveBounds: (containerWidth: number) => { max: number; min: number };
  resolveWidthFromPointer: (clientX: number, gridRect: DOMRect) => number;
};

type PanelResizeCallbacks = {
  onDragEnd: (width: number) => void;
  onDragMove: (width: number) => void;
  onDragStart: (width: number) => void;
};

export function useStudioPanelResize(
  config: PanelResizeConfig,
  callbacks: PanelResizeCallbacks,
  containerWidth: number,
  gridRef: React.RefObject<HTMLElement | null>,
) {
  const [dragWidth, setDragWidth] = useState<number | null>(null);
  const pointerIdRef = useRef<number | null>(null);

  const handlePointerDown = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    if (!config.canResize() || !isStudioDesktopLayout(containerWidth)) {
      return;
    }
    const gridElement = gridRef.current;
    if (!gridElement) {
      return;
    }
    event.preventDefault();
    const pointerId = event.pointerId;
    pointerIdRef.current = pointerId;
    const startWidth = config.currentWidth();
    const previousCursor = document.body.style.cursor;
    const previousUserSelect = document.body.style.userSelect;

    const resolveWidth = (clientX: number) => {
      const rect = gridElement.getBoundingClientRect();
      return config.clampWidth(config.resolveWidthFromPointer(clientX, rect), rect.width);
    };

    const cleanup = () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      window.removeEventListener("pointercancel", handlePointerCancel);
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousUserSelect;
      pointerIdRef.current = null;
    };

    const handlePointerMove = (moveEvent: PointerEvent) => {
      if (moveEvent.pointerId !== pointerId) {
        return;
      }
      const nextWidth = resolveWidth(moveEvent.clientX);
      setDragWidth(nextWidth);
      callbacks.onDragMove(nextWidth);
    };

    const handlePointerUp = (upEvent: PointerEvent) => {
      if (upEvent.pointerId !== pointerId) {
        return;
      }
      cleanup();
      const finalWidth = resolveWidth(upEvent.clientX);
      setDragWidth(null);
      callbacks.onDragEnd(finalWidth);
    };

    const handlePointerCancel = (cancelEvent: PointerEvent) => {
      if (cancelEvent.pointerId !== pointerId) {
        return;
      }
      cleanup();
      setDragWidth(null);
    };

    setDragWidth(startWidth);
    callbacks.onDragStart(startWidth);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    window.addEventListener("pointercancel", handlePointerCancel);
  }, [callbacks, config, containerWidth, gridRef]);

  const handleKeyDown = useCallback((event: React.KeyboardEvent<HTMLDivElement>) => {
    if (!config.canResize() || !isStudioDesktopLayout(containerWidth) || containerWidth <= 0) {
      return;
    }
    const currentWidth = config.currentWidth();
    const bounds = config.resolveBounds(containerWidth);

    let nextWidth: number | null = null;
    if (event.key === config.growKey) {
      nextWidth = config.clampWidth(currentWidth + config.resizeStep, containerWidth);
    } else if (event.key === (config.growKey === "ArrowRight" ? "ArrowLeft" : "ArrowRight")) {
      nextWidth = config.clampWidth(currentWidth - config.resizeStep, containerWidth);
    } else if (event.key === "Home") {
      nextWidth = bounds.min;
    } else if (event.key === "End") {
      nextWidth = bounds.max;
    }

    if (nextWidth === null) {
      return;
    }
    event.preventDefault();
    callbacks.onDragEnd(nextWidth);
  }, [callbacks, config, containerWidth]);

  const resetDrag = useCallback(() => {
    setDragWidth(null);
    if (pointerIdRef.current !== null) {
      pointerIdRef.current = null;
    }
  }, []);

  return { dragWidth, handleKeyDown, handlePointerDown, resetDrag };
}

export function useChatPanelResize(options: {
  chatOpen: boolean;
  leftCollapsed: boolean;
  effectiveLeftWidth: number | null;
  resolvedDesktopChatWidth: number | null;
  projectId: string;
  setStoredChatWidth: (projectId: string, width: number | null) => void;
  studioGridWidth: number;
  gridRef: React.RefObject<HTMLElement | null>;
}) {
  const leftWidth = resolveLeftPanelWidth(options.studioGridWidth, options.leftCollapsed, options.effectiveLeftWidth);
  return useStudioPanelResize(
    {
      canResize: () => options.chatOpen,
      clampWidth: (width, containerWidth) => clampStudioChatSidebarWidth(width, containerWidth, leftWidth),
      currentWidth: () => options.resolvedDesktopChatWidth ?? resolveDefaultStudioChatSidebarWidth(options.studioGridWidth),
      growKey: "ArrowLeft",
      resizeStep: STUDIO_CHAT_RESIZE_STEP,
      resolveBounds: (containerWidth) => resolveStudioChatSidebarBounds(containerWidth, leftWidth),
      resolveWidthFromPointer: (clientX, gridRect) => gridRect.right - clientX,
    },
    {
      onDragEnd: (width) => options.setStoredChatWidth(options.projectId, width),
      onDragMove: () => {},
      onDragStart: () => {},
    },
    options.studioGridWidth,
    options.gridRef,
  );
}

export function useLeftPanelResize(options: {
  leftCollapsed: boolean;
  effectiveLeftWidth: number | null;
  projectId: string;
  setStoredLeftWidth: (projectId: string, width: number | null) => void;
  studioGridWidth: number;
  gridRef: React.RefObject<HTMLElement | null>;
}) {
  return useStudioPanelResize(
    {
      canResize: () => !options.leftCollapsed,
      clampWidth: (width, containerWidth) => clampStudioLeftPanelWidth(width, containerWidth),
      currentWidth: () => resolveLeftPanelWidth(options.studioGridWidth, false, options.effectiveLeftWidth),
      growKey: "ArrowRight",
      resizeStep: STUDIO_LEFT_RESIZE_STEP,
      resolveBounds: resolveStudioLeftPanelBounds,
      resolveWidthFromPointer: (clientX, gridRect) => clientX - gridRect.left,
    },
    {
      onDragEnd: (width) => options.setStoredLeftWidth(options.projectId, width),
      onDragMove: () => {},
      onDragStart: () => {},
    },
    options.studioGridWidth,
    options.gridRef,
  );
}
