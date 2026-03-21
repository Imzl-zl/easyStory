"use client";

export function EngineBlock({
  title,
  children,
}: Readonly<{
  title: string;
  children: React.ReactNode;
}>) {
  return (
    <div className="panel-muted space-y-4 p-5">
      <h2 className="font-serif text-lg font-semibold">{title}</h2>
      {children}
    </div>
  );
}
