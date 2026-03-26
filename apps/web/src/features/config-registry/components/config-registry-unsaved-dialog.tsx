"use client";

import { DialogShell } from "@/components/ui/dialog-shell";

export function ConfigRegistryUnsavedDialog({
  isOpen,
  isPending,
  message = "有未保存的更改，确定要离开吗？",
  onClose,
  onConfirm,
}: Readonly<{
  isOpen: boolean;
  isPending: boolean;
  message?: string;
  onClose: () => void;
  onConfirm: () => void;
}>) {
  if (!isOpen) {
    return null;
  }
  return (
    <DialogShell
      title="未保存更改"
      description="离开当前编辑上下文后，未保存内容会丢失。"
      onClose={onClose}
    >
      <div className="space-y-5">
        <p className="text-sm leading-6 text-[var(--text-secondary)]">{message}</p>
        <div className="flex flex-wrap justify-end gap-3">
          <button className="ink-button-secondary" disabled={isPending} type="button" onClick={onClose}>
            继续编辑
          </button>
          <button className="ink-button-danger" disabled={isPending} type="button" onClick={onConfirm}>
            确认离开
          </button>
        </div>
      </div>
    </DialogShell>
  );
}
