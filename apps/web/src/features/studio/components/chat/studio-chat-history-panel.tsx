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
      <div
        className="overflow-hidden rounded-2xl bg-surface shadow-sm p-2 shadow-lg ring-1 ring-white/90 animate-[slideFromRight_0.22s_cubic-bezier(0.16,1,0.3,1)]"
        ref={popupRef}
        style={panelStyle}
      >
        <div className="mb-1 flex items-center justify-between rounded-2xl bg-surface px-2 py-1">
          <span className="text-[10px] font-medium tracking-[0.08em] text-text-secondary">选择历史对话</span>
          <span className="text-[10px] text-text-tertiary">{conversations.length} 条</span>
        </div>
        <ul className="max-h-[260px] space-y-1 overflow-y-auto pr-0.5">
          {conversations.map((conversation) => {
            const isActive = conversation.id === activeConversationId;
            return (
              <li key={conversation.id}>
                <div
                  className={`flex items-center gap-1.5 rounded-2xl px-1 py-1 ${isActive ? "bg-accent-soft shadow-sm" : "bg-muted shadow-xs hover:bg-surface hover:shadow-sm"}`}
                >
                  <button
                    className="min-w-0 flex-1 rounded-lg px-2.5 py-2 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary/15 disabled:cursor-not-allowed"
                    disabled={disabled}
                    type="button"
                    onClick={() => {
                      onSelectConversation(conversation.id);
                      onOpenChange(false);
                    }}
                  >
                    <div className="flex items-center gap-2">
                      <span className="truncate text-[12px] font-medium leading-5 text-text-primary">
                        {conversation.title}
                      </span>
                      {isActive ? (
                        <span className="inline-flex shrink-0 items-center rounded-full bg-elevated px-1.5 py-0.5 text-[9.5px] leading-4 text-accent-primary">
                          当前
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-0.5 text-[10.5px] leading-4 text-text-secondary">
                      {formatConversationUpdatedAt(conversation.updatedAt)}
                    </p>
                  </button>
                  <button
                    aria-label={`删除对话：${conversation.title}`}
                    className="ink-icon-button text-accent-danger shrink-0"
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
      </div>,
      document.body,
    )
    : null;

  return (
    <div className={`relative flex min-w-0 items-center gap-2 ${compactLayout ? "w-full justify-stretch" : "ml-auto w-[min(228px,100%)] justify-end"}`} ref={containerRef}>
      <button
        aria-label="新对话"
        className={`inline-flex h-[30px] shrink-0 items-center rounded-full bg-surface shadow-sm text-[11px] font-medium text-text-primary transition-[border-color,background-color] hover:border-accent-primary-muted hover:bg-elevated focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary/15 disabled:cursor-not-allowed disabled:opacity-60 ${iconLayout ? "w-[30px] justify-center px-0" : "gap-1.5 px-3"}`}
        disabled={disabled}
        title="新对话"
        type="button"
        onClick={() => {
          onCreateConversation();
          onOpenChange(false);
        }}
      >
        <span className="text-[13px] leading-none">+</span>
        {!iconLayout ? <span>新对话</span> : null}
      </button>
      <button
        aria-expanded={isOpen}
        className="group flex h-[30px] min-w-0 flex-1 items-center gap-2 rounded-full bg-surface shadow-sm px-3 text-left transition-[border-color,background-color,box-shadow] hover:border-accent-primary-muted hover:bg-elevated focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary/15 disabled:cursor-not-allowed disabled:opacity-60"
        disabled={disabled}
        title={activeConversation?.title ?? "新对话"}
        type="button"
        onClick={() => onOpenChange(!isOpen)}
      >
        <span className="inline-flex shrink-0 items-center rounded-full bg-muted px-2 py-0.5 text-[9.5px] leading-4 text-text-secondary">
          历史
        </span>
        <span className="min-w-0 flex-1 truncate text-[12px] font-medium leading-5 text-text-primary">
          {activeConversation?.title ?? "新对话"}
        </span>
        <span className="inline-flex shrink-0 items-center rounded-full bg-muted px-1.5 py-0.5 text-[9px] leading-4 text-text-secondary">
          {conversations.length} 条
        </span>
        <span
          aria-hidden="true"
          className={`shrink-0 text-[10px] text-text-secondary transition-transform ${isOpen ? "rotate-180" : ""}`}
        >
          ▾
        </span>
      </button>
      {popup}
    </div>
  );
}

const HISTORY_PANEL_MIN_WIDTH = 300;
const HISTORY_PANEL_VIEWPORT_MARGIN = 12;
const HISTORY_PANEL_OFFSET = 8;

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
    zIndex: 160,
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
