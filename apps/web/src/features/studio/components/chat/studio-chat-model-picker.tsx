"use client";

import { useMemo, useState } from "react";
import type { CSSProperties, RefObject } from "react";
import { Radio } from "@arco-design/web-react";

import { AppSelect } from "@/components/ui/app-select";
import {
  normalizeAssistantThinkingBudgetInput,
  resolveAssistantReasoningControl,
} from "@/features/shared/assistant/assistant-reasoning-support";
import type { StudioChatSettings, StudioProviderOption } from "@/features/studio/components/chat/studio-chat-support";

type StudioChatModelPickerProps = {
  isCredentialLoading: boolean;
  modelName: string;
  onClose: () => void;
  onModelNameChange: (value: string) => void;
  onProviderChange: (provider: string) => void;
  onReasoningEffortChange: (value: string) => void;
  onStreamOutputChange: (value: boolean) => void;
  onThinkingBudgetChange: (value: string) => void;
  onThinkingLevelChange: (value: string) => void;
  panelRef: RefObject<HTMLDivElement | null>;
  panelStyle?: CSSProperties;
  providerOptions: StudioProviderOption[];
  reasoningEffort: string;
  selectedCredentialApiDialect: string | null;
  selectedCredentialLabel: string | null;
  selectedProvider: string;
  streamOutput: boolean;
  thinkingBudget: string;
  thinkingLevel: string;
};

export function StudioChatModelPicker({
  isCredentialLoading,
  modelName,
  onClose,
  onModelNameChange,
  onProviderChange,
  onReasoningEffortChange,
  onStreamOutputChange,
  onThinkingBudgetChange,
  onThinkingLevelChange,
  panelRef,
  panelStyle,
  providerOptions,
  reasoningEffort,
  selectedCredentialApiDialect,
  selectedCredentialLabel,
  selectedProvider,
  streamOutput,
  thinkingBudget,
  thinkingLevel,
}: Readonly<StudioChatModelPickerProps>) {
  const [showProviderList, setShowProviderList] = useState(false);

  const currentProviderOption = useMemo(
    () =>
      providerOptions.find((option) => option.value === selectedProvider)
      ?? providerOptions[0]
      ?? null,
    [providerOptions, selectedProvider],
  );

  const reasoningControl = useMemo(
    () =>
      resolveAssistantReasoningControl({
        apiDialect: selectedCredentialApiDialect,
        modelName: modelName || currentProviderOption?.defaultModel,
      }),
    [currentProviderOption?.defaultModel, selectedCredentialApiDialect, modelName],
  );

  const handleSelectProvider = (provider: string) => {
    setShowProviderList(false);
    onProviderChange(provider);
  };

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 100 }}>
      <div
        className="chat-panel-overlay"
        style={{ position: "absolute", inset: 0, zIndex: 1 }}
        role="button"
        tabIndex={0}
        onClick={() => { setShowProviderList(false); onClose(); }}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { setShowProviderList(false); onClose(); } }}
      />
      <div
        className="model-picker-panel overflow-y-auto"
        ref={panelRef}
        style={{ ...panelStyle, zIndex: 2, position: "absolute" }}
      >
        <div className="model-picker-header">
          <div>
            <h3 className="model-picker-header__title">切换模型</h3>
            <p className="model-picker-header__subtitle">
              {selectedCredentialLabel ?? "选择渠道与模型配置"}
            </p>
          </div>
          <button
            className="model-picker-header__close"
            type="button"
            onClick={() => { setShowProviderList(false); onClose(); }}
          >
            <PanelCloseIcon />
          </button>
        </div>

        <div className="model-picker-body">
          <div className="model-field">
            <label className="model-field__label">
              <svg aria-hidden="true" className="model-field__label-icon" fill="none" height="14" viewBox="0 0 24 24" width="14">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
              </svg>
              渠道
            </label>
            <div className="relative">
              <button
                aria-expanded={showProviderList}
                className="provider-select-trigger"
                type="button"
                onClick={() => setShowProviderList((v) => !v)}
              >
                <span className="provider-select-trigger__label">
                  {currentProviderOption?.label ?? (isCredentialLoading ? "读取中..." : "选择渠道")}
                </span>
                <svg
                  aria-hidden="true"
                  className={`provider-select-trigger__chevron ${showProviderList ? "provider-select-trigger__chevron--open" : ""}`}
                  fill="none"
                  height="16"
                  viewBox="0 0 24 24"
                  width="16"
                >
                  <path d="M6 9l6 6 6-6" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                </svg>
              </button>
              {showProviderList ? (
                <div className="provider-select-dropdown">
                  {providerOptions.length > 0 ? (
                    providerOptions.map((option) => {
                      const selected = option.value === selectedProvider;
                      return (
                        <button
                          className={`provider-option ${selected ? "provider-option--selected" : ""}`}
                          key={option.value}
                          type="button"
                          onMouseDown={(event) => {
                            event.preventDefault();
                            handleSelectProvider(option.value);
                          }}
                        >
                          <span className="provider-option__indicator">
                            <span className="provider-option__indicator-dot" />
                          </span>
                          <span className="provider-option__content">
                            <span className="provider-option__label">{option.label}</span>
                            {option.description ? (
                              <span className="provider-option__desc">{option.description}</span>
                            ) : null}
                          </span>
                        </button>
                      );
                    })
                  ) : (
                    <div className="provider-select-empty">
                      <div className="provider-select-empty__icon">
                        <svg aria-hidden="true" fill="none" height="20" viewBox="0 0 24 24" width="20">
                          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" fill="currentColor" />
                        </svg>
                      </div>
                      <p>{isCredentialLoading ? "正在读取渠道..." : "当前没有可用渠道"}</p>
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          </div>

          <div className="model-field">
            <label className="model-field__label">
              <svg aria-hidden="true" className="model-field__label-icon" fill="none" height="14" viewBox="0 0 24 24" width="14">
                <path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
              </svg>
              模型
            </label>
            <input
              className="model-input"
              autoComplete="off"
              placeholder="留空则使用渠道默认模型"
              spellCheck={false}
              value={modelName}
              onChange={(e) => onModelNameChange(e.target.value)}
            />
          </div>

          {reasoningControl.kind !== "none" ? (
            <div className="model-settings-card">
              <p className="model-settings-card__title">{reasoningControl.title}</p>
              {reasoningControl.description ? (
                <p className="model-settings-card__desc">{reasoningControl.description}</p>
              ) : null}
              {reasoningControl.kind === "gemini_budget" ? (
                <div className="flex flex-col gap-3">
                  <div className="model-chip-group">
                    <ModelChip
                      active={thinkingBudget === ""}
                      label="跟随默认"
                      onClick={() => onThinkingBudgetChange("")}
                    />
                    {reasoningControl.allowDisable ? (
                      <ModelChip
                        active={thinkingBudget === "0"}
                        label="关闭思考"
                        onClick={() => onThinkingBudgetChange("0")}
                      />
                    ) : null}
                    {reasoningControl.allowDynamic ? (
                      <ModelChip
                        active={thinkingBudget === "-1"}
                        label="动态思考"
                        onClick={() => onThinkingBudgetChange("-1")}
                      />
                    ) : null}
                  </div>
                  <input
                    className="model-input"
                    autoComplete="off"
                    inputMode="numeric"
                    placeholder={reasoningControl.placeholder}
                    spellCheck={false}
                    value={thinkingBudget}
                    onChange={(e) => onThinkingBudgetChange(normalizeAssistantThinkingBudgetInput(e.target.value))}
                  />
                </div>
              ) : (
                <div>
                  <AppSelect
                    ariaLabel={reasoningControl.title}
                    className="min-w-0"
                    options={reasoningControl.options}
                    value={reasoningControl.kind === "openai" ? reasoningEffort : thinkingLevel}
                    onChange={(value) =>
                      reasoningControl.kind === "openai"
                        ? onReasoningEffortChange(value)
                        : onThinkingLevelChange(value)}
                  />
                </div>
              )}
            </div>
          ) : null}

          <div className="model-settings-card">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="model-settings-card__title">回复显示方式</p>
              <Radio.Group
                aria-label="回复显示方式"
                mode="fill"
                size="small"
                type="button"
                value={streamOutput ? "stream" : "buffered"}
                onChange={(value) => onStreamOutputChange(value === "stream")}
              >
                <Radio value="stream">流式</Radio>
                <Radio value="buffered">非流式</Radio>
              </Radio.Group>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ModelChip({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      className={`model-chip ${active ? "model-chip--active" : ""}`}
      type="button"
      onClick={onClick}
    >
      {label}
    </button>
  );
}

function PanelCloseIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
    </svg>
  );
}
