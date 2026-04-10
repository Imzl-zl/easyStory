"use client";

import { useCallback, useEffect, useId, useRef, type RefObject } from "react";
import { cn } from "@/lib/utils/cn";

type ModalSize = "sm" | "md" | "lg";

type ModalProps = {
  children: React.ReactNode;
  description?: string;
  onClose: () => void;
  open: boolean;
  restoreFocusRef?: RefObject<HTMLElement | null>;
  size?: ModalSize;
  title: string;
};

const SIZE_MAP: Record<ModalSize, string> = {
  sm: "max-w-md",
  md: "max-w-2xl",
  lg: "max-w-5xl",
};

export function Modal({
  children,
  description,
  onClose,
  open,
  restoreFocusRef,
  size = "md",
  title,
}: ModalProps) {
  const titleId = useId();
  const descriptionId = useId();
  const containerRef = useRef<HTMLDivElement>(null);

  const handleDismiss = useCallback(() => {
    onClose();
  }, [onClose]);

  useEffect(() => {
    if (!open) return;

    const previousFocusedElement =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const container = containerRef.current;
    const previousOverflow = document.body.style.overflow;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        handleDismiss();
        return;
      }
      if (event.key !== "Tab") return;

      const focusableElements = resolveFocusableElements(container);
      if (focusableElements.length === 0) {
        event.preventDefault();
        container?.focus();
        return;
      }

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];
      if (event.shiftKey && document.activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
        return;
      }
      if (!event.shiftKey && document.activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    };

    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleKeyDown);
    queueMicrotask(() => {
      const firstFocusable = container?.querySelector<HTMLElement>(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled])',
      );
      firstFocusable?.focus();
    });

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
      const focusTarget = restoreFocusRef?.current ?? previousFocusedElement;
      focusTarget?.focus();
    };
  }, [open, handleDismiss, restoreFocusRef]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-modal flex items-center justify-center p-4 animate-overlay-in"
      role="presentation"
      onClick={handleDismiss}
    >
      <div className="absolute inset-0 bg-[rgba(45,35,25,0.18)] backdrop-blur-[2px]" />
      <div
        aria-describedby={description ? descriptionId : undefined}
        aria-labelledby={titleId}
        aria-modal="true"
        className={cn(
          "relative w-full animate-modal-in",
          SIZE_MAP[size],
          "bg-glass-heavy border border-line-glass rounded-2xl",
          "shadow-float backdrop-blur-xl",
          "max-h-[88vh] overflow-hidden",
        )}
        ref={containerRef}
        role="dialog"
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="flex flex-wrap items-start justify-between gap-4 border-b border-line-soft px-6 py-5">
          <div className="space-y-1">
            <h2
              className="text-xl font-semibold text-text-primary tracking-[-0.03em]"
              id={titleId}
            >
              {title}
            </h2>
            {description ? (
              <p
                className="max-w-3xl text-sm leading-6 text-text-secondary"
                id={descriptionId}
              >
                {description}
              </p>
            ) : null}
          </div>
          <button
            aria-label="关闭对话框"
            className="inline-flex items-center justify-center w-8 h-8 rounded-lg text-text-tertiary hover:bg-surface-hover hover:text-text-primary transition-colors duration-fast cursor-pointer"
            onClick={handleDismiss}
            type="button"
          >
            <svg fill="none" height="16" viewBox="0 0 16 16" width="16" xmlns="http://www.w3.org/2000/svg">
              <path d="M4 4L12 12M12 4L4 12" stroke="currentColor" strokeLinecap="round" strokeWidth="1.5" />
            </svg>
          </button>
        </header>
        <div className="max-h-[calc(88vh-88px)] overflow-y-auto px-6 py-6">
          {children}
        </div>
      </div>
    </div>
  );
}

function resolveFocusableElements(container: HTMLDivElement | null): HTMLElement[] {
  if (!container) return [];
  return Array.from(
    container.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  );
}
