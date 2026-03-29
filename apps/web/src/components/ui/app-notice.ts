"use client";

import { Notification } from "@arco-design/web-react";

export type AppNoticeTone = "success" | "info" | "warning" | "danger";

type ShowAppNoticeOptions = {
  content: string;
  duration?: number;
  title?: string;
  tone: AppNoticeTone;
};

const NOTICE_TITLE_BY_TONE: Record<AppNoticeTone, string> = {
  success: "操作成功",
  info: "提示",
  warning: "请注意",
  danger: "操作失败",
};

const NOTICE_DURATION_BY_TONE: Record<AppNoticeTone, number> = {
  success: 2800,
  info: 3200,
  warning: 4200,
  danger: 5200,
};

export function showAppNotice({
  content,
  duration,
  title,
  tone,
}: Readonly<ShowAppNoticeOptions>) {
  const normalizedContent = content.trim();
  if (!normalizedContent) {
    return;
  }

  const notify = resolveNoticeSender(tone);
  notify({
    closable: true,
    content: normalizedContent,
    duration: duration ?? NOTICE_DURATION_BY_TONE[tone],
    position: "topRight",
    showIcon: true,
    title: title ?? NOTICE_TITLE_BY_TONE[tone],
  });
}

function resolveNoticeSender(tone: AppNoticeTone) {
  if (tone === "success") {
    return Notification.success;
  }
  if (tone === "warning") {
    return Notification.warning;
  }
  if (tone === "danger") {
    return Notification.error;
  }
  return Notification.info;
}
