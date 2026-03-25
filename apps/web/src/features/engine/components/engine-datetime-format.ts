const UTC_DATETIME_FORMATTER = new Intl.DateTimeFormat("zh-CN", {
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
  timeZone: "UTC",
});

export function formatEngineDateTime(value: string | null): string {
  if (!value) {
    return "暂无";
  }
  return `${UTC_DATETIME_FORMATTER.format(new Date(value))} UTC`;
}
