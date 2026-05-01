"use client";

import { useEffect, useRef } from "react";
import { StudioDialog } from "@/components/ui/studio-dialog";

type StudioDocumentTreeDialogProps = {
  confirmLoading?: boolean;
  description: string;
  nameValue?: string;
  okText: string;
  onCancel: () => void;
  onConfirm: () => void;
  onNameChange?: (value: string) => void;
  open: boolean;
  title: string;
};

export function StudioDocumentTreeDialog({
  confirmLoading = false,
  description,
  nameValue = "",
  okText,
  onCancel,
  onConfirm,
  onNameChange,
  open,
  title,
}: Readonly<StudioDocumentTreeDialogProps>) {
  const isInputMode = typeof onNameChange === "function";
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open && inputRef.current) {
      setTimeout(() => {
        inputRef.current?.focus();
        inputRef.current?.select();
      }, 100);
    }
  }, [open]);

  return (
    <StudioDialog
      open={open}
      title={title}
      description={description}
      confirmText={okText}
      cancelText="取消"
      confirmLoading={confirmLoading}
      confirmVariant={title.includes("删除") ? "danger" : "primary"}
      onConfirm={onConfirm}
      onCancel={onCancel}
      width={420}
    >
      {isInputMode ? (
        <div className="studio-dialog-input-wrap">
          <input
            ref={inputRef}
            className="studio-dialog-input"
            placeholder="输入名称"
            type="text"
            value={nameValue}
            onChange={(e) => onNameChange?.(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                onConfirm();
              }
            }}
          />
        </div>
      ) : null}
    </StudioDialog>
  );
}
