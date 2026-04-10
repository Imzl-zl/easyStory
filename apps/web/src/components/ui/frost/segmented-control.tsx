"use client";

import { useId, useRef, useState } from "react";
import { cn } from "@/lib/utils/cn";

type SegmentedControlOption = {
  label: string;
  value: string;
};

type SegmentedControlProps = {
  className?: string;
  onChange: (value: string) => void;
  options: SegmentedControlOption[];
  value: string;
};

export function SegmentedControl({
  className,
  onChange,
  options,
  value,
}: SegmentedControlProps) {
  const controlId = useId();
  const containerRef = useRef<HTMLDivElement>(null);
  const [indicatorStyle, setIndicatorStyle] = useState<React.CSSProperties>({});

  const updateIndicator = (activeIndex: number) => {
    const container = containerRef.current;
    if (!container) return;
    const buttons = container.querySelectorAll<HTMLButtonElement>("[data-segment-btn]");
    const activeBtn = buttons[activeIndex];
    if (!activeBtn) return;

    setIndicatorStyle({
      width: activeBtn.offsetWidth,
      transform: `translateX(${activeBtn.offsetLeft - container.firstElementChild!.clientWidth > 0 ? activeBtn.offsetLeft : activeBtn.offsetLeft}px)`,
      left: 0,
    });
  };

  const activeIndex = options.findIndex((opt) => opt.value === value);

  const handleSelect = (option: SegmentedControlOption, index: number) => {
    updateIndicator(index);
    onChange(option.value);
  };

  return (
    <div
      className={cn(
        "relative inline-flex items-center gap-0.5 p-[3px]",
        "bg-muted rounded-pill",
        className,
      )}
      ref={containerRef}
      role="radiogroup"
    >
      <div
        className="absolute top-[3px] h-[calc(100%-6px)] rounded-pill bg-surface shadow-sm border border-line-soft/50 transition-all duration-smooth ease-[cubic-bezier(0.4,0,0.2,1)]"
        style={indicatorStyle}
      />
      {options.map((option, index) => {
        const isActive = option.value === value;
        return (
          <button
            aria-checked={isActive}
            className={cn(
              "relative z-10 inline-flex items-center justify-center",
              "h-7 px-3.5 rounded-pill",
              "text-[12px] font-medium leading-none tracking-[-0.01em]",
              "whitespace-nowrap cursor-pointer select-none",
              "transition-colors duration-fast",
              isActive
                ? "text-text-primary"
                : "text-text-tertiary hover:text-text-secondary",
            )}
            data-segment-btn=""
            key={`${controlId}-${option.value}`}
            onClick={() => handleSelect(option, index)}
            role="radio"
            type="button"
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
