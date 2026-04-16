"use client";

import { Input, Modal } from "@arco-design/web-react";

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

  return (
    <Modal
      cancelText="取消"
      confirmLoading={confirmLoading}
      okText={okText}
      title={title}
      visible={open}
      onCancel={onCancel}
      onOk={onConfirm}
    >
      <div className="flex flex-col gap-3">
        <p className="m-0 text-sm leading-6 text-text-secondary">{description}</p>
        {isInputMode ? (
          <Input
            autoFocus
            placeholder="输入名称"
            value={nameValue}
            onChange={onNameChange}
            onPressEnter={onConfirm}
          />
        ) : null}
      </div>
    </Modal>
  );
}
