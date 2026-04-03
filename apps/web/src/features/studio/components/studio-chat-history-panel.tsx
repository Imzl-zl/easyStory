"use client";

import { createPortal } from "react-dom";
import {
  Button,
} from "@arco-design/web-react";
import {
  useEffect,
  useRef,
  useState,
} from "react";
import type { CSSProperties } from "react";

import type { StudioConversationSummary } from "./studio-chat-store-support";

type StudioChatHistoryPanelProps = {
  activeConversationId: string;
  conversations: StudioConversationSummary[];
  disabled?: boolean;
  onCreateConversation: () => void;
  onDeleteConversation: (conversationId: string) => void;
  onSelectConversation: (conversationId: string) => void;
};

export function StudioChatHistoryPanel({
  activeConversationId,
  conversations,
  disabled = false,
  onCreateConversation,
  onDeleteConversation,
  onSelectConversation,
}: Readonly<StudioChatHistoryPanelProps>) {
  const [isOpen, setIsOpen] = useState(false);
  const [panelStyle, setPanelStyle] = useState<CSSProperties | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const popupRef = useRef<HTMLDivElement>(null);
  const activeConversation = conversations.find((conversation) => conversation.id === activeConversationId)
    ?? conversations[0]
    ?? null;

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    function updatePanelPosition() {
      const container = containerRef.current;
      if (!container) {
        return;
      }
      const rect = container.getBoundingClientRect();
      const width = Math.max(rect.width, 300);
      const viewportWidth = window.innerWidth;
      const left = Math.max(12, Math.min(rect.left, viewportWidth - width - 12));
      setPanelStyle({
        left,
        position: "fixed",
        top: rect.bottom + 8,
        width,
        zIndex: 160,
      });
    }

    function handlePointerDown(event: MouseEvent) {
      const target = event.target as Node;
      if (!containerRef.current?.contains(target) && !popupRef.current?.contains(target)) {
        setIsOpen(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }

    const frameId = window.requestAnimationFrame(updatePanelPosition);
    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleEscape);
    window.addEventListener("resize", updatePanelPosition);
    window.addEventListener("scroll", updatePanelPosition, true);
    return () => {
      window.cancelAnimationFrame(frameId);
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
      window.removeEventListener("resize", updatePanelPosition);
      window.removeEventListener("scroll", updatePanelPosition, true);
    };
  }, [isOpen]);

  const popup = isOpen && panelStyle
    ? createPortal(
      <div
        className="overflow-hidden rounded-[20px] border border-[rgba(101,92,82,0.14)] bg-[#fffdf9] p-2 shadow-[0_18px_40px_rgba(58,45,29,0.14)] ring-1 ring-[rgba(255,255,255,0.88)]"
        ref={popupRef}
        style={panelStyle}
      >
        <div className="mb-1 flex items-center justify-between rounded-[14px] bg-[#fffdf9] px-2 py-1">
          <span className="text-[10px] font-medium tracking-[0.08em] text-[var(--text-secondary)]">选择历史对话</span>
          <span className="text-[10px] text-[var(--text-muted)]">{conversations.length} 条</span>
        </div>
        <ul className="max-h-[260px] space-y-1 overflow-y-auto pr-0.5">
          {conversations.map((conversation) => {
            const isActive = conversation.id === activeConversationId;
            return (
              <li key={conversation.id}>
                <div
                  className={`flex items-center gap-1.5 rounded-[14px] border px-1 py-1 ${isActive ? "border-[rgba(46,111,106,0.18)] bg-[#eef4ea]" : "border-[rgba(101,92,82,0.08)] bg-[#f9f6ef] hover:border-[rgba(101,92,82,0.12)] hover:bg-[#fffdfa]"}`}
                >
                  <button
                    className="min-w-0 flex-1 rounded-[12px] px-2.5 py-2 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(46,111,106,0.18)] disabled:cursor-not-allowed"
                    disabled={disabled}
                    type="button"
                    onClick={() => {
                      onSelectConversation(conversation.id);
                      setIsOpen(false);
                    }}
                  >
                    <div className="flex items-center gap-2">
                      <span className="truncate text-[12px] font-medium leading-5 text-[var(--text-primary)]">
                        {conversation.title}
                      </span>
                      {isActive ? (
                        <span className="inline-flex shrink-0 items-center rounded-full bg-white px-1.5 py-0.5 text-[9.5px] leading-4 text-[var(--accent-ink)]">
                          当前
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-0.5 text-[10.5px] leading-4 text-[var(--text-secondary)]">
                      {formatConversationUpdatedAt(conversation.updatedAt)}
                    </p>
                  </button>
                  <Button
                    aria-label={`删除对话：${conversation.title}`}
                    className="shrink-0"
                    disabled={disabled}
                    icon={<TrashIcon />}
                    shape="circle"
                    size="mini"
                    status="danger"
                    type="text"
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      onDeleteConversation(conversation.id);
                      setIsOpen(false);
                    }}
                  />
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
    <div className="relative w-full max-w-[320px]" ref={containerRef}>
      <div className="flex items-center gap-2">
        <button
          className="inline-flex h-[30px] shrink-0 items-center gap-1.5 rounded-full border border-[rgba(101,92,82,0.12)] bg-[#fffdfa] px-3 text-[11px] font-medium text-[var(--text-primary)] transition-[border-color,background-color] hover:border-[rgba(46,111,106,0.2)] hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(46,111,106,0.16)] disabled:cursor-not-allowed disabled:opacity-60"
          disabled={disabled}
          type="button"
          onClick={() => {
            onCreateConversation();
            setIsOpen(false);
          }}
        >
          <span className="text-[13px] leading-none">+</span>
          <span>新对话</span>
        </button>
        <button
          aria-expanded={isOpen}
          className="group flex h-[30px] min-w-0 flex-1 items-center gap-2 rounded-full border border-[rgba(101,92,82,0.12)] bg-[#fffdfa] px-3 text-left transition-[border-color,background-color,box-shadow] hover:border-[rgba(46,111,106,0.18)] hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(46,111,106,0.16)] disabled:cursor-not-allowed disabled:opacity-60"
          disabled={disabled}
          type="button"
          onClick={() => setIsOpen((current) => !current)}
        >
          <span className="inline-flex shrink-0 items-center rounded-full bg-[#f3ede3] px-2 py-0.5 text-[10px] leading-4 text-[var(--text-secondary)]">
            历史
          </span>
          <span className="min-w-0 flex-1 truncate text-[12px] font-medium leading-5 text-[var(--text-primary)]">
            {activeConversation?.title ?? "新对话"}
          </span>
          <span className="inline-flex shrink-0 items-center rounded-full bg-[#f3ede3] px-2 py-0.5 text-[10px] leading-4 text-[var(--text-secondary)]">
            {conversations.length} 条
          </span>
          <span
            aria-hidden="true"
            className={`shrink-0 text-[10px] text-[var(--text-secondary)] transition-transform ${isOpen ? "rotate-180" : ""}`}
          >
            ▾
          </span>
        </button>
      </div>
      {popup}
    </div>
  );
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
