"use client";

import { createPortal } from "react-dom";
import { useEffect, useState } from "react";
import type { CSSProperties, ReactNode, RefObject } from "react";

const FLOATING_PANEL_VIEWPORT_MARGIN = 16;
const FLOATING_PANEL_GAP = 8;
const FLOATING_PANEL_MIN_HEIGHT = 160;

type FloatingPanelSide = "top" | "bottom";

type FloatingPanelOptions = {
  align: "left" | "right";
  maxHeight: number;
  preferredWidth: number;
  side: FloatingPanelSide;
  zIndex?: number;
};

type FloatingPanelRect = {
  bottom: number;
  left: number;
  right: number;
  top: number;
};

type FloatingPanelViewport = {
  height: number;
  width: number;
};

export function useFloatingPanelStyle(
  open: boolean,
  anchorRef: RefObject<HTMLElement | null>,
  options: Readonly<FloatingPanelOptions>,
) {
  const [style, setStyle] = useState<CSSProperties>();
  const { align, maxHeight, preferredWidth, side, zIndex } = options;

  useEffect(() => {
    if (!open) {
      return;
    }

    function updateStyle() {
      const anchor = anchorRef.current;
      if (!anchor) {
        return;
      }
      setStyle(
        resolveFloatingPanelStyle(
          anchor.getBoundingClientRect(),
          {
            height: window.innerHeight,
            width: window.innerWidth,
          },
          {
            align,
            maxHeight,
            preferredWidth,
            side,
            zIndex,
          },
        ),
      );
    }

    updateStyle();
    const cleanupLayoutObserver = observeFloatingPanelLayoutChanges(anchorRef.current, updateStyle);
    return () => {
      cleanupLayoutObserver();
    };
  }, [
    anchorRef,
    open,
    align,
    maxHeight,
    preferredWidth,
    side,
    zIndex,
  ]);

  return style;
}

export function resolveFloatingPanelStyle(
  rect: Readonly<FloatingPanelRect>,
  viewport: Readonly<FloatingPanelViewport>,
  options: Readonly<FloatingPanelOptions>,
): CSSProperties {
  const width = Math.min(
    options.preferredWidth,
    viewport.width - FLOATING_PANEL_VIEWPORT_MARGIN * 2,
  );
  const left = options.align === "right"
    ? clamp(
      rect.right - width,
      FLOATING_PANEL_VIEWPORT_MARGIN,
      viewport.width - width - FLOATING_PANEL_VIEWPORT_MARGIN,
    )
    : clamp(
      rect.left,
      FLOATING_PANEL_VIEWPORT_MARGIN,
      viewport.width - width - FLOATING_PANEL_VIEWPORT_MARGIN,
    );

  return options.side === "top"
    ? {
      bottom: viewport.height - rect.top + FLOATING_PANEL_GAP,
      left,
      maxHeight: resolveFloatingPanelMaxHeight(rect.top, viewport.height, options.maxHeight),
      position: "fixed",
      width,
      zIndex: options.zIndex ?? 70,
    }
    : {
      left,
      maxHeight: resolveFloatingPanelMaxHeight(
        viewport.height - rect.bottom,
        viewport.height,
        options.maxHeight,
      ),
      position: "fixed",
      top: rect.bottom + FLOATING_PANEL_GAP,
      width,
      zIndex: options.zIndex ?? 70,
    };
}

export function renderFloatingPanel(panel: ReactNode) {
  if (typeof document === "undefined") {
    return null;
  }
  return createPortal(panel, document.body);
}

export function observeFloatingPanelLayoutChanges(
  anchor: HTMLElement | null,
  onLayoutChange: () => void,
) {
  window.addEventListener("resize", onLayoutChange);
  window.addEventListener("scroll", onLayoutChange, true);

  if (typeof ResizeObserver === "undefined") {
    return () => {
      window.removeEventListener("resize", onLayoutChange);
      window.removeEventListener("scroll", onLayoutChange, true);
    };
  }

  const observer = new ResizeObserver(() => onLayoutChange());
  const observedTargets = new Set<HTMLElement>();

  const observe = (target: HTMLElement | null) => {
    if (!target || observedTargets.has(target)) {
      return;
    }
    observedTargets.add(target);
    observer.observe(target);
  };

  observe(anchor);
  observe(anchor?.parentElement ?? null);
  observe(anchor?.closest("aside") ?? null);
  observe(anchor?.closest("section") ?? null);
  observe(anchor?.closest("main") ?? null);

  return () => {
    observer.disconnect();
    window.removeEventListener("resize", onLayoutChange);
    window.removeEventListener("scroll", onLayoutChange, true);
  };
}

function resolveFloatingPanelMaxHeight(
  availableHeight: number,
  viewportHeight: number,
  requestedMaxHeight: number,
) {
  const maxViewportHeight = Math.max(
    FLOATING_PANEL_MIN_HEIGHT,
    viewportHeight - FLOATING_PANEL_VIEWPORT_MARGIN * 2,
  );
  return Math.min(
    requestedMaxHeight,
    maxViewportHeight,
    Math.max(FLOATING_PANEL_MIN_HEIGHT, availableHeight - FLOATING_PANEL_VIEWPORT_MARGIN - FLOATING_PANEL_GAP),
  );
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}
