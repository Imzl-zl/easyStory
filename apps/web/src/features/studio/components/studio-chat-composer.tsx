"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import { Button, Checkbox, Input } from "@arco-design/web-react";

import { AppSelect } from "@/components/ui/app-select";
import type { DocumentTreeNode } from "@/features/studio/components/studio-page-support";

import { STUDIO_ATTACHMENT_ACCEPT, type StudioChatAttachmentMeta } from "./studio-chat-attachment-support";
import type { StudioChatSettings, StudioProviderOption } from "./studio-chat-support";
import { buildStudioComposerHint } from "./studio-chat-ui-support";
import styles from "./studio-chat-composer.module.css";

type StudioChatComposerProps = {
  attachments: StudioChatAttachmentMeta[];
  availableContexts: DocumentTreeNode[];
  canChat: boolean;
  credentialNotice: string | null;
  credentialSettingsHref: string;
  isCredentialLoading: boolean;
  isResponding: boolean;
  modelButtonLabel: string;
  onAttachFiles: (files: FileList | null) => void;
  onModelNameChange: (value: string) => void;
  onProviderChange: (provider: string) => void;
  onRemoveAttachment: (attachmentId: string) => void;
  onSendMessage: (message: string) => void;
  onToggleContext: (path: string) => void;
  providerOptions: StudioProviderOption[];
  selectedContextPaths: string[];
  selectedCredentialLabel: string | null;
  settings: Pick<StudioChatSettings, "modelName" | "provider">;
};

export function StudioChatComposer({
  attachments,
  availableContexts,
  canChat,
  credentialNotice,
  credentialSettingsHref,
  isCredentialLoading,
  isResponding,
  modelButtonLabel,
  onAttachFiles,
  onModelNameChange,
  onProviderChange,
  onRemoveAttachment,
  onSendMessage,
  onToggleContext,
  providerOptions,
  selectedContextPaths,
  selectedCredentialLabel,
  settings,
}: Readonly<StudioChatComposerProps>) {
  const [inputText, setInputText] = useState("");
  const [showModelPicker, setShowModelPicker] = useState(false);
  const [showContextSelector, setShowContextSelector] = useState(false);
  const [contextSearchQuery, setContextSearchQuery] = useState("");
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({ 设定: true, 大纲: true, 章节: true });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const modelPickerRef = useRef<HTMLDivElement>(null);
  const contextSelectorRef = useRef<HTMLDivElement>(null);
  const contextButtonRef = useRef<HTMLButtonElement>(null);
  const composerRef = useRef<HTMLDivElement>(null);

  const toggleGroup = useCallback((groupName: string) => {
    setExpandedGroups((prev) => ({ ...prev, [groupName]: !prev[groupName] }));
  }, []);

  const providerOptionsForSelect = useMemo(
    () => providerOptions.map((p) => ({ label: p.label, value: p.value })),
    [providerOptions],
  );

  const filteredContexts = useMemo(() => {
    const fileContexts = availableContexts.filter((n) => n.type === "file");
    if (!contextSearchQuery.trim()) {
      return fileContexts;
    }
    const query = contextSearchQuery.toLowerCase();
    return fileContexts.filter(
      (node) =>
        node.path.toLowerCase().includes(query) ||
        node.label.toLowerCase().includes(query),
    );
  }, [availableContexts, contextSearchQuery]);

  const groupedContexts = useMemo(() => {
    const groups: { [key: string]: typeof filteredContexts } = {
      设定: [],
      大纲: [],
      章节: [],
    };

    filteredContexts.forEach((node) => {
      const path = node.path.toLowerCase();
      if (path.includes("设定") || path.includes("setting")) {
        groups["设定"].push(node);
      } else if (path.includes("大纲") || path.includes("outline")) {
        groups["大纲"].push(node);
      } else {
        groups["章节"].push(node);
      }
    });

    return groups;
  }, [filteredContexts]);

  const totalFileCount = availableContexts.filter((n) => n.type === "file").length;

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (modelPickerRef.current && !modelPickerRef.current.contains(event.target as Node)) {
        setShowModelPicker(false);
      }
      if (
        contextSelectorRef.current &&
        !contextSelectorRef.current.contains(event.target as Node) &&
        contextButtonRef.current &&
        !contextButtonRef.current.contains(event.target as Node)
      ) {
        setShowContextSelector(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSubmit = useCallback(() => {
    const trimmed = inputText.trim();
    if (!trimmed || isResponding) return;
    onSendMessage(trimmed);
    setInputText("");
  }, [inputText, isResponding, onSendMessage]);

  const handleComposerKeyDown = useCallback(
    (event: KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) return;
      event.preventDefault();
      handleSubmit();
    },
    [handleSubmit],
  );

  return (
    <div className={styles.composer} ref={composerRef}>
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

            <div className={styles.contextButtonWrap}>
              <ToolbarChipButton
                active={showContextSelector}
                label={`上下文 ${selectedContextPaths.length}`}
                onClick={() => setShowContextSelector((v) => !v)}
                buttonRef={contextButtonRef}
              >
                <ContextIcon />
              </ToolbarChipButton>

              {showContextSelector && (
                <div className={styles.contextSelector} ref={contextSelectorRef}>
                  <p className={styles.contextLabel}>
                    附加文档上下文 ({selectedContextPaths.length}/{totalFileCount})
                  </p>
                  <input
                    type="text"
                    className={styles.contextSearch}
                    placeholder="搜索章节..."
                    value={contextSearchQuery}
                    onChange={(e) => setContextSearchQuery(e.target.value)}
                  />
                  <div className={styles.contextList}>
                    {Object.entries(groupedContexts).map(([groupName, nodes]) => {
                      if (nodes.length === 0) return null;
                      return (
                        <div key={groupName} className={styles.contextGroup}>
                          <div
                            className={`${styles.contextGroupHeader} ${expandedGroups[groupName] ? styles.contextGroupHeaderExpanded : ""}`}
                            onClick={() => toggleGroup(groupName)}
                          >
                            <span className={styles.contextGroupIcon}>▶</span>
                            <span>{groupName}</span>
                            <span style={{ marginLeft: "auto", opacity: 0.6 }}>
                              {nodes.length}
                            </span>
                          </div>
                          {expandedGroups[groupName] && (
                            <div className={styles.contextGroupItems}>
                              {nodes.map((node) => (
                                <label className={styles.contextItem} key={node.id}>
                                  <Checkbox
                                    checked={selectedContextPaths.includes(node.path)}
                                    onChange={() => onToggleContext(node.path)}
                                  />
                                  <span className={styles.contextPath}>{node.label}</span>
                                  <span className={styles.contextPathSecondary}>
                                    {node.path.split("/").slice(-2, -1)[0]}
                                  </span>
                                </label>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            <div className={styles.modelPickerWrap}>
              <ToolbarChipButton
                active={showModelPicker}
                label={modelButtonLabel}
                onClick={() => setShowModelPicker((v) => !v)}
              >
                <SparkIcon />
              </ToolbarChipButton>

              {showModelPicker && (
                <div className={styles.modelPicker} ref={modelPickerRef}>
                  <div className={styles.modelPickerHeader}>
                    <p className={styles.modelPickerTitle}>切换模型</p>
                    <p className={styles.modelPickerHint}>
                      {selectedCredentialLabel ?? "先选可用渠道，再决定模型名。"}
                    </p>
                  </div>
                  <label className={styles.field}>
                    <span className={styles.fieldLabel}>渠道</span>
                    <AppSelect
                      aria-label="渠道"
                      options={providerOptionsForSelect}
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
              )}
            </div>
          </div>

          <Button
            disabled={!canChat || isResponding}
            loading={isResponding}
            shape="round"
            type="primary"
            onClick={handleSubmit}
          >
            发送
          </Button>
        </div>

        <input
          accept={STUDIO_ATTACHMENT_ACCEPT}
          className={styles.hiddenInput}
          ref={fileInputRef}
          type="file"
          multiple
          onChange={(e) => onAttachFiles(e.target.files)}
        />
      </div>
    </div>
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
  buttonRef,
}: {
  active?: boolean;
  children: ReactNode;
  label: string;
  onClick: () => void;
  buttonRef?: React.Ref<HTMLButtonElement>;
}) {
  return (
    <button
      ref={buttonRef}
      className={`${styles.chipButton} ${active ? styles.chipButtonActive : ""}`}
      type="button"
      onClick={onClick}
    >
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
