import { clsx } from "clsx";

type MetricCardProps = {
  label: string;
  value: React.ReactNode;
  detail?: string;
  className?: string;
};

export function MetricCard({ label, value, detail, className }: MetricCardProps) {
  return (
    <div
      className={clsx(
        "grid min-w-[118px] gap-1.5 rounded-2xl bg-muted px-4 py-3.5 shadow-sm",
        className,
      )}
    >
      <span className="text-text-tertiary text-[0.68rem] font-semibold tracking-[0.14em] uppercase">
        {label}
      </span>
      <strong className="text-text-primary text-[1.3rem] font-semibold [font-variant-numeric:tabular-nums] tracking-[-0.03em]">
        {value}
      </strong>
      {detail ? (
        <span className="text-text-secondary text-[0.82rem] leading-relaxed">{detail}</span>
      ) : null}
    </div>
  );
}
