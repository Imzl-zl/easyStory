"use client";

import { useEffect, useRef, useCallback } from "react";
import { createPortal } from "react-dom";

export type StudioDialogProps = {
  open: boolean;
  title: string;
  description?: string;
  children?: React.ReactNode;
  confirmText?: string;
  cancelText?: string;
  confirmLoading?: boolean;
  confirmVariant?: "primary" | "danger";
  onConfirm?: () => void;
  onCancel?: () => void;
  onClose?: () => void;
  hideCancel?: boolean;
  width?: number;
};

export function StudioDialog({
  open,
  title,
  description,
  children,
  confirmText = "确定",
  cancelText = "取消",
  confirmLoading = false,
  confirmVariant = "primary",
  onConfirm,
  onCancel,
  onClose,
  hideCancel = false,
  width = 400,
}: StudioDialogProps) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);

  const handleClose = useCallback(() => {
    onClose?.();
    onCancel?.();
  }, [onClose, onCancel]);

  useEffect(() => {
    if (open) {
      previousActiveElement.current = document.activeElement as HTMLElement;
      document.body.style.overflow = "hidden";
      // Focus trap: focus first focusable element
      setTimeout(() => {
        const focusable = contentRef.current?.querySelector<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        focusable?.focus();
      }, 50);
    } else {
      document.body.style.overflow = "";
      previousActiveElement.current?.focus();
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!open) return;
      if (e.key === "Escape") {
        handleClose();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, handleClose]);

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === overlayRef.current) {
      handleClose();
    }
  };

  if (!open) return null;

  const dialog = (
    <div
      ref={overlayRef}
      className="studio-dialog-overlay"
      onClick={handleOverlayClick}
      role="presentation"
    >
      <div
        ref={contentRef}
        className="studio-dialog-content"
        role="dialog"
        aria-modal="true"
        aria-labelledby="studio-dialog-title"
        style={{ maxWidth: width }}
      >
        {/* 顶部装饰线 */}
        <div className="studio-dialog-accent-line" />

        {/* 头部 */}
        <div className="studio-dialog-header">
          <h3 id="studio-dialog-title" className="studio-dialog-title">
            {title}
          </h3>
          {description ? (
            <p className="studio-dialog-description">{description}</p>
          ) : null}
          <button
            className="studio-dialog-close"
            onClick={handleClose}
            type="button"
            aria-label="关闭"
          >
            <CloseIcon />
          </button>
        </div>

        {/* 内容区 */}
        {children ? <div className="studio-dialog-body">{children}</div> : null}

        {/* 底部操作 */}
        {(onConfirm || !hideCancel) ? (
          <div className="studio-dialog-footer">
            {!hideCancel ? (
              <button
                className="studio-dialog-btn studio-dialog-btn--secondary"
                onClick={handleClose}
                type="button"
                disabled={confirmLoading}
              >
                {cancelText}
              </button>
            ) : null}
            {onConfirm ? (
              <button
                className={`studio-dialog-btn ${confirmVariant === "danger" ? "studio-dialog-btn--danger" : "studio-dialog-btn--primary"}`}
                disabled={confirmLoading}
                onClick={onConfirm}
                type="button"
              >
                {confirmLoading ? (
                  <span className="studio-dialog-btn__loading">
                    <LoadingIcon />
                    处理中…
                  </span>
                ) : (
                  confirmText
                )}
              </button>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );

  return createPortal(dialog, document.body);
}

function CloseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function LoadingIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="studio-dialog-spinner">
      <path d="M12 2v4" />
      <path d="m5 5 2.8 2.8" />
      <path d="m19 5-2.8 2.8" />
      <path d="M12 18a6 6 0 1 0 0-12 6 6 0 0 0 0 12Z" opacity="0.3" />
    </svg>
  );
}
