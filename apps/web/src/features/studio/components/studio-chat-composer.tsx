"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import type { KeyboardEvent, ReactNode, RefObject } from "react";
import { Button, Input } from "@arco-design/web-react";

import { AppSelect } from "@/components/ui/app-select";

import { STUDIO_ATTACHMENT_ACCEPT, type StudioChatAttachmentMeta } from "./studio-chat-attachment-support";
import type { StudioChatSettings, StudioProviderOption } from "./studio-chat-support";
import { buildStudioComposerHint } from "./studio-chat-ui-support";
import styles from "./studio-chat-composer.module.css";

type StudioChatComposerProps = {
  attachments: StudioChatAttachmentMeta[];
  canChat: boolean;
  credentialNotice: string | null;
  credentialSettingsHref: string;
  isCredentialLoading: boolean;
  isContextSelectorOpen: boolean;
  isResponding: boolean;
  modelButtonLabel: string;
  onAttachFiles: (files: FileList | null) => void;
  onModelNameChange: (value: string) => void;
  onProviderChange: (provider: string) => void;
  onRemoveAttachment: (attachmentId: string) => void;
  onSendMessage: (message: string) => void;
  onToggleContextSelector: () => void;
  providerOptions: StudioProviderOption[];
  selectedContextCount: number;
  selectedCredentialLabel: string | null;
  settings: Pick<StudioChatSettings, "modelName" | "provider">;
};

export function StudioChatComposer({
  attachments,
  canChat,
  credentialNotice,
  credentialSettingsHref,
  isCredentialLoading,
  isContextSelectorOpen,
  isResponding,
  modelButtonLabel,
  onAttachFiles,
  onModelNameChange,
  onProviderChange,
  onRemoveAttachment,
  onSendMessage,
  onToggleContextSelector,
  providerOptions,
  selectedContextCount,
  selectedCredentialLabel,
  settings,
}: Readonly<StudioChatComposerProps>) {
  const [inputText, setInputText] = useState("");
  const [showModelPicker, setShowModelPicker] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const modelPickerRef = useRef<HTMLDivElement | null>(null);
  const canSubmit = canChat && !isResponding && (inputText.trim().length > 0 || attachments.length > 0);

  useDismissStudioPopover(modelPickerRef, showModelPicker, () => setShowModelPicker(false));

  const handleSubmit = useCallback(() => {
    if (!canSubmit) {
      return;
    }
    onSendMessage(inputText.trim());
    setInputText("");
  }, [canSubmit, inputText, onSendMessage]);

  const handleComposerKeyDown = useCallback((event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) {
      return;
    }
    event.preventDefault();
    handleSubmit();
  }, [handleSubmit]);

  return (
    <footer className={styles.composer}>
      <div className={styles.composerInner}>
        {credentialNotice ? (
          <div className={styles.notice}>
            <p className={styles.noticeText}>{credentialNotice}</p>
            <Link className={styles.noticeLink} href={credentialSettingsHref}>
              模型连接
            </Link>
          </div>
        ) : null}
        {attachments.length > 0 ? (
          <div className={styles.attachmentRow}>
            {attachments.map((attachment) => (
              <button
                className={styles.attachmentChip}
                key={attachment.id}
                type="button"
                onClick={() => onRemoveAttachment(attachment.id)}
              >
                <span className={styles.attachmentName}>{attachment.name}</span>
                <span className={styles.attachmentRemove}>×</span>
              </button>
            ))}
          </div>
        ) : null}
        <Input.TextArea
          autoSize={{ maxRows: 6, minRows: 2 }}
          className={styles.composerInput}
          placeholder={canChat ? "写你的要求，或直接带文件进来一起改。" : "先启用可用模型后再开始提问"}
          value={inputText}
          onChange={setInputText}
          onKeyDown={handleComposerKeyDown}
        />
        <div className={styles.toolbar}>
          <div className={styles.toolbarLeft}>
            <ToolbarIconButton label="上传文件" onClick={() => fileInputRef.current?.click()}>
              <PaperclipIcon />
            </ToolbarIconButton>
            <ToolbarChipButton
              active={isContextSelectorOpen}
              label={selectedContextCount > 0 ? `上下文 ${selectedContextCount}` : "上下文"}
              onClick={onToggleContextSelector}
            >
              <ContextIcon />
            </ToolbarChipButton>
            <div className={styles.modelPickerWrap} ref={modelPickerRef}>
              <ToolbarChipButton
                active={showModelPicker}
                label={modelButtonLabel}
                onClick={() => setShowModelPicker((current) => !current)}
              >
                <SparkIcon />
              </ToolbarChipButton>
              {showModelPicker ? (
                <div className={styles.modelPicker}>
                  <div className={styles.modelPickerHeader}>
                    <p className={styles.modelPickerTitle}>切换模型</p>
                    <p className={styles.modelPickerHint}>{selectedCredentialLabel ?? "先选可用渠道，再决定模型名。"}</p>
                  </div>
                  <label className={styles.field}>
                    <span className={styles.fieldLabel}>渠道</span>
                    <AppSelect
                      ariaLabel="渠道"
                      options={providerOptions}
                      placeholder={isCredentialLoading ? "正在读取渠道..." : "选择可用渠道"}
                      value={settings.provider}
                      onChange={onProviderChange}
                    />
                  </label>
                  <label className={styles.field}>
                    <span className={styles.fieldLabel}>模型</span>
                    <Input
                      allowClear
                      autoComplete="off"
                      placeholder="留空则跟随当前渠道默认模型"
                      spellCheck={false}
                      value={settings.modelName}
                      onChange={onModelNameChange}
                    />
                  </label>
                </div>
              ) : null}
            </div>
          </div>
          <Button disabled={!canSubmit} loading={isResponding} shape="round" type="primary" onClick={handleSubmit}>
            发送
          </Button>
        </div>
        <p className={styles.hint}>
          {buildStudioComposerHint({
            attachmentCount: attachments.length,
            canChat,
            inputLength: inputText.length,
            isResponding,
          })}
        </p>
      </div>
      <input
        accept={STUDIO_ATTACHMENT_ACCEPT}
        className={styles.hiddenInput}
        multiple
        ref={fileInputRef}
        type="file"
        onChange={(event) => {
          onAttachFiles(event.target.files);
          event.target.value = "";
        }}
      />
    </footer>
  );
}

function useDismissStudioPopover(
  ref: RefObject<HTMLDivElement | null>,
  active: boolean,
  onDismiss: () => void,
) {
  useEffect(() => {
    if (!active) {
      return;
    }
    const handlePointerDown = (event: MouseEvent) => {
      if (ref.current?.contains(event.target as Node)) {
        return;
      }
      onDismiss();
    };
    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, [active, onDismiss, ref]);
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
    <button aria-label={label} className={styles.iconButton} type="button" onClick={onClick}>
      {children}
    </button>
  );
}

function ToolbarChipButton({
  active = false,
  children,
  label,
  onClick,
}: {
  active?: boolean;
  children: ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button className={`${styles.chipButton} ${active ? styles.chipButtonActive : ""}`} type="button" onClick={onClick}>
      <span className={styles.chipIcon}>{children}</span>
      <span className={styles.chipLabel}>{label}</span>
      <span className={styles.chipChevron}>⌄</span>
    </button>
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

function ComposerIcon({ path }: { path: string }) {
  return (
    <svg aria-hidden="true" fill="none" height="16" viewBox="0 0 24 24" width="16">
      <path d={path} stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" />
    </svg>
  );
}
