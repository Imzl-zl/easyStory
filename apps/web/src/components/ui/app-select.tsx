"use client";

import { Select } from "@arco-design/web-react";
import { useEffect, useMemo } from "react";

export type AppSelectOption = {
  description?: string;
  disabled?: boolean;
  label: string;
  value: string;
};

type AppSelectProps = {
  ariaLabel?: string;
  className?: string;
  density?: "default" | "roomy";
  disabled?: boolean;
  emptyText?: string;
  getPopupContainer?: (node: HTMLElement) => Element;
  id?: string;
  options: ReadonlyArray<AppSelectOption>;
  placeholder?: string;
  popupClassName?: string;
  value?: string;
  onChange: (value: string) => void;
};

type ResolvedOption = AppSelectOption & {
  isInvalid?: boolean;
};

const DEFAULT_EMPTY_TEXT = "暂无可选项";
const INVALID_VALUE_LABEL_PREFIX = "当前值不可用";
const INVALID_VALUE_DESCRIPTION = "这项配置已不在可选范围内，请重新选择。";

export function AppSelect({
  ariaLabel,
  className,
  density = "default",
  disabled = false,
  emptyText = DEFAULT_EMPTY_TEXT,
  getPopupContainer,
  id,
  options,
  placeholder,
  popupClassName,
  value,
  onChange,
}: Readonly<AppSelectProps>) {
  const resolvedOptions = useMemo(
    () => buildResolvedOptions(options, value),
    [options, value],
  );
  const resolvedValue = resolveAppSelectValueProp(resolvedOptions, value);
  const currentOption = resolvedOptions.find((option) => option.value === resolvedValue);

  useInvalidValueWarning(currentOption, value);

  return (
    <Select
      aria-label={ariaLabel}
      allowClear={false}
      className={buildClassName(
        "w-full",
        density === "roomy" ? "min-h-[2.9rem] p-[0.62rem_0.95rem]" : undefined,
        className,
      )}
      disabled={disabled}
      dropdownMenuClassName="grid gap-[0.18rem]"
      getPopupContainer={getPopupContainer}
      id={id}
      notFoundContent={emptyText}
      placeholder={placeholder}
      showSearch={false}
      size="default"
      triggerProps={{
        autoAlignPopupMinWidth: true,
        className: buildClassName(
          "p-[0.28rem] border border-[var(--dropdown-border)] rounded-4 bg-[var(--dropdown-bg)] shadow-[var(--dropdown-shadow)] backdrop-blur-xl",
          popupClassName,
        ),
      }}
      value={resolvedValue}
      renderFormat={() => (
        currentOption ? (
          <span className={`text-[var(--text-primary)] text-[0.88rem] leading-normal ${currentOption.isInvalid ? "text-[var(--accent-warning)]" : ""}`}>
            {currentOption.label}
          </span>
        ) : undefined
      )}
      onChange={(nextValue) => onChange(resolveAppSelectValue(nextValue))}
    >
      {resolvedOptions.map((option) => (
        <Select.Option key={option.value} disabled={option.disabled} value={option.value}>
          <span className={`grid gap-[0.16rem] p-[0.62rem_0.82rem] rounded-3 transition-all ${option.isInvalid ? "border border-dashed rgba(183,121,31,0.28)] bg-[rgba(183,121,31,0.08)]" : ""}`}>
            <span className="text-[var(--text-primary)] text-[0.86rem] leading-relaxed">{option.label}</span>
            {option.description ? (
              <span className="text-[var(--text-secondary)] text-[0.74rem] leading-relaxed">{option.description}</span>
            ) : null}
          </span>
        </Select.Option>
      ))}
    </Select>
  );
}

function useInvalidValueWarning(option: ResolvedOption | undefined, value: string | undefined) {
  useEffect(() => {
    if (process.env.NODE_ENV === "production" || !option?.isInvalid || !value) {
      return;
    }
    console.warn(`[AppSelect] 收到不在可选范围内的值: "${value}"`);
  }, [option?.isInvalid, value]);
}

function buildResolvedOptions(
  options: ReadonlyArray<AppSelectOption>,
  value: string | undefined,
): ResolvedOption[] {
  if (!value || hasOptionValue(options, value)) {
    return [...options];
  }
  return [buildInvalidOption(value), ...options]
}

function buildInvalidOption(value: string): ResolvedOption {
  return {
    description: INVALID_VALUE_DESCRIPTION,
    disabled: true,
    isInvalid: true,
    label: `${INVALID_VALUE_LABEL_PREFIX}：${value}`,
    value,
  };
}

function hasOptionValue(options: ReadonlyArray<AppSelectOption>, value: string) {
  return options.some((option) => option.value === value)
}

function buildClassName(...parts: Array<string | undefined>) {
  return parts.filter(Boolean).join(" ")
}

function resolveAppSelectValue(value: string | number | { value: string | number }) {
  if (typeof value === "object" && value !== null && "value" in value) {
    return String(value.value)
  }
  return String(value)
}

function resolveAppSelectValueProp(options: ReadonlyArray<AppSelectOption>, value: string | undefined) {
  if (!value) {
    return hasOptionValue(options, "") ? "" : undefined
  }
  return hasOptionValue(options, value) ? value : undefined
}
