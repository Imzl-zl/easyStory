"use client";

import type { ReactNode } from "react";

export function RequestStateCard({
  title,
  message,
  actions,
}: {
  title: string;
  message: string;
  actions?: ReactNode;
}) {
  return (
    <div className="panel-muted space-y-4 p-5">
      <div className="space-y-1">
        <h3 className="font-serif text-lg font-semibold">{title}</h3>
        <p className="text-sm leading-6 text-accent-danger">{message}</p>
      </div>
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </div>
  );
}

export function RequestStateInline({
  message,
  action,
}: {
  message: string;
  action?: ReactNode;
}) {
  return (
    <div className="space-y-3 rounded-2xl bg-accent-danger/10 px-4 py-3 text-sm text-accent-danger">
      <p>{message}</p>
      {action}
    </div>
  );
}
