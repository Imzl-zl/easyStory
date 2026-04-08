export function submitStudioComposerMessage(options: {
  canChat: boolean;
  composerText: string;
  isResponding: boolean;
  onSendMessage: (message: string) => boolean | Promise<boolean>;
  onUnexpectedError?: (error: unknown) => void;
}) {
  const trimmed = options.composerText.trim();
  if (!trimmed || options.isResponding || !options.canChat) {
    return false;
  }
  void Promise.resolve().then(() => options.onSendMessage(trimmed)).catch((error) => {
    options.onUnexpectedError?.(error);
  });
  return true;
}
