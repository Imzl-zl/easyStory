import type { LabFeedback } from "@/features/lab/components/lab-support";

type LabFeedbackBannerProps = {
  feedback: LabFeedback;
};

export function LabFeedbackBanner({ feedback }: Readonly<LabFeedbackBannerProps>) {
  if (!feedback) {
    return null;
  }
  if (feedback.tone === "danger") {
    return (
      <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
        {feedback.message}
      </div>
    );
  }
  return (
    <div className="rounded-2xl bg-[rgba(58,124,165,0.1)] px-4 py-3 text-sm text-[var(--accent-info)]">
      {feedback.message}
    </div>
  );
}
