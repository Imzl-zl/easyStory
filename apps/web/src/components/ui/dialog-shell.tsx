"use client";

import { useEffect, useEffectEvent, useId, useRef, type RefObject } from "react";

type DialogShellProps = {
  children: React.ReactNode;
  closeDisabled?: boolean;
  description?: string;
  onClose: () => void;
  restoreFocusRef?: RefObject<HTMLElement | null>;
  title: string;
};

export function DialogShell({
  title,
  closeDisabled = false,
  description,
  onClose,
  restoreFocusRef,
  children,
}: DialogShellProps) {
  const titleId = useId();
  const descriptionId = useId();
  const containerRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const dismiss = () => {
    if (closeDisabled) {
      return;
    }
    onClose();
  };
  const handleDismiss = useEffectEvent(() => {
    dismiss();
  });
  const resolveRestoreFocusTarget = useEffectEvent((fallbackTarget: HTMLElement | null) => {
    return restoreFocusRef?.current ?? fallbackTarget;
  });

  useEffect(() => {
    const previousFocusedElement =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const container = containerRef.current;
    const previousOverflow = document.body.style.overflow;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        handleDismiss();
        return;
      }
      if (event.key !== "Tab") {
        return;
      }

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
      closeButtonRef.current?.focus();
    });
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
      const focusTarget = resolveRestoreFocusTarget(previousFocusedElement);
      focusTarget?.focus();
    };
  }, []);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-[var(--overlay-bg)] backdrop-blur-[2px] p-4 md:items-center animate-overlay-in"
      role="presentation"
      onClick={dismiss}
    >
      <div
        aria-describedby={description ? descriptionId : undefined}
        aria-labelledby={titleId}
        aria-modal="true"
        className="bg-glass-heavy rounded-2xl shadow-float backdrop-blur-xl max-h-[88vh] w-full max-w-6xl overflow-hidden animate-modal-in"
        ref={containerRef}
        role="dialog"
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="flex flex-wrap items-start justify-between gap-4 border-b border-line-soft px-6 py-5">
          <div className="space-y-1">
            <h2 className="text-xl font-semibold text-text-primary tracking-[-0.03em]" id={titleId}>
              {title}
            </h2>
            {description ? (
              <p className="max-w-3xl text-sm leading-6 text-text-secondary" id={descriptionId}>
                {description}
              </p>
            ) : null}
          </div>
          <button
            aria-label="关闭对话框"
            className="ink-button-secondary min-w-0 px-4 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={closeDisabled}
            onClick={dismiss}
            ref={closeButtonRef}
            type="button"
          >
            关闭
          </button>
        </header>
        <div className="max-h-[calc(88vh-96px)] overflow-y-auto px-6 py-6">{children}</div>
      </div>
    </div>
  );
}

function resolveFocusableElements(container: HTMLDivElement | null): HTMLElement[] {
  if (!container) {
    return [];
  }
  return Array.from(
    container.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  );
}
