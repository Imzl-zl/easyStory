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
            ? "bg-chat-panel shadow-md"
            : "bg-surface shadow-xs hover:shadow-sm"
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
        <span className="inline-flex shrink-0 items-center rounded-full bg-elevated px-2 py-0.5 text-[11px] font-semibold leading-4 text-accent-primary">
          Skill
        </span>
        <span className="min-w-0 flex-1 truncate text-[13px] font-medium leading-5 text-text-primary">
          {resolveTriggerLabel(model.skillState.headline)}
        </span>
        <span
          aria-hidden="true"
          className={`shrink-0 text-[11px] text-text-tertiary transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
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
      className="skill-panel"
      role="dialog"
      style={layout.panelStyle}
    >
      <div className="skill-panel-header">
        <div>
          <p className="skill-panel-header__eyebrow">Skill 模式</p>
          <h3 className="skill-panel-header__title">选择 Skill</h3>
          <p className="skill-panel-header__subtitle">{resultSummary}</p>
        </div>
        <button
          className="skill-panel-header__close"
          type="button"
          onClick={onClose}
        >
          <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
            <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
          </svg>
        </button>
      </div>

      <CurrentModeCard disabled={disabled} model={model} onClose={onClose} />

      <div className="skill-search">
        <label className="block">
          <span className="sr-only">筛选 Skill</span>
          <input
            className="skill-search__input"
            placeholder="按名称、描述或作用域筛选..."
            ref={searchInputRef}
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
      </div>

      <div className="skill-list">
        {model.skillErrorMessage ? (
          <SkillEmpty tone="danger">{model.skillErrorMessage}</SkillEmpty>
        ) : null}
        {model.skillsLoading ? <SkillEmpty>读取中…</SkillEmpty> : null}
        {!model.skillErrorMessage && !model.skillsLoading && model.skillOptions.length === 0 ? (
          <SkillEmpty>暂无可用 Skill</SkillEmpty>
        ) : null}
        {!model.skillErrorMessage && !model.skillsLoading && model.skillOptions.length > 0 && filteredSkillOptions.length === 0 ? (
          <SkillEmpty>无匹配结果</SkillEmpty>
        ) : null}
        {!model.skillErrorMessage && !model.skillsLoading && filteredSkillOptions.length > 0 ? (
          <ul className="flex flex-col">
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
    <div className="skill-current-mode">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="skill-current-mode__eyebrow">当前模式</p>
          <p className="skill-current-mode__name">
            {model.skillState.headline}
          </p>
          {model.skillState.detail ? (
            <p className="skill-current-mode__desc">
              {model.skillState.detail}
            </p>
          ) : null}
        </div>
        <button
          className={`skill-action-btn ${isPlainChatMode(model) ? "skill-action-btn--active" : "skill-action-btn--default"}`}
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
      <div className="skill-current-mode__actions">
        {model.skillState.nextTurnSkillId ? (
          <button
            className="skill-action-btn skill-action-btn--default"
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
            className="skill-action-btn skill-action-btn--default"
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
      <div className={`skill-option ${hasActiveMode ? "skill-option--active" : ""}`}>
        <div className="skill-option__header">
          <span className="skill-option__name">{option.label}</span>
          <span className="skill-option__scope">{option.scopeLabel}</span>
          {nextSelected ? (
            <span className="skill-option__badge skill-option__badge--next">本次</span>
          ) : null}
          {conversationSelected ? (
            <span className="skill-option__badge skill-option__badge--conversation">会话</span>
          ) : null}
        </div>
        {option.description ? (
          <p className="skill-option__desc">{option.description}</p>
        ) : null}
        <div className="skill-option__actions">
          <button
            className={`skill-action-btn ${nextSelected ? "skill-action-btn--active" : "skill-action-btn--default"}`}
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
            className={`skill-action-btn ${conversationSelected ? "skill-action-btn--active" : "skill-action-btn--default"}`}
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
    </li>
  );
}

function SkillEmpty({
  children,
  tone = "muted",
}: Readonly<{
  children: ReactNode;
  tone?: "danger" | "muted";
}>) {
  return (
    <div
      className={`skill-empty ${
        tone === "danger" ? "text-accent-danger" : ""
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

function isPlainChatMode(model: StudioChatSkillModel) {
  return model.skillState.conversationSkillId === null && model.skillState.nextTurnSkillId === null;
}

function resolveTriggerLabel(headline: string) {
  if (headline.startsWith("当前会话 · ")) {
    return `会话 · ${headline.slice("当前会话 · ".length)}`;
  }
  return headline;
}
