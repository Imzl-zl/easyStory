"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import { Input, Message, Radio } from "@arco-design/web-react";

import { AppSelect } from "@/components/ui/app-select";
import { renderFloatingPanel, useFloatingPanelStyle } from "@/components/ui/floating-panel-support";
import type {
  DocumentTreeNode,
  StudioChatLayoutMode,
} from "@/features/studio/components/page/studio-page-support";
import { getErrorMessage } from "@/lib/api/client";
import {
  normalizeAssistantThinkingBudgetInput,
  resolveAssistantReasoningControl,
} from "@/features/shared/assistant/assistant-reasoning-support";

import { STUDIO_ATTACHMENT_ACCEPT, type StudioChatAttachmentMeta } from "@/features/studio/components/chat/studio-chat-attachment-support";
import { submitStudioComposerMessage } from "@/features/studio/components/chat/studio-chat-composer-support";
import { StudioChatContextSelectorContent } from "@/features/studio/components/chat/studio-chat-context-selector";
import type { StudioChatSettings, StudioProviderOption } from "@/features/studio/components/chat/studio-chat-support";
import { resolveStudioWriteToggleDisabled } from "@/features/studio/components/chat/studio-chat-write-support";

type StudioChatComposerProps = {
  attachments: StudioChatAttachmentMeta[];
  availableContexts: DocumentTreeNode[];
  canChat: boolean;
  layoutMode?: StudioChatLayoutMode;
  composerText: string;
  credentialNotice: string | null;
  credentialSettingsHref: string;
  isCredentialLoading: boolean;
  isResponding: boolean;
  modelButtonLabel: string;
  onAttachFiles: (files: FileList | null) => void;
  onComposerTextChange: (value: string) => void;
  onModelNameChange: (value: string) => void;
  onProviderChange: (provider: string) => void;
  onReasoningEffortChange: (value: string) => void;
  onRemoveAttachment: (attachmentId: string) => void;
  onSendMessage: (message: string) => boolean | Promise<boolean>;
  onStreamOutputChange: (value: boolean) => void;
  onThinkingBudgetChange: (value: string) => void;
  onThinkingLevelChange: (value: string) => void;
  onToggleContext: (path: string) => void;
  onToggleWriteToCurrentDocument: () => void;
  providerOptions: StudioProviderOption[];
  selectedContextPaths: string[];
  selectedCredentialApiDialect: string | null;
  selectedCredentialLabel: string | null;
  settings: Pick<
    StudioChatSettings,
    "modelName" | "provider" | "reasoningEffort" | "streamOutput" | "thinkingBudget" | "thinkingLevel"
  >;
  showWriteToCurrentDocument: boolean;
  writeIntentNotice: string | null;
  writeTargetDisabledReason: string | null;
  isWriteToCurrentDocumentEnabled: boolean;
};

const MODEL_PICKER_PROVIDER_LIST_CLASS =
  "mt-2 grid gap-1 rounded-2xl bg-glass shadow-glass-heavy p-1 max-h-56 overflow-y-auto";

export function StudioChatComposer({
  attachments,
  availableContexts,
  canChat,
  layoutMode = "default",
  composerText,
  credentialNotice,
  credentialSettingsHref,
  isCredentialLoading,
  isResponding,
  modelButtonLabel,
  onAttachFiles,
  onComposerTextChange,
  onModelNameChange,
  onProviderChange,
  onReasoningEffortChange,
  onRemoveAttachment,
  onSendMessage,
  onStreamOutputChange,
  onThinkingBudgetChange,
  onThinkingLevelChange,
  onToggleContext,
  onToggleWriteToCurrentDocument,
  providerOptions,
  selectedContextPaths,
  selectedCredentialApiDialect,
  selectedCredentialLabel,
  settings,
  showWriteToCurrentDocument,
  writeIntentNotice,
  writeTargetDisabledReason,
  isWriteToCurrentDocumentEnabled,
}: Readonly<StudioChatComposerProps>) {
  const compactLayout = layoutMode !== "default";
  const iconLayout = layoutMode === "icon";
  const [showModelPicker, setShowModelPicker] = useState(false);
  const [showProviderList, setShowProviderList] = useState(false);
  const [showContextSelector, setShowContextSelector] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const modelPickerRef = useRef<HTMLDivElement>(null);
  const modelButtonRef = useRef<HTMLButtonElement>(null);
  const contextSelectorRef = useRef<HTMLDivElement>(null);
  const contextButtonRef = useRef<HTMLButtonElement>(null);
  const modelPickerStyle = useFloatingPanelStyle(showModelPicker, modelButtonRef, {
    align: "right",
    maxHeight: 600,
    preferredWidth: 352,
    side: "top",
  });
  const contextSelectorStyle = useFloatingPanelStyle(showContextSelector, contextButtonRef, {
    align: "left",
    maxHeight: 320,
    preferredWidth: 352,
    side: "top",
  });

  const currentProviderOption = useMemo(
    () =>
      providerOptions.find((option) => option.value === settings.provider)
      ?? providerOptions[0]
      ?? null,
    [providerOptions, settings.provider],
  );
  const reasoningControl = useMemo(
    () =>
      resolveAssistantReasoningControl({
        apiDialect: selectedCredentialApiDialect,
        modelName: settings.modelName || currentProviderOption?.defaultModel,
      }),
    [currentProviderOption?.defaultModel, selectedCredentialApiDialect, settings.modelName],
  );

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      const target = event.target;
      if (target instanceof HTMLElement && target.closest(".arco-trigger-popup")) {
        return;
      }
      if (
        modelPickerRef.current &&
        !modelPickerRef.current.contains(target as Node) &&
        modelButtonRef.current &&
        !modelButtonRef.current.contains(target as Node)
      ) {
        setShowProviderList(false);
        setShowModelPicker(false);
      }
      if (
        contextSelectorRef.current &&
        !contextSelectorRef.current.contains(target as Node) &&
        contextButtonRef.current &&
        !contextButtonRef.current.contains(target as Node)
      ) {
        setShowContextSelector(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleToggleContextSelector = useCallback(() => {
    setShowModelPicker(false);
    setShowProviderList(false);
    setShowContextSelector((visible) => !visible);
  }, []);

  const handleToggleModelPicker = useCallback(() => {
    setShowContextSelector(false);
    setShowProviderList(false);
    setShowModelPicker((visible) => !visible);
  }, []);

  const handleToggleProviderList = useCallback(() => {
    setShowProviderList((visible) => !visible);
  }, []);

  const handleSelectProvider = useCallback((provider: string) => {
    setShowProviderList(false);
    onProviderChange(provider);
  }, [onProviderChange]);

  const handleUnexpectedSendError = useCallback((error: unknown) => {
    console.error("Studio chat composer send failed unexpectedly.", error);
    Message.error(getErrorMessage(error));
  }, []);

  const handleSubmit = useCallback(() => {
    submitStudioComposerMessage({
      canChat,
      composerText,
      isResponding,
      onSendMessage,
      onUnexpectedError: handleUnexpectedSendError,
    });
  }, [canChat, composerText, handleUnexpectedSendError, isResponding, onSendMessage]);

  const handleComposerKeyDown = useCallback(
    (event: KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) return;
      event.preventDefault();
      handleSubmit();
    },
    [handleSubmit],
  );

  return (
    <div className="relative z-20 shrink-0 bg-gradient-to-b from-surface to-glass-heavy">
      <div className="relative z-20 px-3 py-2.5">
        {credentialNotice ? (
          <div className="studio-notice studio-notice--warning">
            <div className="studio-notice__icon">
              <AlertIcon />
            </div>
            <p className="studio-notice__text">{credentialNotice}</p>
            <Link className="studio-notice__action" href={credentialSettingsHref}>
              模型连接
              <JumpLinkIcon />
            </Link>
          </div>
        ) : null}

        {attachments.length > 0 ? (
          <div className="mb-1.5 flex flex-wrap gap-1.5">
            {attachments.map((attachment) => (
              <button
                className="inline-flex items-center gap-1.5 h-6 px-2 rounded-md bg-accent-primary/10 text-xs text-text-primary hover:bg-accent-primary-muted transition-colors"
                key={attachment.id}
                type="button"
                onClick={() => onRemoveAttachment(attachment.id)}
              >
                <span className="truncate max-w-[120px]">{attachment.name}</span>
                <span className="opacity-60 hover:opacity-100">×</span>
              </button>
            ))}
          </div>
        ) : null}

        <Input.TextArea
          autoSize={{ maxRows: 5, minRows: 2 }}
          className="studio-composer-textarea w-full resize-none"
          placeholder={canChat ? "输入要求，或拖入文件…" : "先配置模型连接"}
          value={composerText}
          onChange={onComposerTextChange}
          onKeyDown={handleComposerKeyDown}
        />

        <div className={`mt-1.5 flex gap-2 ${compactLayout ? "flex-col items-stretch" : "items-start justify-between"}`}>
          <div className="flex min-w-0 flex-1 flex-wrap items-center gap-1">
            <ToolbarIconButton label="上传文件" onClick={() => fileInputRef.current?.click()}>
              <PaperclipIcon />
            </ToolbarIconButton>

            <div className="relative">
              <ToolbarChipButton
                active={showContextSelector}
                badge={selectedContextPaths.length > 0 ? String(selectedContextPaths.length) : null}
                iconOnly={iconLayout}
                label={`上下文 ${selectedContextPaths.length}`}
                onClick={handleToggleContextSelector}
                buttonRef={contextButtonRef}
              >
                <ContextIcon />
              </ToolbarChipButton>

              {showContextSelector ? renderFloatingPanel(
                <StudioChatContextSelectorContent
                  availableContexts={availableContexts}
                  onToggleContext={onToggleContext}
                  panelRef={contextSelectorRef}
                  panelStyle={contextSelectorStyle}
                  selectedContextPaths={selectedContextPaths}
                />,
              ) : null}
            </div>

            <div className="relative">
              <ToolbarChipButton
                active={showModelPicker}
                iconOnly={iconLayout}
                label={modelButtonLabel}
                onClick={handleToggleModelPicker}
                buttonRef={modelButtonRef}
              >
                <SparkIcon />
              </ToolbarChipButton>

              {showModelPicker ? renderFloatingPanel(
                <div style={{ position: 'fixed', inset: 0, zIndex: 100 }}>
                  <div
                    className="chat-panel-overlay"
                    style={{ position: 'absolute', inset: 0, zIndex: 1 }}
                    role="button"
                    tabIndex={0}
                    onClick={() => {
                      setShowProviderList(false);
                      setShowModelPicker(false);
                    }}
                    onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { setShowProviderList(false); setShowModelPicker(false); } }}
                  />
                  <div
                    className="chat-model-panel overflow-y-auto"
                    ref={modelPickerRef}
                    style={{ ...modelPickerStyle, zIndex: 2, position: 'absolute' }}
                  >
                    <div className="chat-panel-header">
                      <div>
                        <h3 className="chat-panel-header__title">切换模型</h3>
                        <p className="chat-panel-header__subtitle">
                          {selectedCredentialLabel ?? "先选可用渠道，再决定模型名"}
                        </p>
                      </div>
                      <button
                        className="chat-panel-header__close"
                        type="button"
                        onClick={() => {
                          setShowProviderList(false);
                          setShowModelPicker(false);
                        }}
                      >
                        ×
                      </button>
                    </div>
                    <div className="chat-model-form">
                      {/* 渠道选择 */}
                      <div className="chat-model-form__group">
                        <label className="chat-model-form__label">渠道</label>
                        <div className="relative">
                          <button
                            aria-expanded={showProviderList}
                            className="chat-model-form__select flex items-center justify-between text-left"
                            type="button"
                            onClick={handleToggleProviderList}
                          >
                            <span className="min-w-0 flex-1 truncate font-semibold text-[14px]">
                              {currentProviderOption?.label ?? (isCredentialLoading ? "读取中..." : "选择渠道")}
                            </span>
                            <span className={`shrink-0 text-[11px] text-[#686e77] transition-transform duration-200 ${showProviderList ? "rotate-180" : ""}`}>▾</span>
                          </button>
                          {showProviderList ? (
                            <div className="mt-2 grid gap-1 rounded-xl bg-[#1e2129] border border-[rgba(150,158,170,0.10)] p-2 max-h-64 overflow-y-auto shadow-lg">
                              {providerOptions.length > 0 ? (
                                providerOptions.map((option) => {
                                  const selected = option.value === settings.provider;
                                  return (
                                    <button
                                      className={`flex w-full flex-col items-start gap-1 rounded-lg px-3 py-2.5 text-left transition-colors ${selected ? "bg-[rgba(160,150,130,0.10)] text-[#a09682]" : "text-[#dde1e6] hover:bg-[rgba(150,158,170,0.06)]"}`}
                                      key={option.value}
                                      type="button"
                                      onMouseDown={(event) => {
                                        event.preventDefault();
                                        handleSelectProvider(option.value);
                                      }}
                                    >
                                      <span className="text-[14px] font-semibold leading-relaxed">{option.label}</span>
                                      {option.description ? (
                                        <span className="text-[12px] leading-relaxed text-[#686e77]">{option.description}</span>
                                      ) : null}
                                    </button>
                                  );
                                })
                              ) : (
                                <p className="px-3 py-3 text-[14px] text-[#686e77]">
                                  {isCredentialLoading ? "正在读取渠道..." : "当前没有可用渠道"}
                                </p>
                              )}
                            </div>
                          ) : null}
                        </div>
                      </div>

                      {/* 模型输入 */}
                      <div className="chat-model-form__group">
                        <label className="chat-model-form__label">模型</label>
                        <input
                          className="chat-model-form__input"
                          autoComplete="off"
                          placeholder="留空则跟随当前渠道默认模型"
                          spellCheck={false}
                          value={settings.modelName}
                          onChange={(e) => onModelNameChange(e.target.value)}
                        />
                      </div>

                      {/* 推理控制 */}
                      <div className="chat-model-form__section">
                        <p className="m-0 text-[14px] font-bold text-[#dde1e6]">{reasoningControl.title}</p>
                        {reasoningControl.description ? (
                          <p className="mt-1 text-[13px] leading-5 text-[#9299a3]">{reasoningControl.description}</p>
                        ) : null}
                        {reasoningControl.kind === "gemini_budget" ? (
                          <div className="mt-3 space-y-3">
                            <div className="flex flex-wrap gap-2">
                              <ReasoningChipButton
                                active={settings.thinkingBudget === ""}
                                label="跟随默认"
                                onClick={() => onThinkingBudgetChange("")}
                              />
                              {reasoningControl.allowDisable ? (
                                <ReasoningChipButton
                                  active={settings.thinkingBudget === "0"}
                                  label="关闭思考"
                                  onClick={() => onThinkingBudgetChange("0")}
                                />
                              ) : null}
                              {reasoningControl.allowDynamic ? (
                                <ReasoningChipButton
                                  active={settings.thinkingBudget === "-1"}
                                  label="动态思考"
                                  onClick={() => onThinkingBudgetChange("-1")}
                                />
                              ) : null}
                            </div>
                            <input
                              className="chat-model-form__input"
                              autoComplete="off"
                              inputMode="numeric"
                              placeholder={reasoningControl.placeholder}
                              spellCheck={false}
                              value={settings.thinkingBudget}
                              onChange={(e) => onThinkingBudgetChange(normalizeAssistantThinkingBudgetInput(e.target.value))}
                            />
                          </div>
                        ) : reasoningControl.kind === "none" ? null : (
                          <div className="mt-3">
                            <AppSelect
                              ariaLabel={reasoningControl.title}
                              className="min-w-0"
                              options={reasoningControl.options}
                              value={reasoningControl.kind === "openai" ? settings.reasoningEffort : settings.thinkingLevel}
                              onChange={(value) =>
                                reasoningControl.kind === "openai"
                                  ? onReasoningEffortChange(value)
                                  : onThinkingLevelChange(value)}
                            />
                          </div>
                        )}
                      </div>

                      {/* 回复显示方式 */}
                      <div className="chat-model-form__section mt-4">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <p className="m-0 text-[14px] font-bold text-[#dde1e6]">回复显示方式</p>
                          <Radio.Group
                            aria-label="回复显示方式"
                            mode="fill"
                            size="small"
                            type="button"
                            value={settings.streamOutput ? "stream" : "buffered"}
                            onChange={(value) => onStreamOutputChange(value === "stream")}
                          >
                            <Radio value="stream">流式</Radio>
                            <Radio value="buffered">非流式</Radio>
                          </Radio.Group>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>,
              ) : null}
            </div>

            {showWriteToCurrentDocument ? (
              <ToolbarToggleButton
                active={isWriteToCurrentDocumentEnabled}
                disabled={resolveStudioWriteToggleDisabled({
                  enabled: isWriteToCurrentDocumentEnabled,
                  writeTargetDisabledReason,
                })}
                iconOnly={iconLayout}
                label={isWriteToCurrentDocumentEnabled ? "本轮改当前稿" : "改当前稿"}
                title={writeTargetDisabledReason ?? "显式开启后，助手本轮才可改写当前文稿。"}
                onClick={onToggleWriteToCurrentDocument}
              >
                <WriteIcon />
              </ToolbarToggleButton>
            ) : null}
          </div>

          <button
            className={`ink-button ${compactLayout ? "w-full" : "shrink-0"}`}
            disabled={!canChat || isResponding}
            type="button"
            onClick={handleSubmit}
          >
            {isResponding ? "发送中…" : "发送"}
          </button>
        </div>

        {writeIntentNotice ? (
          <div className={`studio-write-notice ${!isWriteToCurrentDocumentEnabled ? "studio-write-notice--disabled" : ""}`}>
            <WriteIcon />
            <span>{writeIntentNotice}</span>
          </div>
        ) : null}

        <input
          accept={STUDIO_ATTACHMENT_ACCEPT}
          className="hidden"
          ref={fileInputRef}
          type="file"
          multiple
          onChange={(e) => onAttachFiles(e.target.files)}
        />
      </div>
    </div>
  );
}

function ReasoningChipButton({
  active,
  label,
  onClick,
}: Readonly<{
  active: boolean;
  label: string;
  onClick: () => void;
}>) {
  return (
    <button
      className="ink-toolbar-chip rounded-pill"
      data-active={active ? "true" : undefined}
      type="button"
      onClick={onClick}
    >
      {label}
    </button>
  );
}

function ToolbarIconButton({
  children,
  label,
  onClick,
}: {
  children: ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      aria-label={label}
      className="ink-toolbar-icon"
      title={label}
      type="button"
      onClick={onClick}
    >
      <span className="opacity-80">{children}</span>
    </button>
  );
}

function ToolbarChipButton({
  active = false,
  badge = null,
  children,
  iconOnly = false,
  label,
  onClick,
  buttonRef,
}: {
  active?: boolean;
  badge?: string | null;
  children: ReactNode;
  iconOnly?: boolean;
  label: string;
  onClick: () => void;
  buttonRef?: React.Ref<HTMLButtonElement>;
}) {
  return (
    <button
      ref={buttonRef}
      aria-label={label}
      className={`ink-toolbar-chip ${iconOnly ? "text-[0px]" : ""}`}
      data-active={active ? "true" : undefined}
      data-compact={iconOnly ? "true" : undefined}
      title={label}
      type="button"
      onClick={onClick}
    >
      <span className="opacity-80">{children}</span>
      {!iconOnly ? <span className="min-w-0 truncate">{label}</span> : null}
      {!iconOnly ? (
        <span className={`text-[10px] transition-transform ${active ? "rotate-180 opacity-70" : "opacity-40"}`}>
          ▾
        </span>
      ) : null}
      {iconOnly && badge ? (
        <span className="absolute -right-1 -top-1 inline-flex min-w-4 items-center justify-center rounded-full bg-accent-primary px-1 text-[9px] leading-4 text-white shadow-sm">
          {badge}
        </span>
      ) : null}
    </button>
  );
}

function ToolbarToggleButton({
  active = false,
  children,
  disabled = false,
  iconOnly = false,
  label,
  onClick,
  title,
}: {
  active?: boolean;
  children: ReactNode;
  disabled?: boolean;
  iconOnly?: boolean;
  label: string;
  onClick: () => void;
  title?: string;
}) {
  return (
    <button
      aria-pressed={active}
      aria-label={label}
      className={`ink-toolbar-toggle ${iconOnly ? "text-[0px]" : ""}`}
      data-compact={iconOnly ? "true" : undefined}
      disabled={disabled}
      title={title ?? label}
      type="button"
      onClick={onClick}
    >
      <span className={active ? "opacity-100" : "opacity-80"}>{children}</span>
      {!iconOnly ? <span className="min-w-0 truncate">{label}</span> : null}
    </button>
  );
}

function JumpLinkIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="14" viewBox="0 0 16 16" width="14">
      <path
        d="M6 4h6v6m-1-5-6.5 6.5M4 7.5V12h4.5"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
      />
    </svg>
  );
}

function AlertIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="16" viewBox="0 0 24 24" width="16">
      <path
        d="M12 9v4m0 4h.01M10.3 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.7 3.86a2 2 0 0 0-3.42 0Z"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.7"
      />
    </svg>
  );
}

function PaperclipIcon() {
  return <ComposerIcon path="M9.5 18.5 15.4 12.6a3 3 0 0 0-4.2-4.2l-6.3 6.3a4.5 4.5 0 0 0 6.4 6.4l6.7-6.7" />;
}

function ContextIcon() {
  return <ComposerIcon path="M7 17h10M6 7.5h12l-1 9H7l-1-9Zm4-3h4" />;
}

function SparkIcon() {
  return <ComposerIcon path="m12 3 1.2 3.8L17 8l-3.8 1.2L12 13l-1.2-3.8L7 8l3.8-1.2L12 3Zm6 11 .7 2.3L21 17l-2.3.7L18 20l-.7-2.3L15 17l2.3-.7L18 14Z" />;
}

function WriteIcon() {
  return <ComposerIcon path="M5 19.2 5.7 15l8.9-8.9a1.8 1.8 0 0 1 2.5 0l1 1a1.8 1.8 0 0 1 0 2.5L9.2 18.5 5 19.2Zm7.1-11.4 3.7 3.7" />;
}

function ComposerIcon({ path }: { path: string }) {
  return (
    <svg aria-hidden="true" fill="none" height="16" viewBox="0 0 24 24" width="16">
      <path d={path} stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" />
    </svg>
  );
}
