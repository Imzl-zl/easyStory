export function buildStudioComposerHint(options: {
  attachmentCount: number;
  canChat: boolean;
  inputLength: number;
  isResponding: boolean;
}) {
  if (!options.canChat) {
    return "先连接可用模型，再开始共创。";
  }
  if (options.isResponding) {
    return "正在根据当前文稿整理回复…";
  }
  if (options.attachmentCount > 0) {
    return `${options.inputLength} 字 · ${options.attachmentCount} 个文件待发送`;
  }
  return `${options.inputLength} 字 · Enter 发送`;
}

export function resolveStudioStatusLabel(options: {
  canChat: boolean;
  credentialState: "empty" | "error" | "loading" | "ready";
}) {
  if (options.credentialState === "loading") {
    return "读取中";
  }
  if (options.credentialState === "error") {
    return "连接异常";
  }
  if (!options.canChat) {
    return "待连接";
  }
  return "创作中";
}

export function resolveStudioStatusTone(
  credentialState: "empty" | "error" | "loading" | "ready",
) {
  if (credentialState === "error") {
    return "danger";
  }
  if (credentialState === "loading" || credentialState === "empty") {
    return "muted";
  }
  return "ready";
}
