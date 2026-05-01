"use client";

export function EngineBlock({
  title,
  children,
}: Readonly<{
  title: string;
  children: React.ReactNode;
}>) {
  return (
    <div className="space-y-3">
      <h2 className="text-[13px] font-semibold" style={{ color: "var(--text-secondary)" }}>
        {title}
      </h2>
      {children}
    </div>
  );
}
