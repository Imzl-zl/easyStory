"use client";

import { createPortal } from "react-dom";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, ReactNode, RefObject } from "react";

import { observeFloatingPanelLayoutChanges } from "@/components/ui/floating-panel-support";
import {
  filterStudioChatSkillOptions,
  type StudioChatSkillOption,
} from "@/features/studio/components/chat/studio-chat-skill-support";
import type { StudioChatSkillModel } from "@/features/studio/components/chat/studio-chat-skill-model";
import type { StudioChatLayoutMode } from "@/features/studio/components/page/studio-page-support";

type StudioChatSkillPanelProps = {
  layoutMode?: StudioChatLayoutMode;
  disabled?: boolean;
  isOpen: boolean;
  model: StudioChatSkillModel;
  onOpenChange: (open: boolean) => void;
};

type SkillDrawerLayout = {
  backdropStyle: CSSProperties;
  panelStyle: CSSProperties;
};

export function StudioChatSkillPanel({
  layoutMode = "default",
  disabled = false,
  isOpen,
  model,
  onOpenChange,
}: Readonly<StudioChatSkillPanelProps>) {
  const compactLayout = layoutMode !== "default";
  const [layout, setLayout] = useState<SkillDrawerLayout | null>(null);
  const [query, setQuery] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const filteredSkillOptions = useMemo(
    () => filterStudioChatSkillOptions(model.skillOptions, query),
    [model.skillOptions, query],
  );
  const closeDrawer = useCallback(() => {
    onOpenChange(false);
    setQuery("");
  }, [onOpenChange]);
  const updateLayout = useCallback(() => {
    setLayout(resolveSkillDrawerLayout(containerRef.current));
  }, []);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        closeDrawer();
      }
    }

    updateLayout();
    const frameId = window.requestAnimationFrame(() => searchInputRef.current?.focus());
    const cleanupLayoutObserver = observeFloatingPanelLayoutChanges(containerRef.current, updateLayout);
    document.addEventListener("keydown", handleEscape);
    return () => {
      window.cancelAnimationFrame(frameId);
      cleanupLayoutObserver();
      document.removeEventListener("keydown", handleEscape);
    };
  }, [closeDrawer, isOpen, updateLayout]);

  return (
    <div className={`relative min-w-0 shrink-0 ${compactLayout ? "w-full max-w-none" : "max-w-[160px]"}`} ref={containerRef}>
      <button
        aria-expanded={isOpen}
        className={`group flex h-[32px] min-w-0 items-center gap-2 rounded-full px-3 text-left transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary/15 disabled:cursor-not-allowed disabled:opacity-40 ${compactLayout ? "w-full max-w-none" : "min-w-[140px] max-w-[160px]"} ${
          isOpen
            ? "bg-[#252a33] shadow-md"
            : "bg-[#1e2129] shadow-xs hover:shadow-sm"
        }`}
        disabled={disabled}
        title={model.skillState.headline}
        type="button"
        onClick={() => {
          if (isOpen) {
            closeDrawer();
            return;
          }
          setQuery("");
          onOpenChange(true);
        }}
      >
        <span className="inline-flex shrink-0 items-center rounded-full bg-[#2f343e] px-2 py-0.5 text-[11px] font-semibold leading-4 text-[#a09682]">
          Skill
        </span>
        <span className="min-w-0 flex-1 truncate text-[13px] font-medium leading-5 text-[#dde1e6]">
          {resolveTriggerLabel(model.skillState.headline)}
        </span>
        <span
          aria-hidden="true"
          className={`shrink-0 text-[11px] text-[#686e77] transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
        >
          ▾
        </span>
      </button>
      {isOpen && layout ? createPortal(
        <>
          <div
            aria-label="关闭 Skill 面板"
            className="chat-panel-overlay"
            role="button"
            tabIndex={0}
            onClick={closeDrawer}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") closeDrawer(); }}
          />
          <SkillDrawer
            disabled={disabled}
            filteredSkillOptions={filteredSkillOptions}
            layout={layout}
            model={model}
            onClose={closeDrawer}
            query={query}
            searchInputRef={searchInputRef}
            setQuery={setQuery}
          />
        </>,
        document.body,
      ) : null}
    </div>
  );
}

type SkillDrawerProps = {
  disabled: boolean;
  filteredSkillOptions: StudioChatSkillOption[];
  layout: SkillDrawerLayout;
  model: StudioChatSkillModel;
  onClose: () => void;
  query: string;
  searchInputRef: RefObject<HTMLInputElement | null>;
  setQuery: (value: string) => void;
};

function SkillDrawer({
  disabled,
  filteredSkillOptions,
  layout,
  model,
  onClose,
  query,
  searchInputRef,
  setQuery,
}: Readonly<SkillDrawerProps>) {
  const resultSummary = buildResultSummary(filteredSkillOptions.length, model.skillOptions.length, query);

  return (
    <section
      aria-label="选择 Skill"
      className="chat-skill-panel"
      role="dialog"
      style={layout.panelStyle}
    >
      <div className="shrink-0 px-5 pt-5 pb-4">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="m-0 text-[11px] font-semibold tracking-[0.1em] text-[#a09682] uppercase">Skill 模式</p>
            <h3 className="mt-1.5 text-[16px] font-bold leading-6 text-[#dde1e6]">
              选择 Skill
            </h3>
            <p className="mt-1 text-[13px] leading-5 text-[#9299a3]">
              {resultSummary}
            </p>
          </div>
          <button
            className="chat-panel-header__close"
            type="button"
            onClick={onClose}
          >
            ×
          </button>
        </div>
        <CurrentModeCard disabled={disabled} model={model} onClose={onClose} />
      </div>

      <div className="shrink-0 px-5 py-3 border-t border-[rgba(150,158,170,0.08)]">
        <label className="block">
          <span className="sr-only">筛选 Skill</span>
          <input
            className="chat-panel-search"
            placeholder="按名称、描述或作用域筛选..."
            ref={searchInputRef}
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-3">
        {model.skillErrorMessage ? (
          <StateNotice tone="danger">{model.skillErrorMessage}</StateNotice>
        ) : null}
        {model.skillsLoading ? <StateNotice>读取中…</StateNotice> : null}
        {!model.skillErrorMessage && !model.skillsLoading && model.skillOptions.length === 0 ? (
          <StateNotice>暂无可用 Skill</StateNotice>
        ) : null}
        {!model.skillErrorMessage && !model.skillsLoading && model.skillOptions.length > 0 && filteredSkillOptions.length === 0 ? (
          <StateNotice>无匹配结果</StateNotice>
        ) : null}
        {!model.skillErrorMessage && !model.skillsLoading && filteredSkillOptions.length > 0 ? (
          <ul className="space-y-2">
            {filteredSkillOptions.map((option) => (
              <SkillOptionCard
                disabled={disabled}
                key={option.value}
                model={model}
                option={option}
                onClose={onClose}
              />
            ))}
          </ul>
        ) : null}
      </div>
    </section>
  );
}

function CurrentModeCard({
  disabled,
  model,
  onClose,
}: Readonly<{
  disabled: boolean;
  model: StudioChatSkillModel;
  onClose: () => void;
}>) {
  return (
    <div className="chat-skill-current-mode">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="m-0 text-[11px] font-semibold tracking-[0.1em] text-[#686e77] uppercase">当前模式</p>
          <p className="mt-1.5 text-[14px] font-bold leading-5 text-[#dde1e6]">
            {model.skillState.headline}
          </p>
          {model.skillState.detail ? (
            <p className="mt-1 text-[13px] leading-5 text-[#9299a3]">
              {model.skillState.detail}
            </p>
          ) : null}
        </div>
        <button
          className={`inline-flex h-8 shrink-0 items-center rounded-full border px-3 text-[13px] font-semibold transition-all ${
            isPlainChatMode(model)
              ? "border-[rgba(160,150,130,0.25)] bg-[rgba(160,150,130,0.12)] text-[#a09682]"
              : "bg-[#252a33] border-[rgba(150,158,170,0.12)] text-[#9299a3] hover:text-[#dde1e6]"
          }`}
          disabled={disabled}
          type="button"
          onClick={() => {
            model.resetToPlainChat();
            onClose();
          }}
        >
          普通对话
        </button>
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {model.skillState.nextTurnSkillId ? (
          <button
            className={DRAWER_ACTION_BUTTON_CLASS}
            disabled={disabled}
            type="button"
            onClick={() => {
              model.clearNextTurnSkill();
              onClose();
            }}
          >
            清除本次 Skill
          </button>
        ) : null}
        {model.skillState.conversationSkillId ? (
          <button
            className={DRAWER_ACTION_BUTTON_CLASS}
            disabled={disabled}
            type="button"
            onClick={() => {
              model.clearConversationSkill();
              onClose();
            }}
          >
            清除会话 Skill
          </button>
        ) : null}
      </div>
    </div>
  );
}

function SkillOptionCard({
  disabled,
  model,
  onClose,
  option,
}: Readonly<{
  disabled: boolean;
  model: StudioChatSkillModel;
  onClose: () => void;
  option: StudioChatSkillOption;
}>) {
  const nextSelected = option.value === model.skillState.nextTurnSkillId;
  const conversationSelected = option.value === model.skillState.conversationSkillId;
  const hasActiveMode = nextSelected || conversationSelected;

  return (
    <li>
      <div className={`chat-skill-option ${hasActiveMode ? "chat-skill-option--active" : ""}`}>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[14px] font-bold leading-5 text-[#dde1e6]">
              {option.label}
            </span>
            <span className="inline-flex items-center rounded-full bg-[#2f343e] px-2 py-0.5 text-[11px] leading-4 text-[#9299a3]">
              {option.scopeLabel}
            </span>
            {nextSelected ? (
              <span className="inline-flex items-center rounded-full bg-[rgba(160,150,130,0.12)] px-2 py-0.5 text-[11px] leading-4 text-[#a09682]">
                本次
              </span>
            ) : null}
            {conversationSelected ? (
              <span className="inline-flex items-center rounded-full bg-[rgba(212,168,90,0.12)] px-2 py-0.5 text-[11px] leading-4 text-[#d4a85a]">
                会话
              </span>
            ) : null}
          </div>
          {option.description ? (
            <p className="mt-2 line-clamp-2 text-[13px] leading-5 text-[#9299a3]">
              {option.description}
            </p>
          ) : null}
          <div className="mt-3 flex justify-end gap-2">
            <button
              className={resolveModeButtonClassName(nextSelected)}
              disabled={disabled}
              type="button"
              onClick={() => {
                model.useSkillOnce(option.value);
                onClose();
              }}
            >
              {nextSelected ? "本次中" : "本次"}
            </button>
            <button
              className={resolveModeButtonClassName(conversationSelected)}
              disabled={disabled}
              type="button"
              onClick={() => {
                model.useSkillForConversation(option.value);
                onClose();
              }}
            >
              {conversationSelected ? "会话中" : "会话"}
            </button>
          </div>
        </div>
      </div>
    </li>
  );
}

function StateNotice({
  children,
  tone = "muted",
}: Readonly<{
  children: ReactNode;
  tone?: "danger" | "muted";
}>) {
  return (
    <div
      className={`rounded-xl px-4 py-3 text-[13px] leading-5 ${
        tone === "danger"
          ? "bg-[rgba(196,112,112,0.10)] text-[#c47070]"
          : "bg-[#2f343e] text-[#9299a3]"
      }`}
    >
      {children}
    </div>
  );
}

function resolveSkillDrawerLayout(container: HTMLDivElement | null): SkillDrawerLayout | null {
  if (!container) {
    return null;
  }
  const chatPanel = container?.closest("aside");
  if (!(chatPanel instanceof HTMLElement)) {
    return null;
  }
  const rect = chatPanel.getBoundingClientRect();
  const triggerRect = container.getBoundingClientRect();
  const gutter = rect.width > 460 ? 16 : 12;
  const panelWidth = Math.min(360, Math.max(rect.width - gutter * 2 - 44, 280));
  const panelLeft = Math.max(
    rect.left + gutter,
    Math.min(triggerRect.left, rect.right - gutter - panelWidth),
  );
  const panelTop = Math.max(rect.top + gutter, triggerRect.bottom + 8);
  const panelHeight = Math.max(Math.min(rect.bottom - panelTop - gutter, 560), 280);

  return {
    backdropStyle: {
      height: Math.max(rect.bottom - panelTop, 0),
      left: rect.left,
      position: "fixed",
      top: panelTop,
      width: rect.width,
      zIndex: 145,
    },
    panelStyle: {
      height: panelHeight,
      left: panelLeft,
      position: "fixed",
      top: panelTop,
      width: panelWidth,
      zIndex: 200,
    },
  };
}

function buildResultSummary(visibleCount: number, totalCount: number, query: string) {
  if (!query.trim()) {
    return `共 ${totalCount} 个可用 Skill`;
  }
  return `筛到 ${visibleCount} / ${totalCount} 个 Skill`;
}

const DRAWER_ACTION_BUTTON_CLASS =
  "inline-flex h-8 items-center rounded-full bg-[#252a33] border border-[rgba(150,158,170,0.10)] px-3 text-[13px] text-[#9299a3] transition-all hover:border-[rgba(150,158,170,0.18)] hover:text-[#dde1e6] disabled:cursor-not-allowed disabled:opacity-40";

function isPlainChatMode(model: StudioChatSkillModel) {
  return model.skillState.conversationSkillId === null && model.skillState.nextTurnSkillId === null;
}

function resolveModeButtonClassName(active: boolean) {
  return `inline-flex h-8 items-center justify-center rounded-full px-3 text-[13px] font-semibold transition-all ${
    active
      ? "bg-[rgba(160,150,130,0.12)] text-[#a09682] border border-[rgba(160,150,130,0.20)]"
      : "bg-[#252a33] text-[#9299a3] border border-[rgba(150,158,170,0.10)] hover:text-[#dde1e6] hover:border-[rgba(150,158,170,0.18)]"
  }`;
}

function resolveTriggerLabel(headline: string) {
  if (headline.startsWith("当前会话 · ")) {
    return `会话 · ${headline.slice("当前会话 · ".length)}`;
  }
  return headline;
}
