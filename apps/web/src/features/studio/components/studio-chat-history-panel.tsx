"use client";

import { useState } from "react";
import { Button } from "@arco-design/web-react";

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
  const activeConversation = conversations.find((conversation) => conversation.id === activeConversationId)
    ?? conversations[0]
    ?? null;

  return (
    <div className="mt-2.5 space-y-1.5">
      <div className="flex items-stretch gap-1.5">
        <button
          aria-expanded={isOpen}
          className="group flex min-w-0 flex-1 items-center justify-between rounded-[14px] border border-[rgba(101,92,82,0.12)] bg-[rgba(255,255,255,0.82)] px-3 py-2 text-left transition-[border-color,background-color,box-shadow] hover:border-[rgba(46,111,106,0.18)] hover:bg-[rgba(255,255,255,0.96)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(46,111,106,0.16)] disabled:cursor-not-allowed disabled:opacity-60"
          disabled={disabled}
          type="button"
          onClick={() => setIsOpen((current) => !current)}
        >
          <span className="min-w-0 flex-1">
            <span className="block text-[10px] leading-4 tracking-[0.08em] text-[var(--text-secondary)]">历史对话</span>
            <span className="mt-0.5 block truncate text-[12.5px] font-medium leading-5 text-[var(--text-primary)]">
              {activeConversation?.title ?? "新对话"}
            </span>
          </span>
          <span className="ml-2 inline-flex shrink-0 items-center rounded-full bg-[rgba(248,243,235,0.92)] px-2 py-0.5 text-[10.5px] leading-4 text-[var(--text-secondary)]">
            {conversations.length} 条
          </span>
        </button>
        <Button
          disabled={disabled}
          shape="round"
          size="default"
          type="secondary"
          onClick={() => {
            onCreateConversation();
            setIsOpen(false);
          }}
        >
          新对话
        </Button>
      </div>
      {isOpen ? (
        <div className="rounded-[18px] border border-[rgba(101,92,82,0.12)] bg-[rgba(255,255,255,0.94)] p-1.5 shadow-[0_12px_24px_rgba(58,45,29,0.06)]">
          <ul className="max-h-[220px] space-y-1 overflow-y-auto pr-0.5">
            {conversations.map((conversation) => {
              const isActive = conversation.id === activeConversationId;
              return (
                <li key={conversation.id}>
                  <div
                    className={`flex items-center gap-1.5 rounded-[14px] border px-1 py-1 ${isActive ? "border-[rgba(46,111,106,0.18)] bg-[rgba(46,111,106,0.08)]" : "border-transparent bg-[rgba(248,243,235,0.52)] hover:border-[rgba(101,92,82,0.1)] hover:bg-[rgba(255,255,255,0.92)]"}`}
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
                          <span className="inline-flex shrink-0 items-center rounded-full bg-[rgba(255,255,255,0.88)] px-1.5 py-0.5 text-[9.5px] leading-4 text-[var(--accent-ink)]">
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
        </div>
      ) : null}
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
