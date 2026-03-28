export function ConfigRegistryBanner({
  ariaLive = false,
  message,
  tone,
}: Readonly<{
  ariaLive?: boolean;
  message: string;
  tone: "danger" | "info" | "muted";
}>) {
  const liveProps = ariaLive
    ? { "aria-atomic": true, "aria-live": "polite" as const, role: "status" as const }
    : {};

  if (tone === "danger") {
    return (
      <div
        className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]"
        {...liveProps}
      >
        {message}
      </div>
    );
  }
  if (tone === "info") {
    return (
      <div
        className="rounded-2xl bg-[rgba(58,124,165,0.1)] px-4 py-3 text-sm text-[var(--accent-info)]"
        {...liveProps}
      >
        {message}
      </div>
    );
  }
  return <div className="panel-muted px-4 py-5 text-sm text-[var(--text-secondary)]">{message}</div>;
}
