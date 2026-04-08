"use client";

import { createPortal } from "react-dom";
import { useEffect, useState } from "react";
import type { CSSProperties, ReactNode, RefObject } from "react";

const FLOATING_PANEL_VIEWPORT_MARGIN = 16;
const FLOATING_PANEL_GAP = 8;

type FloatingPanelOptions = {
  align: "left" | "right";
  maxHeight: number;
  preferredWidth: number;
};

export function useFloatingPanelStyle(
  open: boolean,
  anchorRef: RefObject<HTMLElement | null>,
  options: Readonly<FloatingPanelOptions>,
) {
  const [style, setStyle] = useState<CSSProperties>();

  useEffect(() => {
    if (!open) {
      return;
    }

    function updateStyle() {
      const anchor = anchorRef.current;
      if (!anchor) {
        return;
      }
      const rect = anchor.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      const width = Math.min(
        options.preferredWidth,
        viewportWidth - FLOATING_PANEL_VIEWPORT_MARGIN * 2,
      );
      const left = options.align === "right"
        ? clamp(
          rect.right - width,
          FLOATING_PANEL_VIEWPORT_MARGIN,
          viewportWidth - width - FLOATING_PANEL_VIEWPORT_MARGIN,
        )
        : clamp(
          rect.left,
          FLOATING_PANEL_VIEWPORT_MARGIN,
          viewportWidth - width - FLOATING_PANEL_VIEWPORT_MARGIN,
        );

      setStyle({
        position: "fixed",
        zIndex: 70,
        left,
        bottom: viewportHeight - rect.top + FLOATING_PANEL_GAP,
        width,
        maxHeight: Math.min(
          options.maxHeight,
          Math.max(180, rect.top - FLOATING_PANEL_VIEWPORT_MARGIN - FLOATING_PANEL_GAP),
        ),
      });
    }

    updateStyle();
    window.addEventListener("resize", updateStyle);
    window.addEventListener("scroll", updateStyle, true);
    return () => {
      window.removeEventListener("resize", updateStyle);
      window.removeEventListener("scroll", updateStyle, true);
    };
  }, [anchorRef, open, options.align, options.maxHeight, options.preferredWidth]);

  return style;
}

export function renderStudioFloatingPanel(panel: ReactNode) {
  if (typeof document === "undefined") {
    return null;
  }
  return createPortal(panel, document.body);
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}
