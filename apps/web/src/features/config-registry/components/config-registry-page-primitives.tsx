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
        className="rounded-2xl bg-accent-danger/10 px-4 py-3 text-sm text-accent-danger"
        {...liveProps}
      >
        {message}
      </div>
    );
  }
  if (tone === "info") {
    return (
      <div
        className="callout-info px-4 py-3 text-sm text-accent-info"
        {...liveProps}
      >
        {message}
      </div>
    );
  }
  return <div className="panel-muted px-4 py-5 text-sm text-text-secondary">{message}</div>;
}
