"use client";

import { useEffect, useRef, useState } from "react";

export function JsonTextAreaField<T>({
  emptyValue,
  helpText,
  label,
  minHeightClassName,
  onChange,
  onErrorChange,
  parseValue,
  syncKey,
  value,
}: Readonly<{
  emptyValue: T;
  helpText?: string;
  label: string;
  minHeightClassName?: string;
  onChange: (value: T) => void;
  onErrorChange: (message: string | null) => void;
  parseValue: (parsed: unknown) => { errorMessage: string | null; value: T | null };
  syncKey?: number | string;
  value: T;
}>) {
  const latestOnErrorChangeRef = useRef(onErrorChange);
  return (
    <JsonTextAreaFieldBody
      key={syncKey ?? label}
      emptyValue={emptyValue}
      helpText={helpText}
      label={label}
      latestOnErrorChangeRef={latestOnErrorChangeRef}
      minHeightClassName={minHeightClassName}
      parseValue={parseValue}
      value={value}
      onChange={onChange}
      onErrorChange={onErrorChange}
    />
  );
}

function JsonTextAreaFieldBody<T>({
  emptyValue,
  helpText,
  label,
  latestOnErrorChangeRef,
  minHeightClassName,
  onChange,
  onErrorChange,
  parseValue,
  value,
}: Readonly<{
  emptyValue: T;
  helpText?: string;
  label: string;
  latestOnErrorChangeRef: React.RefObject<(message: string | null) => void>;
  minHeightClassName?: string;
  onChange: (value: T) => void;
  onErrorChange: (message: string | null) => void;
  parseValue: (parsed: unknown) => { errorMessage: string | null; value: T | null };
  value: T;
}>) {
  const [text, setText] = useState(() => stringifyJson(value));
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    latestOnErrorChangeRef.current = onErrorChange;
  }, [latestOnErrorChangeRef, onErrorChange]);

  useEffect(() => {
    return () => {
      latestOnErrorChangeRef.current?.(null);
    };
  }, [latestOnErrorChangeRef]);

  return (
    <label className="block space-y-2">
      <span className="label-text">{label}</span>
      <textarea
        autoComplete="off"
        className={`ink-textarea ${minHeightClassName ?? "min-h-28"} font-mono text-sm`}
        spellCheck={false}
        value={text}
        onChange={(event) => {
          const nextText = event.target.value;
          setText(nextText);
          if (!nextText.trim()) {
            setErrorMessage(null);
            onErrorChange(null);
            onChange(emptyValue);
            return;
          }
          try {
            const parsed = JSON.parse(nextText) as unknown;
            const result = parseValue(parsed);
            setErrorMessage(result.errorMessage);
            onErrorChange(result.errorMessage);
            if (!result.errorMessage) {
              onChange(result.value as T);
            }
          } catch (error) {
            const nextError =
              error instanceof Error ? `完整配置格式有误：${error.message}` : "完整配置格式有误。";
            setErrorMessage(nextError);
            onErrorChange(nextError);
          }
        }}
      />
      {errorMessage ? <p className="text-sm text-accent-danger">{errorMessage}</p> : null}
      {helpText ? <p className="text-xs text-text-secondary">{helpText}</p> : null}
    </label>
  );
}

function stringifyJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}
