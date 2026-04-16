"use client";

export function ProjectSettingsTabButton({
  active,
  description,
  disabled,
  label,
  onClick,
}: Readonly<{
  active: boolean;
  description: string;
  disabled: boolean;
  label: string;
  onClick: () => void;
}>) {
  return (
    <button
      className="ink-tab w-full justify-start rounded-2xl px-4 py-3 text-left"
      data-active={active}
      disabled={disabled}
      onClick={onClick}
      type="button"
    >
      <span className="flex flex-col items-start gap-1">
        <span className="text-sm font-medium text-text-primary">{label}</span>
        <span className="text-[12px] leading-5 text-text-secondary">{description}</span>
      </span>
    </button>
  );
}
