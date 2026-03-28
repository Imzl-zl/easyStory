"use client";

export function ProjectSettingField({
  children,
  label,
}: Readonly<{
  children: React.ReactNode;
  label: string;
}>) {
  return (
    <label className="block space-y-2">
      <span className="label-text">{label}</span>
      {children}
    </label>
  );
}
