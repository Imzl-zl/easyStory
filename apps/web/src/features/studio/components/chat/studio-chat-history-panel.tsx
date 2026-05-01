"use client";

import { createPortal } from "react-dom";
import {
  useEffect,
  useCallback,
  useRef,
  useState,
} from "react";
import type { CSSProperties } from "react";

import { observeFloatingPanelLayoutChanges } from "@/components/ui/floating-panel-support";
import type { StudioConversationSummary } from "@/features/studio/components/chat/studio-chat-store-support";
import type { StudioChatLayoutMode } from "@/features/studio/components/page/studio-page-support";

type StudioChatHistoryPanelProps = {
  activeConversationId: string;
  layoutMode?: StudioChatLayoutMode;
  conversations: StudioConversationSummary[];
  disabled?: boolean;
  isOpen: boolean;
  onCreateConversation: () => void;
  onDeleteConversation: (conversationId: string) => void;
  onOpenChange: (open: boolean) => void;
  onSelectConversation: (conversationId: string) => void;
};

export function StudioChatHistoryPanel({
  activeConversationId,
  layoutMode = "default",
  conversations,
  disabled = false,
  isOpen,
  onCreateConversation,
  onDeleteConversation,
  onOpenChange,
  onSelectConversation,
}: Readonly<StudioChatHistoryPanelProps>) {
  const [panelStyle, setPanelStyle] = useState<CSSProperties | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const popupRef = useRef<HTMLDivElement>(null);
  const compactLayout = layoutMode !== "default";
  const iconLayout = layoutMode === "icon";
  const activeConversation = conversations.find((conversation) => conversation.id === activeConversationId)
    ?? conversations[0]
    ?? null;
  const updatePanelPosition = useCallback(() => {
    setPanelStyle(resolveHistoryPanelStyle(containerRef.current));
  }, []);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    function handlePointerDown(event: MouseEvent) {
      const target = event.target as Node;
      if (!containerRef.current?.contains(target) && !popupRef.current?.contains(target)) {
        onOpenChange(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onOpenChange(false);
      }
    }

    const frameId = window.requestAnimationFrame(updatePanelPosition);
    const cleanupLayoutObserver = observeFloatingPanelLayoutChanges(containerRef.current, updatePanelPosition);
    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleEscape);
    return () => {
      window.cancelAnimationFrame(frameId);
      cleanupLayoutObserver();
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [isOpen, onOpenChange, updatePanelPosition]);

  const popup = isOpen && panelStyle
    ? createPortal(
      <>
        <div
          className="chat-panel-overlay"
          role="button"
          tabIndex={0}
          onClick={() => onOpenChange(false)}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onOpenChange(false); }}
        />
        <div
          className="chat-history-panel"
          ref={popupRef}
          style={panelStyle}
        >
          <div className="chat-panel-header">
            <div>
              <h3 className="chat-panel-header__title">历史对话</h3>
              <p className="chat-panel-header__subtitle">{conversations.length} 条对话记录</p>
            </div>
            <button
              className="chat-panel-header__close"
              type="button"
              onClick={() => onOpenChange(false)}
            >
              ×
            </button>
          </div>
          <ul className="chat-panel-list max-h-[320px]">
            {conversations.map((conversation) => {
              const isActive = conversation.id === activeConversationId;
              return (
                <li key={conversation.id}>
                  <div
                    className={`chat-panel-item ${isActive ? "chat-panel-item--active" : ""}`}
                  >
                    <button
                      className="min-w-0 flex-1 rounded-xl px-3 py-2.5 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary/15 disabled:cursor-not-allowed"
                      disabled={disabled}
                      type="button"
                      onClick={() => {
                        onSelectConversation(conversation.id);
                        onOpenChange(false);
                      }}
                    >
                      <div className="flex items-center gap-2.5">
                        <span className="chat-panel-item__title">
                          {conversation.title}
                        </span>
                        {isActive ? (
                          <span className="inline-flex shrink-0 items-center rounded-full bg-elevated px-2 py-0.5 text-[11px] leading-4 text-accent-primary">
                            当前
                          </span>
                        ) : null}
                      </div>
                      <p className="mt-1 text-[12px] leading-4 text-text-tertiary">
                        {formatConversationUpdatedAt(conversation.updatedAt)}
                      </p>
                    </button>
                    <button
                      aria-label={`删除对话：${conversation.title}`}
                      className="ink-toolbar-icon text-accent-danger shrink-0"
                      disabled={disabled}
                      type="button"
                      onClick={(event) => {
                        event.preventDefault();
                        event.stopPropagation();
                        onDeleteConversation(conversation.id);
                      }}
                    >
                      <TrashIcon />
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      </>,
      document.body,
    )
    : null;

  return (
    <div className={`relative flex min-w-0 items-center gap-2 ${compactLayout ? "w-full justify-stretch" : "ml-auto w-[min(240px,100%)] justify-end"}`} ref={containerRef}>
      <button
        aria-label="新对话"
        className={`studio-new-chat-btn focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary/15 disabled:cursor-not-allowed disabled:opacity-40 ${iconLayout ? "" : "studio-new-chat-btn--labeled"}`}
        disabled={disabled}
        title="新对话"
        type="button"
        onClick={() => {
          onCreateConversation();
          onOpenChange(false);
        }}
      >
        <svg aria-hidden="true" fill="none" height="14" viewBox="0 0 24 24" width="14">
          <path d="M12 5v14M5 12h14" stroke="currentColor" strokeLinecap="round" strokeWidth="2"/>
        </svg>
        {!iconLayout ? <span className="text-[13px] font-medium">新对话</span> : null}
      </button>
      <button
        aria-expanded={isOpen}
        className="group flex h-[32px] min-w-0 flex-1 items-center gap-2 rounded-full bg-surface px-3 text-left transition-all hover:bg-chat-panel focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary/15 disabled:cursor-not-allowed disabled:opacity-40"
        disabled={disabled}
        title={activeConversation?.title ?? "新对话"}
        type="button"
        onClick={() => onOpenChange(!isOpen)}
      >
        <span className="inline-flex shrink-0 items-center rounded-full bg-elevated px-2 py-0.5 text-[10px] font-semibold leading-4 text-text-secondary">
          历史
        </span>
        <span className="min-w-0 flex-1 truncate text-[13px] font-medium leading-5 text-text-primary">
          {activeConversation?.title ?? "新对话"}
        </span>
        <span className="inline-flex shrink-0 items-center rounded-full bg-elevated px-1.5 py-0.5 text-[10px] leading-4 text-text-tertiary">
          {conversations.length} 条
        </span>
        <span
          aria-hidden="true"
          className={`shrink-0 text-[11px] text-text-tertiary transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
        >
          ▾
        </span>
      </button>
      {popup}
    </div>
  );
}

const HISTORY_PANEL_MIN_WIDTH = 320;
const HISTORY_PANEL_VIEWPORT_MARGIN = 16;
const HISTORY_PANEL_OFFSET = 10;

function resolveHistoryPanelStyle(container: HTMLDivElement | null): CSSProperties | null {
  if (!container) {
    return null;
  }
  const rect = container.getBoundingClientRect();
  const availableWidth = Math.max(window.innerWidth - HISTORY_PANEL_VIEWPORT_MARGIN * 2, 0);
  const width = availableWidth === 0
    ? 0
    : Math.min(Math.max(rect.width, HISTORY_PANEL_MIN_WIDTH), availableWidth);
  const maxLeft = window.innerWidth - width - HISTORY_PANEL_VIEWPORT_MARGIN;
  const preferredLeft = rect.right - width;

  return {
    left: Math.max(HISTORY_PANEL_VIEWPORT_MARGIN, Math.min(preferredLeft, maxLeft)),
    position: "fixed",
    top: rect.bottom + HISTORY_PANEL_OFFSET,
    width,
    zIndex: 200,
  };
}

function TrashIcon() {
  return (
    <svg aria-hidden="true" className="size-4" fill="none" viewBox="0 0 24 24">
      <path
        d="M5 7h14m-9 4v5m4-5v5M9 4h6l1 2H8l1-2Zm1 16h4a2 2 0 0 0 2-2V7H8v11a2 2 0 0 0 2 2Z"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.6"
      />
    </svg>
  );
}

function formatConversationUpdatedAt(value: string) {
  const updatedAt = new Date(value);
  if (Number.isNaN(updatedAt.getTime())) {
    return "刚刚更新";
  }
  return new Intl.DateTimeFormat("zh-CN", {
    day: "numeric",
    hour: "2-digit",
    hour12: false,
    minute: "2-digit",
    month: "numeric",
  }).format(updatedAt);
}
