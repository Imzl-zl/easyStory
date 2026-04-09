export async function runStudioSendOnce<T>(
  guard: { current: boolean },
  action: () => Promise<T>,
): Promise<T | false> {
  if (guard.current) {
    return false;
  }
  guard.current = true;
  try {
    return await action();
  } finally {
    guard.current = false;
  }
}
