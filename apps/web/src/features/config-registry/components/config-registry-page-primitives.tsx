"use client";

import { startTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

export function ConfigRegistryProtectedLink({
  href,
  isDirty,
  label,
  onNavigate,
}: Readonly<{
  href: string;
  isDirty: boolean;
  label: string;
  onNavigate: (onConfirm: () => void) => void;
}>) {
  const router = useRouter();

  return (
    <Link
      className="ink-button-secondary"
      href={href}
      onClick={(event) => {
        if (!isDirty || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
          return;
        }
        event.preventDefault();
        onNavigate(() => {
          startTransition(() => {
            router.push(href);
          });
        });
      }}
    >
      {label}
    </Link>
  );
}

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
