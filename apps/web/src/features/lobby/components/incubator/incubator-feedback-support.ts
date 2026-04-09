"use client";

import { getErrorMessage } from "@/lib/api/client";

export type FeedbackState = {
  tone: "info" | "danger";
  message: string;
};

export function buildInfoFeedback(message: string): FeedbackState {
  return { tone: "info", message };
}

export function buildErrorFeedback(error: unknown): FeedbackState {
  return { tone: "danger", message: getErrorMessage(error) };
}
